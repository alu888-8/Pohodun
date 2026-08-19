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
- можеш спілкуватися дружньо та з легким гумором;
- якщо користувач питає про погоду, тривоги або загрози,
  не вигадуй поточні дані — їх ми додамо окремо через API.
"""


def ask_ai(
    question: str,
):

    if not OPENROUTER_API_KEY:

        print(
            "⚠️ OPENROUTER_API_KEY не знайдено"
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
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=(5, 30),
        )

        print(
            f"🤖 AI status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                f"❌ OpenRouter помилка: "
                f"{response.text}"
            )

            return (
                "❌ Не вдалося отримати "
                "відповідь від AI."
            )

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "❌ OpenRouter: "
                "порожня відповідь"
            )

            return (
                "❌ AI не повернув відповідь."
            )

        message = choices[0].get(
            "message",
            {}
        )

        answer = message.get(
            "content"
        )

        if not answer:

            return (
                "❌ AI не повернув текст "
                "відповіді."
            )

        return str(
            answer
        ).strip()

    except requests.Timeout:

        print(
            "⏱️ AI: перевищено "
            "час очікування"
        )

        return (
            "⏱️ AI занадто довго "
            "не відповідає. Спробуйте ще раз."
        )

    except Exception as e:

        print(
            f"❌ Помилка AI: {e}"
        )

        return (
            "❌ Сталася помилка "
            "під час звернення до AI."
        )
