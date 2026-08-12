import asyncio

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


@router.message(
    lambda message: message.text == "🌤 Погода зараз"
)
async def weather_now(message: Message):

    user_id = message.from_user.id

    # ==========================================
    # МІСТО
    # ==========================================

    city_ua = await asyncio.to_thread(
        get_city,
        user_id
    )

    city_api = CITY_API.get(
        city_ua,
        city_ua
    )

    print(
        f"🌤 Погода | user={user_id} | city={city_ua}"
    )

    # ==========================================
    # ПОГОДА
    # ==========================================

    # requests не блокує Telegram-бота
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
    feels = weather["feels_like"]
    humidity = weather["humidity"]
    wind = weather["wind"]
    description = weather["condition"]

    icon = get_weather_icon(
        description
    )

    # ==========================================
    # КОНТЕНТ ДНЯ
    # ==========================================

    today = datetime.now(
        ZoneInfo("Europe/Kyiv")
    ).strftime("%Y-%m-%d")

    # SQLite теж виносимо з event loop
    daily_content = await asyncio.to_thread(
        get_daily_content,
        city_ua
    )

    # ==========================================
    # ЯКЩО КОНТЕНТУ НА СЬОГОДНІ НЕМАЄ
    # ==========================================

    if (
        daily_content is None
        or daily_content["date"] != today
    ):

        print(
            f"🤖 Генеруємо контент дня "
            f"для {city_ua}: {today}"
        )

        # AI-запит НЕ блокує Telegram-бота
        daily_content = await asyncio.to_thread(
            generate_daily_content,
            city=city_ua,
            weather=weather
        )

        if daily_content is not None:

            await asyncio.to_thread(
                save_daily_content,
                city=city_ua,
                content_date=today,
                joke=daily_content["joke"],
                greeting=daily_content["greeting"]
            )

            print(
                f"✅ Контент дня збережено "
                f"для {city_ua}"
            )

        else:

            print(
                f"❌ AI-контент не отримано "
                f"для {city_ua}"
            )

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
            f"📦 Використовуємо готовий "
            f"контент дня для {city_ua}: {today}"
        )

    # ==========================================
    # ФОРМУЄМО ПОВІДОМЛЕННЯ
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

    print(
        f"✅ Погода відправлена | "
        f"user={user_id} | city={city_ua}"
    )