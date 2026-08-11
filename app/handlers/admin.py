from collections import Counter

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_all_users


router = Router()

ADMIN_ID = 366025054


# =========================
# АДМІН-ПАНЕЛЬ
# =========================

@router.message(
    lambda message:
    message.text == "🔧 Адмінка"
    and message.from_user.id == ADMIN_ID
)
async def admin_panel(message: Message):

    users = get_all_users()

    total_users = len(users)

    cities = Counter(
        user["city"]
        for user in users
    )

    text = (
        "🔧 <b>АДМІН-ПАНЕЛЬ</b>\n\n"
        f"👥 Користувачів: <b>{total_users}</b>\n\n"
        "📍 <b>Користувачі по містах:</b>\n\n"
    )

    if cities:

        for city, count in cities.most_common():

            text += (
                f"📍 {city} — <b>{count}</b>\n"
            )

    else:

        text += "Користувачів поки немає."

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================
# КОМАНДА /admin
# =========================

@router.message(
    lambda message:
    message.text == "/admin"
    and message.from_user.id == ADMIN_ID
)
async def admin_command(message: Message):

    users = get_all_users()

    total_users = len(users)

    cities = Counter(
        user["city"]
        for user in users
    )

    text = (
        "🔧 <b>АДМІН-ПАНЕЛЬ</b>\n\n"
        f"👥 Користувачів: <b>{total_users}</b>\n\n"
        "📍 <b>Користувачі по містах:</b>\n\n"
    )

    if cities:

        for city, count in cities.most_common():

            text += (
                f"📍 {city} — <b>{count}</b>\n"
            )

    else:

        text += "Користувачів поки немає."

    await message.answer(
        text,
        parse_mode="HTML"
    )