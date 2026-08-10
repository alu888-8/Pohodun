from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.regions import CITY_REGIONS

from app.services.threats import get_threats

router = Router()


@router.message(lambda message: message.text == "🛰 Загрози")
async def threats(message: Message):

    city = get_city(message.from_user.id)

    keywords = CITY_REGIONS.get(city, [city.lower()])

    data = get_threats()

    if data is None:
        await message.answer("❌ Не вдалося отримати список загроз.")
        return

    threats = data.get("threats", [])

    result = []

    for t in threats:

        search_text = (
            f"{t.get('region', '')} "
            f"{t.get('district', '')} "
            f"{t.get('locality', '')} "
            f"{t.get('title', '')} "
            f"{t.get('explanationShort', '')}"
        ).lower()

        if any(word in search_text for word in keywords):

            icon = {
                "uav": "🛸",
                "missile": "🚀",
                "ballistic": "💥",
                "kab": "💣",
                "mig31k": "✈️",
                "recon": "👀",
                "unknown": "❓"
            }.get(t.get("type"), "❓")

            result.append(
                f"{icon} <b>{t.get('title')}</b>\n"
                f"📍 {t.get('region')}\n"
                f"{t.get('explanationShort')}"
            )

    if not result:

        await message.answer(
            f"🛰 <b>Загрози</b>\n\n"
            f"📍 <b>{city}</b>\n\n"
            "🟢 Поблизу активних загроз немає.",
            parse_mode="HTML"
        )
        return

    text = (
        f"🛰 <b>Загрози для {city}</b>\n\n"
        + "\n\n".join(result)
    )

    await message.answer(text, parse_mode="HTML")