from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


settings_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🗺 Місто для погоди"
            ),
        ],
        [
            KeyboardButton(
                text="📍 Локація моніторингу"
            ),
        ],
        [
            KeyboardButton(
                text="🛰 Загрози"
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
