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
from app.handlers.admin import router as admin_router

from app.services.group_notifications import (
    group_alert_monitor,
    morning_weather_scheduler
)


# ID Telegram-групи
GROUP_CHAT_ID = -493936504


async def main():

    # =========================
    # БАЗА ДАНИХ
    # =========================

    init_db()


    # =========================
    # BOT
    # =========================

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()


    # =========================
    # РОУТЕРИ
    # =========================

    dp.include_router(start_router)
    dp.include_router(weather_router)
    dp.include_router(forecast_router)
    dp.include_router(air_quality_router)
    dp.include_router(alerts_router)
    dp.include_router(threats_router)
    dp.include_router(advice_router)
    dp.include_router(users_router)
    dp.include_router(settings_router)
    dp.include_router(admin_router)


    print(
        "✅ Pohodun запущений"
    )


    # =========================
    # МОНІТОРИНГ ТРИВОГ
    # =========================

    asyncio.create_task(
        group_alert_monitor(bot)
    )

    print(
        "🚨 Моніторинг початку "
        "та відбою тривог запущений"
    )


    # =========================
    # РАНКОВА ПОГОДА 08:00
    # =========================

    asyncio.create_task(
        morning_weather_scheduler(bot)
    )

    print(
        "🌅 Планувальник ранкової "
        "погоди запущений"
    )


    # =========================
    # ЗАПУСК БОТА
    # =========================

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )