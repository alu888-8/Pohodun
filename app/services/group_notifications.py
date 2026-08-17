import asyncio
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.services.alerts import get_alerts
from app.services.threats import get_threats
from app.services.weather import get_weather
from app.services.advice import get_advice
from app.services import ai_joke
from app.services.neptun_locations import find_city_location

from app.utils.weather_icons import get_weather_icon
from app.data.regions import CITY_REGIONS

# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

GROUP_CHAT_ID = -493936504
KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")
CHECK_INTERVAL = 10

# =====================================================
# СТАН ТРИВОГ
# =====================================================

_last_alert_states = {}

# =====================================================
# ВІДПРАВКА В ГРУПУ
# =====================================================

async def send_to_group(bot: Bot, text: str):
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
        print("✅ Повідомлення відправлено в групу")
    except Exception as e:
        print(f"❌ Помилка відправки в групу: {e}")

# =====================================================
# МІСТА КОРИСТУВАЧІВ
# =====================================================

def get_users_cities():
    try:
        conn = sqlite3.connect("app/database/users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM users")
        rows = cursor.fetchall()
        conn.close()
        
        cities = []
        for row in rows:
            if row[0]:
                cities.append(row[0])
        return cities
    except Exception as e:
        print(f"❌ Помилка отримання міст: {e}")
        return []

# =====================================================
# НОРМАЛІЗАЦІЯ ТЕКСТУ
# =====================================================

def normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()

# =====================================================
# ІКОНКА ЗАГРОЗИ
# =====================================================

def get_threat_icon(threat_type):
    return {
        "uav": "🛸",
        "missile": "🚀",
        "ballistic": "💥",
        "kab": "💣",
        "mig31k": "✈️",
        "recon": "👀",
        "unknown": "❓"
    }.get(normalize(threat_type), "❓")

# =====================================================
# ПЕРЕВІРКА ТРИВОГИ ДЛЯ МІСТА (Точна + Резервна)
# =====================================================

def is_city_alert_active(city, data):
    if not data:
        return False

    raions = data.get("raions", [])
    oblasts = data.get("oblasts", [])

    # Специфіка для Києва
    if city == "Київ":
        for item in raions + oblasts:
            name = normalize(item.get("name"))
            key = normalize(item.get("key"))
            if name in ("київ", "м. київ", "місто київ") or key in ("київ", "м. київ", "місто київ"):
                return True
        return False

    # 1. Пошук через точні геодані Neptun
    location_data = find_city_location(city)
    if location_data:
        target_raion = normalize(location_data.get("raion_name"))
        target_oblast = normalize(location_data.get("oblast_name"))
        
        for item in raions + oblasts:
            item_name = normalize(item.get("name"))
            if item_name and (item_name == target_raion or item_name == target_oblast):
                return True

    # 2. Резервний пошук (якщо геодані не спрацювали)
    city_normalized = normalize(city)
    keywords = CITY_REGIONS.get(city, [city_normalized])
    keywords = [normalize(word) for word in keywords]

    for item in raions + oblasts:
        name = normalize(item.get("name"))
        key = normalize(item.get("key"))
        oblast = normalize(item.get("oblast"))
        
        if name in (city_normalized, f"м. {city_normalized}", f"місто {city_normalized}") or key in (city_normalized, f"м. {city_normalized}"):
            return True
            
        search_text = f"{name} {oblast}"
        if any(word in search_text for word in keywords if word):
            return True

    return False

# =====================================================
# ОТРИМАТИ ЗАГРОЗИ ДЛЯ МІСТА
# =====================================================

def get_city_threats(city, data):
    if not data:
        return []

    threats = data.get("threats", [])
    if not threats:
        return []

    result = []
    
    # 1. Спроба через точні геодані
    location_data = find_city_location(city)
    target_raion = normalize(location_data.get("raion_name")) if location_data else ""
    target_oblast = normalize(location_data.get("oblast_name")) if location_data else ""

    keywords = CITY_REGIONS.get(city, [normalize(city)])
    keywords = [normalize(word) for word in keywords]

    if city == "Київ":
        keywords = list(set(keywords + ["київ", "м. київ", "київська область"]))

    for threat in threats:
        region = normalize(threat.get("region"))
        district = normalize(threat.get("district"))
        locality = normalize(threat.get("locality"))
        title = normalize(threat.get("title"))
        explanation = normalize(threat.get("explanationShort"))

        # Перевірка точного збігу області чи району
        if target_oblast and target_oblast in region:
            result.append(threat)
            continue
        if target_raion and target_raion in district:
            result.append(threat)
            continue

        # Резервна перевірка по ключових словах
        search_text = f"{region} {district} {locality} {title} {explanation}"
        if any(word in search_text for word in keywords if word):
            result.append(threat)

    return result

# =====================================================
# ФОРМУВАННЯ ТЕКСТІВ ТРИВОГИ
# =====================================================

def format_alert_start(city, threats):
    text = (
        "🚨 <b>ПОВІТРЯНА ТРИВОГА</b>\n\n"
        f"📍 <b>{city.upper()}</b>\n\n"
    )

    if threats:
        text += "⚠️ <b>Причина:</b>\n"
        # Використовуємо сет, щоб уникнути дублів однакових загроз
        seen_threats = set()
        for threat in threats:
            threat_type = threat.get("type")
            title = threat.get("title", "Невідома загроза") or "Невідома загроза"
            explanation = threat.get("explanationShort", "") or ""
            
            threat_key = f"{title}_{explanation}"
            if threat_key not in seen_threats:
                icon = get_threat_icon(threat_type)
                text += f"{icon} <b>{title}</b>"
                if explanation:
                    text += f" — {explanation}"
                text += "\n"
                seen_threats.add(threat_key)
    else:
        text += "⚠️ Негайно перейдіть у безпечне місце (причина уточнюється)."

    return text

def format_alert_end(city):
    return (
        "🟢 <b>ВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
        f"📍 <b>{city.upper()}</b>\n\n"
        "✅ Небезпека минула."
    )

# =====================================================
# ГОЛОВНИЙ МОНІТОР (ОДНЕ ПОВІДОМЛЕННЯ НА ТРИВОГУ)
# =====================================================

async def group_alert_monitor(bot: Bot):
    print("🚨 Моніторинг тривог запущений (без спаму)")

    while True:
        try:
            cities = await asyncio.to_thread(get_users_cities)
            if not cities:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            alerts_data = await asyncio.to_thread(get_alerts)
            if alerts_data is None:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            for city in cities:
                alert_active = is_city_alert_active(city, alerts_data)
                previous_alert = _last_alert_states.get(city)

                if previous_alert is None:
                    _last_alert_states[city] = alert_active
                    print(f"📡 Початковий стан {city}: тривога={alert_active}")
                else:
                    # ПОЧАТОК ТРИВОГИ
                    if alert_active and not previous_alert:
                        threats_data = await asyncio.to_thread(get_threats)
                        city_threats = get_city_threats(city, threats_data) if threats_data else []
                        
                        await send_to_group(bot, format_alert_start(city, city_threats))
                        _last_alert_states[city] = True
                        print(f"🚨 Почалася тривога: {city}")

                    # ВІДБІЙ
                    elif not alert_active and previous_alert:
                        await send_to_group(bot, format_alert_end(city))
                        _last_alert_states[city] = False
                        print(f"🟢 Відбій: {city}")

        except Exception as e:
            print(f"❌ Помилка моніторингу: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# =====================================================
# (РАНКОВА ПОГОДА ЗАЛИШАЄТЬСЯ БЕЗ ЗМІН)
# =====================================================

def get_morning_joke():
    for function_name in ("get_ai_joke", "get_joke", "generate_joke", "ai_joke"):
        function = getattr(ai_joke, function_name, None)
        if callable(function):
            try:
                result = function()
                if result:
                    return str(result).strip()
            except Exception as e:
                print(f"⚠️ Помилка анекдоту ({function_name}): {e}")
    return "— Офіціанте, у вас є щось від спеки?\n— Так. Рахунок."

async def send_morning_weather(bot: Bot):
    try:
        city_ua = "Київ"
        city_api = "Kyiv"
        weather = await asyncio.to_thread(get_weather, city_api)

        if weather is None:
            await send_to_group(bot, "❌ Не вдалося отримати ранкову погоду для Києва.")
            return

        temp = weather["temp"]
        feels = weather["feels_like"]
        humidity = weather["humidity"]
        wind = weather["wind"]
        description = weather["condition"]
        icon = get_weather_icon(description)

        advice = await asyncio.to_thread(get_advice, temp, description, city_ua, feels, wind, humidity)
        joke = await asyncio.to_thread(get_morning_joke)

        text = (
            f"🌅 <b>Доброго ранку!</b>\n\n"
            f"🌤 <b>Погодун — погода на ранок</b>\n\n"
            f"📍 <b>{city_ua}</b>\n\n"
            f"{icon} <b>{description}</b>\n\n"
            f"🌡 Температура: <b>{temp}°C</b>\n"
            f"🤗 Відчувається: <b>{feels}°C</b>\n"
            f"💨 Вітер: <b>{wind} м/с</b>\n"
            f"💧 Вологість: <b>{humidity}%</b>\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"👕 <b>Порада:</b>\n{advice}\n\n"
            f"😂 <b>Анекдот дня:</b>\n{joke}"
        )

        await send_to_group(bot, text)
        print("🌅 Ранкова погода відправлена")
    except Exception as e:
        print(f"❌ Помилка ранкової погоди: {e}")

async def morning_weather_scheduler(bot: Bot):
    print("🌅 Планувальник ранкової погоди запущений")
    while True:
        now = datetime.now(KYIV_TIMEZONE)
        next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
            
        wait_seconds = (next_run - now).total_seconds()
        print("⏰ Наступна погода: " + next_run.strftime("%Y-%m-%d %H:%M:%S"))
        
        await asyncio.sleep(wait_seconds)
        await send_morning_weather(bot)