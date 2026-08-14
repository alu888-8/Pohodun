import math

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_location
from app.services.threats import get_threats
from app.services.neptun_locations import get_city_locations


router = Router()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

# Максимальна відстань, на якій показуємо загрозу
# відносно вибраного міста.
THREAT_RADIUS_KM = 70


# ============================================================
# ВІДСТАНЬ МІЖ КООРДИНАТАМИ
# ============================================================

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

    radius = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(
        lat2 - lat1
    )

    delta_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_phi / 2) ** 2
        +
        math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


# ============================================================
# ОТРИМАТИ ВИБРАНУ ЛОКАЦІЮ
# ============================================================

def get_selected_location(user_id):

    location = get_location(
        user_id
    )

    if not location:

        return None

    location_key = str(
        location.get("key", "")
    ).strip().lower()

    if not location_key:

        return None

    locations = get_city_locations()

    for item in locations:

        city_key = str(
            item.get("key", "")
        ).strip().lower()

        raion_key = str(
            item.get("raion_key", "")
        ).strip().lower()

        # Звичайні міста:
        #
        # location key:
        # харківський
        #
        # city:
        # Харків
        #
        # raion_key:
        # харківський

        if raion_key == location_key:

            return item

        # Окремі міські локації,
        # наприклад Київ.

        if city_key == location_key:

            return item

    return None


# ============================================================
# ОТРИМАТИ КООРДИНАТИ ВИБРАНОГО МІСТА
# ============================================================

def get_selected_coordinates(user_id):

    location = get_selected_location(
        user_id
    )

    if not location:

        return None

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    if latitude is None or longitude is None:

        return None

    return {
        "name": location.get(
            "name"
        ),
        "latitude": latitude,
        "longitude": longitude,
        "key": location.get(
            "key"
        ),
        "raion_key": location.get(
            "raion_key"
        ),
        "raion_name": location.get(
            "raion_name"
        ),
        "oblast_name": location.get(
            "oblast_name"
        ),
    }


# ============================================================
# КООРДИНАТИ ЗАГРОЗИ
# ============================================================

def get_threat_coordinates(threat):

    if not threat:

        return None

    latitude = (
        threat.get("latitude")
        if threat.get("latitude") is not None
        else threat.get("lat")
    )

    longitude = (
        threat.get("longitude")
        if threat.get("longitude") is not None
        else threat.get("lon")
    )

    if latitude is None or longitude is None:

        return None

    try:

        return (
            float(latitude),
            float(longitude),
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# ПОШУК ЗАГРОЗ БІЛЯ ВИБРАНОГО МІСТА
# ============================================================

def find_nearby_threats(
    user_id,
    threats,
):

    selected = get_selected_coordinates(
        user_id
    )

    if not selected:

        return []

    user_lat = selected["latitude"]
    user_lon = selected["longitude"]

    result = []

    for threat in threats:

        if not isinstance(
            threat,
            dict,
        ):
            continue

        status = str(
            threat.get(
                "status",
                ""
            )
        ).strip().lower()

        # Показуємо тільки активні загрози.
        if status and status not in (
            "active",
            "activated",
        ):
            continue

        coordinates = get_threat_coordinates(
            threat
        )

        if not coordinates:

            # Якщо API не дало координат,
            # не вгадуємо місце загрози.
            continue

        threat_lat, threat_lon = coordinates

        distance = distance_km(
            user_lat,
            user_lon,
            threat_lat,
            threat_lon,
        )

        if distance is None:

            continue

        if distance <= THREAT_RADIUS_KM:

            item = dict(
                threat
            )

            item["_distance_km"] = round(
                distance,
                1
            )

            result.append(
                item
            )

    result.sort(
        key=lambda x:
        x.get(
            "_distance_km",
            999999
        )
    )

    return result


# ============================================================
# НАЗВА ЗАГРОЗИ
# ============================================================

def threat_title(threat):

    threat_type = str(
        threat.get(
            "type",
            ""
        )
    ).strip().lower()

    title = str(
        threat.get(
            "title",
            ""
        )
    ).strip()

    if title:

        return title

    mapping = {

        "uav": "БпЛА",

        "drone": "БпЛА",

        "shahed": "БпЛА",

        "missile": "Ракетна загроза",

        "rocket": "Ракетна загроза",

        "ballistic": "Балістична загроза",

        "aircraft": "Загроза з повітря",

    }

    return mapping.get(
        threat_type,
        "Повітряна загроза"
    )


# ============================================================
# МІСЦЕ ЗАГРОЗИ
# ============================================================

def threat_place(threat):

    locality = str(
        threat.get(
            "locality",
            ""
        )
    ).strip()

    district = str(
        threat.get(
            "district",
            ""
        )
    ).strip()

    region = str(
        threat.get(
            "region",
            ""
        )
    ).strip()

    if locality:

        return locality

    if district:

        return district

    if region:

        return region

    return "Місце не визначено"


# ============================================================
# ФОРМУВАННЯ ПОВІДОМЛЕННЯ
# ============================================================

def build_threat_message(
    location,
    threats,
):

    location_name = (
        location.get("name")
        or "Невідома локація"
    )

    if not threats:

        return (
            f"🟢 <b>{location_name}</b>\n\n"
            "Наразі поблизу вибраної "
            "локації активних загроз не виявлено."
        )

    lines = [

        "⚠️ <b>ЗАГРОЗИ</b>",
        "",
        f"📍 <b>{location_name}</b>",
        "",
    ]

    for threat in threats:

        title = threat_title(
            threat
        )

        place = threat_place(
            threat
        )

        distance = threat.get(
            "_distance_km"
        )

        lines.append(
            f"⚠️ <b>{title}</b>"
        )

        lines.append(
            f"📍 {place}"
        )

        if distance is not None:

            lines.append(
                f"📏 Приблизно {distance} км"
            )

        lines.append("")

    lines.extend(
        [
            "Будьте уважні та стежте "
            "за офіційними повідомленнями.",
        ]
    )

    return "\n".join(
        lines
    )


# ============================================================
# КНОПКА «ЗАГРОЗИ»
# ============================================================

@router.message(
    lambda message:
    message.text == "⚠️ Загрози"
)
async def threats_handler(
    message: Message
):

    user_id = message.from_user.id

    # ========================================================
    # ЛОКАЦІЯ КОРИСТУВАЧА
    # ========================================================

    location = get_selected_location(
        user_id
    )

    if not location:

        await message.answer(
            "📍 <b>Локацію ще не вибрано.</b>\n\n"
            "Зайдіть у ⚙️ Налаштування → "
            "🗺 Змінити локацію.",
            parse_mode="HTML"
        )

        return

    location_name = location.get(
        "name"
    ) or "Невідома локація"

    print(
        f"⚠️ Перевірка загроз | "
        f"user_id={user_id} | "
        f"location={location_name} | "
        f"key={location.get('key')}"
    )

    # ========================================================
    # API
    # ========================================================

    data = get_threats()

    if data is None:

        await message.answer(
            "❌ Не вдалося отримати "
            "актуальну інформацію "
            "про загрози."
        )

        return

    threats = data.get(
        "threats",
        []
    )

    print(
        f"⚠️ Загроз в API: {len(threats)}"
    )

    # ========================================================
    # ФІЛЬТРАЦІЯ
    # ========================================================

    nearby = find_nearby_threats(
        user_id,
        threats,
    )

    print(
        f"⚠️ Загроз поблизу "
        f"{location_name}: {len(nearby)}"
    )

    # ========================================================
    # ПОВІДОМЛЕННЯ
    # ========================================================

    text = build_threat_message(
        location,
        nearby,
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )