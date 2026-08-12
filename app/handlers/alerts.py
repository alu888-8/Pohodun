from aiogram import Router
from aiogram.types import Message

from datetime import datetime
from zoneinfo import ZoneInfo

from app.database.db import get_city
from app.data.regions import CITY_REGIONS
from app.services.alerts import get_alerts

router = Router()


KYIV_TZ = ZoneInfo("Europe/Kyiv")


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
                duration_text = (
                    f"{hours} год {mins} хв"
                )
            else:
                duration_text = f"{hours} год"

        since = local_time.strftime("%H:%M")

        return since, duration_text

    except Exception as e:
        print(
            f"❌ Помилка обробки часу тривоги: {e}"
        )

        return "невідомо", "невідомо"


@router.message(
    lambda message: message.text == "🚨 Тривоги"
)
async def alerts(message: Message):

    city = get_city(message.from_user.id)

    print(
        f"🚨 Перевірка тривоги | "
        f"user_id={message.from_user.id} | "
        f"city={city}"
    )

    data = get_alerts()

    if data is None:

        await message.answer(
            "❌ Не вдалося отримати "
            "актуальну інформацію про тривоги."
        )

        return

    raions = data.get("raions", [])
    oblasts = data.get("oblasts", [])

    print(
        f"🚨 API | "
        f"raions={len(raions)} | "
        f"oblasts={len(oblasts)}"
    )

    region_alert = None

    # =====================================================
    # КИЇВ
    # =====================================================

    if city == "Київ":

        for item in raions + oblasts:

            name = (
                item.get("name", "")
                .strip()
                .lower()
            )

            oblast = (
                item.get("oblast", "")
                .strip()
                .lower()
            )

            key = (
                item.get("key", "")
                .strip()
                .lower()
            )

            if (
                name in (
                    "київ",
                    "м. київ",
                    "місто київ"
                )
                or key in (
                    "київ",
                    "м. київ",
                    "місто київ"
                )
            ):
                region_alert = item

                print(
                    f"🔴 Знайдено тривогу Києва: "
                    f"{item}"
                )

                break

    # =====================================================
    # ІНШІ МІСТА
    # =====================================================

    else:

        keywords = CITY_REGIONS.get(
            city,
            [city.lower()]
        )

        keywords = [
            word.lower()
            for word in keywords
        ]

        for item in raions + oblasts:

            name = (
                item.get("name", "")
                .lower()
            )

            oblast = (
                item.get("oblast", "")
                .lower()
            )

            key = (
                item.get("key", "")
                .lower()
            )

            search_text = (
                f"{name} "
                f"{oblast} "
                f"{key}"
            )

            if any(
                word in search_text
                for word in keywords
            ):

                region_alert = item

                print(
                    f"🔴 Знайдено тривогу: "
                    f"{item}"
                )

                break

    # =====================================================
    # АКТИВНА ТРИВОГА
    # =====================================================

    if region_alert:

        since_value = region_alert.get(
            "since"
        )

        since, duration_text = get_duration(
            since_value
        )

        text = (
            "🚨 <b>Повітряна тривога</b>\n\n"
            f"📍 <b>{city}</b>\n\n"
            "🔴 Статус: <b>Активна</b>\n"
            f"🕒 Початок: <b>{since}</b>\n"
            f"⏱ Триває: <b>{duration_text}</b>\n\n"
            "⚠️ Будьте в безпечному місці."
        )

    # =====================================================
    # ТРИВОГИ НЕМАЄ
    # =====================================================

    else:

        print(
            f"🟢 Активної тривоги не знайдено | "
            f"city={city}"
        )

        text = (
            f"🟢 <b>{city}</b>\n\n"
            "✅ Повітряної тривоги немає\n\n"
            "🛡 Залишайтеся уважними."
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )