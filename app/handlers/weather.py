from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.weather import get_weather
from app.utils.weather_icons import get_weather_icon

router = Router()


@router.message(lambda message: message.text == "🌤 Погода зараз")
async def weather_now(message: Message):

    # Отримуємо місто користувача
    city_ua = get_city(message.from_user.id)

    # Перетворюємо назву для WeatherAPI
    city_api = CITY_API.get(city_ua, city_ua)

    weather = get_weather(city_api)

    if weather is None:
        await message.answer(
            "❌ Не вдалося отримати погоду."
        )
        return

    temp = weather["temp"]
    feels = weather["feels_like"]
    humidity = weather["humidity"]
    wind = weather["wind"]
    description = weather["condition"]

    # Автоматична іконка погоди
    icon = get_weather_icon(description)

    text = (
        f"🌤 <b>Погодун</b>\n\n"
        f"📍 <b>{city_ua}</b>\n\n"
        f"{icon} <b>{description}</b>\n\n"
        f"🌡 Температура: <b>{temp}°C</b>\n"
        f"🤗 Відчувається: <b>{feels}°C</b>\n"
        f"💨 Вітер: <b>{wind} м/с</b>\n"
        f"💧 Вологість: <b>{humidity}%</b>\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"☀️ <b>Гарного дня!</b> "
        f"Нехай погода сьогодні буде на твоєму боці 😉"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )