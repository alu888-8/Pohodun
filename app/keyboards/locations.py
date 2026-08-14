from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def oblasts_keyboard(oblasts):

    keyboard = []

    row = []

    for oblast in oblasts:

        button = KeyboardButton(
            text=f"🗺 {oblast['name']}"
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
                text="⬅️ Назад"
            )
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def raions_keyboard(
    raions,
    oblast_name
):

    keyboard = []

    row = []

    for raion in raions:

        button = KeyboardButton(
            text=f"📍 {raion['name']}"
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