from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


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
# ЛОКАЦІЇ ОБЛАСТІ
# МІСТА + РАЙОНИ
# =====================================================

def locations_keyboard(
    cities,
    raions,
):

    keyboard = []

    # -------------------------------------------------
    # МІСТА
    # -------------------------------------------------

    row = []

    for city in cities:

        row.append(
            KeyboardButton(
                text=f"🏙 {city['name']}"
            )
        )

        if len(row) == 2:

            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # -------------------------------------------------
    # РАЙОНИ
    # -------------------------------------------------

    row = []

    for raion in raions:

        row.append(
            KeyboardButton(
                text=f"📍 {raion['name']}"
            )
        )

        if len(row) == 2:

            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # -------------------------------------------------
    # НАЗАД
    # -------------------------------------------------

    keyboard.append(
        [
            KeyboardButton(
                text="🔙 До областей"
            )
        ]
    )

    keyboard.append(
        [
            KeyboardButton(
                text="⬅️ Назад"
            )
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


# =====================================================
# СТАРІ ФУНКЦІЇ
# =====================================================

def raions_keyboard(raions):

    return _make_keyboard(
        raions,
        "📍",
        "🔙 До областей",
    )


def cities_keyboard(cities):

    return _make_keyboard(
        cities,
        "🏙",
        "🔙 До районів",
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
# ПІДТВЕРДЖЕННЯ
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