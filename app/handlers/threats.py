import math

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_location
from app.services.threats import get_threats
from app.services.neptun_locations import get_locations, _representative_point
from app.data.cities import CITY_API

router = Router()

# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

THREAT_RADIUS_KM = 70

# ============================================================
# ВІДСТАНЬ МІЖ КООРДИНАТАМИ
# ============================================================

def distance_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return None

    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius * c

# ============================================================
# ОТРИМАТИ КООРДИНАТИ ВИБРАНОЇ ЛОКАЦІЇ (ЦЕНТР РАЙОНУ)
# ============================================================

def get_selected_coordinates(user_id):
    location = get_location(user_id)
    if not location:
        return None

    location_key = str(location.get("key", "")).strip().lower()
    if not location_key:
        return None

    # Специфіка для Києва (беремо з нашого CITY_API)
    if location_key in ("kyiv-city", "київ"):
        coords = CITY_API.get("Київ") or CITY_API.get("Kyiv")
        if coords:
            lat, lon = coords.split(",")
            return {
                "name": location.get("name", "Київ"),
                "latitude": float(lat.strip()),
                "longitude": float(lon.strip()),
                "key": location_key
            }

    # Для районів беремо геометричний центр прямо з бази Neptun
    data = get_locations()
    for raion in data.get("raions", []):
        if str(raion.get("key", "")).strip().lower() == location_key:
            geometry = raion.get("geometry")
            if geometry:
                centroid = _representative_point(geometry)
                if centroid:
                    return {
                        "name": location.get("name", raion.get("name")),
                        "latitude": centroid[1],
                        "longitude": centroid[0],
                        "key": location_key
                    }

    return None

# ============================================================
# КООРДИНАТИ ЗАГРОЗИ
# ============================================================

def get_threat_coordinates(threat):
    if not threat:
        return None

    latitude = threat.get("latitude") if threat.get("latitude") is not None else threat.get("lat")
    longitude = threat.get("longitude") if threat.get("longitude") is not None else threat.get("lon")

    if latitude is None or longitude is None:
        return None

    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None

# ============================================================
# ПОШУК ЗАГРОЗ БІЛЯ ВИБРАНОЇ ЛОКАЦІЇ
# ============================================================

def find_nearby_threats(user_id, threats):
    selected = get_selected_coordinates(user_id)
    if not selected:
        return []

    user_lat = selected["latitude"]
    user_lon = selected["longitude"]
    result = []

    for threat in threats:
        if not isinstance(threat, dict):
            continue

        status = str(threat.get("status", "")).strip().lower()
        if status and status not in ("active", "activated"):
            continue

        coordinates = get_threat_coordinates(threat)
        if not coordinates:
            continue

        threat_lat, threat_lon = coordinates
        distance = distance_km(user_lat, user_lon, threat_lat, threat_lon)

        if distance is None:
            continue

        if distance <= THREAT_RADIUS_KM:
            item = dict(threat)
            item["_distance_km"] = round(distance, 1)
            result.append(item)

    result.sort(key=lambda x: x.get("_distance_km", 999999))
    return result

# ============================================================
# НАЗВА ЗАГРОЗИ
# ============================================================

def threat_title(threat):
    threat_type = str(threat.get("type", "")).strip().lower()
    title = str(threat.get("title", "")).strip()

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
    return mapping.get(threat_type, "Повітряна загроза")

# ============================================================
# МІСЦЕ ЗАГРОЗИ
# ============================================================

def threat_place(threat):
    locality = str(threat.get("locality", "")).strip()
    district = str(threat.get("district", "")).strip()
    region = str(threat.get("region", "")).strip()

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

def build_threat_message(location_name, threats):
    if not threats:
        return (
            f"🟢 <b>{location_name}</b>\n\n"
            "Наразі поблизу вибраної локації активних загроз не виявлено."
        )

    lines = [
        "⚠️ <b>ЗАГРОЗИ</b>",
        "",
        f"📍 <b>{location_name}</b>",
        "",
    ]

    for threat in threats:
        title = threat_title(threat)
        place = threat_place(threat)
        distance = threat.get("_distance_km")

        lines.append(f"⚠️ <b>{title}</b>")
        lines.append(f"📍 {place}")
        if distance is not None:
            lines.append(f"📏 Приблизно {distance} км")
        lines.append("")

    lines.append("Будьте уважні та стежте за офіційними повідомленнями.")
    return "\n".join(lines)

# ============================================================
# КНОПКА «ЗАГРОЗИ»
# ============================================================

# Підтримуємо обидві варіації назви кнопки зі скріншоту
@router.message(lambda message: message.text in ("⚠️ Загрози", "🛰 Загрози"))
async def threats_handler(message: Message):
    user_id = message.from_user.id

    location = get_selected_coordinates(user_id)
    if not location:
        await message.answer(
            "📍 <b>Локацію ще не вибрано.</b>\n\n"
            "Зайдіть у ⚙️ Налаштування → "
            "📍 Локація моніторингу.",
            parse_mode="HTML"
        )
        return

    location_name = location.get("name", "Невідома локація")

    data = get_threats()
    if data is None:
        await message.answer("❌ Не вдалося отримати актуальну інформацію про загрози.")
        return

    threats = data.get("threats", [])
    nearby = find_nearby_threats(user_id, threats)

    text = build_threat_message(location_name, nearby)
    await message.answer(text, parse_mode="HTML")