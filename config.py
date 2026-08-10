if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено")

if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY не знайдено")

print("BOT_TOKEN:", "OK" if BOT_TOKEN else "MISSING")
print("WEATHER_API_KEY:", "OK" if WEATHER_API_KEY else "MISSING")