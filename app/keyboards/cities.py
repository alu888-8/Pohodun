from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

cities_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📍 Київ"),
            KeyboardButton(text="📍 Львів"),
        ],
        [
            KeyboardButton(text="📍 Одеса"),
            KeyboardButton(text="📍 Харків"),
        ],
        [
            KeyboardButton(text="📍 Дніпро"),
            KeyboardButton(text="📍 Запоріжжя"),
        ],
        [
            KeyboardButton(text="📍 Вінниця"),
            KeyboardButton(text="📍 Полтава"),
        ],
        [
            KeyboardButton(text="📍 Черкаси"),
            KeyboardButton(text="📍 Миколаїв"),
        ],
        [
            KeyboardButton(text="📍 Житомир"),
            KeyboardButton(text="📍 Чернігів"),
        ],
        [
            KeyboardButton(text="📍 Суми"),
            KeyboardButton(text="📍 Рівне"),
        ],
        [
            KeyboardButton(text="📍 Луцьк"),
            KeyboardButton(text="📍 Тернопіль"),
        ],
        [
            KeyboardButton(text="📍 Хмельницький"),
            KeyboardButton(text="📍 Чернівці"),
        ],
        [
            KeyboardButton(text="📍 Івано-Франківськ"),
            KeyboardButton(text="📍 Ужгород"),
        ],
        [
            KeyboardButton(text="📍 Кропивницький"),
            KeyboardButton(text="📍 Херсон"),
        ],
        [
            KeyboardButton(text="✏️ Інше місто"),
        ],
        [
            KeyboardButton(text="⬅️ Назад"),
        ],
    ],
    resize_keyboard=True
)