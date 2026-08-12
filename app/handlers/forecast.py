import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.cities import CITY_API

from app.services.forecast import get_forecast
from app.utils.weather_icons import get_weather_icon


router = Router()


@router.message(
    lambda message: message.text == "📅 Прогноз"
)
async def forecast(message: Message):

    city_ua = get_city(
        message.from_user.id
    )

    city_api = CITY_API.get(
        city_ua,
        city_ua
    )

    print(
        f"📅 Прогноз | "
        f"user_id={message.from_user.id} | "
        f"city={city_ua} | "
        f"api_city={city_api}"
    )

    # ==========================================
    # Отримуємо прогноз у окремому потоці
    # ==========================================

    data = await asyncio.to_thread(
        get_forecast,
        city_api
    )

    if data is None:

        await message.answer(
            "❌ Не вдалося отримати прогноз."
        )

        return

    # ==========================================
    # Перевіряємо структуру відповіді
    # ==========================================

    try:

        days = data["forecast"]["forecastday"]

    except (
        KeyError,
        TypeError
    ) as e:

        print(
            f"❌ Помилка структури прогнозу: {e}"
        )

        await message.answer(
            "❌ API повернув неправильний "
            "формат прогнозу."
        )

        return

    if not days:

        await message.answer(
            "❌ Прогноз для цього міста відсутній."
        )

        return

    names = [
        "📍 Сьогодні",
        "🌅 Завтра",
        "📆 Післязавтра"
    ]

    text = (
        f"📅 <b>Прогноз погоди</b>\n\n"
        f"📍 <b>{city_ua}</b>\n"
    )

    # ==========================================
    # Формуємо прогноз
    # ==========================================

    for i, day in enumerate(days[:3]):

        try:

            condition = (
                day["day"]["condition"]["text"]
            )

            icon = get_weather_icon(
                condition
            )

            max_temp = round(
                day["day"]["maxtemp_c"]
            )

            min_temp = round(
                day["day"]["mintemp_c"]
            )

            rain = day["day"].get(
                "daily_chance_of_rain",
                0
            )

            day_name = (
                names[i]
                if i < len(names)
                else f"📆 День {i + 1}"
            )

            text += (
                f"\n<b>{day_name}</b>\n"
                f"{icon} {condition}\n"
                f"🌡 {min_temp}°C ... {max_temp}°C\n"
                f"💧 Ймовірність опадів: "
                f"{rain}%\n"
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ) as e:

            print(
                f"❌ Помилка обробки дня "
                f"{i}: {e}"
            )

            continue

    # ==========================================
    # Відправляємо результат
    # ==========================================

    await message.answer(
        text,
        parse_mode="HTML"
    )