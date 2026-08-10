from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
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
            KeyboardButton(text="⚙️ Налаштування"),
        ],
    ],
    resize_keyboard=True,
)