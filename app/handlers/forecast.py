import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.forecast import get_forecast
from app.utils.weather_icons import get_weather_icon

router = Router()


@router.message(lambda message: message.text == "📅 Прогноз")
async def forecast(message: Message):

    city_ua = get_city(message.from_user.id)
    city_api = CITY_API.get(city_ua, city_ua)

    # Не блокуємо Telegram-бота під час запиту WeatherAPI
    data = await asyncio.to_thread(
        get_forecast,
        city_api
    )

    if data is None:
        await message.answer(
            "❌ Не вдалося отримати прогноз."
        )
        return

    try:
        days = data["forecast"]["forecastday"]

        names = [
            "📍 Сьогодні",
            "🌅 Завтра",
            "📆 Післязавтра"
        ]

        text = (
            f"📅 <b>Прогноз погоди</b>\n\n"
            f"📍 <b>{city_ua}</b>\n"
        )

        for i, day in enumerate(days):

            condition = day["day"]["condition"]["text"]
            icon = get_weather_icon(condition)

            max_temp = round(day["day"]["maxtemp_c"])
            min_temp = round(day["day"]["mintemp_c"])
            rain = day["day"]["daily_chance_of_rain"]

            text += (
                f"\n<b>{names[i]}</b>\n"
                f"{icon} {condition}\n"
                f"🌡 {min_temp}°C ... {max_temp}°C\n"
                f"💧 Ймовірність опадів: {rain}%\n"
            )

        await message.answer(
            text,
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            f"❌ Помилка обробки прогнозу: {e}"
        )

        await message.answer(
            "❌ Не вдалося сформувати прогноз."
        )