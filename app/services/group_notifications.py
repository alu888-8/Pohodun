import asyncio

from aiogram import Bot, Router
from aiogram.types import Message


async def group_alert_monitor(bot: Bot):

    print(
        "🚨 Моніторинг початку та відбою тривог запущений"
    )

    print(
        f"⏱ Інтервал перевірки: "
        f"{MONITOR_INTERVAL} секунд"
    )

    # далі весь твій код моніторингу