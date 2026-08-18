import math
import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city, get_location
from app.data.cities import CITY_API
from app.data.regions import CITY_REGIONS

from app.services.threats import get_threats
from app.services.alerts import get_alerts
from app.services.neptun_locations import find_city_location


router = Router()


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

THREAT_RADIUS_KM = 70


# =====================================================
# МІСТО → РАЙОН
#
# Для міст, де API працює по районах,
# визначаємо район, до якого належить місто.
# =====================================================

CITY_RAIONS = {

    # -------------------------
    # КИЇВСЬКА ОБЛАСТЬ
    # -------------------------

    "Біла Церква": "Білоцерківський район",
    "Бровари": "Броварський район",
    "Бориспіль": "Бориспільський район",
    "Буча": "Бучанський район",
    "Ірпінь": "Бучанський район",
    "Вишгород": "Вишгородський район",
    "Фастів": "Фастівський район",
    "Обухів": "Обухівський район",

    # -------------------------
    # ЧЕРНІГІВСЬКА ОБЛАСТЬ
    # -------------------------

    "Чернігів": "Чернігівський район",
    "Ніжин": "Ніжинський район",
    "Прилуки": "Прилуцький район",
    "Корюківка": "Корюківський район",

    # -------------------------
    # ЖИТОМИРСЬКА ОБЛАСТЬ
    # -------------------------

    "Житомир": "Житомирський район",
    "Бердичів": "Бердичівський район",
    "Коростень": "Коростенський район",
    "Звягель": "Звягельський район",

    # -------------------------
    # ВІННИЦЬКА ОБЛАСТЬ
    # -------------------------

    "Вінниця": "Вінницький район",
    "Жмеринка": "Жмеринський район",
    "Могилів-Подільський": "Могилів-Подільський район",
    "Хмільник": "Хмільницький район",

    # -------------------------
    # ВОЛИНСЬКА ОБЛАСТЬ
    # -------------------------

    "Луцьк": "Луцький район",
    "Ковель": "Ковельський район",
    "Володимир": "Володимирський район",
    "Камінь-Каширський": "Камінь-Каширський район",

    # -------------------------
    # РІВНЕНСЬКА ОБЛАСТЬ
    # -------------------------

    "Рівне": "Рівненський район",
    "Дубно": "Дубенський район",
    "Вараш": "Вараський район",
    "Сарни": "Сарненський район",

    # -------------------------
    # ЛЬВІВСЬКА ОБЛАСТЬ
    # -------------------------

    "Львів": "Львівський район",
    "Дрогобич": "Дрогобицький район",
    "Стрий": "Стрийський район",
    "Червоноград": "Червоноградський район",
    "Самбір": "Самбірський район",
    "Золочів": "Золочівський район",

    # -------------------------
    # ТЕРНОПІЛЬСЬКА ОБЛАСТЬ
    # -------------------------

    "Тернопіль": "Тернопільський район",
    "Чортків": "Чортківський район",
    "Кременець": "Кременецький район",

    # -------------------------
    # ХМЕЛЬНИЦЬКА ОБЛАСТЬ
    # -------------------------

    "Хмельницький": "Хмельницький район",
    "Кам'янець-Подільський": "Кам'янець-Подільський район",
    "Шепетівка": "Шепетівський район",

    # -------------------------
    # ЧЕРНІВЕЦЬКА ОБЛАСТЬ
    # -------------------------

    "Чернівці": "Чернівецький район",
    "Вижниця": "Вижницький район",
    "Дністровський": "Дністровський район",

    # -------------------------
    # ІВАНО-ФРАНКІВСЬКА ОБЛАСТЬ
    # -------------------------

    "Івано-Франківськ": "Івано-Франківський район",
    "Калуш": "Калуський район",
    "Коломия": "Коломийський район",
    "Надвірна": "Надвірнянський район",

    # -------------------------
    # ЗАКАРПАТСЬКА ОБЛАСТЬ
    # -------------------------

    "Ужгород": "Ужгородський район",
    "Мукачево": "Мукачівський район",
    "Хуст": "Хустський район",
    "Берегове": "Берегівський район",

    # -------------------------
    # ОДЕСЬКА ОБЛАСТЬ
    # -------------------------

    "Одеса": "Одеський район",
    "Ізмаїл": "Ізмаїльський район",
    "Білгород-Дністровський": "Білгород-Дністровський район",
    "Подільськ": "Подільський район",

    # -------------------------
    # МИКОЛАЇВСЬКА ОБЛАСТЬ
    # -------------------------

    "Миколаїв": "Миколаївський район",
    "Вознесенськ": "Вознесенський район",
    "Первомайськ": "Первомайський район",

    # -------------------------
    # ХЕРСОНСЬКА ОБЛАСТЬ
    # -------------------------

    "Херсон": "Херсонський район",
    "Берислав": "Бериславський район",
    "Генічеськ": "Генічеський район",

    # -------------------------
    # ЗАПОРІЗЬКА ОБЛАСТЬ
    # -------------------------

    "Запоріжжя": "Запорізький район",
    "Бердянськ": "Бердянський район",
    "Мелітополь": "Мелітопольський район",
    "Василівка": "Василівський район",

    # -------------------------
    # ДНІПРОПЕТРОВСЬКА ОБЛАСТЬ
    # -------------------------

    "Дніпро": "Дніпровський район",
    "Кам'янське": "Кам’янський район",
    "Кривий Ріг": "Криворізький район",
    "Нікополь": "Нікопольський район",
    "Синельникове": "Синельниківський район",

    # -------------------------
    # ПОЛТАВСЬКА ОБЛАСТЬ
    # -------------------------

    "Полтава": "Полтавський район",
    "Кременчук": "Кременчуцький район",
    "Лубни": "Лубенський район",
    "Миргород": "Миргородський район",

    # -------------------------
    # ХАРКІВСЬКА ОБЛАСТЬ
    # -------------------------

    "Харків": "Харківський район",
    "Ізюм": "Ізюмський район",
    "Куп'янськ": "Куп'янський район",
    "Чугуїв": "Чугуївський район",
    "Богодухів": "Богодухівський район",

    # -------------------------
    # СУМСЬКА ОБЛАСТЬ
    # -------------------------

    "Суми": "Сумський район",
    "Конотоп": "Конотопський район",
    "Шостка": "Шосткинський район",
    "Охтирка": "Охтирський район",
    "Ромни": "Роменський район",

    # -------------------------
    # ЧЕРКАСЬКА ОБЛАСТЬ
    # -------------------------

    "Черкаси": "Черкаський район",
    "Умань": "Уманський район",
    "Золотоноша": "Золотоніський район",
    "Звенигородка": "Звенигородський район",

    # -------------------------
    # КІРОВОГРАДСЬКА ОБЛАСТЬ
    # -------------------------

    "Кропивницький": "Кропивницький район",
    "Олександрія": "Олександрійський район",
    "Голованівськ": "Голованівський район",

    # -------------------------
    # ДОНЕЦЬКА ОБЛАСТЬ
    # -------------------------

    "Краматорськ": "Краматорський район",
    "Слов'янськ": "Краматорський район",
    "Покровськ": "Покровський район",
    "Бахмут": "Бахмутський район",
}


# =====================================================
# ОБЛАСТЬ МІСТА
# =====================================================

CITY_OBLASTS = {

    "Київ": "Київська область",

    "Біла Церква": "Київська область",
    "Бровари": "Київська область",
    "Бориспіль": "Київська область",
    "Буча": "Київська область",
    "Ірпінь": "Київська область",
    "Вишгород": "Київська область",
    "Фастів": "Київська область",
    "Обухів": "Київська область",

    "Чернігів": "Чернігівська область",
    "Ніжин": "Чернігівська область",
    "Прилуки": "Чернігівська область",
    "Корюківка": "Чернігівська область",

    "Житомир": "Житомирська область",
    "Вінниця": "Вінницька область",
    "Луцьк": "Волинська область",
    "Рівне": "Рівненська область",
    "Львів": "Львівська область",
    "Тернопіль": "Тернопільська область",
    "Хмельницький": "Хмельницька область",
    "Чернівці": "Чернівецька область",
    "Івано-Франківськ": "Івано-Франківська область",
    "Ужгород": "Закарпатська область",
    "Одеса": "Одеська область",
    "Миколаїв": "Миколаївська область",
    "Херсон": "Херсонська область",
    "Запоріжжя": "Запорізька область",
    "Дніпро": "Дніпропетровська область",
    "Полтава": "Полтавська область",
    "Харків": "Харківська область",
    "Суми": "Сумська область",
    "Черкаси": "Черкаська область",
    "Кропивницький": "Кіровоградська область",
}


# =====================================================
# ВІДСТАНЬ МІЖ КООРДИНАТАМИ
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
            f"❌ Помилка координат "
            f"{city}: {e}"
        )

        return None


# =====================================================
# ПЕРЕВІРКА АКТИВНОСТІ
# =====================================================

def is_alert_active(item):

    if not item:
        return False

    return bool(
        item.get("since")
    )


# =====================================================
# СТАН КОНКРЕТНОГО МІСТА
# =====================================================

def get_city_alert_status(
    city,
    alerts_data,
    location=None,
):
    """Перевіряє тривогу саме для вибраної локації."""

    if not alerts_data:
        return False

    # Київ — окрема адміністративна одиниця.
    if city == "Київ":
        items = (
            alerts_data.get("raions", [])
            + alerts_data.get("oblasts", [])
        )

        for item in items:
            name = item.get("name", "").strip().lower()
            key = item.get("key", "").strip().lower()
            if name in ("київ", "м. київ", "місто київ") or key in ("київ", "м. київ", "місто київ"):
                return is_alert_active(item)
        return False

    city_raion = None

    if location:
        city_raion = location.get("raion_name") or location.get("raion")

    if not city_raion:
        try:
            neptun_city = find_city_location(city)
            if neptun_city:
                city_raion = neptun_city.get("raion_name")
        except Exception as e:
            print(f"⚠️ Neptun location lookup failed for {city}: {e}")

    if not city_raion:
        city_raion = CITY_RAIONS.get(city)

    if not city_raion:
        return False

    target = city_raion.lower().strip()

    for item in alerts_data.get("raions", []):
        name = item.get("name", "").strip().lower()
        key = item.get("key", "").strip().lower()

        if name == target or key == target:
            active = is_alert_active(item)
            print(f"🚨 CITY ALERT | city={city} | raion={name or key} | active={active}")
            return active

    return False


# =====================================================
# АКТИВНІ РАЙОНИ ОБЛАСТІ
# =====================================================

def get_active_oblast_raions(
    oblast,
    alerts_data
):

    if not alerts_data or not oblast:
        return []

    result = []

    target = (
        oblast
        .strip()
        .lower()
    )

    for item in alerts_data.get(
        "raions",
        []
    ):

        item_oblast = (
            item.get(
                "oblast",
                ""
            )
            .strip()
            .lower()
        )

        if item_oblast != target:
            continue

        if is_alert_active(item):

            result.append(item)

    return result


# =====================================================
# КОНКРЕТНІ ЗАГРОЗИ ПОБЛИЗУ
# =====================================================

def find_nearby_threats(
    location,
    threats_data
):
    """
    Повертає конкретні активні загрози в радіусі THREAT_RADIUS_KM
    від вибраної локації моніторингу.

    Координати беруться саме з location, а якщо їх немає —
    додатково шукаються через Neptun.
    API загроз підтримує як lat/lon, так і latitude/longitude.
    """

    result = []

    if not threats_data or not location:
        return result

    # =================================================
    # КООРДИНАТИ ВИБРАНОЇ ЛОКАЦІЇ
    # =================================================

    latitude = (
        location.get("latitude")
        if location.get("latitude") is not None
        else location.get("lat")
    )

    longitude = (
        location.get("longitude")
        if location.get("longitude") is not None
        else location.get("lon")
    )

    # Якщо координат у location немає — пробуємо Neptun
    if latitude is None or longitude is None:
        city = location.get("name")

        if city:
            try:
                neptun_location = find_city_location(city)

                if neptun_location:
                    latitude = (
                        neptun_location.get("latitude")
                        if neptun_location.get("latitude") is not None
                        else neptun_location.get("lat")
                    )

                    longitude = (
                        neptun_location.get("longitude")
                        if neptun_location.get("longitude") is not None
                        else neptun_location.get("lon")
                    )

            except Exception as e:
                print(
                    f"⚠️ Neptun coordinates lookup failed: {e}"
                )

    if latitude is None or longitude is None:
        print(
            f"❌ Немає координат вибраної локації: {location}"
        )
        return result

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        print(
            f"❌ Некоректні координати локації: "
            f"{latitude}, {longitude}"
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

        if not isinstance(threat, dict):
            continue

        status = str(
            threat.get("status", "active")
        ).strip().lower()

        if status not in (
            "active",
            "activated",
            "stale",
        ):
            continue

        # API може повертати lat/lon
        # або latitude/longitude
        threat_lat = (
            threat.get("latitude")
            if threat.get("latitude") is not None
            else threat.get("lat")
        )

        threat_lon = (
            threat.get("longitude")
            if threat.get("longitude") is not None
            else threat.get("lon")
        )

        if threat_lat is None or threat_lon is None:
            continue

        try:
            threat_lat = float(threat_lat)
            threat_lon = float(threat_lon)
        except (TypeError, ValueError):
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

        result.append(
            {
                "threat": threat,
                "distance": distance,
            }
        )

    # Найближчі загрози показуємо першими
    result.sort(
        key=lambda item: item["distance"]
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
# ФОРМУВАННЯ ЗАГРОЗИ
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
    lambda message: message.text == "🛰 Загрози"
)
async def threats(message: Message):
    """Ручна перевірка: один натиск → один запит → одне повідомлення."""

    user_id = message.from_user.id

    # Використовуємо саме локацію моніторингу.
    location = get_location(user_id)

    # Резерв для старих записів.
    if not location:
        city = get_city(user_id)
        if city:
            location = {
                "key": city.lower(),
                "name": city,
                "oblast": CITY_OBLASTS.get(city, ""),
            }

    print(f"🛰 THREATS | user_id={user_id} | location={location}")

    if not location:
        await message.answer("❌ Спочатку оберіть свою локацію.")
        return

    city = location.get("name") or get_city(user_id)
    if not city:
        await message.answer("❌ Не вдалося визначити вашу локацію.")
        return

    threats_api = await asyncio.to_thread(get_threats)
    alerts_api = await asyncio.to_thread(get_alerts)

    city_alert = get_city_alert_status(
        city,
        alerts_api,
        location=location,
    )

    city_oblast = (
        location.get("oblast")
        or location.get("oblast_name")
        or CITY_OBLASTS.get(city)
    )

    if not city_oblast:
        try:
            neptun_city = find_city_location(city)
            if neptun_city:
                city_oblast = neptun_city.get("oblast_name")
        except Exception:
            pass

    active_oblast_raions = (
        get_active_oblast_raions(city_oblast, alerts_api)
        if city_oblast else []
    )

    threats_data = threats_api.get("threats", []) if threats_api else []
    nearby_threats = find_nearby_threats(
        location,
        threats_data
    )

    print(
        f"🛰 STATUS | city={city} | city_alert={city_alert} | "
        f"oblast={city_oblast} | active_raions={len(active_oblast_raions)} | "
        f"nearby_threats={len(nearby_threats)}"
    )

    text = (
        "🛰 <b>СТАН БЕЗПЕКИ</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
    )

    text += "🚨 <b>МОЯ ЛОКАЦІЯ</b>\n"

    if city_alert:
        text += "🔴 Повітряна тривога: <b>АКТИВНА</b>\n\n"
    else:
        text += "🟢 Повітряної тривоги <b>НЕМАЄ</b>\n\n"

    if city_oblast:
        text += f"🗺 <b>{city_oblast.upper()}</b>\n"

        if active_oblast_raions:
            text += "🟡 У частині області <b>АКТИВНА ТРИВОГА</b>\n\n"
            text += "📍 <b>Активні райони:</b>\n"
            for item in active_oblast_raions:
                text += f"• {item.get('name', 'Невідомий район')}\n"
            text += "\n"
        else:
            text += "🟢 Активної тривоги в області не виявлено.\n\n"

    text += "📡 <b>КОНКРЕТНІ ЗАГРОЗИ ПОБЛИЗУ</b>\n"

    if nearby_threats:
        text += "\n"
        for item in nearby_threats:
            text += format_threat(item) + "\n\n"
        text = text.rstrip()
    else:
        text += (
            "🟢 Конкретних активних загроз у радіусі "
            f"{THREAT_RADIUS_KM} км не виявлено."
        )

    if not city_alert and active_oblast_raions:
        text += (
            "\n\nℹ️ <b>Важливо:</b> тривога в іншому районі області "
            "не означає автоматично тривогу "
            f"в місті {city}."
        )

    if city_alert:
        city_raion = location.get("raion_name") or CITY_RAIONS.get(city)
        if city_raion:
            text += f"\n\n🔴 <b>{city_raion}</b>: повітряна тривога активна."
        text += "\n\n⚠️ <b>Перебувайте в безпечному місці.</b>"
    elif nearby_threats:
        text += (
            "\n\n🟡 <b>Поблизу є конкретна активна загроза.</b>\n"
            "Слідкуйте за офіційними повідомленнями."
        )
    else:
        text += "\n\n🛡 <b>Залишайтеся уважними.</b>"

    # Рівно одне повідомлення на одне натискання кнопки.
    await message.answer(text, parse_mode="HTML")

    print(
        f"✅ THREATS | city={city} | city_alert={city_alert} | "
        f"oblast_raions={len(active_oblast_raions)} | nearby={len(nearby_threats)}"
)