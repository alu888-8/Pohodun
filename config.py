import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

DEFAULT_CITY = "Kyiv"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено")

if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY не знайдено")