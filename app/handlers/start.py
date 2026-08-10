from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🌤 Вітаю!\n\n"
        "Я Pohodun 2.0\n\n"
        "Оберіть потрібний розділ 👇",
        reply_markup=main_menu,
    )