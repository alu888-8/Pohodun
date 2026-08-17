from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


# =====================================================
# УНІВЕРСАЛЬНА КЛАВІАТУРА
# =====================================================

def _make_keyboard(
    items,
    prefix,
    back_text="⬅️ Назад",
):
    keyboard = []
    row = []

    for item in items:
        button = KeyboardButton(
            text=f"{prefix} {item['name']}"
        )

        row.append(button)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append(
        [
            KeyboardButton(
                text=back_text
            )
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


# =====================================================
# ОБЛАСТІ
# =====================================================

def oblasts_keyboard(oblasts):

    return _make_keyboard(
        oblasts,
        "🗺",
        "⬅️ Назад",
    )


# =====================================================
# РАЙОНИ
# =====================================================

def raions_keyboard(raions):

    return _make_keyboard(
        raions,
        "📍",
        "🔙 До областей",
    )


# =====================================================
# МІСТА
# =====================================================

def cities_keyboard(cities):

    return _make_keyboard(
        cities,
        "🏙",
        "🔙 До областей",
    )


# =====================================================
# МЕНЮ ВИБОРУ ЛОКАЦІЇ
# =====================================================

def monitoring_location_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🏙 Обрати місто"
                ),
            ],
            [
                KeyboardButton(
                    text="🗺 Обрати область"
                ),
            ],
            [
                KeyboardButton(
                    text="⬅️ Назад"
                ),
            ],
        ],
        resize_keyboard=True,
    )


# =====================================================
# ПОШУК
# =====================================================

def location_search_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🔎 Пошук населеного пункту"
                )
            ],
            [
                KeyboardButton(
                    text="🗺 Обрати область"
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Назад"
                )
            ],
        ],
        resize_keyboard=True,
    )


# =====================================================
# ПІДТВЕРДЖЕННЯ ЛОКАЦІЇ
# =====================================================

def confirm_location_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="✅ Моніторити цю локацію"
                )
            ],
            [
                KeyboardButton(
                    text="🔄 Обрати іншу"
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Назад"
                )
            ],
        ],
        resize_keyboard=True,
    )