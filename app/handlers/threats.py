import math
import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API
from app.data.regions import CITY_REGIONS
from app.data.location_regions import CITY_OBLASTS

from app.services.threats import get_threats
from app.services.alerts import get_alerts


router = Router()


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

THREAT_RADIUS_KM = 70

KYIV_CITY = "Київ"
KYIV_OBLAST = "Київська область"


# =====================================================
# ВІДСТАНЬ МІЖ КООРДИНАТАМИ
# =====================================================

def distance_km(lat1, lon1, lat2, lon2):

    try:

        lat1 = float(lat1)
        lon1 = float(lon1)

        lat2 = float(lat2)
        lon2 = float(lon2)

    except (
        TypeError,
        ValueError
    ):

        return None

    earth_radius = 6371

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(
        lat2 - lat1
    )

    delta_lon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(delta_lon / 2) ** 2
    )

    c = (
        2
        *
        math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    return earth_radius * c


# =====================================================
# КООРДИНАТИ МІСТА
# =====================================================

def get_city_coordinates(city):

    coordinates = CITY_API.get(
        city
    )

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
            f"❌ Помилка координат "
            f"{city}: {e}"
        )

        return None


# =====================================================
# ОБЛАСТЬ МІСТА
# =====================================================

def get_city_oblast(city):

    return CITY_OBLASTS.get(
        city
    )


# =====================================================
# ЧИ АКТИВНИЙ ЕЛЕМЕНТ API
# =====================================================

def is_item_active(item):

    if not item:
        return False

    if item.get("since"):
        return True

    if item.get("active") is True:
        return True

    status = item.get("status")

    if isinstance(status, str):

        if status.lower() in (
            "active",
            "activated",
            "тривога"
        ):
            return True

    if status is True:
        return True

    return False


# =====================================================
# АКТИВНІ РАЙОНИ ОБЛАСТІ
# =====================================================

def get_active_oblast_raions(
    oblast,
    alerts_data
):

    if not alerts_data:
        return []

    raions = alerts_data.get(
        "raions",
        []
    )

    result = []

    for item in raions:

        item_oblast = (
            item.get(
                "oblast",
                ""
            )
            .strip()
            .lower()
        )

        if (
            item_oblast
            != oblast.strip().lower()
        ):
            continue

        if is_item_active(item):

            result.append(item)

    return result


# =====================================================
# СТАН КИЄВА
# =====================================================

def get_kyiv_city_alert(
    alerts_data
):

    if not alerts_data:
        return False

    raions = alerts_data.get(
        "raions",
        []
    )

    oblasts = alerts_data.get(
        "oblasts",
        []
    )

    # -------------------------------------------------
    # Шукаємо тільки саме Київ
    # -------------------------------------------------

    for item in raions + oblasts:

        name = (
            item.get(
                "name",
                ""
            )
            .strip()
            .lower()
        )

        key = (
            item.get(
                "key",
                ""
            )
            .strip()
            .lower()
        )

        if name in (
            "київ",
            "м. київ",
            "місто київ"
        ):

            return is_item_active(item)

        if key in (
            "київ",
            "м. київ",
            "місто київ"
        ):

            return is_item_active(item)

    return False


# =====================================================
# СТАН КОНКРЕТНОЇ ЛОКАЦІЇ
# =====================================================

def get_location_alert(
    city,
    alerts_data
):

    # -------------------------------------------------
    # КИЇВ — ОСОБЛИВИЙ ВИПАДОК
    #
    # Київ ≠ Київська область
    # -------------------------------------------------

    if city == KYIV_CITY:

        return get_kyiv_city_alert(
            alerts_data
        )

    # -------------------------------------------------
    # ІНШІ МІСТА
    #
    # Поки API дає районний статус,
    # не будемо брехати користувачу,
    # що тривога саме в місті.
    # -------------------------------------------------

    return False


# =====================================================
# КОНКРЕТНІ ЗАГРОЗИ ПОБЛИЗУ
# =====================================================

def find_nearby_threats(
    city,
    threats_data
):

    result = []

    if not threats_data:
        return result

    city_coordinates = (
        get_city_coordinates(city)
    )

    for threat in threats_data:

        status = (
            threat.get(
                "status",
                "active"
            )
            or "active"
        ).lower()

        if status not in (
            "active",
            "stale"
        ):
            continue

        threat_lat = threat.get(
            "lat"
        )

        threat_lon = threat.get(
            "lon"
        )

        distance = None

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

            if distance is None:
                continue

            if distance > THREAT_RADIUS_KM:
                continue

        else:

            # Якщо координат немає —
            # використовуємо текстовий пошук.

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

            found = any(
                keyword.lower()
                in search_text
                for keyword in keywords
            )

            if not found:
                continue

        result.append(
            {
                "threat": threat,
                "distance": distance
            }
        )

    return result


# =====================================================
# ІКОНКА ЗАГРОЗИ
# =====================================================

def get_threat_icon(
    threat_type
):

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

def format_threat(
    item
):

    threat = item["threat"]
    distance = item["distance"]

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

    if distance is not None:

        text += (
            f"📏 Відстань: "
            f"<b>{distance:.0f} км</b>\n"
        )

    if source_count:

        text += (
            f"🔎 Підтверджень: "
            f"<b>{source_count}</b>\n"
        )

    return text.rstrip()


# =====================================================
# КНОПКА ЗАГРОЗ
# =====================================================

@router.message(
    lambda message:
    message.text == "🛰 Загрози"
)
async def threats(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    city = get_city(
        user_id
    )

    print(
        f"🛰 THREATS | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    if not city:

        await message.answer(
            "❌ Спочатку оберіть "
            "свою локацію."
        )

        return

    # =================================================
    # API
    # =================================================

    threats_api = await asyncio.to_thread(
        get_threats
    )

    alerts_api = await asyncio.to_thread(
        get_alerts
    )

    # =================================================
    # СТАН КОНКРЕТНОГО МІСТА
    # =================================================

    city_alert = get_location_alert(
        city,
        alerts_api
    )

    # =================================================
    # ОБЛАСТЬ
    # =================================================

    city_oblast = get_city_oblast(
        city
    )

    oblast_raions = (
        get_active_oblast_raions(
            city_oblast,
            alerts_api
        )
        if city_oblast
        else []
    )

    oblast_alert = bool(
        oblast_raions
    )

    # =================================================
    # КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    threats_data = []

    if threats_api:

        threats_data = threats_api.get(
            "threats",
            []
        )

    nearby_threats = find_nearby_threats(
        city,
        threats_data
    )

    # =================================================
    # ЛОГ
    # =================================================

    print(
        f"🛰 LOCATION STATUS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"oblast_alert={oblast_alert} | "
        f"threats={len(nearby_threats)}"
    )

    # =================================================
    # ПОЧАТОК ПОВІДОМЛЕННЯ
    # =================================================

    text = (
        "🛰 <b>СТАН БЕЗПЕКИ</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
    )

    # =================================================
    # 1. КОНКРЕТНА ЛОКАЦІЯ
    # =================================================

    text += (
        "🚨 <b>МОЯ ЛОКАЦІЯ</b>\n"
    )

    if city_alert:

        text += (
            "🔴 Повітряна тривога: "
            "<b>АКТИВНА</b>\n\n"
        )

    else:

        text += (
            "🟢 Повітряної тривоги "
            "<b>НЕМАЄ</b>\n\n"
        )

    # =================================================
    # 2. ОБЛАСТЬ
    # =================================================

    if city_oblast:

        text += (
            f"🗺 <b>{city_oblast.upper()}</b>\n"
        )

        if oblast_alert:

            text += (
                "🟡 У частині області "
                "<b>АКТИВНА ТРИВОГА</b>\n"
            )

            if oblast_raions:

                text += (
                    "\n📍 <b>Активні райони:</b>\n"
                )

                for item in oblast_raions:

                    name = item.get(
                        "name",
                        "Невідомий район"
                    )

                    text += (
                        f"• {name}\n"
                    )

            text += "\n"

        else:

            text += (
                "🟢 Активної тривоги "
                "в області не виявлено.\n\n"
            )

    # =================================================
    # 3. КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    text += (
        "📡 <b>КОНКРЕТНІ ЗАГРОЗИ ПОБЛИЗУ</b>\n"
    )

    if nearby_threats:

        text += "\n"

        for item in nearby_threats:

            text += (
                format_threat(item)
                +
                "\n\n"
            )

        text = text.rstrip()

    else:

        text += (
            "🟢 Конкретних активних "
            "загроз у радіусі "
            f"{THREAT_RADIUS_KM} км "
            "не виявлено.\n"
        )

    # =================================================
    # 4. ПОЯСНЕННЯ
    # =================================================

    if city == KYIV_CITY:

        if (
            not city_alert
            and oblast_alert
        ):

            text += (
                "\n\n"
                "ℹ️ <b>Важливо:</b> "
                "тривога в Київській області "
                "не означає автоматично "
                "тривогу в Києві."
            )

        if (
            not city_alert
            and nearby_threats
        ):

            text += (
                "\n\n"
                "⚠️ <b>Увага:</b> "
                "конкретна загроза знаходиться "
                "поблизу Києва, але "
                "повітряна тривога "
                "в Києві наразі не оголошена."
            )

    # =================================================
    # 5. РЕКОМЕНДАЦІЯ
    # =================================================

    if city_alert:

        text += (
            "\n\n"
            "⚠️ <b>Перебувайте "
            "в безпечному місці.</b>"
        )

    elif nearby_threats:

        text += (
            "\n\n"
            "🟡 <b>Слідкуйте за офіційними "
            "повідомленнями.</b>"
        )

    else:

        text += (
            "\n\n"
            "🛡 <b>Залишайтеся уважними.</b>"
        )

    # =================================================
    # ВІДПРАВКА
    # =================================================

    await message.answer(
        text,
        parse_mode="HTML"
    )

    print(
        f"✅ THREATS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast_alert={oblast_alert} | "
        f"nearby={len(nearby_threats)}"
    )