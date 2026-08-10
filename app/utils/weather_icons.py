def get_weather_icon(condition: str):

    condition = condition.lower()

    if "соняч" in condition:
        return "☀️"

    if "ясно" in condition:
        return "☀️"

    if "мінлива" in condition:
        return "🌤"

    if "хмар" in condition:
        return "☁️"

    if "дощ" in condition:
        return "🌧"

    if "злива" in condition:
        return "🌧"

    if "гроза" in condition:
        return "⛈"

    if "сніг" in condition:
        return "❄️"

    if "туман" in condition:
        return "🌫"

    if "дим" in condition:
        return "🌫"

    return "🌤"