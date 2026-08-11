import json
import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_daily_content(city, weather):
    """
    Генерує контент дня:
    - анекдот дня
    - живе побажання дня
    """

    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY не заданий")
        return None

    temp = weather.get("temp")
    feels = weather.get("feels_like")
    condition = weather.get("condition")
    wind = weather.get("wind")
    humidity = weather.get("humidity")

    prompt = f"""
Ти — Погодун, веселий український погодний помічник.

Створи сьогоднішній КОНТЕНТ ДНЯ.

Погода:
Місто: {city}
Температура: {temp}°C
Відчувається: {feels}°C
Погода: {condition}
Вітер: {wind} м/с
Вологість: {humidity}%

Потрібно створити ДВА тексти.

1. АНЕКДОТ ДНЯ

Створи хороший короткий оригінальний анекдот.

Вимоги:
- українською;
- 3–6 речень;
- повинна бути смішна кінцівка;
- природний живий гумор;
- без політики;
- без образ;
- без чорного гумору;
- без матюків;
- не використовуй відомий старий анекдот;
- придумай нову ситуацію;
- можна використовувати роботу, сім'ю,
  друзів, телефон, гроші, відпочинок або погоду.

2. ПОБАЖАННЯ ДНЯ

Створи коротку живу фразу.

Вимоги:
- українською;
- 1–2 речення;
- тепла та позитивна;
- трохи пов'язана з погодою;
- може бути веселою або з характером;
- не використовуй фразу
  "Гарного дня! Нехай погода буде на твоєму боці";
- текст повинен бути новим.

Поверни ВИКЛЮЧНО JSON:

{{
    "joke": "текст анекдоту",
    "greeting": "текст побажання"
}}
"""

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openrouter/free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 1.1,
                "max_tokens": 350,
            },
            timeout=30,
        )

        if response.status_code != 200:
            print(
                f"❌ OpenRouter помилка: "
                f"{response.status_code} "
                f"{response.text}"
            )
            return None

        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()

        if content.startswith("```"):
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

        result = json.loads(content)

        joke = result.get("joke")
        greeting = result.get("greeting")

        if not joke or not greeting:
            print("❌ AI не повернув joke/greeting")
            return None

        return {
            "joke": joke.strip(),
            "greeting": greeting.strip()
        }

    except Exception as e:
        print(f"❌ Помилка генерації контенту дня: {e}")
        return None