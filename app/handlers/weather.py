import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.weather import get_weather
from app.utils.weather_icons import get_weather_icon


router = Router()


@router.message(
    lambda message: message.text == "🌤 Погода зараз"
)
async def weather_now(message: Message):

    user_id = message.from_user.id

    # ==========================================
    # ОТРИМУЄМО МІСТО КОРИСТУВАЧА
    # ==========================================

    city_ua = get_city(user_id)

    print(
        f"🌤 WEATHER | user_id={user_id} | "
        f"city_from_db={city_ua}"
    )

    if not city_ua:

        await message.answer(
            "❌ Спочатку оберіть місто."
        )

        return

    # ==========================================
    # КООРДИНАТИ МІСТА
    # ==========================================

    city_api = CITY_API.get(
        city_ua,
        city_ua
    )

    print(
        f"🌤 WEATHER | city_api={city_api}"
    )

    # ==========================================
    # ОТРИМУЄМО ПОГОДУ
    # ==========================================

    weather = await asyncio.to_thread(
        get_weather,
        city_api
    )

    if weather is None:

        await message.answer(
            "❌ Не вдалося отримати актуальну погоду.\n"
            "Спробуйте ще раз через кілька секунд."
        )

        return

    # ==========================================
    # ДАНІ
    # ==========================================

    temp = weather.get(
        "temp",
        "?"
    )

    feels = weather.get(
        "feels_like",
        "?"
    )

    humidity = weather.get(
        "humidity",
        "?"
    )

    wind = weather.get(
        "wind",
        "?"
    )

    description = weather.get(
        "condition",
        "Невідомо"
    )

    icon = get_weather_icon(
        description
    )

    # ==========================================
    # ВІДПОВІДЬ
    # ==========================================

    text = (
        f"🌤 <b>Погодун</b>\n\n"
        f"📍 <b>{city_ua}</b>\n\n"
        f"{icon} <b>{description}</b>\n\n"
        f"🌡 Температура: <b>{temp}°C</b>\n"
        f"🤗 Відчувається: <b>{feels}°C</b>\n"
        f"💨 Вітер: <b>{wind} м/с</b>\n"
        f"💧 Вологість: <b>{humidity}%</b>"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )

    print(
        f"✅ WEATHER | Відправлено | "
        f"user_id={user_id} | city={city_ua}"
    )