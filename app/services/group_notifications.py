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

from app.services.neptun_locations import (
    find_city_location,
    find_raion,
)

from app.utils.weather_icons import get_weather_icon


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

async def send_to_group(
    bot: Bot,
    text: str,
):

    try:

        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML",
        )

        print(
            "✅ Повідомлення відправлено в групу"
        )

    except Exception as e:

        print(
            f"❌ Помилка відправки в групу: {e}"
        )


# =====================================================
# ЛОКАЦІЇ ДЛЯ МОНІТОРИНГУ
# =====================================================

def get_users_locations():

    try:

        conn = sqlite3.connect(
            "app/database/users.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT
                location_key,
                location_name,
                location_oblast
            FROM users
            WHERE location_key IS NOT NULL
              AND location_key != ''
        """)

        rows = cursor.fetchall()

        conn.close()

        locations = []

        for row in rows:

            location_key = row[0]
            location_name = row[1]
            location_oblast = row[2]

            if not location_key:
                continue

            locations.append({
                "key": location_key,
                "name": (
                    location_name
                    or location_key
                ),
                "oblast": (
                    location_oblast
                    or ""
                ),
            })

        return locations

    except Exception as e:

        print(
            f"❌ Помилка отримання локацій: {e}"
        )

        return []


# =====================================================
# СУМІСНІСТЬ
# =====================================================

def get_users_cities():

    return get_users_locations()


# =====================================================
# НОРМАЛІЗАЦІЯ
# =====================================================

def normalize(value):

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


# =====================================================
# ІКОНКА ЗАГРОЗИ
# =====================================================

def get_threat_icon(
    threat_type,
):

    return {
        "uav": "🛸",
        "missile": "🚀",
        "ballistic": "💥",
        "kab": "💣",
        "mig31k": "✈️",
        "recon": "👀",
        "fpv": "🛸",
        "unknown": "❓",
    }.get(
        normalize(threat_type),
        "❓",
    )


# =====================================================
# ІНФОРМАЦІЯ ПРО ЛОКАЦІЮ
# =====================================================

def get_location_info(location):

    if not location:
        return None

    location_key = normalize(
        location.get("key")
    )

    location_name = (
        location.get("name")
        or ""
    )

    # Київ
    if location_key == "kyiv-city":

        return {
            "type": "city",
            "key": "kyiv-city",
            "name": "Київ",
            "raion_key": None,
            "raion_name": None,
            "oblast_key": "kyiv-city",
            "oblast_name": "Київ",
        }

    # Район
    try:

        raion = find_raion(
            location_key
        )

    except Exception:

        raion = None

    if raion:

        return {
            "type": "raion",
            "key": raion.get("key"),
            "name": (
                location_name
                or raion.get("name")
            ),
            "raion_key": raion.get("key"),
            "raion_name": raion.get("name"),
            "oblast_key": raion.get("oblast_key"),
            "oblast_name": raion.get("oblast_name"),
        }

    # Місто
    try:

        city = find_city_location(
            location_name
        )

    except Exception:

        city = None

    if city:

        return {
            "type": "city",
            "key": city.get("key"),
            "name": city.get("name"),
            "raion_key": city.get("raion_key"),
            "raion_name": city.get("raion_name"),
            "oblast_key": city.get("oblast_key"),
            "oblast_name": city.get("oblast_name"),
            "latitude": city.get("latitude"),
            "longitude": city.get("longitude"),
        }

    return {
        "type": "unknown",
        "key": location_key,
        "name": location_name,
        "raion_key": None,
        "raion_name": None,
        "oblast_key": None,
        "oblast_name": location.get("oblast"),
    }


# =====================================================
# ПЕРЕВІРКА ТРИВОГИ
# =====================================================

def is_location_alert_active(
    location,
    data,
):

    if not data:
        return False

    info = get_location_info(
        location
    )

    if not info:
        return False

    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )

    # -------------------------------------------------
    # КИЇВ
    # -------------------------------------------------

    if info["key"] == "kyiv-city":

        for item in raions + oblasts:

            key = normalize(
                item.get("key")
            )

            name = normalize(
                item.get("name")
            )

            if key in (
                "kyiv",
                "м. київ",
                "місто київ",
            ):
                return True

            if name in (
                "київ",
                "м. київ",
                "місто київ",
            ):
                return True

        return False

    # -------------------------------------------------
    # КОНКРЕТНИЙ РАЙОН
    # -------------------------------------------------

    target_raion = normalize(
        info.get("raion_key")
    )

    if target_raion:

        for item in raions:

            item_key = normalize(
                item.get("key")
            )

            if item_key == target_raion:

                return True

        return False

    return False


# =====================================================
# ЗАГРОЗИ ДЛЯ ПРИЧИНИ ТРИВОГИ
# =====================================================

def get_location_threats(
    location,
    data,
):

    if not data:
        return []

    threats = data.get(
        "threats",
        []
    )

    if not threats:
        return []

    info = get_location_info(
        location
    )

    if not info:
        return []

    result = []

    target_raion = normalize(
        info.get("raion_name")
    )

    target_city = normalize(
        info.get("name")
    )

    for threat in threats:

        status = normalize(
            threat.get("status")
        )

        if status not in (
            "",
            "active",
        ):
            continue

        district = normalize(
            threat.get("district")
        )

        locality = normalize(
            threat.get("locality")
        )

        # Точний район
        if (
            target_raion
            and target_raion in district
        ):

            result.append(
                threat
            )

            continue

        # Точний населений пункт
        if (
            target_city
            and locality
            and locality == target_city
        ):

            result.append(
                threat
            )

            continue

        # Київ
        if info["key"] == "kyiv-city":

            if locality in (
                "київ",
                "м. київ",
                "місто київ",
            ):

                result.append(
                    threat
                )

    return result


# =====================================================
# ПОЧАТОК ТРИВОГИ
# =====================================================

def format_alert_start(
    location,
    threats,
):

    name = (
        location.get("name")
        or "Невідома локація"
    )

    text = (
        "🚨 <b>ПОВІТРЯНА ТРИВОГА</b>\n\n"
        f"📍 <b>{name.upper()}</b>\n\n"
    )

    if threats:

        text += (
            "⚠️ <b>Причина:</b>\n"
        )

        seen = set()

        for threat in threats:

            title = (
                threat.get("title")
                or "Невідома загроза"
            )

            explanation = (
                threat.get(
                    "explanationShort"
                )
                or ""
            )

            unique_key = (
                f"{title}|{explanation}"
            )

            if unique_key in seen:
                continue

            seen.add(
                unique_key
            )

            icon = get_threat_icon(
                threat.get("type")
            )

            text += (
                f"{icon} <b>{title}</b>"
            )

            if explanation:

                text += (
                    f" — {explanation}"
                )

            text += "\n"

    else:

        text += (
            "⚠️ Причина уточнюється.\n"
            "Негайно перейдіть у безпечне місце."
        )

    return text


# =====================================================
# ВІДБІЙ
# =====================================================

def format_alert_end(
    location,
):

    name = (
        location.get("name")
        or "Невідома локація"
    )

    return (
        "🟢 <b>ВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
        f"📍 <b>{name.upper()}</b>\n\n"
        "✅ Небезпека минула."
    )


# =====================================================
# МОНІТОР ТРИВОГ
#
# ПОЧАТОК → 1 повідомлення
# ТРИВАЄ → НІЧОГО
# НОВА ЗАГРОЗА → НІЧОГО
# ЗМІНА ЗАГРОЗИ → НІЧОГО
# ВІДБІЙ → 1 повідомлення
#
# АВТОМАТИЧНИХ ПОВІДОМЛЕНЬ
# ПРО ЗАГРОЗИ НЕМАЄ.
# =====================================================

async def group_alert_monitor(
    bot: Bot,
):

    print(
        "🚨 Моніторинг тривог запущений"
    )

    while True:

        try:

            locations = await asyncio.to_thread(
                get_users_locations
            )

            if not locations:

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

                continue

            alerts_data = await asyncio.to_thread(
                get_alerts
            )

            if not alerts_data:

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

                continue

            for location in locations:

                location_key = (
                    location["key"]
                )

                alert_active = (
                    is_location_alert_active(
                        location,
                        alerts_data,
                    )
                )

                previous_state = (
                    _last_alert_states.get(
                        location_key
                    )
                )

                # =====================================
                # ПЕРШИЙ ЗАПУСК
                # =====================================

                if previous_state is None:

                    _last_alert_states[
                        location_key
                    ] = alert_active

                    print(
                        f"📡 Початковий стан "
                        f"{location['name']}: "
                        f"тривога={alert_active}"
                    )

                    continue

                # =====================================
                # ПОЧАТОК
                # =====================================

                if (
                    alert_active
                    and not previous_state
                ):

                    threats_data = (
                        await asyncio.to_thread(
                            get_threats
                        )
                    )

                    location_threats = (
                        get_location_threats(
                            location,
                            threats_data,
                        )
                        if threats_data
                        else []
                    )

                    await send_to_group(
                        bot,
                        format_alert_start(
                            location,
                            location_threats,
                        ),
                    )

                    _last_alert_states[
                        location_key
                    ] = True

                    print(
                        f"🚨 Почалася тривога: "
                        f"{location['name']}"
                    )

                # =====================================
                # ВІДБІЙ
                # =====================================

                elif (
                    not alert_active
                    and previous_state
                ):

                    await send_to_group(
                        bot,
                        format_alert_end(
                            location
                        ),
                    )

                    _last_alert_states[
                        location_key
                    ] = False

                    print(
                        f"🟢 Відбій: "
                        f"{location['name']}"
                    )

        except Exception as e:

            print(
                f"❌ Помилка моніторингу: {e}"
            )

        await asyncio.sleep(
            CHECK_INTERVAL
        )


# =====================================================
# РАНКОВИЙ ЖАРТ
# =====================================================

def get_morning_joke():

    try:

        joke = ai_joke.get_joke()

        if joke:
            return joke

    except Exception as e:

        print(
            f"❌ Помилка отримання жарту: {e}"
        )

    return (
        "☀️ Доброго ранку! "
        "Нехай сьогодні все працює "
        "з першого разу 😎"
    )


# =====================================================
# РАНКОВА ПОГОДА
# =====================================================

async def send_morning_weather(
    bot: Bot,
):

    print(
        "🌅 Формування ранкової погоди..."
    )

    try:

        conn = sqlite3.connect(
            "app/database/users.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT city
            FROM users
            WHERE city IS NOT NULL
              AND city != ''
        """)

        rows = cursor.fetchall()

        conn.close()

        cities = [
            row[0]
            for row in rows
            if row[0]
        ]

        if not cities:

            print(
                "ℹ️ Немає міст для ранкової погоди"
            )

            return

        sent_cities = set()

        for city in cities:

            if city in sent_cities:
                continue

            sent_cities.add(
                city
            )

            try:

                weather = await asyncio.to_thread(
                    get_weather,
                    city,
                )

                if not weather:
                    continue

                advice = ""

                try:

                    advice_result = get_advice(
                        weather
                    )

                    if advice_result:

                        advice = (
                            f"\n\n💡 "
                            f"{advice_result}"
                        )

                except Exception as e:

                    print(
                        f"⚠️ Помилка поради: {e}"
                    )

                icon = get_weather_icon(
                    weather.get(
                        "weather"
                    )
                )

                text = (
                    "🌅 <b>Доброго ранку!</b>\n\n"
                    f"📍 <b>{city}</b>\n\n"
                    f"{icon} "
                    f"{weather.get('description', '')}\n"
                    f"🌡 Температура: "
                    f"{weather.get('temperature', '—')}°C\n"
                    f"💨 Вітер: "
                    f"{weather.get('wind_speed', '—')} м/с\n"
                    f"💧 Вологість: "
                    f"{weather.get('humidity', '—')}%"
                    f"{advice}"
                )

                await send_to_group(
                    bot,
                    text,
                )

                await asyncio.sleep(
                    1
                )

            except Exception as e:

                print(
                    f"❌ Помилка погоди "
                    f"{city}: {e}"
                )

    except Exception as e:

        print(
            f"❌ Помилка ранкової погоди: {e}"
        )


# =====================================================
# ПЛАНУВАЛЬНИК РАНКОВОЇ ПОГОДИ
# =====================================================

async def morning_weather_scheduler(
    bot: Bot,
):

    print(
        "🌅 Планувальник ранкової погоди запущений"
    )

    while True:

        try:

            now = datetime.now(
                KYIV_TIMEZONE
            )

            next_run = now.replace(
                hour=8,
                minute=0,
                second=0,
                microsecond=0,
            )

            if next_run <= now:

                next_run += timedelta(
                    days=1
                )

            wait_seconds = (
                next_run - now
            ).total_seconds()

            print(
                "⏰ Наступна ранкова погода: "
                f"{next_run.strftime('%d.%m.%Y %H:%M')}"
            )

            await asyncio.sleep(
                wait_seconds
            )

            await send_morning_weather(
                bot
            )

        except asyncio.CancelledError:

            print(
                "🌅 Планувальник ранкової погоди зупинений"
            )

            raise

        except Exception as e:

            print(
                f"❌ Помилка планувальника: {e}"
            )

            await asyncio.sleep(
                60
            )