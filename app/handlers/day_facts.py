import asyncio

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.services.day_facts import get_day_facts


router = Router()


@router.message(
    lambda message: message.text == "📣 Є що сказати"
)
async def day_facts(message: Message):

    user_id = message.from_user.id

    city = get_city(user_id)

    if not city:
        await message.answer(
            "❌ Спочатку оберіть місто."
        )
        return

    print(
        f"📅 DAY FACTS | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    text = await asyncio.to_thread(
        get_day_facts,
        city,
    )

    await message.answer(
        text,
        parse_mode="HTML",
    )

    print(
        f"✅ DAY FACTS | "
        f"city={city}"
    )