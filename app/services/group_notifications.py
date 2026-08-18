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

THREAT_RADIUS_KM = 70


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

        print("✅ Повідомлення відправлено в групу")

    except Exception as e:
        print(f"❌ Помилка відправки в групу: {e}")


# =====================================================
# НОРМАЛІЗАЦІЯ
# =====================================================

def normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


# =====================================================
# ЛОКАЦІЇ ДЛЯ МОНІТОРИНГУ
#
# Нові записи:
#   location_key / location_name / location_oblast
#
# Старі записи:
#   city
#
# Якщо нової локації немає, використовуємо city
# і шукаємо місто через Neptun.
# =====================================================

def get_users_locations():
    try:
        conn = sqlite3.connect(
            "app/database/users.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                telegram_id,
                city,
                location_key,
                location_name,
                location_oblast
            FROM users
        """)

        rows = cursor.fetchall()
        conn.close()

        locations = []
        seen = set()

        for row in rows:
            telegram_id = row[0]
            legacy_city = row[1]
            location_key = row[2]
            location_name = row[3]
            location_oblast = row[4]

            # =================================================
            # НОВА ЛОКАЦІЯ
            # =================================================

            if location_key:
                key = normalize(location_key)

                if not key:
                    continue

                if key in seen:
                    continue

                seen.add(key)

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

                continue

            # =================================================
            # СТАРИЙ ФОРМАТ — МІСТО
            # =================================================

            if legacy_city:
                try:
                    city_location = find_city_location(
                        legacy_city
                    )
                except Exception as e:
                    print(
                        f"⚠️ Neptun legacy lookup "
                        f"{legacy_city}: {e}"
                    )
                    city_location = None

                if city_location:
                    key = normalize(
                        city_location.get("key")
                    )

                    if not key or key in seen:
                        continue

                    seen.add(key)

                    location = {
                        "key": city_location.get("key"),
                        "name": (
                            city_location.get("name")
                            or legacy_city
                        ),
                        "oblast": (
                            city_location.get("oblast_name")
                            or ""
                        ),
                    }

                    locations.append(location)

                    print(
                        f"📍 LEGACY LOCATION | "
                        f"user={telegram_id} | "
                        f"{legacy_city} → {location['key']}"
                    )

                else:
                    print(
                        f"⚠️ Не знайдено місто "
                        f"через Neptun: {legacy_city}"
                    )

        print(
            f"📡 Локацій для моніторингу: "
            f"{len(locations)}"
        )

        for location in locations:
            print(
                f"   📍 {location['name']} "
                f"→ {location['key']} "
                f"({location['oblast']})"
            )

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

    # =================================================
    # КИЇВ
    # =================================================

    if location_key in (
        "kyiv-city",
        "київ",
        "kyiv",
    ):
        return {
            "type": "city",
            "key": "kyiv-city",
            "name": "Київ",
            "raion_key": None,
            "raion_name": None,
            "oblast_key": "kyiv-city",
            "oblast_name": "Київ",
        }

    # =================================================
    # РАЙОН
    # =================================================

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

    # =================================================
    # МІСТО
    # =================================================

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

    # =================================================
    # НЕВІДОМА ЛОКАЦІЯ
    # =================================================

    return {
        "type": "unknown",
        "key": location_key,
        "name": location_name,
        "raion_key": None,
        "raion_name": None,
        "oblast_key": None,
        "oblast_name": (
            location.get("oblast")
            or ""
        ),
    }


# =====================================================
# ПЕРЕВІРКА ТРИВОГИ
#
# Для міста:
#   перевіряємо саме його район.
#
# Для району:
#   перевіряємо саме цей район.
#
# Область сама по собі НЕ робить тривогу
# в конкретному місті активною.
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

    # =================================================
    # КИЇВ
    # =================================================

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
                "kyiv-city",
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

    # =================================================
    # КОНКРЕТНИЙ РАЙОН
    # =================================================

    target_raion_key = normalize(
        info.get("raion_key")
    )

    target_raion_name = normalize(
        info.get("raion_name")
    )

    if target_raion_key:
        for item in raions:
            item_key = normalize(
                item.get("key")
            )

            item_name = normalize(
                item.get("name")
            )

            if item_key == target_raion_key:
                return True

            if (
                target_raion_name
                and item_name == target_raion_name
            ):
                return True

        return False

    # =================================================
    # ЯКЩО NEPTUN НЕ ДАВ РАЙОН
    #
    # Перевіряємо точний населений пункт.
    # Область автоматично не вважаємо тривогою.
    # =================================================

    target_city = normalize(
        info.get("name")
    )

    for item in raions + oblasts:
        item_key = normalize(
            item.get("key")
        )

        item_name = normalize(
            item.get("name")
        )

        if target_city and (
            item_key == target_city
            or item_name == target_city
        ):
            return True

    return False


# =====================================================
# ВІДСТАНЬ
# =====================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    from math import (
        radians,
        sin,
        cos,
        asin,
        sqrt,
    )

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

    except (
        TypeError,
        ValueError,
    ):
        return None

    earth_radius = 6371.0

    dlat = radians(
        lat2 - lat1
    )

    dlon = radians(
        lon2 - lon1
    )

    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return (
        2
        * earth_radius
        * asin(
            sqrt(a)
        )
    )


# =====================================================
# КООРДИНАТИ ЛОКАЦІЇ
# =====================================================

def get_location_coordinates(
    location,
):
    if not location:
        return None, None

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    if latitude is None:
        latitude = location.get(
            "lat"
        )

    if longitude is None:
        longitude = location.get(
            "lon"
        )

    # Координати вже є
    if (
        latitude is not None
        and longitude is not None
    ):
        try:
            return (
                float(latitude),
                float(longitude),
            )
        except (
            TypeError,
            ValueError,
        ):
            pass

    name = (
        location.get("name")
        or ""
    )

    if not name:
        return None, None

    try:
        city = find_city_location(
            name
        )

        if city:
            latitude = city.get(
                "latitude"
            )

            longitude = city.get(
                "longitude"
            )

            if (
                latitude is not None
                and longitude is not None
            ):
                return (
                    float(latitude),
                    float(longitude),
                )

    except Exception as e:
        print(
            f"⚠️ Помилка отримання "
            f"координат {name}: {e}"
        )

    return None, None


# =====================================================
# ЗАГРОЗИ ПОБЛИЗУ ЛОКАЦІЇ
#
# Реальні дані Threats API
# + координати Neptun
# + радіус 70 км
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

    latitude, longitude = (
        get_location_coordinates(
            location
        )
    )

    if (
        latitude is None
        or longitude is None
    ):
        print(
            f"⚠️ Немає координат для "
            f"{location.get('name')}"
        )

        return []

    print(
        f"📍 ALERT THREAT LOCATION | "
        f"{location.get('name')} | "
        f"{latitude}, {longitude}"
    )

    result = []

    for threat in threats:
        if not isinstance(
            threat,
            dict,
        ):
            continue

        status = normalize(
            threat.get("status")
        )

        if status not in (
            "active",
            "activated",
            "stale",
        ):
            continue

        threat_lat = threat.get(
            "latitude"
        )

        if threat_lat is None:
            threat_lat = threat.get(
                "lat"
            )

        threat_lon = threat.get(
            "longitude"
        )

        if threat_lon is None:
            threat_lon = threat.get(
                "lon"
            )

        if (
            threat_lat is None
            or threat_lon is None
        ):
            continue

        try:
            threat_lat = float(
                threat_lat
            )

            threat_lon = float(
                threat_lon
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        distance = distance_km(
            latitude,
            longitude,
            threat_lat,
            threat_lon,
        )

        if distance is None:
            continue

        if distance > THREAT_RADIUS_KM:
            continue

        threat_copy = dict(
            threat
        )

        threat_copy[
            "_distance_km"
        ] = distance

        result.append(
            threat_copy
        )

        print(
            f"🎯 THREAT NEAR "
            f"{location.get('name')}: "
            f"{threat.get('title')} | "
            f"{threat.get('locality')} | "
            f"{distance:.1f} км"
        )

    result.sort(
        key=lambda item: item.get(
            "_distance_km",
            999999,
        )
    )

    unique = []
    seen = set()

    for threat in result:
        threat_id = (
            threat.get("id")
            or (
                threat.get("title"),
                threat.get("locality"),
                threat.get("lat"),
                threat.get("lon"),
            )
        )

        if threat_id in seen:
            continue

        seen.add(
            threat_id
        )

        unique.append(
            threat
        )

    print(
        f"📡 Загроз поблизу "
        f"{location.get('name')}: "
        f"{len(unique)}"
    )

    return unique


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
        f"📍 <b>{name.upper()}</b>\n"
    )

    if threats:
        text += "\n⚠️ <b>Конкретні загрози поблизу:</b>\n"

        seen = set()

        for threat in threats:
            title = (
                threat.get("title")
                or "Невідома загроза"
            )

            locality = (
                threat.get("locality")
                or ""
            )

            distance = threat.get(
                "_distance_km"
            )

            explanation = (
                threat.get(
                    "explanationShort"
                )
                or ""
            )

            unique_key = (
                threat.get("id")
                or (
                    title,
                    locality,
                    threat.get("lat"),
                    threat.get("lon"),
                )
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

            if locality:
                text += (
                    f" — {locality}"
                )

            if distance is not None:
                text += (
                    f" ({distance:.1f} км)"
                )

            if explanation:
                text += (
                    f"\n   {explanation}"
                )

            text += "\n"

    else:
        text += (
            "\n⚠️ <b>Конкретна загроза "
            "поблизу не визначена.</b>\n"
            "Тривога підтверджена даними Alerts API.\n"
        )

    text += (
        "\n🛡 <b>Негайно перейдіть "
        "у безпечне місце.</b>"
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
# ПЕРШИЙ ЗАПУСК:
#   стан запам'ятовується без повідомлення.
#
# ПОЧАТОК:
#   False → True = 1 повідомлення.
#
# ТРИВАЄ:
#   True → True = нічого.
#
# ВІДБІЙ:
#   True → False = 1 повідомлення.
#
# НОВА ЗАГРОЗА ПІД ЧАС ТРИВОГИ:
#   не надсилаємо окремого повідомлення.
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
                print(
                    "📡 Немає локацій для моніторингу"
                )

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

                continue

            alerts_data = await asyncio.to_thread(
                get_alerts
            )

            if not alerts_data:
                print(
                    "⚠️ API тривог не повернув дані"
                )

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

                continue

            current_keys = set()

            for location in locations:
                location_key = normalize(
                    location.get("key")
                )

                if not location_key:
                    continue

                current_keys.add(
                    location_key
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

                print(
                    f"📡 ALERT CHECK | "
                    f"{location.get('name')} | "
                    f"active={alert_active} | "
                    f"previous={previous_state}"
                )

                # =================================================
                # ПЕРШИЙ ЗАПУСК
                # =================================================

                if previous_state is None:
                    _last_alert_states[
                        location_key
                    ] = alert_active

                    print(
                        f"📡 Початковий стан "
                        f"{location.get('name')}: "
                        f"тривога={alert_active}"
                    )

                    continue

                # =================================================
                # ПОЧАТОК ТРИВОГИ
                # =================================================

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
                        f"🚨 ПОЧАЛАСЯ ТРИВОГА: "
                        f"{location.get('name')}"
                    )

                # =================================================
                # ВІДБІЙ
                # =================================================

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
                        f"🟢 ВІДБІЙ: "
                        f"{location.get('name')}"
                    )

                # =================================================
                # СТАН НЕ ЗМІНИВСЯ
                # =================================================

                else:
                    _last_alert_states[
                        location_key
                    ] = alert_active

            # =================================================
            # ВИДАЛЯЄМО СТАРІ ЛОКАЦІЇ
            # =================================================

            for key in list(
                _last_alert_states.keys()
            ):
                if key not in current_keys:
                    del _last_alert_states[
                        key
                    ]

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

            sent_cities.add(city)

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

                await asyncio.sleep(1)

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