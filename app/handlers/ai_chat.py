import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

MODEL = "openrouter/free"


SYSTEM_PROMPT = """
Ти — Pohodun AI, український помічник.

Відповідай українською мовою.

Правила:
- відповідай зрозуміло та по суті;
- не вигадуй факти;
- якщо не знаєш відповіді — чесно скажи про це;
- не використовуй надмірно офіційний стиль;
- спілкуйся дружньо;
- можеш використовувати легкий гумор;
- якщо користувач питає про поточну погоду,
  тривоги або загрози, не вигадуй поточні дані;
- актуальні дані ми будемо передавати тобі окремо.
"""


def ask_ai(
    question: str,
):

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
            "❓ Напишіть своє питання."
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
            timeout=(5, 30),
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
                "❌ OpenRouter повернув "
                "неправильний JSON | "
                f"{e}"
            )

            print(
                f"❌ Response body: "
                f"{response.text}"
            )

            return (
                "❌ AI повернув "
                "некоректну відповідь."
            )

        # =================================================
        # CHOICES
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
                f"❌ OpenRouter data: "
                f"{data}"
            )

            return (
                "❌ AI не повернув "
                "відповідь."
            )

        # =================================================
        # MESSAGE
        # =================================================

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
                f"❌ AI message: "
                f"{message}"
            )

            return (
                "❌ AI не повернув "
                "текст відповіді."
            )

        answer = str(
            answer
        ).strip()

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
            "Спробуйте ще раз."
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