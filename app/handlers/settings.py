import asyncio

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.db import (
    get_city,
    save_city,
    get_location,
    save_location,
)

from app.services.weather import get_weather
from app.data.cities import CITY_API

from app.keyboards.settings import settings_keyboard
from app.keyboards.cities import cities_keyboard as weather_cities_keyboard

from app.keyboards.locations import (
    monitoring_location_keyboard,
    cities_keyboard as monitoring_cities_keyboard,
    oblasts_keyboard,
    raions_keyboard,
)

from app.keyboards.menu import get_main_menu

from app.services.neptun_locations import (
    get_oblasts,
    get_raions_by_oblast,
    get_city_locations,
)


router = Router()


# =====================================================
# СТАНИ
# =====================================================

class CityState(StatesGroup):
    waiting_for_city = State()


class LocationState(StatesGroup):
    waiting_for_city = State()
    waiting_for_oblast = State()
    waiting_for_raion = State()


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

@router.message(
    lambda message:
    message.text == "⚙️ Налаштування"
)
async def settings(
    message: Message
):

    user_id = message.from_user.id

    city = get_city(user_id)

    location = get_location(user_id)

    if location:

        location_name = location.get(
            "name",
            "Не вибрана"
        )

        location_oblast = (
            location.get("oblast")
            or location.get("oblast_name")
            or ""
        )

        location_text = (
            f"📍 <b>{location_name}</b>"
        )

        if location_oblast:
            location_text += (
                f"\n🗺 {location_oblast}"
            )

    else:

        location_text = (
            "📍 <b>Не вибрана</b>"
        )

    weather_city = city or "Не вибране"

    text = (
        "⚙️ <b>Налаштування</b>\n\n"
        f"🌤 Місто для погоди: "
        f"<b>{weather_city}</b>\n\n"
        "🛰 <b>Локація моніторингу:</b>\n"
        f"{location_text}"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=settings_keyboard,
    )


# =====================================================
# МІСТО ДЛЯ ПОГОДИ
# =====================================================

@router.message(
    lambda message:
    message.text == "🗺 Місто для погоди"
)
async def choose_weather_city_menu(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await message.answer(
        "🌤 <b>Оберіть місто для погоди:</b>",
        parse_mode="HTML",
        reply_markup=weather_cities_keyboard,
    )


# =====================================================
# ПОЧАТОК ВИБОРУ ЛОКАЦІЇ МОНІТОРИНГУ
# =====================================================

@router.message(
    lambda message:
    message.text == "📍 Локація моніторингу"
)
async def choose_monitoring_location(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await message.answer(
        "📍 <b>Локація моніторингу</b>\n\n"
        "Оберіть, що хочете моніторити:",
        parse_mode="HTML",
        reply_markup=monitoring_location_keyboard(),
    )


# =====================================================
# ОБРАТИ МІСТО ДЛЯ МОНІТОРИНГУ
# =====================================================

@router.message(
    lambda message:
    message.text == "🏙 Обрати місто"
)
async def choose_monitoring_city(
    message: Message,
    state: FSMContext
):

    await state.clear()

    try:

        cities = await asyncio.to_thread(
            get_city_locations
        )

    except Exception as e:

        print(
            f"❌ NEPTUN міста: {e}"
        )

        await message.answer(
            "❌ Не вдалося отримати "
            "список міст NEPTUN."
        )

        return

    if not cities:

        await message.answer(
            "❌ Список міст порожній."
        )

        return

    await state.set_state(
        LocationState.waiting_for_city
    )

    await message.answer(
        "🏙 <b>Оберіть місто для моніторингу:</b>",
        parse_mode="HTML",
        reply_markup=monitoring_cities_keyboard(
            cities,
            "⬅️ Назад",
        ),
    )


# =====================================================
# ВИБІР МІСТА ДЛЯ МОНІТОРИНГУ
# =====================================================

@router.message(
    LocationState.waiting_for_city
)
async def select_monitoring_city(
    message: Message,
    state: FSMContext
):

    if message.text == "⬅️ Назад":

        await state.clear()

        await message.answer(
            "📍 <b>Локація моніторингу</b>",
            parse_mode="HTML",
            reply_markup=monitoring_location_keyboard(),
        )

        return

    if not message.text:

        return

    city_name = (
        message.text
        .replace("🏙", "")
        .strip()
    )

    cities = await asyncio.to_thread(
        get_city_locations
    )

    selected_city = None

    for city in cities:

        if (
            city["name"].strip().lower()
            == city_name.lower()
        ):

            selected_city = city

            break

    if not selected_city:

        await message.answer(
            "❌ Місто не знайдене."
        )

        return

    user_id = message.from_user.id

    # =================================================
    # ЗБЕРІГАЄМО САМЕ МІСТО
    # =================================================

    save_location(
        user_id,
        selected_city["key"],
        selected_city["name"],
        selected_city.get("oblast_name") or "",
    )

    await state.clear()

    oblast_name = (
        selected_city.get("oblast_name")
        or "—"
    )

    raion_name = (
        selected_city.get("raion_name")
        or "—"
    )

    await message.answer(
        "✅ <b>Локацію моніторингу збережено</b>\n\n"
        f"🏙 <b>{selected_city['name']}</b>\n"
        f"🗺 {oblast_name}\n"
        f"📍 {raion_name}",
        parse_mode="HTML",
        reply_markup=settings_keyboard,
    )


# =====================================================
# ОБРАТИ ОБЛАСТЬ
# =====================================================

@router.message(
    lambda message:
    message.text == "🗺 Обрати область"
)
async def choose_monitoring_oblast(
    message: Message,
    state: FSMContext
):

    await state.clear()

    try:

        oblasts = await asyncio.to_thread(
            get_oblasts
        )

    except Exception as e:

        print(
            f"❌ NEPTUN області: {e}"
        )

        await message.answer(
            "❌ Не вдалося отримати "
            "список областей NEPTUN."
        )

        return

    if not oblasts:

        await message.answer(
            "❌ Список областей порожній."
        )

        return

    await state.set_state(
        LocationState.waiting_for_oblast
    )

    await message.answer(
        "🗺 <b>Оберіть область:</b>",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(
            oblasts,
            "⬅️ Назад",
        ),
    )


# =====================================================
# ВИБІР ОБЛАСТІ
# =====================================================

@router.message(
    LocationState.waiting_for_oblast
)
async def select_oblast(
    message: Message,
    state: FSMContext
):

    if message.text == "⬅️ Назад":

        await state.clear()

        await message.answer(
            "📍 <b>Локація моніторингу</b>",
            parse_mode="HTML",
            reply_markup=monitoring_location_keyboard(),
        )

        return

    if not message.text:

        return

    oblast_name = (
        message.text
        .replace("🗺", "")
        .strip()
    )

    oblasts = await asyncio.to_thread(
        get_oblasts
    )

    selected_oblast = None

    for oblast in oblasts:

        if (
            oblast["name"].strip().lower()
            == oblast_name.lower()
        ):

            selected_oblast = oblast

            break

    if not selected_oblast:

        await message.answer(
            "❌ Область не знайдена."
        )

        return

    raions = await asyncio.to_thread(
        get_raions_by_oblast,
        selected_oblast["key"]
    )

    if not raions:

        await message.answer(
            "❌ Для цієї області "
            "не знайдено районів."
        )

        return

    await state.update_data(
        oblast_key=selected_oblast["key"],
        oblast_name=selected_oblast["name"],
    )

    await state.set_state(
        LocationState.waiting_for_raion
    )

    await message.answer(
        f"🗺 <b>{selected_oblast['name']}</b>\n\n"
        "Оберіть район:",
        parse_mode="HTML",
        reply_markup=raions_keyboard(
            raions,
            selected_oblast["name"],
        ),
    )


# =====================================================
# ВИБІР РАЙОНУ
# =====================================================

@router.message(
    LocationState.waiting_for_raion
)
async def select_raion(
    message: Message,
    state: FSMContext
):

    if message.text == "🔙 До областей":

        await state.set_state(
            LocationState.waiting_for_oblast
        )

        oblasts = await asyncio.to_thread(
            get_oblasts
        )

        await message.answer(
            "🗺 <b>Оберіть область:</b>",
            parse_mode="HTML",
            reply_markup=oblasts_keyboard(
                oblasts,
                "⬅️ Назад",
            ),
        )

        return

    if message.text == "⬅️ Назад":

        await state.clear()

        await message.answer(
            "📍 <b>Локація моніторингу</b>",
            parse_mode="HTML",
            reply_markup=monitoring_location_keyboard(),
        )

        return

    if not message.text:

        return

    raion_name = (
        message.text
        .replace("📍", "")
        .strip()
    )

    data = await state.get_data()

    oblast_name = data.get(
        "oblast_name"
    )

    oblast_key = data.get(
        "oblast_key"
    )

    if not oblast_key:

        await state.clear()

        await message.answer(
            "❌ Сесія вибору локації "
            "завершилася. Спробуйте ще раз."
        )

        return

    raions = await asyncio.to_thread(
        get_raions_by_oblast,
        oblast_key
    )

    selected_raion = None

    for raion in raions:

        if (
            raion["name"].strip().lower()
            == raion_name.lower()
        ):

            selected_raion = raion

            break

    if not selected_raion:

        await message.answer(
            "❌ Район не знайдений."
        )

        return

    user_id = message.from_user.id

    save_location(
        user_id,
        selected_raion["key"],
        selected_raion["name"],
        oblast_name,
    )

    await state.clear()

    await message.answer(
        "✅ <b>Локацію моніторингу збережено</b>\n\n"
        f"📍 {selected_raion['name']}\n"
        f"🗺 {oblast_name}",
        parse_mode="HTML",
        reply_markup=settings_keyboard,
    )


# =====================================================
# НАЗАД
# =====================================================

@router.message(
    lambda message:
    message.text == "⬅️ Назад"
)
async def back_to_menu(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await message.answer(
        "🏠 Головне меню",
        reply_markup=get_main_menu(
            message.from_user.id,
            message.chat.type,
        ),
    )


# =====================================================
# ВИБІР МІСТА ДЛЯ ПОГОДИ
# =====================================================

@router.message(
    lambda message:
    message.text
    and message.text.startswith("📍")
)
async def choose_weather_city(
    message: Message,
    state: FSMContext
):

    current_state = await state.get_state()

    # Під час вибору району/міста моніторингу
    # цей handler не повинен перехоплювати кнопки.

    if current_state in (
        LocationState.waiting_for_city.state,
        LocationState.waiting_for_raion.state,
    ):

        return

    city = (
        message.text
        .replace("📍", "")
        .strip()
    )

    user_id = message.from_user.id

    api_city = CITY_API.get(
        city
    )

    if api_city is None:

        await message.answer(
            "❌ Такого міста немає "
            "у списку."
        )

        return

    weather = await asyncio.to_thread(
        get_weather,
        api_city
    )

    if weather is None:

        await message.answer(
            "❌ Не вдалося отримати "
            "погоду для цього міста."
        )

        return

    save_city(
        user_id,
        city
    )

    await state.clear()

    await message.answer(
        f"✅ Місто для погоди "
        f"змінено на <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard,
    )


# =====================================================
# ІНШЕ МІСТО
# =====================================================

@router.message(
    lambda message:
    message.text == "✏️ Інше місто"
)
async def other_city(
    message: Message,
    state: FSMContext
):

    await state.set_state(
        CityState.waiting_for_city
    )

    await message.answer(
        "✍️ <b>Напишіть назву міста "
        "англійською.</b>\n\n"
        "Наприклад:\n"
        "Kyiv\n"
        "Lviv\n"
        "Odesa",
        parse_mode="HTML",
    )


# =====================================================
# ВВЕДЕНЕ МІСТО
# =====================================================

@router.message(
    CityState.waiting_for_city
)
async def change_city(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "❌ Напишіть назву міста."
        )

        return

    city = message.text.strip()

    user_id = message.from_user.id

    weather = await asyncio.to_thread(
        get_weather,
        city
    )

    if weather is None:

        await message.answer(
            "❌ Не вдалося знайти це місто.\n\n"
            "Напишіть англійською:\n"
            "Kyiv, Lviv, Odesa."
        )

        return

    save_city(
        user_id,
        city
    )

    await state.clear()

    await message.answer(
        f"✅ Місто для погоди "
        f"змінено на <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard,
    )