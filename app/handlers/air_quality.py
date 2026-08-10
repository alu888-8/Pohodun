from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.air_quality import get_air_quality

router = Router()


@router.message(lambda message: message.text == "🌫 Якість повітря")
async def air_quality(message: Message):

    city_ua = get_city(message.from_user.id)

    city_api = CITY_API.get(city_ua, city_ua)

    data = get_air_quality(city_api)

    if data is None:
        await message.answer("❌ Не вдалося отримати дані.")
        return

    air = data["current"]["air_quality"]

    aqi = air["us-epa-index"]

    if aqi == 1:
        status = "🟢 Добра"
    elif aqi == 2:
        status = "🟡 Помірна"
    elif aqi == 3:
        status = "🟠 Нездорова для чутливих"
    elif aqi == 4:
        status = "🔴 Нездорова"
    elif aqi == 5:
        status = "🟣 Дуже нездорова"
    else:
        status = "⚫ Небезпечна"

    text = (
        f"🌫 <b>Якість повітря</b>\n\n"

        f"📍 <b>{city_ua}</b>\n\n"

        f"{status}\n\n"

        f"🇺🇸 EPA AQI: <b>{aqi}</b>\n\n"

        f"🌬 PM2.5: <b>{air['pm2_5']:.1f}</b>\n"
        f"🌬 PM10: <b>{air['pm10']:.1f}</b>\n"
        f"🟤 CO: <b>{air['co']:.1f}</b>\n"
        f"🟣 O₃: <b>{air['o3']:.1f}</b>"
    )

    await message.answer(text, parse_mode="HTML")