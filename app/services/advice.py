import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_advice(
    temp,
    description,
    city,
    feels_like=None,
    wind=None,
    humidity=None
):
    """
    Генерує живу пораду через AI
    саме для міста користувача.
    """

    if not OPENROUTER_API_KEY:
        print("⚠️ OPENROUTER_API_KEY не знайдено")
        return fallback_advice(temp, description)

    feels = feels_like if feels_like is not None else temp
    wind_value = wind if wind is not None else "невідомо"
    humidity_value = humidity if humidity is not None else "невідомо"

    prompt = f"""
Ти — Погодун, веселий український погодний помічник.

Користувач обрав місто: {city}

Поточна погода саме в цьому місті:
Температура: {temp}°C
Відчувається: {feels}°C
Вітер: {wind_value} м/с
Вологість: {humidity_value}%
Стан погоди: {description}

Напиши коротку, живу та корисну пораду користувачу.

ВАЖЛИВО:
- Пиши саме про місто {city}.
- НІКОЛИ не замінюй {city} на Київ або будь-яке інше місто.
- Якщо згадуєш місто у тексті, використовуй саме "{city}".
- Не вигадуй іншу погоду.
- Враховуй температуру, вітер, вологість і стан погоди.

Правила:
- тільки українською;
- 3–5 коротких речень;
- природний живий стиль;
- можна трохи жартувати;
- кожна відповідь повинна бути іншою;
- не просто переписуй температуру;
- можна порадити одяг, воду, парасолю, окуляри,
  прогулянку або інший доречний варіант;
- не будь занадто офіційним;
- без політики;
- без образ;
- без матюків;
- не використовуй небезпечних медичних рекомендацій;
- не починай кожну відповідь словами "Погодун радить".

Напиши тільки готовий текст поради без лапок і без пояснень.
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
    Резервна порада, якщо AI недоступний.
    """

    text = description.lower()

    if temp >= 30:
        return (
            "🥵 Сьогодні літо явно вирішило не жартувати. "
            "Візьми воду, легкий одяг і не геройствуй під прямим сонцем."
        )

    if temp >= 24:
        return (
            "😎 Погода чудово підходить для прогулянки. "
            "Легкий одяг буде саме те, а воду краще прихопити із собою."
        )

    if temp <= 0:
        return (
            "🥶 На вулиці серйозно прохолодно. "
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
            "Парасоля та взуття, яке не боїться калюж, будуть доречні."
        )

    if "сніг" in text or "snow" in text:
        return (
            "❄️ Зима нагадує про себе. "
            "Одягайся тепліше й обережно ходи — слизькі сюрпризи ніхто не скасовував."
        )

    if "туман" in text or "fog" in text:
        return (
            "🌫️ Видимість сьогодні не найкраща. "
            "Будь уважним на дорозі та подбай про свою помітність."
        )

    return (
        "🙂 Погода сьогодні без особливих сюрпризів. "
        "Одягайся по ситуації та сміливо плануй свій день."
    )