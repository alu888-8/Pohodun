import asyncio

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_location
from app.services.alerts import get_alerts


router = Router()

KYIV_TZ = ZoneInfo("Europe/Kyiv")


# ============================================================
# ЧАС ТРИВОГИ
# ============================================================

def get_duration(since_value):

    if not since_value:
        return "невідомо", "невідомо"

    try:
        utc_time = datetime.fromisoformat(
            since_value.replace("Z", "+00:00")
        )

        local_time = utc_time.astimezone(KYIV_TZ)
        now = datetime.now(KYIV_TZ)

        duration = now - local_time

        minutes = max(
            0,
            int(duration.total_seconds() // 60)
        )

        if minutes < 60:
            duration_text = f"{minutes} хв"
        else:
            hours = minutes // 60
            mins = minutes % 60

            if mins:
                duration_text = f"{hours} год {mins} хв"
            else:
                duration_text = f"{hours} год"

        since = local_time.strftime("%H:%M")

        return since, duration_text

    except Exception as e:

        print(
            f"❌ Помилка обробки часу тривоги: {e}"
        )

        return "невідомо", "невідомо"


# ============================================================
# ПОШУК ТРИВОГИ ДЛЯ КОНКРЕТНОЇ ЛОКАЦІЇ
# ============================================================

def get_location_alert(location, data):

    if not location or not data:
        return None

    target_key = str(
        location.get("key", "")
    ).strip().lower()

    if not target_key:
        return None

    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )

    # ========================================================
    # РАЙОН / ЛОКАЦІЯ
    # ========================================================

    for item in raions:

        key = str(
            item.get("key", "")
        ).strip().lower()

        if key == target_key:

            print(
                f"🔴 Знайдено активну тривогу | "
                f"location={location.get('name')} | "
                f"key={target_key}"
            )

            return item

    # ========================================================
    # КИЇВ
    # ========================================================

    if target_key == "kyiv-city":

        for item in oblasts:

            key = str(
                item.get("key", "")
            ).strip().lower()

            name = str(
                item.get("name", "")
            ).strip().lower()

            oblast = str(
                item.get("oblast", "")
            ).strip().lower()

            if key == "kyiv-city":
                return item

            if key in (
                "київ",
                "м. київ",
                "місто київ",
            ):
                return item

            if name in (
                "київ",
                "м. київ",
                "місто київ",
            ):
                return item

            if oblast in (
                "київ",
                "м. київ",
                "місто київ",
            ):
                return item

    # ========================================================
    # ВАЖЛИВО:
    #
    # НЕ ПІДМІНЯЄМО ЛОКАЦІЮ ОБЛАСТЮ.
    # ========================================================

    return None


# ============================================================
# КНОПКА ТРИВОГИ
# ============================================================

@router.message(
    lambda message:
    message.text == "🚨 Тривоги"
)
async def alerts(message: Message):

    user_id = message.from_user.id

    # ========================================================
    # ОТРИМУЄМО ВИБРАНУ ЛОКАЦІЮ
    # ========================================================

    location = await asyncio.to_thread(
        get_location,
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

    location_name = (
        location.get("name")
        or "Невідома локація"
    )

    location_key = location.get(
        "key"
    )

    print(
        f"🚨 Перевірка тривоги | "
        f"user_id={user_id} | "
        f"location={location_name} | "
        f"key={location_key}"
    )

    # ========================================================
    # ОТРИМУЄМО АКТУАЛЬНІ ДАНІ
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
        f"raions={len(data.get('raions', []))} | "
        f"oblasts={len(data.get('oblasts', []))}"
    )

    # ========================================================
    # ШУКАЄМО СТАН САМЕ ВИБРАНОЇ ЛОКАЦІЇ
    # ========================================================

    location_alert = get_location_alert(
        location,
        data
    )

    # ========================================================
    # АКТИВНА ТРИВОГА
    # ========================================================

    if location_alert:

        since_value = location_alert.get(
            "since"
        )

        since, duration_text = get_duration(
            since_value
        )

        text = (
            "🚨 <b>Повітряна тривога</b>\n\n"
            f"📍 <b>{location_name}</b>\n\n"
            "🔴 Статус: <b>Активна</b>\n"
            f"🕒 Початок: <b>{since}</b>\n"
            f"⏱ Триває: <b>{duration_text}</b>\n\n"
            "⚠️ Будьте в безпечному місці."
        )

    # ========================================================
    # ТРИВОГИ НЕМАЄ
    # ========================================================

    else:

        print(
            f"🟢 Активної тривоги не знайдено | "
            f"location={location_name} | "
            f"key={location_key}"
        )

        text = (
            f"🟢 <b>{location_name}</b>\n\n"
            "✅ Повітряної тривоги немає\n\n"
            "🛡 Залишайтеся уважними."
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )
