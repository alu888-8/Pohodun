from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from app.database.db import get_users_count

router = Router()


@router.message(Command("clear_keyboard"))
async def clear_keyboard_command(message: Message):
    await message.answer(
        "✅ Стару клавіатуру прибрано.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("chatid"))
async def chatid_command(message: Message):
    await message.answer(
        f"🆔 ID цієї групи:\n`{message.chat.id}`",
        parse_mode="Markdown"
    )


@router.message(Command("users"))
async def users_command(message: Message):
    count = get_users_count()

    await message.answer(
        f"👥 Користувачів бота: {count}"
    )