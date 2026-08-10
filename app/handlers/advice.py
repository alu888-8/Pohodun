from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.weather import get_weather
from app.services.advice import get_advice

from app.utils.weather_icons import get_weather_icon

router = Router()


@router.message(lambda message: message.text == "👕 Поради")
async def advice(message: Message):

    city_ua = get_city(message.from_user.id)
    city_api = CITY_API.get(city_ua, city_ua)

    weather = get_weather(city_api)

    if weather is None:
        await message.answer("❌ Не вдалося отримати погоду.")
        return

    temp = weather["temp"]
    condition = weather["condition"]

    icon = get_weather_icon(condition)

    tips = get_advice(temp, condition)

    text = (
        f"👕 <b>Поради</b>\n\n"
        f"📍 <b>{city_ua}</b>\n\n"
        f"🌡 Температура: <b>{temp}°C</b>\n"
        f"{icon} {condition}\n\n"
        f"{tips}"
    )

    await message.answer(text, parse_mode="HTML")