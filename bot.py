import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN

from app.database.db import init_db

from app.handlers.start import router as start_router
from app.handlers.weather import router as weather_router
from app.handlers.forecast import router as forecast_router
from app.handlers.air_quality import router as air_quality_router
from app.handlers.alerts import router as alerts_router
from app.handlers.threats import router as threats_router
from app.handlers.advice import router as advice_router
from app.handlers.users import router as users_router
from app.handlers.settings import router as settings_router


# ID Telegram-групи
GROUP_CHAT_ID = -493936504


async def main():

    # Створюємо базу даних, якщо її ще немає
    init_db()

    bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher()

    # Роутери
    dp.include_router(start_router)
    dp.include_router(weather_router)
    dp.include_router(forecast_router)
    dp.include_router(air_quality_router)
    dp.include_router(alerts_router)
    dp.include_router(threats_router)
    dp.include_router(advice_router)
    dp.include_router(users_router)
    dp.include_router(settings_router)

    print("✅ Pohodun запущений")

    # Тестове повідомлення в групу
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text="🤖 Pohodun підключився до групи!"
        )
        print("✅ Повідомлення в групу відправлено")
    except Exception as e:
        print(f"❌ Помилка відправки в групу: {e}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())