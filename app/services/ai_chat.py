import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# Конкретна безкоштовна модель.
# Не використовуємо openrouter/free,
# бо він випадково вибирає різні моделі.
MODEL = "openai/gpt-oss-20b:free"


SYSTEM_PROMPT = """
Ти — Pohodun AI, дружній український помічник.

Ти спілкуєшся з користувачем у Telegram.

ГОЛОВНІ ПРАВИЛА:

1. Завжди відповідай українською мовою.
2. Не переходь на англійську без прямого прохання.
3. Не використовуй китайські, японські або інші випадкові символи.
4. Не вигадуй слова, факти або назви.
5. Не згадуй випадкові слова, які не мають відношення
   до питання користувача.
6. Не вигадуй, що ти бачиш телефон, комп'ютер,
   Telegram, файли або інші пристрої користувача.
7. Якщо користувач просто вітається — відповідай природно.
8. Якщо питають "як справи?" — відповідай коротко,
   дружньо і по-людськи.
9. Якщо питання просте — відповідь теж має бути простою.
10. Не пиши величезні відповіді без потреби.
11. Не повторюй своє ім'я в кожній відповіді.
12. Не починай кожну відповідь словами
    "Привіт! Я Pohodun AI".
13. Можеш використовувати емодзі, але помірно.
14. Не використовуй дивні або випадкові набори символів.
15. Якщо користувач жартує — можеш відповісти з гумором.
16. Якщо користувач просить допомогти — допомагай конкретно.
17. Якщо не знаєш відповіді — чесно скажи,
    що не знаєш.
18. Не вигадуй актуальну інформацію про погоду,
    тривоги, загрози або новини.
19. Якщо користувач питає про функції Pohodun,
    пояснюй тільки те, що тобі відомо з контексту.

СТИЛЬ:

- природна українська;
- дружній тон;
- коротко і зрозуміло;
- без зайвої офіційності;
- без дивних фраз;
- без "машинного" стилю.

Приклад:

Користувач:
"як справи?"

Хороша відповідь:
"Все добре 😎 Готовий допомагати. А в тебе як?"

Користувач:
"що нового?"

Хороша відповідь:
"Та потроху все рухається 😎 Я тут і готовий щось вирішувати разом з тобою."

Не вигадуй додаткових слів або тем,
яких користувач не просив.
"""


def ask_ai(question: str):

    print(
        "🤖 AI REQUEST | "
        f"model={MODEL}"
    )

    if not OPENROUTER_API_KEY:

        print(
            "❌ OPENROUTER_API_KEY "
            "не знайдено"
        )

        return (
            "❌ AI зараз недоступний."
        )

    question = (
        question or ""
    ).strip()

    if not question:

        return (
            "❓ Напиши своє питання."
        )

    payload = {
        "model": MODEL,

        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question,
            },
        ],

        # Трохи нижча температура,
        # щоб відповіді були стабільнішими.
        "temperature": 0.4,

        # Не дозволяємо моделі писати величезні полотна.
        "max_tokens": 500,

        # Зменшуємо повторення.
        "frequency_penalty": 0.2,
        "presence_penalty": 0.0,
    }

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),

        "Content-Type": (
            "application/json"
        ),

        "HTTP-Referer": (
            "https://github.com/alu888-8/Pohodun"
        ),

        "X-Title": "Pohodun",
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=(5, 45),
        )

        print(
            "🤖 AI RESPONSE | "
            f"status={response.status_code}"
        )

        # =================================================
        # ПОМИЛКА OPENROUTER
        # =================================================

        if response.status_code != 200:

            print(
                "❌ OpenRouter помилка | "
                f"status={response.status_code}"
            )

            print(
                "❌ OpenRouter response | "
                f"{response.text}"
            )

            return (
                "❌ Не вдалося отримати "
                "відповідь від AI."
            )

        # =================================================
        # JSON
        # =================================================

        try:

            data = response.json()

        except Exception as e:

            print(
                "❌ OpenRouter JSON error | "
                f"{e}"
            )

            print(
                "❌ Response body | "
                f"{response.text}"
            )

            return (
                "❌ AI повернув "
                "некоректну відповідь."
            )

        # =================================================
        # ВІДПОВІДЬ
        # =================================================

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "❌ OpenRouter: "
                "choices порожній"
            )

            print(
                f"❌ OpenRouter data | "
                f"{data}"
            )

            return (
                "❌ AI не повернув "
                "відповідь."
            )

        message = choices[0].get(
            "message",
            {}
        )

        answer = message.get(
            "content"
        )

        if not answer:

            print(
                "❌ OpenRouter: "
                "content порожній"
            )

            print(
                f"❌ AI message | "
                f"{message}"
            )

            return (
                "❌ AI не повернув "
                "текст відповіді."
            )

        answer = str(
            answer
        ).strip()

        if not answer:

            print(
                "❌ AI повернув "
                "порожній текст"
            )

            return (
                "❌ AI не сформував "
                "відповідь."
            )

        print(
            "✅ AI RESPONSE | "
            f"length={len(answer)}"
        )

        return answer

    except requests.Timeout:

        print(
            "⏱️ AI: перевищено "
            "час очікування"
        )

        return (
            "⏱️ AI занадто довго "
            "не відповідає. "
            "Спробуй ще раз."
        )

    except requests.RequestException as e:

        print(
            "❌ AI network error | "
            f"{e}"
        )

        return (
            "❌ Помилка з'єднання "
            "з AI."
        )

    except Exception as e:

        print(
            "❌ Помилка AI | "
            f"{type(e).__name__}: {e}"
        )

        return (
            "❌ Сталася помилка "
            "під час звернення до AI."
        )