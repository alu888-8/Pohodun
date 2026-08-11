import asyncio

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

    city_api = CITY_API.get(
        city_ua,
        city_ua
    )

    # Запит погоди не блокує бота
    weather = await asyncio.to_thread(
        get_weather,
        city_api
    )

    if weather is None:
        await message.answer(
            "❌ Не вдалося отримати погоду."
        )
        return

    temp = weather["temp"]
    condition = weather["condition"]
    feels = weather["feels_like"]
    wind = weather["wind"]
    humidity = weather["humidity"]

    icon = get_weather_icon(condition)

    # Генерація поради
    tips = await asyncio.to_thread(
        get_advice,
        temp,
        condition,
        city_ua,
        feels,
        wind,
        humidity
    )

    text = (
        f"👕 <b>Поради</b>\n\n"
        f"📍 <b>{city_ua}</b>\n\n"
        f"🌡 Температура: <b>{temp}°C</b>\n"
        f"🤗 Відчувається: <b>{feels}°C</b>\n"
        f"{icon} <b>{condition}</b>\n"
        f"💨 Вітер: <b>{wind} м/с</b>\n"
        f"💧 Вологість: <b>{humidity}%</b>\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"👕 <b>Що вдягнути:</b>\n"
        f"{tips}"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )