from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city, save_city
from app.services.weather import get_weather

from app.data.cities import CITY_API

from app.keyboards.settings import settings_keyboard
from app.keyboards.cities import cities_keyboard
from app.keyboards.menu import main_menu

router = Router()


@router.message(lambda message: message.text == "⚙️ Налаштування")
async def settings(message: Message):

    city = get_city(message.from_user.id)

    text = (
        "⚙️ <b>Налаштування</b>\n\n"
        f"📍 Поточне місто: <b>{city}</b>"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=settings_keyboard
    )


@router.message(lambda message: message.text == "🗺 Змінити місто")
async def choose_city_menu(message: Message):

    await message.answer(
        "📍 Оберіть місто:",
        reply_markup=cities_keyboard
    )


@router.message(lambda message: message.text == "⬅️ Назад")
async def back_to_menu(message: Message):

    await message.answer(
        "🏠 Головне меню",
        reply_markup=main_menu
    )


@router.message(lambda message: message.text.startswith("📍"))
async def choose_city(message: Message):

    city = message.text.replace("📍", "").strip()

    api_city = CITY_API.get(city)

    if api_city is None:
        await message.answer("❌ Такого міста немає.")
        return

    weather = get_weather(api_city)

    if weather is None:
        await message.answer("❌ Не вдалося знайти це місто.")
        return

    save_city(
        message.from_user.id,
        city
    )

    await message.answer(
        f"✅ Місто змінено на <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )


@router.message(lambda message: message.text == "✏️ Інше місто")
async def other_city(message: Message):

    await message.answer(
        "✍️ Напишіть назву міста англійською.\n\n"
        "Наприклад:\n"
        "Kyiv\n"
        "Lviv\n"
        "Odesa"
    )


@router.message()
async def change_city(message: Message):

    api_city = message.text.strip()

    weather = get_weather(api_city)

    if weather is None:
        return

    save_city(
        message.from_user.id,
        api_city
    )

    await message.answer(
        f"✅ Місто змінено на <b>{api_city}</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )