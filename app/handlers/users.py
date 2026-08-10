from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.db import get_users_count


router = Router()


@router.message(Command("users"))
async def users_command(message: Message):
    count = get_users_count()

    await message.answer(
        f"👥 Користувачів бота: {count}"
    )