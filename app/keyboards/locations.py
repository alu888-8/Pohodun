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
    columns=2,
):
    keyboard = []
    row = []

    for item in items:
        row.append(
            KeyboardButton(
                text=f"{prefix} {item['name']}"
            )
        )

        if len(row) == columns:
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
# ГОЛОВНЕ МЕНЮ ЛОКАЦІЇ
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
# МІСТА
# =====================================================

def cities_keyboard(
    cities,
    back_text="⬅️ Назад",
):
    return _make_keyboard(
        cities,
        "🏙",
        back_text,
        columns=2,
    )


# =====================================================
# ОБЛАСТІ
# =====================================================

def oblasts_keyboard(
    oblasts,
    back_text="⬅️ Назад",
):
    return _make_keyboard(
        oblasts,
        "🗺",
        back_text,
        columns=2,
    )


# =====================================================
# РАЙОНИ
# =====================================================

def raions_keyboard(
    raions,
    oblast_name=None,
):
    """
    oblast_name залишений для сумісності
    зі старим settings.py.
    """

    return _make_keyboard(
        raions,
        "📍",
        "🔙 До областей",
        columns=2,
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
                    text="🏙 Обрати місто"
                ),
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