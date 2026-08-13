from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

ADMIN_ID = 366025054


def get_main_menu(user_id: int):

    keyboard = [
        [
            KeyboardButton(text="🌤 Погода зараз"),
        ],
        [
            KeyboardButton(text="📅 Прогноз"),
            KeyboardButton(text="🚨 Тривоги"),
        ],
        [
            KeyboardButton(text="🛰 Загрози"),
            KeyboardButton(text="🌫 Якість повітря"),
        ],
        [
            KeyboardButton(text="👕 Поради"),
            KeyboardButton(text="📅 Цей день"),
        ],
        [
            KeyboardButton(text="⚙️ Налаштування"),
        ],
    ]

    # Кнопка адмінки тільки для адміністратора
    if user_id == ADMIN_ID:
        keyboard.append(
            [
                KeyboardButton(text="🔧 Адмінка"),
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )