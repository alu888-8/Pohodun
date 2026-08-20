import asyncio
import re

from math import radians, sin, cos, asin, sqrt

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city, get_location
from app.data.cities import CITY_API

from app.services.alerts import get_alerts
from app.services.threats import get_threats

from app.services.neptun_locations import (
    find_city_location,
    find_raion,
)


router = Router()


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================



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
# ВІДСТАНЬ МІЖ КООРДИНАТАМИ
# =====================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):

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
        *
        cos(radians(lat2))
        *
        sin(dlon / 2) ** 2
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
    Отримує координати вибраної локації.

    Порядок:
    1. Координати вже є в location.
    2. Якщо вибрано район — шукаємо район через Neptun.
    3. Якщо Neptun має координати району — використовуємо їх.
    4. Якщо координат району немає — беремо центр
       основного міста району.
    5. Для міста — шукаємо через Neptun.
    6. Резерв — CITY_API.
    """

    if not location:
        return None, None

    # -------------------------------------------------
    # 1. Координати вже збережені
    # -------------------------------------------------

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

    # -------------------------------------------------
    # 2. Якщо це район — шукаємо саме район
    # -------------------------------------------------

    raion = None

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

    if raion:
        # Різні версії Neptun можуть називати поля по-різному.
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

        # -------------------------------------------------
        # 3. Якщо координат району немає —
        #    шукаємо центр за назвою району.
        #
        # Наприклад:
        # Броварський район → Бровари
        # Обухівський район → Обухів
        # Харківський район → Харків
        # -------------------------------------------------

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

    # -------------------------------------------------
    # 4. Звичайне місто
    # -------------------------------------------------

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

    # -------------------------------------------------
    # 5. Резерв — CITY_API
    # -------------------------------------------------

    coordinates = CITY_API.get(
        location_name
    )

    if coordinates:
        try:
            latitude, longitude = (
                coordinates.split(",")
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

    return None, None


# =====================================================
# ПОШУК АКТИВНИХ ЗАГРОЗ
# =====================================================

def normalize_oblast_name(value):
    """
    Нормалізує назву області для порівняння.

    NEPTUN / Threats API можуть повертати:
        "Київська область"
        "Київська"
        "київська обл."
        "Kyiv oblast"

    Для порівняння прибираємо лише службову частину назви.
    Сам текст загрози не змінюємо.
    """

    value = normalize(value)

    if not value:
        return ""

    replacements = (
        " область",
        " обл.",
        " обл",
        " oblast",
        " region",
    )

    for suffix in replacements:
        if value.endswith(suffix):
            value = value[:-len(suffix)].strip()

    return value


def get_threat_oblast(threat):
    """
    Визначає область загрози без геометричних припущень.

    Пріоритет:
    1. region з Threats API.
    2. district через NEPTUN.
    3. locality через NEPTUN.

    Якщо визначити область неможливо — повертаємо "".
    """

    if not isinstance(threat, dict):
        return ""

    region = (
        threat.get("region")
        or threat.get("oblast")
        or threat.get("oblastName")
        or ""
    )

    if region:
        return str(region).strip()

    district = (
        threat.get("district")
        or threat.get("raion")
        or threat.get("raionName")
        or ""
    )

    if district:
        try:
            raion = find_raion(
                str(district).strip()
            )

            if raion:
                oblast = (
                    raion.get("oblast_name")
                    or raion.get("oblast")
                    or ""
                )

                if oblast:
                    return str(oblast).strip()

        except Exception as e:
            print(
                f"⚠️ NEPTUN threat district lookup "
                f"{district}: {e}"
            )

    locality = (
        threat.get("locality")
        or threat.get("city")
        or ""
    )

    if locality:
        try:
            city = find_city_location(
                str(locality).strip()
            )

            if city:
                oblast = (
                    city.get("oblast_name")
                    or city.get("oblast")
                    or ""
                )

                if oblast:
                    return str(oblast).strip()

        except Exception as e:
            print(
                f"⚠️ NEPTUN threat locality lookup "
                f"{locality}: {e}"
            )

    return ""


def find_relevant_threats(
    location,
    threats_data,
    city_oblast,
):
    """
    Повертає ТІЛЬКИ активні загрози, які NEPTUN/Threats API
    можна віднести до області користувача.

    ВАЖЛИВО:
    - не використовуємо кілометраж;
    - не рахуємо власний радіус;
    - не трактуємо areaOnly як точку;
    - не вигадуємо район або населений пункт;
    - stale НЕ показуємо як "активну загрозу";
    - область визначаємо з region, а якщо його немає —
      через NEPTUN за district/locality.
    """

    result = []

    if not threats_data:
        return result

    target_oblast = normalize_oblast_name(
        city_oblast
    )

    if not target_oblast:
        print(
            "⚠️ THREATS | не вдалося визначити "
            "область користувача"
        )
        return result

    for threat in threats_data:

        if not isinstance(threat, dict):
            continue

        # ---------------------------------------------
        # Тільки реально активні.
        # ---------------------------------------------

        status = normalize(
            threat.get("status")
        )

        if status != "active":
            continue

        # ---------------------------------------------
        # Визначаємо область загрози.
        # ---------------------------------------------

        threat_oblast = get_threat_oblast(
            threat
        )

        normalized_threat_oblast = (
            normalize_oblast_name(
                threat_oblast
            )
        )

        if not normalized_threat_oblast:
            print(
                f"ℹ️ THREAT SKIP | "
                f"область не визначена | "
                f"title={threat.get('title')}"
            )
            continue

        # ---------------------------------------------
        # Порівнюємо області.
        # ---------------------------------------------

        if normalized_threat_oblast != target_oblast:
            continue

        area_only = bool(
            threat.get("areaOnly")
        )

        result.append(
            {
                "threat": threat,
                "area_only": area_only,
            }
        )

        print(
            f"🎯 ACTIVE THREAT RELEVANT | "
            f"title={threat.get('title')} | "
            f"region={threat.get('region')} | "
            f"district={threat.get('district')} | "
            f"locality={threat.get('locality')} | "
            f"oblast={threat_oblast} | "
            f"areaOnly={area_only}"
        )

    # Новіші записи першими.
    result.sort(
        key=lambda item: (
            item.get("threat", {}).get(
                "updatedAt",
                ""
            )
        ),
        reverse=True,
    )

    # ---------------------------------------------
    # Дублікати.
    # ---------------------------------------------

    unique = []
    seen = set()

    for item in result:

        threat = item.get(
            "threat",
            {},
        )

        threat_id = (
            threat.get("id")
            or (
                threat.get("title"),
                threat.get("type"),
                threat.get("district"),
                threat.get("locality"),
                threat.get("region"),
            )
        )

        if threat_id in seen:
            continue

        seen.add(
            threat_id
        )

        unique.append(
            item
        )

    print(
        f"📡 АКТИВНИХ ЗАГРОЗ ДЛЯ ОБЛАСТІ "
        f"{city_oblast}: {len(unique)}"
    )

    return unique


# =====================================================
# ФОРМУВАННЯ ЗАГРОЗИ
# =====================================================

def get_heading_text(
    heading,
):
    if heading is None:
        return ""

    try:
        value = float(heading) % 360
    except (TypeError, ValueError):
        return str(heading).strip()

    directions = (
        "північ",
        "північний схід",
        "схід",
        "південний схід",
        "південь",
        "південний захід",
        "захід",
        "північний захід",
    )

    index = int(
        (value + 22.5) // 45
    ) % 8

    return (
        f"{directions[index]} "
        f"({value:.0f}°)"
    )


def format_threat(
    item,
):
    threat = item.get(
        "threat",
        item,
    )

    area_only = bool(
        item.get("area_only")
        or threat.get("areaOnly")
    )

    threat_type = normalize(
        threat.get("type")
    )

    icons = {
        "uav": "🛸",
        "missile": "🚀",
        "ballistic": "💥",
        "kab": "💣",
        "mig31k": "✈️",
        "recon": "👀",
        "fpv": "🛸",
        "unknown": "❓",
    }

    icon = icons.get(
        threat_type,
        "❓",
    )

    title = (
        threat.get("title")
        or "Невідома загроза"
    )

    region = (
        threat.get("region")
        or ""
    )

    district = (
        threat.get("district")
        or ""
    )

    locality = (
        threat.get("locality")
        or ""
    )

    source_count = (
        threat.get("sourceCount")
        or 0
    )

    confidence = (
        threat.get("confidenceLevel")
        or ""
    )

    heading = threat.get(
        "heading"
    )

    if heading is None:
        velocity = threat.get(
            "velocity"
        )

        if isinstance(velocity, dict):
            heading = velocity.get(
                "bearingDeg"
            )

    speed = None
    velocity = threat.get(
        "velocity"
    )

    if isinstance(velocity, dict):
        speed = velocity.get(
            "speedKmh"
        )

    explanation = (
        threat.get("explanationShort")
        or ""
    )

    text = (
        f"{icon} <b>{title}</b>\n"
    )

    if region:
        text += (
            f"🗺 Область: "
            f"<b>{region}</b>\n"
        )

    # areaOnly не дозволяє видавати координатний центр
    # за точний населений пункт або район.
    if not area_only and district:
        text += (
            f"📍 Район: "
            f"<b>{district}</b>\n"
        )

    if not area_only and locality:
        text += (
            f"📌 Локація: "
            f"<b>{locality}</b>\n"
        )

    heading_text = get_heading_text(
        heading
    )

    if heading_text:
        text += (
            f"🧭 Напрямок: "
            f"<b>{heading_text}</b>\n"
        )

    if speed is not None:
        try:
            text += (
                f"💨 Швидкість: "
                f"<b>{float(speed):.0f} км/год</b>\n"
            )
        except (TypeError, ValueError):
            pass

    if confidence:
        text += (
            f"📊 Достовірність: "
            f"<b>{confidence}</b>\n"
        )

    if source_count:
        text += (
            f"🔎 Підтверджень: "
            f"<b>{source_count}</b>\n"
        )

    if explanation:
        text += (
            f"ℹ️ {explanation}\n"
        )

    if area_only:
        text += (
            "⚠️ Точне місце загрози "
            "не визначене."
        )

    return text.rstrip()


# =====================================================
# 🛰 ЗАГРОЗИ
# =====================================================

@router.message(
    lambda message:
    message.text == "🛰 Загрози"
)
async def threats(
    message: Message,
):

    user_id = (
        message.from_user.id
    )

    # =================================================
    # ЛОКАЦІЯ
    # =================================================

    location = get_location(
        user_id
    )

    # =================================================
    # СТАРА ЛОКАЦІЯ
    # =================================================

    if not location:

        city = get_city(
            user_id
        )

        if city:

            location = {
                "key": city.lower(),
                "name": city,
            }

    print(
        f"🛰 THREATS | "
        f"user_id={user_id} | "
        f"location={location}"
    )

    if not location:

        await message.answer(
            "❌ Спочатку оберіть "
            "свою локацію."
        )

        return

    city = (
        location.get("name")
        or get_city(user_id)
    )

    if not city:

        await message.answer(
            "❌ Не вдалося визначити "
            "вашу локацію."
        )

        return

    # =================================================
    # API
    # =================================================

    threats_api = (
        await asyncio.to_thread(
            get_threats
        )
    )

    alerts_api = (
        await asyncio.to_thread(
            get_alerts
        )
    )

    # =================================================
    # ТРИВОГА В МОЇЙ ЛОКАЦІЇ
    # =================================================

    city_alert = (
        get_city_alert_status(
            city,
            alerts_api,
            location=location,
        )
    )

    # =================================================
    # ОБЛАСТЬ
    #
    # Для Києва примусово:
    # Київська область.
    # =================================================

    city_oblast = get_city_oblast(
        city,
        location,
    )

    # =================================================
    # АКТИВНІ РАЙОНИ ОБЛАСТІ
    # =================================================

    active_oblast_raions = (
        get_active_oblast_raions(
            city_oblast,
            alerts_api,
        )
        if city_oblast
        else []
    )

    # =================================================
    # КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    threats_data = (
        threats_api.get(
            "threats",
            [],
        )
        if threats_api
        else []
    )

    nearby_threats = (
        find_relevant_threats(
            location,
            threats_data,
            city_oblast,
        )
    )

    print(
        f"🛰 STATUS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"active_raions="
        f"{len(active_oblast_raions)} | "
        f"threats="
        f"{len(nearby_threats)}"
    )

    # =================================================
    # ТЕКСТ
    # =================================================

    text = (
        "🛰 <b>СТАН БЕЗПЕКИ</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
    )

    # =================================================
    # МОЯ ЛОКАЦІЯ
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
    # ОБЛАСТЬ
    # =================================================

    if city_oblast:

        text += (
            f"🗺 <b>"
            f"{city_oblast.upper()}"
            f"</b>\n"
        )

        if active_oblast_raions:

            text += (
                "🔴 У частині області "
                "<b>АКТИВНА ТРИВОГА</b>\n\n"
            )

            text += (
                "📍 <b>Активні райони:</b>\n"
            )

            for item in active_oblast_raions:

                text += (
                    f"• "
                    f"{item.get('name', 'Невідомий район')}"
                    f"\n"
                )

            text += "\n"

        else:

            text += (
                "🟢 Активної тривоги "
                "в області не виявлено.\n\n"
            )

    # =================================================
    # АКТИВНІ ЗАГРОЗИ
    # =================================================

    text += (
        "🛰 <b>АКТИВНІ ЗАГРОЗИ</b>\n"
    )

    if nearby_threats:

        text += "\n"

        for item in nearby_threats:

            text += (
                format_threat(
                    item
                )
                + "\n\n"
            )

        text = text.rstrip()

    else:

        text += (
            "🟢 Активних загроз, "
            "віднесених до вашої області, "
            "не виявлено."
        )

    # =================================================
    # ПОЯСНЕННЯ
    # =================================================

    if (
        not city_alert
        and active_oblast_raions
    ):

        )

    # =================================================
    # ФІНАЛ
    # =================================================

    if city_alert:

        text += (
            "\n\n⚠️ <b>Перебувайте "
            "в безпечному місці.</b>"
        )

    elif nearby_threats:

        text += (
            "\n\n🟡 <b>У вашій області "
            "зафіксовані активні загрози.</b>\n"
            "Слідкуйте за офіційними "
            "повідомленнями."
        )

    elif active_oblast_raions:

        text += (
            "\n\n🟡 <b>У вашій області "
            "є активна тривога в іншому "
            "районі.</b>\n"
            "Слідкуйте за офіційними "
            "повідомленнями."
        )

    else:

        text += (
            "\n\n🛡 <b>Залишайтеся "
            "уважними.</b>"
        )

    # =================================================
    # ВІДПРАВКА
    # =================================================

    text += (
        "\n\n"
        "🔗 <a href=\"https://neptun.in.ua/\">NEPTUN</a>"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    print(
        f"✅ THREATS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"oblast_raions="
        f"{len(active_oblast_raions)} | "
        f"threats="
        f"{len(nearby_threats)}"
    )