import requests
from html import escape

from config import OPENROUTER_API_KEY


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_advice(
    temp,
    description,
    city_ua,
    feels,
    wind,
    humidity
):
    """
    Генерує коротку погодну пораду українською.
    Повертає звичайний текст без HTML/Markdown.
    """

    if not OPENROUTER_API_KEY:
        print("⚠️ OPENROUTER_API_KEY не знайдено")
        return "Візьміть одяг за погодою та не забудьте про комфорт."

    prompt = f"""
Ти — доброзичливий український помічник з погоди.

Дані:
- Місто: {city_ua}
- Температура: {temp}°C
- Відчувається: {feels}°C
- Погода: {description}
- Вітер: {wind} м/с
- Вологість: {humidity}%

Напиши ОДНУ коротку природну пораду українською мовою для людини, яка виходить з дому.

Правила:
1. Максимум 2 короткі речення.
2. Пиши грамотною сучасною українською.
3. Не вигадуй дощ, сніг, сонце або інші умови, яких немає в даних.
4. Орієнтуйся насамперед на температуру, відчуття температури, вітер та опис погоди.
5. Не використовуй Markdown, HTML, лапки, заголовки та слово "Порада".
6. Не пиши зайвих пояснень.
7. Текст має звучати природно, як повідомлення від українського погодного бота.
""".strip()

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
                        "role": "system",
                        "content": (
                            "Відповідай тільки грамотною українською. "
                            "Будь коротким і природним."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.7,
                "max_tokens": 120,
            },
            timeout=20,
        )

        if response.status_code != 200:
            print(
                f"❌ OpenRouter помилка: "
                f"{response.status_code} {response.text[:300]}"
            )
            return "Візьміть одяг відповідно до погоди та бережіть себе."

        data = response.json()

        advice = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not advice:
            return "Візьміть одяг відповідно до погоди та бережіть себе."

        # На випадок, якщо модель все ж додала Markdown/HTML.
        advice = advice.replace("**", "").replace("__", "")
        advice = advice.replace("<br>", " ").replace("<br/>", " ")
        advice = advice.replace("<br />", " ")
        advice = advice.replace("<p>", "").replace("</p>", "")
        advice = advice.strip(" \"'")

        # Не даємо моделі повернути багато абзаців.
        advice = " ".join(advice.split())

        return escape(advice)

    except Exception as e:
        print(
            f"❌ Помилка генерації поради: {e}"
        )

        return (
            "Візьміть одяг відповідно до погоди "
            "та бережіть себе."
        )