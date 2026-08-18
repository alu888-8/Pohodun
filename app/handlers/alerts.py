import asyncio

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_location, get_city
from app.services.alerts import get_alerts


router = Router()

KYIV_TZ = ZoneInfo("Europe/Kyiv")


# ============================================================
# ТОЧНИЙ РАЙОН ДЛЯ КОЖНОГО МІСТА
# ============================================================

CITY_ALERT_KEYS = {
    "Вінниця": "вінницький",
    "Луцьк": "луцький",
    "Дніпро": "дніпровський",
    "Донецьк": "донецький",
    "Житомир": "житомирський",
    "Ужгород": "ужгородський",
    "Запоріжжя": "запорізький",
    "Івано-Франківськ": "івано-франківський",
    "Кропивницький": "кропивницький",
    "Луганськ": "луганський",
    "Львів": "львівський",
    "Миколаїв": "миколаївський",
    "Одеса": "одеський",
    "Полтава": "полтавський",
    "Рівне": "рівненський",
    "Суми": "сумський",
    "Тернопіль": "тернопільський",
    "Харків": "харківський",
    "Херсон": "херсонський",
    "Хмельницький": "хмельницький",
    "Черкаси": "черкаський",
    "Чернівці": "чернівецький",
    "Чернігів": "чернігівський",
}


# ============================================================
# ОБЛАСТІ ДЛЯ МІСТ
# ============================================================

CITY_OBLASTS = {
    "Вінниця": "вінницька область",
    "Луцьк": "волинська область",
    "Дніпро": "дніпропетровська область",
    "Донецьк": "донецька область",
    "Житомир": "житомирська область",
    "Ужгород": "закарпатська область",
    "Запоріжжя": "запорізька область",
    "Івано-Франківськ": "івано-франківська область",
    "Кропивницький": "кіровоградська область",
    "Луганськ": "луганська область",
    "Львів": "львівська область",
    "Миколаїв": "миколаївська область",
    "Одеса": "одеська область",
    "Полтава": "полтавська область",
    "Рівне": "рівненська область",
    "Суми": "сумська область",
    "Тернопіль": "тернопільська область",
    "Харків": "харківська область",
    "Херсон": "херсонська область",
    "Хмельницький": "хмельницька область",
    "Черкаси": "черкаська область",
    "Чернівці": "чернівецька область",
    "Чернігів": "чернігівська область",
}


# ============================================================
# НОРМАЛІЗАЦІЯ
# ============================================================

def normalize(value):
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("’", "'")
    )


# ============================================================
# ОБРОБКА ЧАСУ
# ============================================================

def get_duration(since_value):

    if not since_value:
        return "невідомо", "невідомо"

    try:

        utc_time = datetime.fromisoformat(
            since_value.replace(
                "Z",
                "+00:00"
            )
        )

        local_time = utc_time.astimezone(
            KYIV_TZ
        )

        now = datetime.now(
            KYIV_TZ
        )

        duration = now - local_time

        minutes = max(
            0,
            int(
                duration.total_seconds() // 60
            )
        )

        if minutes < 60:

            duration_text = (
                f"{minutes} хв"
            )

        else:

            hours = minutes // 60
            mins = minutes % 60

            if mins:

                duration_text = (
                    f"{hours} год "
                    f"{mins} хв"
                )

            else:

                duration_text = (
                    f"{hours} год"
                )

        since = local_time.strftime(
            "%H:%M"
        )

        return (
            since,
            duration_text
        )

    except Exception as e:

        print(
            f"❌ Помилка обробки часу "
            f"тривоги: {e}"
        )

        return (
            "невідомо",
            "невідомо"
        )


# ============================================================
# ПОШУК ТРИВОГИ ДЛЯ КОНКРЕТНОЇ ЛОКАЦІЇ
# ============================================================

def get_location_alert(
    location,
    data,
):
    """
    Повертає конкретний активний запис тривоги
    для вибраної локації моніторингу.

    Підтримує:

    1. Київ
    2. Конкретний район
    3. Місто
    4. Область

    ВАЖЛИВО:
    функція працює саме з location,
    а не зі старим city з таблиці users.
    """

    if not data or not location:
        return None

    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )

    location_key = normalize(
        location.get("key")
    )

    location_name = normalize(
        location.get("name")
    )

    location_oblast = normalize(
        location.get("oblast")
        or location.get("oblast_name")
    )

    print(
        "🚨 LOCATION ALERT SEARCH | "
        f"key={location_key} | "
        f"name={location_name} | "
        f"oblast={location_oblast}"
    )

    # ========================================================
    # КИЇВ
    # ========================================================

    if location_key == "kyiv-city" or location_name in (
        "київ",
        "м. київ",
        "місто київ",
    ):

        for item in raions:

            key = normalize(
                item.get("key")
            )

            name = normalize(
                item.get("name")
            )

            oblast = normalize(
                item.get("oblast")
            )

            if key in (
                "київ",
                "м. київ",
                "м-київ",
                "місто київ",
                "kyiv",
                "kyiv-city",
            ):

                print(
                    f"🔴 KYIV ALERT FOUND | {item}"
                )

                return item

            if name in (
                "київ",
                "м. київ",
                "місто київ",
            ):

                if oblast in (
                    "",
                    "м. київ",
                    "київ",
                    "місто київ",
                ):

                    print(
                        f"🔴 KYIV ALERT FOUND | {item}"
                    )

                    return item

        for item in oblasts:

            key = normalize(
                item.get("key")
            )

            name = normalize(
                item.get("name")
            )

            if key in (
                "київ",
                "м. київ",
                "м-київ",
                "місто київ",
                "kyiv",
                "kyiv-city",
            ):

                return item

            if name in (
                "київ",
                "м. київ",
                "місто київ",
            ):

                return item

        print(
            "🟢 KYIV ALERT NOT FOUND"
        )

        return None

    # ========================================================
    # КОНКРЕТНИЙ РАЙОН
    # ========================================================

    # Якщо key самої локації є ключем району —
    # перевіряємо ТІЛЬКИ цей район.
    if location_key:

        for item in raions:

            item_key = normalize(
                item.get("key")
            )

            if item_key == location_key:

                print(
                    f"🔴 EXACT DISTRICT ALERT FOUND | "
                    f"{location_name} | {item}"
                )

                return item

    # ========================================================
    # РАЙОН ЗА НАЗВОЮ
    # ========================================================

    # Наприклад:
    # location_name = "Броварський район"

    if location_name:

        for item in raions:

            item_key = normalize(
                item.get("key")
            )

            item_name = normalize(
                item.get("name")
            )

            if (
                item_name == location_name
                or item_key == location_name
            ):

                print(
                    f"🔴 DISTRICT NAME ALERT FOUND | "
                    f"{location_name} | {item}"
                )

                return item

    # ========================================================
    # МІСТО
    # ========================================================

    # Якщо це місто і ми знаємо відповідний район,
    # перевіряємо саме його.

    city_name = (
        location.get("name")
        or ""
    )

    target_key = CITY_ALERT_KEYS.get(
        city_name
    )

    if target_key:

        target_key = normalize(
            target_key
        )

        for item in raions:

            item_key = normalize(
                item.get("key")
            )

            if item_key == target_key:

                print(
                    f"🔴 CITY DISTRICT ALERT FOUND | "
                    f"{city_name} | {item}"
                )

                return item

        target_name = (
            f"{target_key} район"
        )

        for item in raions:

            item_name = normalize(
                item.get("name")
            )

            if item_name == target_name:

                print(
                    f"🔴 CITY DISTRICT NAME ALERT FOUND | "
                    f"{city_name} | {item}"
                )

                return item

    # ========================================================
    # ОБЛАСТЬ
    # ========================================================

    target_oblast = (
        location_oblast
        or CITY_OBLASTS.get(
            city_name,
            ""
        )
    )

    target_oblast = normalize(
        target_oblast
    )

    if target_oblast:

        for item in oblasts:

            item_name = normalize(
                item.get("name")
            )

            item_oblast = normalize(
                item.get("oblast")
            )

            if (
                item_name == target_oblast
                or item_oblast == target_oblast
            ):

                print(
                    f"🔴 OBLAST ALERT FOUND | "
                    f"{city_name} | {item}"
                )

                return item

    print(
        f"🟢 ALERT NOT FOUND | "
        f"{location_name}"
    )

    return None


# ============================================================
# СТАРА ФУНКЦІЯ ДЛЯ СУМІСНОСТІ
# ============================================================

def get_city_alert(
    city,
    data
):
    """
    Сумісність зі старим кодом.

    Для міста створюємо тимчасову location
    і використовуємо нову логіку.
    """

    if not city:
        return None

    location = {
        "key": "",
        "name": city,
        "oblast": CITY_OBLASTS.get(
            city,
            ""
        ),
    }

    if city == "Київ":

        location["key"] = "kyiv-city"

    else:

        location["key"] = CITY_ALERT_KEYS.get(
            city,
            ""
        )

    return get_location_alert(
        location,
        data
    )


# ============================================================
# КНОПКА ТРИВОГИ
# ============================================================

@router.message(
    lambda message:
    message.text == "🚨 Тривоги"
)
async def alerts(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    # ========================================================
    # ГОЛОВНЕ:
    # БЕРЕМО САМЕ ЛОКАЦІЮ МОНІТОРИНГУ
    # ========================================================

    location = await asyncio.to_thread(
        get_location,
        user_id
    )

    # ========================================================
    # РЕЗЕРВ ДЛЯ СТАРИХ КОРИСТУВАЧІВ
    # ========================================================

    if not location:

        city = await asyncio.to_thread(
            get_city,
            user_id
        )

        if city:

            location = {
                "key": (
                    "kyiv-city"
                    if city == "Київ"
                    else CITY_ALERT_KEYS.get(
                        city,
                        ""
                    )
                ),
                "name": city,
                "oblast": CITY_OBLASTS.get(
                    city,
                    ""
                ),
            }

            print(
                f"⚠️ LEGACY LOCATION | "
                f"user={user_id} | "
                f"city={city}"
            )

    # ========================================================
    # НЕМАЄ ЛОКАЦІЇ
    # ========================================================

    if not location:

        await message.answer(
            "❌ Спочатку оберіть "
            "локацію моніторингу."
        )

        return

    location_name = (
        location.get("name")
        or "Невідома локація"
    )

    print(
        f"🚨 ПЕРЕВІРКА ТРИВОГИ | "
        f"user_id={user_id} | "
        f"location={location}"
    )

    # ========================================================
    # API
    # ========================================================

    data = await asyncio.to_thread(
        get_alerts
    )

    if data is None:

        await message.answer(
            "❌ Не вдалося отримати "
            "актуальну інформацію "
            "про тривоги."
        )

        return

    print(
        f"🚨 API | "
        f"raions="
        f"{len(data.get('raions', []))} | "
        f"oblasts="
        f"{len(data.get('oblasts', []))}"
    )

    # ========================================================
    # ШУКАЄМО ТРИВОГУ САМЕ ДЛЯ ВИБРАНОЇ ЛОКАЦІЇ
    # ========================================================

    region_alert = get_location_alert(
        location,
        data
    )

    # ========================================================
    # АКТИВНА ТРИВОГА
    # ========================================================

    if region_alert:

        since_value = region_alert.get(
            "since"
        )

        since, duration_text = (
            get_duration(
                since_value
            )
        )

        text = (
            "🚨 <b>Повітряна тривога</b>\n\n"
            f"📍 <b>{location_name}</b>\n\n"
            "🔴 Статус: <b>Активна</b>\n"
            f"🕒 Початок: <b>{since}</b>\n"
            f"⏱ Триває: "
            f"<b>{duration_text}</b>\n\n"
            "⚠️ Будьте в безпечному місці."
        )

        print(
            f"🔴 ACTIVE ALERT | "
            f"{location_name} | "
            f"{region_alert}"
        )

    # ========================================================
    # ТРИВОГИ НЕМАЄ
    # ========================================================

    else:

        print(
            f"🟢 Активної тривоги "
            f"не знайдено | "
            f"location={location_name}"
        )

        text = (
            f"🟢 <b>{location_name}</b>\n\n"
            "✅ Повітряної тривоги немає\n\n"
            "🛡 Залишайтеся уважними."
        )

    # ========================================================
    # ОДНЕ ПОВІДОМЛЕННЯ
    # ========================================================

    await message.answer(
        text,
        parse_mode="HTML"
    )