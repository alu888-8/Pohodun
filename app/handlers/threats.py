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
# РАДІУС ПОШУКУ ЗАГРОЗ
# =====================================================

THREAT_RADIUS_KM = 70


# =====================================================
# ВІДСТАНЬ МІЖ ДВОМА КООРДИНАТАМИ
# =====================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):

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
            f"❌ Помилка координат міста "
            f"{city}: {e}"
        )

        return None


# =====================================================
# ПЕРЕВІРКА ЧИ ЗАГРОЗА ПОБЛИЗУ МІСТА
# =====================================================

def is_threat_near_city(
    threat,
    city
):

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
        return False

    # -------------------------------------------------
    # КООРДИНАТИ МІСТА
    # -------------------------------------------------

    city_coordinates = (
        get_city_coordinates(city)
    )

    # -------------------------------------------------
    # КООРДИНАТИ ЗАГРОЗИ
    # -------------------------------------------------

    threat_lat = threat.get(
        "lat"
    )

    threat_lon = threat.get(
        "lon"
    )

    # -------------------------------------------------
    # ОСНОВНИЙ СПОСІБ
    # -------------------------------------------------

    if (
        city_coordinates
        and threat_lat is not None
        and threat_lon is not None
    ):

        city_lat, city_lon = (
            city_coordinates
        )

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

            if (
                distance
                <= THREAT_RADIUS_KM
            ):

                return True

    # -------------------------------------------------
    # ЗАПАСНИЙ ВАРІАНТ — ПОШУК ПО ТЕКСТУ
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
# ПЕРЕВІРКА ПОВІТРЯНОЇ ТРИВОГИ
# =====================================================

def is_city_alert_active(
    city,
    data
):

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

                # Якщо об'єкт знайдений,
                # перевіряємо його статус

                status = item.get(
                    "status"
                )

                if status is True:
                    return True

                if isinstance(status, str):

                    if status.lower() in (
                        "active",
                        "activated",
                        "тривога"
                    ):
                        return True

                # Деякі API можуть використовувати
                # поле active

                if item.get(
                    "active"
                ) is True:

                    return True

                # Якщо об'єкт присутній,
                # але структура API інша —
                # дивимося на поле since

                if item.get(
                    "since"
                ):
                    return True

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

    for item in raions + oblasts:

        name = (
            item.get(
                "name",
                ""
            )
            .lower()
        )

        oblast = (
            item.get(
                "oblast",
                ""
            )
            .lower()
        )

        key = (
            item.get(
                "key",
                ""
            )
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

            status = item.get(
                "status"
            )

            if status is True:
                return True

            if isinstance(status, str):

                if status.lower() in (
                    "active",
                    "activated",
                    "тривога"
                ):
                    return True

            if item.get(
                "active"
            ) is True:

                return True

            if item.get(
                "since"
            ):
                return True

            return False

    return False


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
        "unknown": "❓"
    }.get(
        threat_type,
        "❓"
    )


# =====================================================
# ФОРМУВАННЯ ЗАГРОЗИ
# =====================================================

def format_threat(
    threat
):

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

    explanation = threat.get(
        "explanationShort",
        ""
    )

    count = threat.get(
        "count"
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

    if explanation:

        text += (
            f"{explanation}\n"
        )

    if count and count > 1:

        text += (
            f"🎯 Група: {count}\n"
        )

    if source_count:

        text += (
            f"🔎 Підтверджень: "
            f"{source_count}"
        )

    return text


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

    # -------------------------------------------------
    # МІСТО
    # -------------------------------------------------

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
            "❌ Спочатку оберіть місто."
        )

        return

    # =================================================
    # ОДНОЧАСНО ОТРИМУЄМО
    # ЗАГРОЗИ + ТРИВОГИ
    # =================================================

    threats_data_api = await asyncio.to_thread(
        get_threats
    )

    alerts_data = await asyncio.to_thread(
        get_alerts
    )

    # =================================================
    # ПЕРЕВІРКА ЗАГРОЗ
    # =================================================

    result = []

    if threats_data_api:

        threats_data = threats_data_api.get(
            "threats",
            []
        )

        print(
            f"🛰 THREATS | "
            f"API threats={len(threats_data)}"
        )

        for threat in threats_data:

            if is_threat_near_city(
                threat,
                city
            ):

                result.append(
                    format_threat(
                        threat
                    )
                )

    # =================================================
    # ЯКЩО Є КОНКРЕТНА ЗАГРОЗА
    # =================================================

    if result:

        text = (
            f"🛰 <b>ЗАГРОЗИ ДЛЯ "
            f"{city.upper()}</b>\n\n"
            +
            "\n\n".join(
                result
            )
        )

    else:

        # =================================================
        # ПЕРЕВІРЯЄМО ПОВІТРЯНУ ТРИВОГУ
        # =================================================

        alert_active = (
            is_city_alert_active(
                city,
                alerts_data
            )
        )

        print(
            f"🚨 THREATS | "
            f"city={city} | "
            f"alert_active={alert_active}"
        )

        # =================================================
        # Є ТРИВОГА, АЛЕ КОНКРЕТНОЇ ЗАГРОЗИ НЕМАЄ
        # =================================================

        if alert_active:

            text = (
                "🛰 <b>ЗАГРОЗИ</b>\n\n"
                f"📍 <b>{city}</b>\n\n"
                "🔴 <b>Повітряна тривога активна</b>\n\n"
                "⚠️ Конкретний тип загрози "
                "наразі не визначений."
            )

        # =================================================
        # НЕМАЄ НІ ЗАГРОЗИ, НІ ТРИВОГИ
        # =================================================

        else:

            text = (
                "🛰 <b>ЗАГРОЗИ</b>\n\n"
                f"📍 <b>{city}</b>\n\n"
                "🟢 <b>Активних загроз "
                "не виявлено.</b>"
            )

    # =================================================
    # ВІДПОВІДЬ
    # =================================================

    await message.answer(
        text,
        parse_mode="HTML"
    )

    print(
        f"✅ THREATS | "
        f"city={city} | "
        f"found={len(result)}"
    )