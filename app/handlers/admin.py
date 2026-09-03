import asyncio
from collections import Counter

from aiogram import Router
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.db import (
    get_all_users,
    save_group_location,
)
from app.services.neptun_locations import (
    get_city_locations,
    get_oblasts,
    get_raions_by_oblast,
)
from app.keyboards.locations import (
    cities_keyboard,
    oblasts_keyboard,
    raions_keyboard,
)


router = Router()

ADMIN_ID = 366025054


class GroupLocationState(StatesGroup):
    waiting_for_city = State()
    waiting_for_oblast = State()
    waiting_for_raion = State()


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
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📍 Локація групи"
                    )
                ]
            ],
            resize_keyboard=True,
        ),
    )


# =========================

# ЛОКАЦІЯ ГРУПИ
# =========================

@router.message(
    lambda message:
    message.text == "📍 Локація групи"
)
async def group_location_menu(
    message: Message,
    state: FSMContext,
):

    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        await message.answer(
            "❌ Цю функцію потрібно "
            "налаштовувати саме в групі."
        )
        return

    try:
        member = await message.bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        if member.status not in (
            "creator",
            "administrator",
        ):
            await message.answer(
                "❌ Локацію групи може "
                "налаштувати тільки адміністратор."
            )
            return

    except Exception as e:
        print(
            f"❌ Перевірка адміна групи: {e}"
        )

        await message.answer(
            "❌ Не вдалося перевірити "
            "права адміністратора."
        )
        return

    await state.clear()

    await message.answer(
        "📍 <b>Локація групи</b>\n\n"
        "Оберіть тип локації:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🏙 Обрати місто")],
                [KeyboardButton(text="🗺 Обрати область")],
                [KeyboardButton(text="⬅️ Назад")],
            ],
            resize_keyboard=True,
        ),
    )
# =========================
# ПОЧАТОК ВИБОРУ ОБЛАСТІ ГРУПИ

@router.message(lambda message: message.text == "/group_location")
async def group_location_command(message: Message, state: FSMContext):
    await group_location_menu(message, state)
# =========================

@router.message(
    lambda message:
    message.text == "🗺 Обрати область"
)
async def choose_group_oblast(
    message: Message,
    state: FSMContext,
):
    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        return

    try:
        member = await message.bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        if member.status not in (
            "creator",
            "administrator",
        ):
            return

    except Exception:
        return

    try:
        oblasts = await asyncio.to_thread(
            get_oblasts
        )
    except Exception as e:
        print(
            f"❌ NEPTUN області для групи: {e}"
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
        GroupLocationState.waiting_for_oblast
    )

    await message.answer(
        "🗺 <b>Оберіть область для групи:</b>",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(
            oblasts,
            "⬅️ Назад",
        ),
    )

# =========================
# ВИБІР ОБЛАСТІ ГРУПИ
# =========================

@router.message(
    GroupLocationState.waiting_for_oblast
)
async def select_group_oblast(
    message: Message,
    state: FSMContext,
):
    if message.text == "⬅️ Назад":
        await state.clear()
        await group_location_menu(message, state)
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

    selected_oblast = next(
        (
            oblast
            for oblast in oblasts
            if oblast["name"].strip().lower()
            == oblast_name.lower()
        ),
        None,
    )

    if not selected_oblast:
        await message.answer(
            "❌ Область не знайдена."
        )
        return

    raions = await asyncio.to_thread(
        get_raions_by_oblast,
        selected_oblast["key"],
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
        GroupLocationState.waiting_for_raion
    )

    await message.answer(
        f"🗺 <b>{selected_oblast['name']}</b>\n\n"
        "Оберіть район для групи:",
        parse_mode="HTML",
        reply_markup=raions_keyboard(
            raions,
            selected_oblast["name"],
        ),
    )

# =========================
# ВИБІР РАЙОНУ ГРУПИ
# =========================

@router.message(
    GroupLocationState.waiting_for_raion
)
async def select_group_raion(
    message: Message,
    state: FSMContext,
):
    if message.text == "🔙 До областей":
        await state.set_state(
            GroupLocationState.waiting_for_oblast
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
        await group_location_menu(message, state)
        return

    if not message.text:
        return

    raion_name = (
        message.text
        .replace("📍", "")
        .strip()
    )

    data = await state.get_data()

    oblast_key = data.get("oblast_key")
    oblast_name = data.get("oblast_name")

    if not oblast_key:
        await state.clear()

        await message.answer(
            "❌ Сесія вибору локації "
            "завершилася. Спробуйте ще раз."
        )
        return

    raions = await asyncio.to_thread(
        get_raions_by_oblast,
        oblast_key,
    )

    selected_raion = next(
        (
            raion
            for raion in raions
            if raion["name"].strip().lower()
            == raion_name.lower()
        ),
        None,
    )

    if not selected_raion:
        await message.answer(
            "❌ Район не знайдений."
        )
        return

    save_group_location(
        message.chat.id,
        selected_raion["key"],
        selected_raion["name"],
        oblast_name or "",
    )

    await state.clear()

    await message.answer(
        "✅ <b>Локацію групи збережено</b>\n\n"
        f"📍 <b>{selected_raion['name']}</b>\n"
        f"🗺 {oblast_name or '—'}",
        parse_mode="HTML",
    )


# =========================
# ПОЧАТОК ВИБОРУ МІСТА ГРУПИ
# =========================

@router.message(
    lambda message:
    message.text == "🏙 Обрати місто"
)
async def choose_group_city(
    message: Message,
    state: FSMContext,
):
    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        return

    try:
        member = await message.bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )

        if member.status not in (
            "creator",
            "administrator",
        ):
            return

    except Exception:
        return

    cities = await asyncio.to_thread(
        get_city_locations
    )

    await state.set_state(
        GroupLocationState.waiting_for_city
    )

    await message.answer(
        "🏙 <b>Оберіть місто для групи:</b>",
        parse_mode="HTML",
        reply_markup=cities_keyboard(
            cities,
            "⬅️ Назад",
        ),
    )


# =========================
# ВИБІР МІСТА ДЛЯ ГРУПИ
# =========================

@router.message(
    GroupLocationState.waiting_for_city
)
async def select_group_city(
    message: Message,
    state: FSMContext,
):

    if message.text == "⬅️ Назад":
        await state.clear()

        await message.answer(
            "🔧 <b>АДМІН-ПАНЕЛЬ</b>",
            parse_mode="HTML",
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

    save_group_location(
        message.chat.id,
        selected_city["key"],
        selected_city["name"],
        selected_city.get("oblast_name") or "",
    )

    await state.clear()

    await message.answer(
        "✅ <b>Локацію групи збережено</b>\n\n"
        f"🏙 <b>{selected_city['name']}</b>\n"
        f"🗺 {selected_city.get('oblast_name') or '—'}",
        parse_mode="HTML",
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
