import math
import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API
from app.data.regions import CITY_REGIONS

from app.services.threats import get_threats
from app.services.alerts import get_alerts


router = Router()


# =====================================================
# РАДІУС ПОШУКУ КОНКРЕТНИХ ЗАГРОЗ
# =====================================================

THREAT_RADIUS_KM = 70


# =====================================================
# ВІДСТАНЬ МІЖ ДВОМА КООРДИНАТАМИ
# =====================================================

def distance_km(lat1, lon1, lat2, lon2):

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

    except (TypeError, ValueError):
        return None

    earth_radius = 6371

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = (
        2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    return earth_radius * c


# =====================================================
# КООРДИНАТИ МІСТА
# =====================================================

def get_city_coordinates(city):

    coordinates = CITY_API.get(city)

    if not coordinates:
        return None

    try:

        lat, lon = coordinates.split(",")

        return (
            float(lat.strip()),
            float(lon.strip())
        )

    except Exception as e:

        print(
            f"❌ Помилка координат міста "
            f"{city}: {e}"
        )

        return None


# =====================================================
# ПЕРЕВІРКА КОНКРЕТНОЇ ЗАГРОЗИ
# =====================================================

def is_threat_near_city(threat, city):

    status = (
        threat.get("status", "active")
        or "active"
    ).lower()

    if status not in ("active", "stale"):
        return False

    city_coordinates = get_city_coordinates(city)

    threat_lat = threat.get("lat")
    threat_lon = threat.get("lon")

    # -------------------------------------------------
    # ОСНОВНИЙ СПОСІБ — КООРДИНАТИ
    # -------------------------------------------------

    if (
        city_coordinates
        and threat_lat is not None
        and threat_lon is not None
    ):

        city_lat, city_lon = city_coordinates

        distance = distance_km(
            city_lat,
            city_lon,
            threat_lat,
            threat_lon
        )

        if distance is not None:

            print(
                f"📡 Загроза | "
                f"{city} | "
                f"{threat.get('title')} | "
                f"{distance:.1f} км"
            )

            if distance <= THREAT_RADIUS_KM:
                return True

            # Якщо координати є і загроза далеко —
            # НЕ використовуємо текстовий fallback.
            return False

    # -------------------------------------------------
    # FALLBACK ПО ТЕКСТУ
    # Використовується ТІЛЬКИ якщо координат немає
    # -------------------------------------------------

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    search_text = (
        f"{threat.get('region', '')} "
        f"{threat.get('district', '')} "
        f"{threat.get('locality', '')} "
        f"{threat.get('title', '')} "
        f"{threat.get('explanationShort', '')}"
    ).lower()

    for keyword in keywords:

        if keyword.lower() in search_text:
            return True

    return False


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
        "fpv": "🛸",
        "unknown": "❓"
    }.get(
        threat_type,
        "❓"
    )


# =====================================================
# ФОРМУВАННЯ КОНКРЕТНОЇ ЗАГРОЗИ
# =====================================================

def format_threat(threat, city):

    icon = get_threat_icon(
        threat.get("type")
    )

    title = threat.get(
        "title",
        "Невідома загроза"
    )

    region = threat.get(
        "region",
        ""
    )

    district = threat.get(
        "district",
        ""
    )

    locality = threat.get(
        "locality",
        ""
    )

    source_count = threat.get(
        "sourceCount"
    )

    city_coordinates = get_city_coordinates(city)

    threat_lat = threat.get("lat")
    threat_lon = threat.get("lon")

    distance_text = ""

    if (
        city_coordinates
        and threat_lat is not None
        and threat_lon is not None
    ):

        distance = distance_km(
            city_coordinates[0],
            city_coordinates[1],
            threat_lat,
            threat_lon
        )

        if distance is not None:
            distance_text = (
                f"📏 Відстань: "
                f"<b>{distance:.0f} км</b>\n"
            )

    text = (
        f"{icon} <b>{title}</b>\n"
    )

    if region:

        text += (
            f"📍 {region}\n"
        )

    if district:

        text += (
            f"🏙 {district}\n"
        )

    if locality:

        text += (
            f"📌 {locality}\n"
        )

    text += distance_text

    if source_count:

        text += (
            f"🔎 Підтверджень: "
            f"<b>{source_count}</b>\n"
        )

    return text.rstrip()


# =====================================================
# ПЕРЕВІРКА ПОВІТРЯНОЇ ТРИВОГИ
# =====================================================

def is_city_alert_active(city, data):

    if not data:
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

    if city == "Київ":

        for item in raions + oblasts:

            name = (
                item.get("name", "")
                .strip()
                .lower()
            )

            key = (
                item.get("key", "")
                .strip()
                .lower()
            )

            if (
                name in (
                    "київ",
                    "м. київ",
                    "місто київ"
                )
                or key in (
                    "київ",
                    "м. київ",
                    "місто київ"
                )
            ):

                return bool(
                    item.get("since")
                    or item.get("active") is True
                    or item.get("status") is True
                    or (
                        isinstance(
                            item.get("status"),
                            str
                        )
                        and item.get(
                            "status"
                        ).lower()
                        in (
                            "active",
                            "activated",
                            "тривога"
                        )
                    )
                )

        return False

    # =================================================
    # ІНШІ МІСТА
    # =================================================

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    keywords = [
        word.lower()
        for word in keywords
    ]

    for item in raions:

        name = (
            item.get("name", "")
            .lower()
        )

        oblast = (
            item.get("oblast", "")
            .lower()
        )

        key = (
            item.get("key", "")
            .lower()
        )

        search_text = (
            f"{name} "
            f"{oblast} "
            f"{key}"
        )

        if any(
            word in search_text
            for word in keywords
        ):

            return bool(
                item.get("since")
                or item.get("active") is True
                or item.get("status") is True
                or (
                    isinstance(
                        item.get("status"),
                        str
                    )
                    and item.get(
                        "status"
                    ).lower()
                    in (
                        "active",
                        "activated",
                        "тривога"
                    )
                )
            )

    return False


# =====================================================
# КНОПКА ЗАГРОЗ
# =====================================================

@router.message(
    lambda message:
    message.text == "🛰 Загрози"
)
async def threats(message: Message):

    user_id = message.from_user.id

    city = get_city(user_id)

    print(
        f"🛰 THREATS | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    if not city:

        await message.answer(
            "❌ Спочатку оберіть місто."
        )

        return

    # =================================================
    # ОТРИМУЄМО ОБИДВА API
    # =================================================

    threats_data_api = await asyncio.to_thread(
        get_threats
    )

    alerts_data = await asyncio.to_thread(
        get_alerts
    )

    # =================================================
    # ПЕРЕВІРЯЄМО ТРИВОГУ
    # =================================================

    alert_active = is_city_alert_active(
        city,
        alerts_data
    )

    print(
        f"🚨 THREATS | "
        f"city={city} | "
        f"alert_active={alert_active}"
    )

    # =================================================
    # ШУКАЄМО КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    result = []

    if threats_data_api:

        threats_data = threats_data_api.get(
            "threats",
            []
        )

        print(
            f"🛰 THREATS API | "
            f"count={len(threats_data)}"
        )

        for threat in threats_data:

            if is_threat_near_city(
                threat,
                city
            ):

                result.append(
                    format_threat(
                        threat,
                        city
                    )
                )

    # =================================================
    # ФОРМУЄМО ЗРОЗУМІЛУ ВІДПОВІДЬ
    # =================================================

    text = (
        "🛰 <b>ЗАГРОЗИ</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
    )

    # =================================================
    # СТАН ТРИВОГИ
    # =================================================

    text += (
        "🚨 <b>СТАН ТРИВОГИ</b>\n"
    )

    if alert_active:

        text += (
            "🔴 Повітряна тривога: "
            "<b>АКТИВНА</b>\n\n"
        )

    else:

        text += (
            "🟢 Повітряна тривога: "
            "<b>НЕМАЄ</b>\n\n"
        )

    # =================================================
    # КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    text += (
        "📡 <b>КОНКРЕТНІ ЗАГРОЗИ</b>\n"
    )

    if result:

        text += (
            "\n"
            +
            "\n\n".join(result)
            +
            "\n"
        )

    else:

        text += (
            "🟢 Поблизу активних "
            "конкретних загроз не виявлено.\n"
        )

        if alert_active:

            text += (
                "\n"
                "ℹ️ Тривога активна, але "
                "Threats API наразі не передає "
                "конкретну загрозу поблизу міста.\n"
            )

    # =================================================
    # ЗАСТЕРЕЖЕННЯ
    # =================================================

    if alert_active:

        text += (
            "\n⚠️ <b>Перебувайте "
            "в безпечному місці.</b>"
        )

    else:

        text += (
            "\n🛡 Залишайтеся уважними."
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

    print(
        f"✅ THREATS | "
        f"city={city} | "
        f"alert={alert_active} | "
        f"found={len(result)}"
    )