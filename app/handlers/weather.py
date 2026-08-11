from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.types import Message

from app.database.db import (
    get_city,
    get_daily_content,
    save_daily_content
)

from app.data.cities import CITY_API

from app.services.weather import get_weather
from app.services.ai_joke import generate_daily_content

from app.utils.weather_icons import get_weather_icon

router = Router()


@router.message(lambda message: message.text == "🌤 Погода зараз")
async def weather_now(message: Message):

    # Отримуємо місто конкретного користувача
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

    # ==========================================
    # КОНТЕНТ ДНЯ ДЛЯ КОНКРЕТНОГО МІСТА
    # ==========================================

    today = datetime.now(
        ZoneInfo("Europe/Kyiv")
    ).strftime("%Y-%m-%d")

    # Шукаємо контент саме для цього міста
    daily_content = get_daily_content(city_ua)

    # Якщо для цього міста сьогодні контенту ще немає —
    # генеруємо його через AI
    if (
        daily_content is None
        or daily_content["date"] != today
    ):

        print(
            f"🤖 Генеруємо контент дня для {city_ua}: {today}"
        )

        daily_content = generate_daily_content(
            city=city_ua,
            weather=weather
        )

        if daily_content is not None:

            save_daily_content(
                city=city_ua,
                content_date=today,
                joke=daily_content["joke"],
                greeting=daily_content["greeting"]
            )

            print(
                f"✅ Контент дня збережено для {city_ua}"
            )

        else:

            print(
                f"❌ Не вдалося згенерувати контент для {city_ua}"
            )

            # Запасний варіант, якщо AI недоступний
            daily_content = {
                "joke": (
                    "Погодун сьогодні вирішив "
                    "не жартувати. Каже, погода "
                    "і так достатньо непередбачувана 😄"
                ),
                "greeting": (
                    "☀️ Нехай цей день принесе "
                    "щось приємне 😉"
                )
            }

    else:

        print(
            f"📦 Використовуємо контент дня для {city_ua}: {today}"
        )

    # ==========================================
    # ТЕКСТ ПОВІДОМЛЕННЯ
    # ==========================================

    joke = daily_content["joke"]
    greeting = daily_content["greeting"]

    text = (
        f"🌤 <b>Погодун</b>\n\n"

        f"📍 <b>{city_ua}</b>\n\n"

        f"{icon} <b>{description}</b>\n\n"

        f"🌡 Температура: <b>{temp}°C</b>\n"
        f"🤗 Відчувається: <b>{feels}°C</b>\n"
        f"💨 Вітер: <b>{wind} м/с</b>\n"
        f"💧 Вологість: <b>{humidity}%</b>\n\n"

        f"━━━━━━━━━━━━━━\n\n"

        f"😂 <b>Анекдот дня</b>\n\n"
        f"{joke}\n\n"

        f"━━━━━━━━━━━━━━\n\n"

        f"☀️ <b>{greeting}</b>"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )