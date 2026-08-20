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
# СУМІСНІСТЬ
# =====================================================
# Залишаємо константу, бо інші модулі старої версії
# можуть імпортувати її. Логіка нового threats.py
# її НЕ використовує для визначення загроз.
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

def find_relevant_threats(
    location,
    threats_data,
    city_oblast,
):
    """
    Показує активні загрози так, як вони визначені NEPTUN:
    - область (region)
    - район (district)
    - населений пункт (locality)
    - курс (heading / velocity.bearingDeg)
    - тип, достовірність, підтвердження
    - без власного радіуса та без розрахунку "відстані".

    Для areaOnly=True не використовуємо координати як точну
    позицію і не вигадуємо район/населений пункт.
    """

    result = []

    if not threats_data:
        return result

    target_city = normalize(
        (location or {}).get("name")
    )

    target_oblast = normalize(
        city_oblast
    )

    for threat in threats_data:

        if not isinstance(threat, dict):
            continue

        status = normalize(
            threat.get("status")
        )

        if status not in (
            "active",
            "stale",
        ):
            continue

        region = normalize(
            threat.get("region")
        )

        district = normalize(
            threat.get("district")
        )

        locality = normalize(
            threat.get("locality")
        )

        # areaOnly означає, що координати не можна трактувати
        # як точне місце загрози.
        area_only = bool(
            threat.get("areaOnly")
        )

        # Для звичайної точкової загрози залишаємо її,
        # якщо вона відноситься до області користувача.
        # Для Києва окремо допускаємо записи, що прямо
        # стосуються Києва.
        matches_oblast = (
            bool(target_oblast)
            and region == target_oblast
        )

        matches_city = (
            bool(target_city)
            and locality == target_city
        )

        if not (
            matches_oblast
            or matches_city
        ):
            continue

        result.append(
            {
                "threat": threat,
                "area_only": area_only,
            }
        )

        print(
            f"🎯 THREAT RELEVANT | "
            f"{threat.get('title')} | "
            f"region={threat.get('region')} | "
            f"district={threat.get('district')} | "
            f"locality={threat.get('locality')} | "
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
                threat.get("region"),
                threat.get("district"),
                threat.get("locality"),
                threat.get("updatedAt"),
            )
        )

        if threat_id in seen:
            continue

        seen.add(threat_id)
        unique.append(item)

    print(
        f"📡 Релевантних загроз "
        f"для {location.get('name') if location else ''}: "
        f"{len(unique)}"
    )

    return unique


# Зворотна сумісність для інших імпортів.
def find_nearby_threats(
    location,
    threats_data,
):
    return find_relevant_threats(
        location,
        threats_data,
        "",
    )


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