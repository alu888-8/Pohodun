from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.db import get_city, save_city
from app.services.weather import get_weather

from app.data.cities import CITY_API

from app.keyboards.settings import settings_keyboard
from app.keyboards.cities import cities_keyboard
from app.keyboards.menu import main_menu


router = Router()


# Стан для введення іншого міста
class CityState(StatesGroup):
    waiting_for_city = State()


# =========================
# НАЛАШТУВАННЯ
# =========================

@router.message(lambda message: message.text == "⚙️ Налаштування")
async def settings(message: Message):

    user_id = message.from_user.id
    city = get_city(user_id)

    print(
        f"⚙️ Налаштування | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    text = (
        "⚙️ <b>Налаштування</b>\n\n"
        f"📍 Поточне місто: <b>{city}</b>"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=settings_keyboard
    )


# =========================
# ЗМІНИТИ МІСТО
# =========================

@router.message(lambda message: message.text == "🗺 Змінити місто")
async def choose_city_menu(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "📍 <b>Оберіть місто:</b>",
        parse_mode="HTML",
        reply_markup=cities_keyboard
    )


# =========================
# НАЗАД
# =========================

@router.message(lambda message: message.text == "⬅️ Назад")
async def back_to_menu(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "🏠 Головне меню",
        reply_markup=main_menu
    )


# =========================
# ВИБІР МІСТА З КНОПКИ
# =========================

@router.message(lambda message: message.text and message.text.startswith("📍"))
async def choose_city(message: Message, state: FSMContext):

    city = message.text.replace("📍", "").strip()
    user_id = message.from_user.id

    print(
        f"📍 Вибір міста | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    api_city = CITY_API.get(city)

    if api_city is None:
        await message.answer(
            "❌ Такого міста немає у списку."
        )
        return

    weather = get_weather(api_city)

    if weather is None:
        await message.answer(
            "❌ Не вдалося отримати погоду для цього міста."
        )
        return

    # Зберігаємо місто КОНКРЕТНОГО користувача
    save_city(
        user_id,
        city
    )

    print(
        f"✅ Місто збережено | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    await state.clear()

    await message.answer(
        f"✅ Місто змінено на <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )


# =========================
# ІНШЕ МІСТО
# =========================

@router.message(lambda message: message.text == "✏️ Інше місто")
async def other_city(message: Message, state: FSMContext):

    await state.set_state(
        CityState.waiting_for_city
    )

    await message.answer(
        "✍️ <b>Напишіть назву міста англійською.</b>\n\n"
        "Наприклад:\n"
        "Kyiv\n"
        "Lviv\n"
        "Odesa",
        parse_mode="HTML"
    )


# =========================
# ОБРОБКА ВВЕДЕНОГО МІСТА
# =========================

@router.message(CityState.waiting_for_city)
async def change_city(message: Message, state: FSMContext):

    if not message.text:
        await message.answer(
            "❌ Напишіть назву міста текстом."
        )
        return

    city = message.text.strip()
    user_id = message.from_user.id

    print(
        f"✏️ Інше місто | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    weather = get_weather(city)

    if weather is None:
        await message.answer(
            "❌ Не вдалося знайти це місто.\n\n"
            "Спробуйте написати назву англійською.\n"
            "Наприклад: Kyiv, Lviv, Odesa."
        )
        return

    save_city(
        user_id,
        city
    )

    print(
        f"✅ Місто збережено | "
        f"user_id={user_id} | "
        f"city={city}"
    )

    await state.clear()

    await message.answer(
        f"✅ Місто змінено на <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )