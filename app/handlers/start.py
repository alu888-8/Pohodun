from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import get_main_menu
from app.database.db import save_city


router = Router()


@router.message(CommandStart())
async def start(message: Message):

    # =====================================================
    # ДОДАЄМО КОРИСТУВАЧА В БАЗУ
    # =====================================================

    save_city(
        message.from_user.id,
        "Київ"
    )

    # =====================================================
    # ГОЛОВНЕ МЕНЮ
    #
    # chat_type потрібен для того,
    # щоб Адмінка показувалась
    # тільки в особистому чаті.
    # =====================================================

    await message.answer(
        "🌤 Вітаю!\n\n"
        "Я Pohodun 2.0\n\n"
        "Оберіть потрібний розділ 👇",
        reply_markup=get_main_menu(
            message.from_user.id,
            message.chat.type,
        ),
    )