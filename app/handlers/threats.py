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

THREAT_RADIUS_KM = 70


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
# ПОШУК КОНКРЕТНИХ ЗАГРОЗ ПОБЛИЗУ
# =====================================================

def find_nearby_threats(
    location,
    threats_data,
):

    """
    Повертає конкретні активні загрози
    в радіусі THREAT_RADIUS_KM.

    Координати локації:
        1. location
        2. Neptun
        3. CITY_API

    Координати загроз:
        Threats API.
    """

    result = []

    if not location:
        return result

    if not threats_data:
        return result

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
            f"❌ Немає координат для "
            f"{location.get('name')}"
        )

        return result

    print(
        f"📍 THREAT LOCATION | "
        f"{location.get('name')} | "
        f"{latitude}, {longitude}"
    )

    # =================================================
    # ПЕРЕВІРЯЄМО ВСІ ЗАГРОЗИ
    # =================================================

    for threat in threats_data:

        if not isinstance(
            threat,
            dict,
        ):
            continue

        # -------------------------------------------------
        # Тільки активні
        # -------------------------------------------------

        status = normalize(
            threat.get("status")
        )

        if status not in (
            "active",
            "activated",
            "stale",
        ):

            continue

        # -------------------------------------------------
        # Координати загрози
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Відстань
        # -------------------------------------------------

        distance = distance_km(
            latitude,
            longitude,
            threat_lat,
            threat_lon,
        )

        if distance is None:
            continue

        # -------------------------------------------------
        # Радіус
        # -------------------------------------------------

        if distance > THREAT_RADIUS_KM:
            continue

        result.append(
            {
                "threat": threat,
                "distance": distance,
            }
        )

        print(
            f"🎯 THREAT NEAR "
            f"{location.get('name')}: "
            f"{threat.get('title')} | "
            f"{threat.get('locality')} | "
            f"{distance:.1f} км"
        )

    # =================================================
    # Найближчі першими
    # =================================================

    result.sort(
        key=lambda item:
        item.get(
            "distance",
            999999,
        )
    )

    # =================================================
    # Дублікати
    # =================================================

    unique = []

    seen = set()

    for item in result:

        threat = item.get(
            "threat",
            {}
        )

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
            item
        )

    print(
        f"📡 Загроз поблизу "
        f"{location.get('name')}: "
        f"{len(unique)}"
    )

    return unique


# =====================================================
# ВИЗНАЧЕННЯ ТРИВОГИ В МІСТІ
# =====================================================

def get_city_alert_status(
    city,
    alerts_data,
    location=None,
):

    if not city:
        return False

    if not alerts_data:
        return False

    city_key = normalize(
        city
    )

    # =================================================
    # КИЇВ
    #
    # Київ — окрема адміністративна одиниця.
    #
    # НЕ МОЖНА брати:
    # Бориспільський район
    # Броварський район
    #
    # за тривогу в Києві.
    # =================================================

    if city_key in (
        "київ",
        "kyiv",
    ):

        for item in (
            alerts_data.get(
                "raions",
                []
            )
            +
            alerts_data.get(
                "oblasts",
                []
            )
        ):

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

                print(
                    "🚨 CITY ALERT | "
                    "city=Київ | active=True"
                )

                return True

            if name in (
                "київ",
                "м. київ",
                "місто київ",
            ):

                print(
                    "🚨 CITY ALERT | "
                    "city=Київ | active=True"
                )

                return True

        print(
            "🟢 CITY ALERT | "
            "city=Київ | active=False"
        )

        return False

    # =================================================
    # РАЙОН МІСТА
    #
    # Беремо його безпосередньо
    # з location, якщо є.
    # =================================================

    target_raion_key = ""

    target_raion_name = ""

    if location:

        target_raion_key = normalize(
            location.get(
                "raion_key"
            )
        )

        target_raion_name = normalize(
            location.get(
                "raion_name"
            )
        )

    # =================================================
    # Якщо location не має району:
    # 1. спочатку перевіряємо, чи сама location є районом;
    # 2. потім пробуємо знайти місто через Neptun.
    # =================================================

    if not target_raion_key:

        location_key = ""

        if location:
            location_key = normalize(
                location.get("key")
            )

        if location_key:

            try:

                raion = find_raion(
                    location_key
                )

                if raion:

                    target_raion_key = normalize(
                        raion.get("key")
                    )

                    target_raion_name = normalize(
                        raion.get("name")
                    )

                    print(
                        f"📍 LOCATION RAION | "
                        f"{city} → "
                        f"{raion.get('name')}"
                    )

            except Exception as e:

                print(
                    f"⚠️ Neptun direct raion error "
                    f"{location_key}: {e}"
                )

    if not target_raion_key:

        try:

            neptun_city = (
                find_city_location(
                    city
                )
            )

            if neptun_city:

                target_raion_key = normalize(
                    neptun_city.get(
                        "raion_key"
                    )
                )

                target_raion_name = normalize(
                    neptun_city.get(
                        "raion_name"
                    )
                )

        except Exception as e:

            print(
                f"⚠️ Neptun city raion error "
                f"{city}: {e}"
            )

    # =================================================
    # Перевіряємо райони
    # =================================================

    if target_raion_key:

        for item in alerts_data.get(
            "raions",
            [],
        ):

            item_key = normalize(
                item.get("key")
            )

            item_name = normalize(
                item.get("name")
            )

            if item_key == target_raion_key:

                print(
                    f"🚨 CITY ALERT | "
                    f"city={city} | "
                    f"raion={item.get('name')} | "
                    f"active=True"
                )

                return True

            if (
                target_raion_name
                and item_name
                == target_raion_name
            ):

                print(
                    f"🚨 CITY ALERT | "
                    f"city={city} | "
                    f"raion={item.get('name')} | "
                    f"active=True"
                )

                return True

        return False

    # =================================================
    # РЕЗЕРВНА ПЕРЕВІРКА
    # =================================================

    for item in (
        alerts_data.get(
            "raions",
            []
        )
        +
        alerts_data.get(
            "oblasts",
            []
        )
    ):

        key = normalize(
            item.get("key")
        )

        name = normalize(
            item.get("name")
        )

        if key == city_key:
            return True

        if name == city_key:
            return True

    return False


# =====================================================
# АКТИВНІ РАЙОНИ КОНКРЕТНОЇ ОБЛАСТІ
# =====================================================

def get_active_oblast_raions(
    oblast_name,
    alerts_data,
):

    if not oblast_name:
        return []

    if not alerts_data:
        return []

    target_oblast = normalize(
        oblast_name
    )

    result = []

    for item in alerts_data.get(
        "raions",
        [],
    ):

        item_oblast = normalize(
            item.get("oblast")
        )

        if item_oblast != target_oblast:
            continue

        result.append(
            item
        )

    return result


# =====================================================
# НАЗВА ОБЛАСТІ ДЛЯ МІСТА
# =====================================================

def get_city_oblast(
    city,
    location=None,
):

    city_key = normalize(
        city
    )

    # =================================================
    # КИЇВ
    #
    # Окремо від Київської області.
    # =================================================

    if city_key in (
        "київ",
        "kyiv",
    ):

        return "Київська область"

    # =================================================
    # Дані з location
    # =================================================

    if location:

        oblast = (
            location.get(
                "oblast_name"
            )
            or location.get(
                "oblast"
            )
            or ""
        )

        oblast_key = normalize(
            oblast
        )

        # Старий запис міг містити
        # "Київ" замість "Київська область".
        if oblast_key in (
            "київ",
            "kyiv",
        ):

            return "Київська область"

        if oblast:
            return oblast

    # =================================================
    # Neptun — спочатку район, потім місто
    # =================================================

    if location:

        location_key = normalize(
            location.get("key")
        )

        if location_key:

            try:

                raion = find_raion(
                    location_key
                )

                if raion:

                    oblast = (
                        raion.get(
                            "oblast_name"
                        )
                        or raion.get(
                            "oblast"
                        )
                        or ""
                    )

                    if oblast:
                        return oblast

            except Exception as e:

                print(
                    f"⚠️ Neptun direct raion oblast error "
                    f"{location_key}: {e}"
                )

    try:

        neptun_city = (
            find_city_location(
                city
            )
        )

        if neptun_city:

            oblast = (
                neptun_city.get(
                    "oblast_name"
                )
            )

            if oblast:
                return oblast

    except Exception as e:

        print(
            f"⚠️ Neptun city oblast error "
            f"{city}: {e}"
        )

    return ""


# =====================================================
# ФОРМУВАННЯ ЗАГРОЗИ
# =====================================================

THREAT_TYPE_NAMES = {
    "uav": "БпЛА",
    "missile": "ракета",
    "ballistic": "балістика",
    "kab": "КАБ",
    "mig31k": "МіГ-31К",
    "recon": "розвідувальна загроза",
    "fpv": "FPV-дрон",
    "unknown": "невідома загроза",
}


def get_threat_type_name(
    threat,
):
    """
    Перетворює type з Threats API
    у нормальну українську назву.

    Нічого не вигадуємо:
    беремо саме поле type.
    """

    threat_type = normalize(
        threat.get("type")
    )

    return THREAT_TYPE_NAMES.get(
        threat_type,
        threat.get("title")
        or "невідома загроза",
    )


def get_heading_text(
    heading,
):
    """
    Перетворює курс у градусах
    на зрозумілий напрямок.

    Наприклад:
        0   → північ
        90  → схід
        180 → південь
        270 → захід
    """

    if heading is None:
        return ""

    try:
        value = float(
            heading
        )

    except (
        TypeError,
        ValueError,
    ):
        return str(
            heading
        ).strip()

    value %= 360

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
    """
    Формує одну актуальну загрозу.

    ВАЖЛИВО:
    Тип загрози показуємо явно:
        Загроза: БпЛА
        Загроза: балістика
        Загроза: ракета
        Загроза: КАБ
        тощо.

    Додаткові дані показуємо тільки якщо
    вони реально є у Threats API.
    """

    threat = item.get(
        "threat",
        item,
    )

    distance = item.get(
        "distance"
    )

    threat_type = normalize(
        threat.get("type")
    )

    type_name = get_threat_type_name(
        threat
    )

    icon = get_threat_icon(
        threat_type
    )

    locality = (
        threat.get("locality")
        or ""
    )

    region = (
        threat.get("region")
        or ""
    )

    district = (
        threat.get("district")
        or ""
    )

    source_count = (
        threat.get("sourceCount")
        or 0
    )

    heading = get_heading_text(
        threat.get("heading")
    )

    destination = threat.get(
        "destination"
    )

    presumptive_course = threat.get(
        "presumptiveCourse"
    )

    uncertainty = threat.get(
        "uncertaintyKm"
    )

    confidence = (
        threat.get("confidenceLevel")
        or threat.get("displayConfidence")
        or ""
    )

    updated_at = (
        threat.get("updatedAt")
        or ""
    )

    explanation = (
        threat.get("explanationShort")
        or ""
    )

    text = (
        f"{icon} <b>Загроза: "
        f"{type_name}</b>\n"
    )

    if locality:
        text += (
            f"📍 {locality}\n"
        )

    if district:
        text += (
            f"🏙 {district}\n"
        )

    if region:
        text += (
            f"🗺 {region}\n"
        )

    if distance is not None:
        text += (
            f"📏 Відстань: "
            f"<b>{distance:.0f} км</b>\n"
        )

    if heading:
        text += (
            f"🧭 Курс: "
            f"<b>{heading}</b>\n"
        )

    if destination:
        if locality:
            text += (
                "🎯 Визначено напрямок/ціль "
                f"на <b>{locality}</b>\n"
            )
        else:
            text += (
                "🎯 Визначено напрямок/ціль\n"
            )

    elif presumptive_course:
        text += (
            "🧭 Курс визначений "
            "орієнтовно\n"
        )

    if source_count:
        text += (
            f"🔎 Підтверджень: "
            f"<b>{source_count}</b>\n"
        )

    if confidence:
        confidence_names = {
            "high": "висока",
            "medium": "середня",
            "low": "низька",
        }

        confidence_text = (
            confidence_names.get(
                normalize(confidence),
                str(confidence),
            )
        )

        text += (
            f"📊 Достовірність: "
            f"<b>{confidence_text}</b>\n"
        )

    if uncertainty is not None:
        try:
            uncertainty_value = float(
                uncertainty
            )

            text += (
                f"🎯 Похибка позиції: "
                f"≈ {uncertainty_value:.1f} км\n"
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    if explanation:
        text += (
            f"ℹ️ {explanation}\n"
        )

    if updated_at:
        text += (
            f"🕒 Оновлено: "
            f"<code>{updated_at}</code>"
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
        find_nearby_threats(
            location,
            threats_data,
        )
    )

    print(
        f"🛰 STATUS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"active_raions="
        f"{len(active_oblast_raions)} | "
        f"nearby="
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
    # ЗАГРОЗИ ПОБЛИЗУ
    # =================================================

    text += (
        "📡 <b>КОНКРЕТНІ ЗАГРОЗИ "
        "ПОБЛИЗУ</b>\n"
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
            "🟢 Конкретних активних "
            "загроз у радіусі "
            f"{THREAT_RADIUS_KM} км "
            "не виявлено."
        )

    # =================================================
    # ПОЯСНЕННЯ
    # =================================================

    if (
        not city_alert
        and active_oblast_raions
    ):

        text += (
            "\n\nℹ️ <b>Важливо:</b> "
            "тривога в іншому районі "
            "області не означає автоматично "
            f"тривогу в місті {city}."
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
            "\n\n🟡 <b>Поблизу є "
            "конкретна активна загроза.</b>\n"
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

    await message.answer(
        text,
        parse_mode="HTML",
    )

    print(
        f"✅ THREATS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"oblast_raions="
        f"{len(active_oblast_raions)} | "
        f"nearby="
        f"{len(nearby_threats)}"
    )