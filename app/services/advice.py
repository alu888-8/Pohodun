import os
import requests


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_advice(
    temp,
    description,
    city="Київ",
    feels_like=None,
    wind=None,
    humidity=None
):
    """
    Генерує живу пораду через AI.
    Якщо AI недоступний — повертає резервну пораду.
    """

    # Якщо немає API ключа — резерв
    if not OPENROUTER_API_KEY:
        print("⚠️ OPENROUTER_API_KEY не знайдено")
        return fallback_advice(temp, description)

    prompt = f"""
Ти — Погодун, веселий український погодний помічник.

Людина попросила пораду щодо сьогоднішньої погоди.

Місто: {city}
Температура: {temp}°C
Відчувається: {feels_like if feels_like is not None else temp}°C
Вітер: {wind if wind is not None else "невідомо"} м/с
Вологість: {humidity if humidity is not None else "невідомо"}%
Стан погоди: {description}

Твоє завдання — написати коротку, живу та корисну пораду.

Правила:

- Пиши тільки українською.
- 3–5 коротких речень.
- Пиши так, ніби ти живий співрозмовник.
- Можеш трохи жартувати.
- Кожна відповідь повинна бути іншою.
- Не повторюй одну й ту саму структуру.
- Не просто переписуй температуру.
- Враховуй реальні погодні умови.
- Можеш порадити одяг, воду, парасолю, окуляри,
  прогулянку або інший доречний варіант.
- Не будь занадто офіційним.
- Не використовуй фрази "як штучний інтелект".
- Не вигадуй небезпечних медичних рекомендацій.
- Не починай кожну відповідь словами "Погодун радить".

Приклад стилю:

"Сьогодні сонце явно вирішило взяти керування містом у свої руки 😎
Якщо підеш гуляти — прихопи воду й не забудь про окуляри.
Для довгої прогулянки краще вибрати місце з тінню."

Але НЕ копіюй цей приклад — придумай нову відповідь.
"""

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 1.1,
                "max_tokens": 180,
            },
            timeout=30,
        )

        if response.status_code != 200:
            print(
                f"❌ OpenRouter помилка: "
                f"{response.status_code} {response.text}"
            )

            return fallback_advice(temp, description)

        data = response.json()

        advice = data["choices"][0]["message"]["content"].strip()

        if not advice:
            return fallback_advice(temp, description)

        return advice

    except Exception as e:
        print(f"❌ Помилка AI-поради: {e}")

        return fallback_advice(temp, description)


def fallback_advice(temp, description):
    """
    Резервні поради, якщо AI тимчасово недоступний.
    """

    text = description.lower()

    if temp >= 30:
        return (
            "🥵 Сьогодні літо явно вирішило не жартувати. "
            "Візьми воду, легкий одяг і не геройствуй під прямим сонцем."
        )

    if temp >= 24:
        return (
            "😎 Погода виглядає дуже непогано для прогулянки. "
            "Легкий одяг буде саме те, а воду краще прихопити із собою."
        )

    if temp <= 0:
        return (
            "🥶 На вулиці вже серйозно прохолодно. "
            "Теплий одяг сьогодні — не рекомендація, а стратегічний план."
        )

    if temp <= 10:
        return (
            "🧥 Прохолодно, тому куртка сьогодні точно не буде зайвою. "
            "Якщо виходиш надовго — одягайся тепліше."
        )

    if "дощ" in text or "rain" in text:
        return (
            "🌧️ Схоже, небо сьогодні має свої плани. "
            "Парасоля та взуття, яке не боїться калюж, будуть дуже доречні."
        )

    if "сніг" in text or "snow" in text:
        return (
            "❄️ Зима нагадує про себе. "
            "Одягайся тепліше й обережно ходи — слизькі сюрпризи ніхто не скасовував."
        )

    if "туман" in text or "fog" in text:
        return (
            "🌫️ Видимість сьогодні не найкраща. "
            "Пішоходам варто бути помітнішими, а водіям — їхати спокійніше."
        )

    return (
        "🙂 Погода сьогодні без особливих сюрпризів. "
        "Одягайся по ситуації, а далі вже можна сміливо планувати день."
    )