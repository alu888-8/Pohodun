import json
import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_daily_content(city, weather):
    """
    Генерує один раз на день:
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

Створи КОНТЕНТ ДНЯ для користувачів.

Погода:
Місто: {city}
Температура: {temp}°C
Відчувається: {feels}°C
Стан погоди: {condition}
Вітер: {wind} м/с
Вологість: {humidity}%

Потрібно створити ДВА окремі тексти.

1. АНЕКДОТ ДНЯ

Придумай справді хороший короткий анекдот.

Вимоги:
- тільки українською мовою;
- 3–6 речень;
- має бути зав'язка і смішна кінцівка;
- природний живий гумор;
- зрозумілий звичайній людині;
- можна використати побут, роботу, сім'ю, друзів,
  гроші, телефон, відпочинок або погоду;
- не обов'язково прив'язувати до погоди;
- без політики;
- без образ;
- без чорного гумору;
- без матюків;
- не використовуй банальні старі анекдоти;
- придумай новий сюжет.

2. ПОБАЖАННЯ ДНЯ

Напиши одну коротку живу фразу або 1–2 речення.

Вимоги:
- тільки природною сучасною українською мовою;
- звучить так, ніби це написала жива людина;
- можна трохи врахувати сьогоднішню погоду;
- іноді тепле;
- іноді веселе;
- іноді з легкою іронією;
- кожного дня має бути іншим;
- не використовуй шаблонні фрази;
- не будь надто пафосним;
- не повторюй:
  "Гарного дня! Нехай погода буде на твоєму боці";
- не використовуй кальки з російської або англійської;
- не використовуй неприродні словосполучення;
- не пиши фрази на кшталт:
  "веселого смеху",
  "піднімає настрій до сміху",
  "додає настрою до веселого сміху";
- використовуй звичайні українські слова та природні конструкції;
- уяви, що пишеш коротке повідомлення хорошому знайомому в Telegram.

ПЕРЕВІР ТЕКСТ ПЕРЕД ВІДПОВІДДЮ:
Якщо будь-яка фраза звучить як машинний переклад,
перепиши її простіше і природніше.

ПОВЕРНИ ВИКЛЮЧНО JSON:

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

        # Прибираємо markdown ```json, якщо модель його додасть
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