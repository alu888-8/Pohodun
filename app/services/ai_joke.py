import json
import requests
from datetime import date

from config import OPENROUTER_API_KEY
from app.database.db import (
    get_daily_content,
    save_daily_content,
)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

AI_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "z-ai/glm-5.2:free",
    "minimax/minimax-m3:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]


def generate_daily_content(city, weather):
    """
    Генерує один раз на день:
    - анекдот дня
    - живе побажання дня

    Якщо контент на сьогодні вже є в БД —
    повторно AI не викликаємо.
    """

    today = date.today().isoformat()

    # =================================================
    # ПЕРЕВІРКА ГОТОВОГО КОНТЕНТУ
    # =================================================

    try:
        cached = get_daily_content(city)

        if (
            cached
            and cached.get("date") == today
            and cached.get("joke")
            and cached.get("greeting")
            and cached.get("advice")
        ):
            print(
                f"💾 DAILY CONTENT | "
                f"{city} | взято з БД"
            )

            return {
                "joke": cached["joke"],
                "greeting": cached["greeting"],
                "advice": cached["advice"],
            }

    except Exception as e:
        print(
            f"⚠️ Помилка читання контенту "
            f"{city}: {e}"
        )

    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY не заданий")
        return None

    temp = weather.get("temp")
    feels = weather.get("feels_like")
    condition = weather.get("condition")
    wind = weather.get("wind")
    humidity = weather.get("humidity")

    today = date.today().isoformat()

    prompt = f"""
Ти — Погодун, веселий український погодний помічник.

Сьогодні: {today}

ВАЖЛИВО:
Це новий випуск контенту дня.
Не використовуй шаблон із попередніх відповідей.
Щоразу вигадуй новий сюжет, нову подачу та нову фразу.
Не повторюй однакові жарти, побажання або конструкції речень.

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
- ВИКЛЮЧНО природною українською мовою;
- заборонені будь-які слова, літери або фрази іншими мовами;
- не використовуй випадкові іноземні символи або транслітерацію;
- не вигадуй дивні слова та імена без потреби;
- якщо не впевнений у слові — заміни його простим українським словом;
- 3–6 речень;
- має бути зав'язка і смішна кінцівка;
- природний живий гумор;
- зрозумілий звичайній людині;
- можна використати побут, роботу, сім'ю, друзів,
  гроші, телефон, відпочинок або погоду;
- не обов'язково прив'язувати до погоди;
- без політики;
- без образ;
- допускається легкий чорний гумор та сарказм, якщо він доречний;
- без жорстоких подробиць, шок-контенту та образ реальних людей;
- без матюків;
- не використовуй банальні старі анекдоти;
- придумай новий сюжет;
- гумор має бути різним: побут, робота, гроші, сім'я, технології, стосунки, втома, погода тощо;
- не повторюй типові сюжети з попередніх днів.

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
- чергуй стиль: тепле побажання, іронія, короткий жарт, мотивація без пафосу;
- іноді можеш додати легкий чорний гумор або сарказм;
- не починай постійно зі слів "Нехай", "Бажаю", "Гарного дня";
- не повторюй однакову структуру речення;
- побажання має звучати по-різному кожного разу;
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

1. Перевір, що весь текст написаний українською.
2. Прибери випадкові слова іншими мовами.
3. Прибери дивні або вигадані слова.
4. Прибери машинні переклади.
5. Перечитай анекдот як звичайний україномовний читач.
6. Якщо звучить неприродно — перепиши простіше.
7. Не використовуй слова, яких не існує в нормальній українській мові.

ВАЖЛИВО:
Не пояснюй свої дії.
Не додавай вступу.
Не додавай markdown.
Не додавай зайвих полів.

ПОВЕРНИ ВИКЛЮЧНО JSON:

{{
    "joke": "текст анекдоту",
    "greeting": "текст побажання"
}}
"""

    try:
        data = None

        for model in AI_MODELS:

            print(
                f"🤖 AI MODEL | {model}"
            )

            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 1.0,
                        "max_tokens": 500,
                        "response_format": {
                            "type": "json_object"
                        },
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    break

                print(
                    f"⚠️ {model} | "
                    f"HTTP {response.status_code}"
                )

                if response.status_code == 429:
                    continue

                print(response.text)

            except Exception as e:
                print(
                    f"⚠️ Помилка моделі "
                    f"{model}: {e}"
                )
                continue

        if data is None:
            print(
                "❌ Усі AI-моделі недоступні"
            )
            return None

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        print("🤖 OPENROUTER RESPONSE:")
        print("finish_reason:", choice.get("finish_reason"))
        print("message keys:", list(message.keys()))
        print("message:", repr(message))

        content = message.get("content")

        if not isinstance(content, str) or not content.strip():
            print("❌ AI не повернув текстовий content")
            return None

        content = content.strip()

        content = content.strip()

        # Прибираємо markdown ```json, якщо модель його додасть
        if content.startswith("```"):
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

        result = json.loads(content)

        joke = result.get("joke")
        greeting = result.get("greeting")
        advice = result.get("advice")

        print("🤖 AI JSON:")
        print(result)

        if not isinstance(joke, str) or not joke.strip():
            print(
                f"❌ AI повернув некоректний joke: "
                f"{joke!r}"
            )
            return None

        if not isinstance(greeting, str) or not greeting.strip():
            print(
                f"❌ AI повернув некоректний greeting: "
                f"{greeting!r}"
            )
            return None

        # =================================================
        # ЯКЩО AI НЕ ПОВЕРНУВ ADVICE —
        # ОКРЕМИЙ ЗАПИТ ТІЛЬКИ ДЛЯ ПОРАДИ
        # =================================================

        if not isinstance(advice, str) or not advice.strip():

            print("⚠️ AI не повернув advice — генеруємо окремо")

            advice_prompt = f"""
Ти — Погодун, український погодний помічник.

Місто: {city}
Температура: {temp}°C
Відчувається: {feels}°C
Погода: {condition}
Вітер: {wind} м/с
Вологість: {humidity}%

Напиши ОДНУ коротку практичну пораду на сьогодні.

Правила:
- тільки природна сучасна українська мова;
- одне речення;
- конкретна і корисна порада;
- врахуй сьогоднішню погоду;
- кожного разу обирай іншу тему;
- можна радити щодо одягу, прогулянки, води,
  сонця, активності, відпочинку, роботи або побуту;
- іноді додай легкий гумор;
- без пафосу;
- без медичних рекомендацій;
- не починай зі слів "Гарного дня", "Бажаю" або "Нехай".

Поверни ТІЛЬКИ текст поради.
"""

            try:
                advice_response = requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "minimax/minimax-m3:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": advice_prompt,
                            }
                        ],
                        "temperature": 1.0,
                        "max_tokens": 100,
                    },
                    timeout=30,
                )

                if advice_response.status_code == 200:

                    advice_data = advice_response.json()

                    advice_content = (
                        advice_data
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content")
                    )

                    if (
                        isinstance(advice_content, str)
                        and advice_content.strip()
                    ):
                        advice = advice_content.strip()

                        print(
                            f"💡 AI ADVICE: {advice}"
                        )

            except Exception as e:
                print(
                    f"⚠️ Помилка генерації advice: {e}"
                )

        if not isinstance(advice, str) or not advice.strip():
            print(
                f"❌ AI не зміг згенерувати advice"
            )
            return None

        joke = joke.strip()
        greeting = greeting.strip()
        advice = advice.strip()

        # =================================================
        # ЗБЕРІГАЄМО КОНТЕНТ НА СЬОГОДНІ
        # =================================================

        try:
            save_daily_content(
                city,
                today,
                joke,
                greeting,
                advice,
            )

            print(
                f"💾 DAILY CONTENT | "
                f"{city} | збережено в БД"
            )

        except Exception as e:
            print(
                f"⚠️ Не вдалося зберегти "
                f"контент {city}: {e}"
            )

        return {
            "joke": joke,
            "greeting": greeting,
            "advice": advice,
        }

    except Exception as e:
        print(f"❌ Помилка генерації контенту дня: {e}")
        return None