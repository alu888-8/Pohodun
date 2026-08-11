from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import get_main_menu
from app.database.db import save_city


router = Router()


@router.message(CommandStart())
async def start(message: Message):

    # Додаємо користувача в базу.
    # Якщо він уже є — його місто залишиться без змін.
    save_city(
        message.from_user.id,
        "Київ"
    )

    await message.answer(
        "🌤 Вітаю!\n\n"
        "Я Pohodun 2.0\n\n"
        "Оберіть потрібний розділ 👇",
        reply_markup=get_main_menu(
            message.from_user.id
        ),
    )