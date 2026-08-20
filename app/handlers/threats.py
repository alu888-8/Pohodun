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

def get_location_admin_info(
    location,
    city,
):
    """
    Визначає адміністративну прив'язку локації через NEPTUN.

    Повертає:
        oblast_name,
        raion_key,
        raion_name.

    Не використовуємо координати для визначення того,
    чи є загроза релевантною для користувача.
    """

    oblast_name = normalize(
        location.get("oblast_name")
        or location.get("oblast")
        or ""
    ) if location else ""

    raion_key = normalize(
        location.get("raion_key")
        or ""
    ) if location else ""

    raion_name = normalize(
        location.get("raion_name")
        or ""
    ) if location else ""

    location_key = normalize(
        location.get("key")
        or ""
    ) if location else ""

    # Район NEPTUN — головне джерело.
    if not raion_key and location_key:
        try:
            raion = find_raion(
                location_key
            )
        except Exception as e:
            print(
                f"⚠️ NEPTUN raion lookup error "
                f"{location_key}: {e}"
            )
            raion = None

        if raion:
            raion_key = normalize(
                raion.get("key")
            )
            raion_name = normalize(
                raion.get("name")
            )
            oblast_name = normalize(
                raion.get("oblast_name")
                or raion.get("oblast")
                or oblast_name
            )

    # Якщо району ще немає — беремо місто з NEPTUN.
    if city and (
        not raion_key
        or not oblast_name
    ):
        try:
            neptun_city = find_city_location(
                city
            )
        except Exception as e:
            print(
                f"⚠️ NEPTUN city lookup error "
                f"{city}: {e}"
            )
            neptun_city = None

        if neptun_city:
            raion_key = raion_key or normalize(
                neptun_city.get("raion_key")
            )
            raion_name = raion_name or normalize(
                neptun_city.get("raion_name")
            )
            oblast_name = oblast_name or normalize(
                neptun_city.get("oblast_name")
                or neptun_city.get("oblast")
            )

    # Київ — окрема адміністративна одиниця.
    if normalize(city) in ("київ", "kyiv"):
        oblast_name = normalize(
            "Київська область"
        )
        raion_key = ""
        raion_name = ""

    return (
        oblast_name,
        raion_key,
        raion_name,
    )


def _same_admin_value(
    value,
    target,
):
    """Порівнює адміністративні назви без зайвих припущень."""

    value = normalize(value)
    target = normalize(target)

    if not value or not target:
        return False

    return value == target


def find_nearby_threats(
    location,
    threats_data,
    city=None,
    city_oblast=None,
):
    """
    Повертає тільки адміністративно релевантні загрози NEPTUN.

    ВАЖЛИВО:
    Кілометри НЕ використовуються для визначення релевантності.
    Координати areaOnly також НЕ використовуються.

    Для точкової загрози:
        - показуємо її, якщо locality = місто користувача;
        - або якщо district = район користувача.

    Для areaOnly=True:
        - точне місце невідоме;
        - показуємо лише як обласну загрозу тієї самої області;
        - не показуємо курс та не робимо висновок про близькість.
    """

    result = []

    if not location or not threats_data:
        return result

    city_name = (
        city
        or location.get("name")
        or ""
    )

    user_oblast, user_raion_key, user_raion_name = (
        get_location_admin_info(
            location,
            city_name,
        )
    )

    if city_oblast:
        user_oblast = normalize(
            city_oblast
        )

    print(
        f"📍 NEPTUN ADMIN | "
        f"city={city_name} | "
        f"oblast={user_oblast} | "
        f"raion={user_raion_name}"
    )

    for threat in threats_data:
        if not isinstance(threat, dict):
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

        threat_region = normalize(
            threat.get("region")
        )

        threat_district = normalize(
            threat.get("district")
        )

        threat_locality = normalize(
            threat.get("locality")
        )

        area_only = bool(
            threat.get("areaOnly", False)
        )

        relevant = False
        relevance = ""

        # =================================================
        # AREA ONLY
        # =================================================

        if area_only:
            if (
                user_oblast
                and threat_region
                and _same_admin_value(
                    threat_region,
                    user_oblast,
                )
            ):
                relevant = True
                relevance = "oblast"

        # =================================================
        # ТОЧКОВА ЗАГРОЗА
        # =================================================

        else:
            # Для Києва locality=Київ — єдина безпечна
            # точна міська прив'язка. Київська область
            # автоматично до Києва не прирівнюється.
            if (
                normalize(city_name) in ("київ", "kyiv")
                and threat_locality in (
                    "київ",
                    "kyiv",
                    "м. київ",
                    "місто київ",
                )
            ):
                relevant = True
                relevance = "city"

            # Для інших міст — точна locality.
            elif (
                threat_locality
                and _same_admin_value(
                    threat_locality,
                    city_name,
                )
            ):
                relevant = True
                relevance = "city"

            # Район NEPTUN — другий рівень прив'язки.
            elif (
                threat_district
                and user_raion_name
                and _same_admin_value(
                    threat_district,
                    user_raion_name,
                )
            ):
                relevant = True
                relevance = "raion"

            elif (
                threat_region
                and user_oblast
                and threat_district
                and user_raion_key
                and threat_district == user_raion_key
            ):
                relevant = True
                relevance = "raion_key"

        if not relevant:
            continue

        result.append(
            {
                "threat": threat,
                "distance": None,
                "area_only": area_only,
                "relevance": relevance,
            }
        )

        print(
            f"🎯 NEPTUN THREAT MATCH | "
            f"{threat.get('type')} | "
            f"locality={threat.get('locality')} | "
            f"district={threat.get('district')} | "
            f"region={threat.get('region')} | "
            f"areaOnly={area_only} | "
            f"relevance={relevance}"
        )

    # Точні міські/районні загрози першими,
    # areaOnly — після них.
    result.sort(
        key=lambda item: (
            item.get("area_only", False),
            item.get("relevance") == "oblast",
        )
    )

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
                threat.get("type"),
                threat.get("locality"),
                threat.get("district"),
                threat.get("region"),
                threat.get("updatedAt"),
            )
        )

        if threat_id in seen:
            continue

        seen.add(threat_id)
        unique.append(item)

    print(
        f"📡 NEPTUN релевантних загроз "
        f"для {city_name}: {len(unique)}"
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
        "unknown": "❓",
    }.get(
        normalize(threat_type),
        "❓",
    )



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
    Формує загрозу без штучного визначення відстані або цілі.

    locality/district/region — це адміністративні дані NEPTUN.
    destination та presumptiveCourse не використовуємо,
    бо вони не є базовими полями актуальної схеми Threats API.
    """

    threat = item.get(
        "threat",
        item,
    )

    area_only = bool(
        item.get("area_only", False)
        or threat.get("areaOnly", False)
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

    confidence = (
        threat.get("confidenceLevel")
        or threat.get("displayConfidence")
        or ""
    )

    updated_at = (
        threat.get("updatedAt")
        or ""
    )

    uncertainty = (
        threat.get("uncertaintyKm")
    )

    position_quality = (
        threat.get("positionQuality")
        or ""
    )

    advisory = bool(
        threat.get("advisory", False)
    )

    heading = ""
    if not area_only and not advisory:
        heading = get_heading_text(
            threat.get("heading")
        )

    text = (
        f"{icon} <b>Загроза: "
        f"{type_name}</b>\n"
    )

    if area_only:
        text += (
            "⚠️ <b>Точне місце загрози "
            "не визначене.</b>\n"
        )

    if advisory:
        text += (
            "ℹ️ Інформаційне спостереження NEPTUN.\n"
        )

    if locality:
        text += (
            f"📍 Локація: <b>{locality}</b>\n"
        )

    if district:
        text += (
            f"🏙 Район: {district}\n"
        )

    if region:
        text += (
            f"🗺 Область: {region}\n"
        )

    if heading:
        text += (
            f"🧭 Курс: <b>{heading}</b>\n"
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

        confidence_text = confidence_names.get(
            normalize(confidence),
            str(confidence),
        )

        text += (
            f"📊 Достовірність: "
            f"<b>{confidence_text}</b>\n"
        )

    # Похибку можна показувати як якість координат,
    # але НЕ перетворюємо її на відстань до користувача.
    if (
        uncertainty is not None
        and not area_only
    ):
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

    if position_quality:
        text += (
            f"📍 Якість позиції: "
            f"<b>{position_quality}</b>\n"
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
            city=city,
            city_oblast=city_oblast,
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
    # АКТИВНІ ЗАГРОЗИ NEPTUN
    # Показуємо блок тільки якщо
    # NEPTUN реально знайшов загрозу.
    # =================================================

    if nearby_threats:

        text += (
            "📡 <b>АКТИВНІ ЗАГРОЗИ</b>\n\n"
        )

        for item in nearby_threats:

            text += (
                format_threat(
                    item
                )
                + "\n\n"
            )

        text = text.rstrip()

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
            "\n\n🟡 <b>Є активна загроза, "
            "адміністративно пов'язана "
            "з вашою локацією.</b>\n"
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