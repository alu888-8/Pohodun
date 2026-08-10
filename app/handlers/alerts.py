from aiogram import Router
from aiogram.types import Message

from datetime import datetime
from zoneinfo import ZoneInfo

from app.database.db import get_city
from app.data.regions import CITY_REGIONS

from app.services.alerts import get_alerts

router = Router()


@router.message(lambda message: message.text == "🚨 Тривоги")
async def alerts(message: Message):

    city = get_city(message.from_user.id)

    keywords = CITY_REGIONS.get(city, [city.lower()])

    data = get_alerts()

    if data is None:
        await message.answer("❌ Не вдалося отримати інформацію.")
        return

    region_alert = None

    for r in data.get("raions", []):

        text = (
            f"{r.get('name', '')} "
            f"{r.get('oblast', '')}"
        ).lower()

        if any(word in text for word in keywords):
            region_alert = r
            break

    if region_alert:

        utc_time = datetime.fromisoformat(
            region_alert["since"].replace("Z", "+00:00")
        )

        local_time = utc_time.astimezone(
            ZoneInfo("Europe/Kyiv")
        )

        now = datetime.now(
            ZoneInfo("Europe/Kyiv")
        )

        duration = now - local_time

        minutes = int(duration.total_seconds() // 60)

        if minutes < 60:
            duration_text = f"{minutes} хв"
        else:
            hours = minutes // 60
            mins = minutes % 60
            duration_text = f"{hours} год {mins} хв"

        since = local_time.strftime("%H:%M")

        text = (
            "🚨 <b>Повітряна тривога</b>\n\n"

            f"📍 <b>{city}</b>\n\n"

            "🔴 Статус: <b>Активна</b>\n"
            f"🕒 Початок: <b>{since}</b>\n"
            f"⏱ Триває: <b>{duration_text}</b>\n\n"

            "⚠️ Будьте в безпечному місці."
        )

    else:

        text = (
            f"🟢 <b>{city}</b>\n\n"

            "✅ Повітряної тривоги немає\n\n"

            "🛡 Залишайтеся уважними."
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )