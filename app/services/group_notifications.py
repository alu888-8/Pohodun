import asyncio
import re
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.handlers.threats import format_threat
from app.services.alerts import get_alerts
from app.services.threats import get_threats
from app.services.weather import get_weather
from app.services.advice import get_advice
from app.services import ai_joke
from app.services.day_facts import get_day_facts

from app.database.db import (
    get_connection,
    get_scheduler_last_run,
    set_scheduler_last_run,
)

from app.services.neptun_locations import (
    find_city_location,
    find_raion,
    find_raion_by_coordinates,
    _point_in_geometry,
)

from app.utils.weather_icons import get_weather_icon


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

GROUP_CHAT_ID = -5561223347

KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

CHECK_INTERVAL = 5

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
    # =================================================
    # ГРУПА НЕ ПІДКЛЮЧЕНА
    #
    # Стару групу відв'язано.
    # Після створення нової групи достатньо
    # вказати її chat_id у GROUP_CHAT_ID.
    # =================================================

    if not GROUP_CHAT_ID:
        print(
            "ℹ️ GROUP NOTIFICATIONS | "
            "група не підключена"
        )
        return

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
        conn = get_connection()

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

                location = {
                    "key": location_key,
                    "name": (
                        location_name
                        or location_key
                    ),
                    "oblast": (
                        location_oblast
                        or ""
                    ),
                }

                # Якщо це район — зберігаємо його дані,
                # щоб монітор і пошук загроз працювали
                # саме для вибраного району.
                try:

                    raion = find_raion(
                        location_key
                    )

                    if raion:

                        location["raion_key"] = (
                            raion.get("key")
                        )

                        location["raion_name"] = (
                            raion.get("name")
                        )

                        location["oblast_key"] = (
                            raion.get("oblast_key")
                        )

                        location["oblast_name"] = (
                            raion.get("oblast_name")
                            or raion.get("oblast")
                            or location_oblast
                            or ""
                        )

                        location["latitude"] = (
                            raion.get("latitude")
                            or raion.get("lat")
                            or raion.get("center_latitude")
                            or raion.get("center_lat")
                        )

                        location["longitude"] = (
                            raion.get("longitude")
                            or raion.get("lon")
                            or raion.get("center_longitude")
                            or raion.get("center_lon")
                        )

                except Exception as e:

                    print(
                        f"⚠️ Neptun location lookup "
                        f"{location_key}: {e}"
                    )

                locations.append(
                    location
                )

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
                        "raion_key": city_location.get(
                            "raion_key"
                        ),
                        "raion_name": city_location.get(
                            "raion_name"
                        ),
                        "oblast_key": city_location.get(
                            "oblast_key"
                        ),
                        "oblast_name": city_location.get(
                            "oblast_name"
                        ),
                        "latitude": city_location.get(
                            "latitude"
                        ),
                        "longitude": city_location.get(
                            "longitude"
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
            "latitude": 50.4501,
            "longitude": 30.5234,
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

        latitude = (
            raion.get("latitude")
            or raion.get("lat")
            or raion.get("center_latitude")
            or raion.get("center_lat")
        )

        longitude = (
            raion.get("longitude")
            or raion.get("lon")
            or raion.get("center_longitude")
            or raion.get("center_lon")
        )

        # Якщо Neptun не має координат району,
        # беремо координати головного міста району.
        if (
            latitude is None
            or longitude is None
        ):

            raion_name = (
                raion.get("name")
                or location_name
                or ""
            )

            city_name = re.sub(
                r"\s+район$",
                "",
                str(raion_name),
                flags=re.IGNORECASE,
            ).strip()

            if city_name:

                try:

                    city = find_city_location(
                        city_name
                    )

                    if city:

                        latitude = city.get(
                            "latitude"
                        )

                        longitude = city.get(
                            "longitude"
                        )

                except Exception:
                    pass

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
            "oblast_name": (
                raion.get("oblast_name")
                or raion.get("oblast")
                or location.get("oblast")
                or ""
            ),
            "latitude": latitude,
            "longitude": longitude,
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
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
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
    """
    Отримує координати локації.

    Для району:
    1. Беремо координати з location.
    2. Шукаємо район через Neptun.
    3. Якщо координат району немає —
       беремо центр міста, назва якого відповідає району.

    Для міста:
    1. location.
    2. Neptun.
    3. CITY_API.
    """

    if not location:
        return None, None

    latitude = location.get("latitude")
    longitude = location.get("longitude")

    if latitude is None:
        latitude = location.get("lat")

    if longitude is None:
        longitude = location.get("lon")

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

    location_key = normalize(
        location.get("key")
    )

    location_name = (
        location.get("name")
        or ""
    )

    # =================================================
    # РАЙОН
    # =================================================

    if location_key:

        try:

            raion = find_raion(
                location_key
            )

        except Exception as e:

            print(
                f"⚠️ Neptun raion coordinates error "
                f"{location_name}: {e}"
            )

            raion = None

        if raion:

            latitude = (
                raion.get("latitude")
                or raion.get("lat")
                or raion.get("center_latitude")
                or raion.get("center_lat")
            )

            longitude = (
                raion.get("longitude")
                or raion.get("lon")
                or raion.get("center_longitude")
                or raion.get("center_lon")
            )

            if (
                latitude is not None
                and longitude is not None
            ):

                try:

                    print(
                        f"📍 RAION COORDINATES | "
                        f"{location_name} | "
                        f"{latitude}, {longitude}"
                    )

                    return (
                        float(latitude),
                        float(longitude),
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            # -----------------------------------------
            # Центр району через головне місто
            # -----------------------------------------

            raion_name = (
                raion.get("name")
                or location_name
                or ""
            )

            city_name = re.sub(
                r"\s+район$",
                "",
                str(raion_name),
                flags=re.IGNORECASE,
            ).strip()

            if city_name:

                try:

                    city = find_city_location(
                        city_name
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

                            print(
                                f"📍 RAION CENTER | "
                                f"{location_name} → "
                                f"{city_name} | "
                                f"{latitude}, {longitude}"
                            )

                            return (
                                float(latitude),
                                float(longitude),
                            )

                except Exception as e:

                    print(
                        f"⚠️ Neptun district center error "
                        f"{city_name}: {e}"
                    )

    # =================================================
    # МІСТО
    # =================================================

    if location_name:

        try:

            city = find_city_location(
                location_name
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
                f"⚠️ Neptun coordinates error "
                f"{location_name}: {e}"
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
    """
    Визначення загроз для конкретної локації.

    Для Києва:
        - locality == Київ;
        - або координати threat знаходяться всередині
          офіційно визначеної геометрії Києва.

    Для інших міст:
        - locality == місто;
        - або threat знаходиться в тому самому районі NEPTUN.
    """

    if not data:
        return []

    threats = data.get("threats", [])

    if not threats:
        return []

    city_name = normalize(
        location.get("name")
        or location.get("city")
        or ""
    )

    location_raion = normalize(
        location.get("raion_key")
        or ""
    )

    location_oblast = normalize(
        location.get("oblast_key")
        or ""
    )

    print(
        f"📍 THREAT MATCH | "
        f"{location.get('name')} | "
        f"raion={location_raion or 'NONE'} | "
        f"oblast={location_oblast or 'NONE'}"
    )

    result = []

    # =================================================
    # ГЕОМЕТРІЯ КИЄВА
    # =================================================

    kyiv_geometry = None

    if city_name in ("київ", "kyiv"):
        try:
            import json

            kyiv_path = (
                __import__("pathlib")
                .Path(__file__)
                .resolve()
                .parents[1]
                / "data"
                / "kyiv_boundary.geojson"
            )

            with open(
                kyiv_path,
                encoding="utf-8",
            ) as f:
                kyiv_geometry = json.load(f)

        except Exception as e:
            print(
                f"⚠️ Не вдалося завантажити "
                f"геометрію Києва: {e}"
            )

    for threat in threats:

        if not isinstance(
            threat,
            dict,
        ):
            continue

        status = normalize(
            threat.get("status")
            or ""
        )

        if status not in (
            "active",
            "activated",
            "stale",
        ):
            continue

        locality = normalize(
            threat.get("locality")
            or ""
        )

        # =================================================
        # 1. ПРЯМА ЗАГРОЗА МІСТУ
        # =================================================

        if locality == city_name:

            threat_copy = dict(threat)

            threat_copy[
                "_threat_raion"
            ] = location_raion

            threat_copy[
                "_threat_oblast"
            ] = location_oblast

            result.append(
                threat_copy
            )

            print(
                f"🎯 THREAT MATCH | "
                f"{city_name} ← "
                f"{threat.get('type')} | "
                f"{threat.get('title')} | "
                f"{locality}"
            )

            continue

        # =================================================
        # 2. КИЇВ
        #
        # Якщо locality не Київ, перевіряємо координати.
        #
        # Важливо:
        # Київська область ≠ Київ.
        # Тому Переяслав, Яготин, Бровари тощо
        # не потрапляють сюди лише через область.
        # =================================================

        if city_name in (
            "київ",
            "kyiv",
        ):

            lat = threat.get("lat")
            lon = threat.get("lon")

            if lat is None or lon is None:
                continue

            try:
                lat = float(lat)
                lon = float(lon)

            except (
                TypeError,
                ValueError,
            ):
                continue

            if not kyiv_geometry:
                continue

            try:
                inside_kyiv = _point_in_geometry(
                    (lon, lat),
                    kyiv_geometry,
                )

            except Exception as e:
                print(
                    f"⚠️ Помилка перевірки "
                    f"геометрії Києва: {e}"
                )
                continue

            if not inside_kyiv:
                continue

            threat_copy = dict(threat)

            threat_copy[
                "_threat_raion"
            ] = "kyiv-city"

            threat_copy[
                "_threat_oblast"
            ] = "kyiv-city"

            result.append(
                threat_copy
            )

            print(
                f"🎯 THREAT MATCH | "
                f"КИЇВ ← "
                f"{threat.get('type')} | "
                f"{threat.get('title')} | "
                f"{locality or 'без locality'} | "
                f"lat={lat} lon={lon}"
            )

            continue

        # =================================================
        # 3. ІНШІ МІСТА
        #
        # Визначаємо район загрози по координатах
        # через геометрію NEPTUN.
        # =================================================

        lat = threat.get("lat")
        lon = threat.get("lon")

        if lat is None or lon is None:
            continue

        try:
            lat = float(lat)
            lon = float(lon)

        except (
            TypeError,
            ValueError,
        ):
            continue

        try:
            threat_raion = (
                find_raion_by_coordinates(
                    lat,
                    lon,
                )
            )

        except Exception as e:

            print(
                f"⚠️ Помилка визначення району "
                f"{locality}: {e}"
            )

            continue

        if not threat_raion:
            print(
                f"⚠️ Не вдалося визначити район "
                f"загрози: {locality}"
            )
            continue

        threat_raion_key = normalize(
            threat_raion.get("key")
            or ""
        )

        threat_oblast_key = normalize(
            threat_raion.get("oblast_key")
            or ""
        )

        threat_copy = dict(
            threat
        )

        threat_copy[
            "_threat_raion"
        ] = threat_raion_key

        threat_copy[
            "_threat_oblast"
        ] = threat_oblast_key

        # =================================================
        # ЗАГРОЗА В ТОМУ САМОМУ РАЙОНІ
        # =================================================

        if (
            location_raion
            and
            threat_raion_key
            == location_raion
        ):

            result.append(
                threat_copy
            )

            print(
                f"🎯 THREAT MATCH | "
                f"{city_name} ← "
                f"{threat.get('type')} | "
                f"{threat.get('title')} | "
                f"{locality} | "
                f"район={threat_raion_key}"
            )

    print(
        f"📡 Загроз для {location.get('name')}: "
        f"{len(result)}"
    )

    return result

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
            threat_type = normalize(
                threat.get("type")
            )

            threat_type_names = {
                "uav": "БпЛА",
                "missile": "ракета",
                "ballistic": "балістика",
                "kab": "КАБ",
                "mig31k": "МіГ-31К",
                "recon": "розвідувальна загроза",
                "fpv": "FPV-дрон",
                "unknown": "невідома загроза",
            }

            title = threat_type_names.get(
                threat_type,
                "невідома загроза",
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

def threat_signature(threat):
    """
    Сигнатура реальної зміни загрози.

    НЕ враховуємо динамічні поля NEPTUN:
        - updatedAt
        - sourceCount
        - confidenceLevel
        - uncertaintyKm
        - positionQuality
        - heading

    Вони можуть змінюватися при кожному оновленні API
    і не повинні створювати Telegram-спам.
    """

    if not isinstance(threat, dict):
        return None

    return (
        threat.get("type"),
        threat.get("title"),
        threat.get("region"),
        threat.get("district"),
        threat.get("locality"),
        threat.get("status"),
        threat.get("destination"),
        threat.get("presumptiveCourse"),
        threat.get("areaOnly"),
    )


async def group_alert_monitor(
    bot: Bot,
):
    print(
        "🚨 Моніторинг тривог запущений"
    )

    # Стан тривог по локаціях
    _last_alert_states = {}

    # Стан загроз по локаціях.
    # updatedAt НЕ враховується, щоб не було спаму.
    _last_threat_states = {}

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
                try:
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

                        try:
                            threats_data = (
                                await asyncio.to_thread(
                                    get_threats
                                )
                            )

                            initial_threats = (
                                get_location_threats(
                                    location,
                                    threats_data,
                                )
                                if threats_data
                                else []
                            )

                            _last_threat_states[
                                location_key
                            ] = {
                                threat.get("id"):
                                threat_signature(threat)
                                for threat in initial_threats
                                if threat.get("id")
                            }

                        except Exception as e:
                            print(
                                f"⚠️ Не вдалося отримати "
                                f"початкові загрози "
                                f"{location.get('name')}: {e}"
                            )

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
                        location_threats = []

                        # Чекаємо появу реальних threat-даних.
                        for attempt in range(10):
                            try:
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

                            except Exception as e:
                                print(
                                    f"⚠️ Помилка Threats API "
                                    f"{location.get('name')}: {e}"
                                )

                                location_threats = []

                            if location_threats:
                                print(
                                    f"🎯 Загрози знайдені для "
                                    f"{location.get('name')} "
                                    f"з {attempt + 1}-ї перевірки"
                                )
                                break

                            if attempt < 9:
                                print(
                                    f"⏳ Threats API: "
                                    f"загроз для "
                                    f"{location.get('name')} "
                                    f"ще немає "
                                    f"({attempt + 1}/10)"
                                )

                                await asyncio.sleep(3)

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

                        _last_threat_states[
                            location_key
                        ] = {
                            threat.get("id"):
                            threat_signature(threat)
                            for threat in location_threats
                            if threat.get("id")
                        }

                        print(
                            f"🚨 ПОЧАЛАСЯ ТРИВОГА: "
                            f"{location.get('name')}"
                        )

                        continue

                    # =================================================
                    # ВІДБІЙ
                    # =================================================

                    if (
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

                        _last_threat_states[
                            location_key
                        ] = {}

                        print(
                            f"🟢 ВІДБІЙ: "
                            f"{location.get('name')}"
                        )

                        continue

                    # =================================================
                    # ТРИВОГА ПРОДОВЖУЄТЬСЯ
                    # =================================================

                    _last_alert_states[
                        location_key
                    ] = alert_active

                    if not alert_active:
                        continue

                    threats_data = await asyncio.to_thread(
                        get_threats
                    )

                    location_threats = (
                        get_location_threats(
                            location,
                            threats_data,
                        )
                        if threats_data
                        else []
                    )

                    current_threats = {
                        threat.get("id"): threat
                        for threat in location_threats
                        if threat.get("id")
                    }

                    previous_threats = (
                        _last_threat_states.get(
                            location_key,
                            {}
                        )
                    )

                    current_signatures = {
                        threat_id:
                        threat_signature(threat)
                        for threat_id, threat
                        in current_threats.items()
                    }

                    # =================================================
                    # НОВА ЗАГРОЗА
                    # =================================================

                    new_ids = (
                        set(current_threats)
                        - set(previous_threats)
                    )

                    for threat_id in new_ids:
                        threat = current_threats[
                            threat_id
                        ]

                        print(
                            f"🆕 НОВА ЗАГРОЗА | "
                            f"{location.get('name')} | "
                            f"id={threat_id}"
                        )

                        try:
                            threat_text = format_threat(
                                threat
                            )

                            await send_to_group(
                                bot,
                                (
                                    f"🚨 <b>Нова загроза</b> — "
                                    f"{location.get('name')}\n\n"
                                    f"{threat_text}"
                                ),
                            )

                        except Exception as e:
                            print(
                                f"❌ Помилка повідомлення "
                                f"про нову загрозу "
                                f"{threat_id}: {e}"
                            )


                    _last_threat_states[
                        location_key
                    ] = current_signatures

                except Exception as e:
                    print(
                        f"❌ Помилка моніторингу "
                        f"{location.get('name', 'невідома локація')}: "
                        f"{e}"
                    )

            # Видаляємо старі локації.
            for key in list(
                _last_alert_states.keys()
            ):
                if key not in current_keys:
                    _last_alert_states.pop(
                        key,
                        None
                    )

                    _last_threat_states.pop(
                        key,
                        None
                    )

        except Exception as e:
            print(
                f"❌ Критична помилка "
                f"моніторингу тривог: {e}"
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
        conn = get_connection()

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
                    print(
                        f"⚠️ Немає погоди для {city}"
                    )
                    continue

                advice = ""

                try:

                    advice_result = get_advice(
                        weather.get("temp"),
                        weather.get("condition", ""),
                        city,
                        weather.get("feels_like"),
                        weather.get("wind"),
                        weather.get("humidity"),
                    )

                    if advice_result:
                        advice = (
                            f"\n\n💡 "
                            f"{advice_result}"
                        )

                except Exception as e:

                    print(
                        f"⚠️ Помилка поради "
                        f"{city}: {e}"
                    )

                icon = get_weather_icon(
                    weather.get(
                        "condition"
                    )
                )

                text = (
                    "🌅 <b>Доброго ранку!</b>\n\n"
                    f"📍 <b>{city}</b>\n\n"
                    f"{icon} "
                    f"{weather.get('condition', '')}\n"
                    f"🌡 Температура: "
                    f"{weather.get('temp', '—')}°C\n"
                    f"💨 Вітер: "
                    f"{weather.get('wind', '—')} м/с\n"
                    f"💧 Вологість: "
                    f"{weather.get('humidity', '—')}%"
                    f"{advice}"
                )

                await send_to_group(
                    bot,
                    text,
                )

                print(
                    f"✅ Ранкова погода "
                    f"відправлена: {city}"
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
# Є ЩО СКАЗАТИ
# =====================================================

async def send_morning_day_facts(
    bot: Bot,
):
    print(
        "📣 Формування ранкового "
        "«Є що сказати»..."
    )

    try:

        conn = get_connection()

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
                "ℹ️ Немає міст для "
                "«Є що сказати»"
            )

            return

        sent_cities = set()

        for city in cities:

            if city in sent_cities:
                continue

            sent_cities.add(city)

            try:

                text = await asyncio.to_thread(
                    get_day_facts,
                    city,
                )

                if not text:
                    print(
                        f"⚠️ Немає контенту "
                        f"для {city}"
                    )
                    continue

                await send_to_group(
                    bot,
                    text,
                )

                print(
                    f"✅ «Є що сказати» "
                    f"відправлено: {city}"
                )

                await asyncio.sleep(1)

            except Exception as e:

                print(
                    f"❌ Помилка «Є що сказати» "
                    f"{city}: {e}"
                )

    except Exception as e:

        print(
            "❌ Помилка формування "
            f"«Є що сказати»: {e}"
        )


# =====================================================
# РАНКОВА РОЗСИЛКА
# =====================================================

async def send_morning_content(
    bot: Bot,
):
    print(
        "🌅 Початок ранкової розсилки"
    )

    try:
        conn = get_connection()
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
                "ℹ️ Немає міст для ранкової розсилки"
            )
            return

        sent_cities = set()

        for city in cities:

            if city in sent_cities:
                continue

            sent_cities.add(city)

            try:
                # =============================================
                # ПОГОДА
                # =============================================

                weather = await asyncio.to_thread(
                    get_weather,
                    city,
                )

                if not weather:
                    print(
                        f"⚠️ Немає погоди для {city}"
                    )
                    continue

                icon = get_weather_icon(
                    weather.get("condition")
                )

                weather_text = (
                    f"{icon} "
                    f"<b>{weather.get('condition', '')}</b>\n"
                    f"🌡 Температура: "
                    f"{weather.get('temp', '—')}°C\n"
                    f"💨 Вітер: "
                    f"{weather.get('wind', '—')} м/с\n"
                    f"💧 Вологість: "
                    f"{weather.get('humidity', '—')}%"
                )

                # =============================================
                # AI: АНЕКДОТ + ПОБАЖАННЯ
                # =============================================

                ai_content = None

                try:
                    ai_content = await asyncio.to_thread(
                        ai_joke.generate_daily_content,
                        city,
                        weather,
                    )

                except Exception as e:
                    print(
                        f"⚠️ AI помилка {city}: {e}"
                    )

                # =============================================
                # ФОРМУЄМО ОДНЕ ПОВІДОМЛЕННЯ
                # =============================================

                text = (
                    "☀️ <b>ДОБРОГО РАНКУ!</b>\n\n"
                    f"📍 <b>{city}</b>\n\n"
                    f"{weather_text}"
                )

                # AI побажання
                if ai_content:
                    greeting = ai_content.get(
                        "greeting"
                    )

                    if greeting:
                        text += (
                            "\n\n💡 <b>Побажання дня:</b>\n"
                            f"{greeting}"
                        )

                # AI анекдот
                if ai_content:
                    joke = ai_content.get(
                        "joke"
                    )

                    if joke:
                        text += (
                            "\n\n😂 <b>Анекдот дня:</b>\n"
                            f"{joke}"
                        )

                # AI порада дня
                if ai_content:
                    advice = ai_content.get(
                        "advice"
                    )

                    if advice:
                        text += (
                            "\n\n💡 <b>Порада дня:</b>\n"
                            f"{advice}"
                        )

                await send_to_group(
                    bot,
                    text,
                )

                print(
                    f"✅ Ранкове повідомлення "
                    f"відправлено: {city}"
                )

                await asyncio.sleep(1)

            except Exception as e:

                print(
                    f"❌ Помилка ранкової розсилки "
                    f"{city}: {e}"
                )

    except Exception as e:

        print(
            f"❌ Помилка ранкової розсилки: {e}"
        )

    print(
        "✅ Ранкова розсилка завершена"
    )



# =====================================================
# ПЛАНУВАЛЬНИК РАНКОВОЇ РОЗСИЛКИ
# =====================================================

async def morning_weather_scheduler(
    bot: Bot,
):
    """
    Щодня запускає ранкову розсилку один раз.
    """

    print("🌅 Morning weather scheduler запущений")

    while True:

        try:
            now = datetime.now()
            today = now.date().isoformat()

            # Час ранкової розсилки
            if (
                now.hour == 8
                and now.minute == 0
                and get_scheduler_last_run(
                    "morning_weather"
                ) != today
            ):

                print(
                    "🌅 Час ранкової розсилки — запускаємо"
                )

                await send_morning_content(bot)

                set_scheduler_last_run(
                    "morning_weather",
                    today,
                )

        except Exception as e:
            print(
                f"❌ Помилка morning scheduler: {e}"
            )

        await asyncio.sleep(30)
