from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


ADMIN_ID = 366025054


def get_main_menu(
    user_id: int,
    chat_type: str = "private",
):

    keyboard = [
        [
            KeyboardButton(text="🌤 Погода зараз"),
            KeyboardButton(text="📅 Прогноз"),
        ],
        [
            KeyboardButton(text="🚨 Тривоги"),
            KeyboardButton(text="🛰 Загрози"),
        ],
        [
            KeyboardButton(text="🌫 Якість повітря"),
            KeyboardButton(text="📣 Є що сказати"),
        ],
        [
            KeyboardButton(text="🤖 Поговорити з Pohodun"),
            KeyboardButton(text="⚙️ Налаштування"),
        ],
    ]

    # Адмінка тільки в особистому чаті
    if (
        user_id == ADMIN_ID
        and chat_type == "private"
    ):
        keyboard.append(
            [
                KeyboardButton(
                    text="🔧 Адмінка"
                )
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )