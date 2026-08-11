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

    data = get_alerts()

    if data is None:
        await message.answer(
            "❌ Не вдалося отримати інформацію."
        )
        return

    region_alert = None

    # =====================================================
    # КИЇВ — окремо від Київської області
    # =====================================================

    if city == "Київ":

        for r in data.get("raions", []):

            name = r.get("name", "").strip().lower()
            oblast = r.get("oblast", "").strip().lower()

            # Не плутаємо Київ із Київською областю
            if name == "м. київ" or name == "київ":
                region_alert = r
                break

            if (
                name == "київський район"
                and oblast == "м. київ"
            ):
                region_alert = r
                break

    # =====================================================
    # ІНШІ МІСТА
    # =====================================================

    else:

        keywords = CITY_REGIONS.get(
            city,
            [city.lower()]
        )

        for r in data.get("raions", []):

            name = r.get("name", "").lower()
            oblast = r.get("oblast", "").lower()

            text = f"{name} {oblast}"

            if any(word.lower() in text for word in keywords):
                region_alert = r
                break

    # =====================================================
    # ПОКАЗУЄМО РЕЗУЛЬТАТ
    # =====================================================

    if region_alert:

        since_value = region_alert.get("since")

        if since_value:

            utc_time = datetime.fromisoformat(
                since_value.replace("Z", "+00:00")
            )

            local_time = utc_time.astimezone(
                ZoneInfo("Europe/Kyiv")
            )

            now = datetime.now(
                ZoneInfo("Europe/Kyiv")
            )

            duration = now - local_time

            minutes = int(
                duration.total_seconds() // 60
            )

            if minutes < 60:
                duration_text = f"{minutes} хв"
            else:
                hours = minutes // 60
                mins = minutes % 60

                duration_text = (
                    f"{hours} год {mins} хв"
                )

            since = local_time.strftime("%H:%M")

        else:
            since = "невідомо"
            duration_text = "невідомо"

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