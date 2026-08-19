import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# =====================================================
# МОДЕЛІ
# =====================================================
#
# Перша — автоматичний вибір доступної безкоштовної
# моделі OpenRouter.
#
# Якщо вона тимчасово недоступна — пробуємо резервні.
#

MODELS = [
    "openrouter/free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-30b-a3b:free",
    "meta-llama/llama-3.3-8b-instruct:free",
]


# =====================================================
# SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
Ти — Pohodun AI, дружній український помічник.

Ти спілкуєшся з користувачем у Telegram.

ГОЛОВНІ ПРАВИЛА:

1. Завжди відповідай українською мовою.

2. Не переходь на англійську без прямого прохання
   користувача.

3. Не використовуй китайські, японські або інші
   випадкові символи.

4. Не вигадуй слова, факти або назви.

5. Не згадуй випадкові слова, які не мають
   відношення до питання користувача.

6. Не вигадуй, що ти бачиш телефон, комп'ютер,
   Telegram, файли або інші пристрої користувача.

7. Якщо користувач просто вітається —
   відповідай природно.

8. Якщо користувач питає "як справи?" —
   відповідай коротко, дружньо і по-людськи.

9. Якщо питання просте —
   відповідь теж має бути простою.

10. Не пиши величезні відповіді без потреби.

11. Не повторюй своє ім'я в кожній відповіді.

12. Не починай кожну відповідь словами
    "Привіт! Я Pohodun AI".

13. Можеш використовувати емодзі,
    але помірно.

14. Не використовуй дивні або випадкові
    набори символів.

15. Якщо користувач жартує —
    можеш відповісти з гумором.

16. Якщо користувач просить допомогти —
    допомагай конкретно.

17. Якщо не знаєш відповіді —
    чесно скажи, що не знаєш.

18. Не вигадуй актуальну інформацію про:
    - погоду;
    - тривоги;
    - загрози;
    - новини.

19. Актуальні тривоги та загрози отримуються
    окремо з системи Pohodun. Не вигадуй їх.

20. Якщо користувач питає про функції Pohodun —
    пояснюй тільки те, що тобі відомо.

СТИЛЬ:

- природна українська;
- дружній тон;
- коротко і зрозуміло;
- без зайвої офіційності;
- без дивних фраз;
- без машинного стилю.

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


# =====================================================
# ЗАПИТ ДО OPENROUTER
# =====================================================

def _request_model(
    model: str,
    question: str,
):

    payload = {
        "model": model,

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

        "temperature": 0.4,

        "max_tokens": 500,

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

    return requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=(5, 45),
    )


# =====================================================
# AI
# =====================================================

def ask_ai(question: str):

    print(
        "🤖 AI REQUEST | "
        f"question={question}"
    )

    # =================================================
    # API KEY
    # =================================================

    if not OPENROUTER_API_KEY:

        print(
            "❌ OPENROUTER_API_KEY "
            "не знайдено"
        )

        return (
            "❌ AI зараз недоступний."
        )

    # =================================================
    # ПИТАННЯ
    # =================================================

    question = (
        question or ""
    ).strip()

    if not question:

        return (
            "❓ Напиши своє питання."
        )

    # =================================================
    # ПРОБУЄМО МОДЕЛІ
    # =================================================

    for index, model in enumerate(
        MODELS,
        start=1,
    ):

        print(
            f"🤖 AI MODEL {index}/"
            f"{len(MODELS)} | "
            f"{model}"
        )

        try:

            response = _request_model(
                model,
                question,
            )

        except requests.Timeout:

            print(
                f"⏱️ AI TIMEOUT | "
                f"{model}"
            )

            continue

        except requests.RequestException as e:

            print(
                f"❌ AI NETWORK ERROR | "
                f"{model} | {e}"
            )

            continue

        except Exception as e:

            print(
                f"❌ AI REQUEST ERROR | "
                f"{model} | "
                f"{type(e).__name__}: {e}"
            )

            continue

        # =================================================
        # СТАТУС
        # =================================================

        print(
            f"🤖 AI RESPONSE | "
            f"model={model} | "
            f"status={response.status_code}"
        )

        # =================================================
        # УСПІШНА ВІДПОВІДЬ
        # =================================================

        if response.status_code == 200:

            try:

                data = response.json()

            except Exception as e:

                print(
                    f"❌ AI JSON ERROR | "
                    f"{model} | {e}"
                )

                continue

            choices = data.get(
                "choices",
                [],
            )

            if not choices:

                print(
                    f"❌ AI EMPTY CHOICES | "
                    f"{model}"
                )

                continue

            message = choices[0].get(
                "message",
                {},
            )

            answer = message.get(
                "content"
            )

            if not answer:

                print(
                    f"❌ AI EMPTY CONTENT | "
                    f"{model}"
                )

                continue

            answer = str(
                answer
            ).strip()

            if not answer:

                print(
                    f"❌ AI EMPTY ANSWER | "
                    f"{model}"
                )

                continue

            print(
                f"✅ AI SUCCESS | "
                f"model={model} | "
                f"length={len(answer)}"
            )

            return answer

        # =================================================
        # 401 / 403
        #
        # Це вже не проблема конкретної моделі.
        # Зазвичай проблема з API key / account.
        # =================================================

        if response.status_code in (
            401,
            403,
        ):

            print(
                f"❌ AI AUTH ERROR | "
                f"status={response.status_code} | "
                f"model={model}"
            )

            print(
                f"❌ OpenRouter response | "
                f"{response.text}"
            )

            return (
                "❌ Помилка доступу до AI. "
                "Перевір API-ключ OpenRouter."
            )

        # =================================================
        # 429
        #
        # Модель перевантажена або rate limit.
        # Переходимо до наступної.
        # =================================================

        if response.status_code == 429:

            print(
                f"⚠️ AI RATE LIMIT | "
                f"{model} | "
                "переходимо до наступної моделі"
            )

            print(
                f"⚠️ OpenRouter response | "
                f"{response.text}"
            )

            continue

        # =================================================
        # 5XX
        #
        # Тимчасова помилка провайдера.
        # Переходимо до наступної моделі.
        # =================================================

        if response.status_code >= 500:

            print(
                f"⚠️ AI PROVIDER ERROR | "
                f"status={response.status_code} | "
                f"{model}"
            )

            print(
                f"⚠️ OpenRouter response | "
                f"{response.text}"
            )

            continue

        # =================================================
        # ІНША ПОМИЛКА
        # =================================================

        print(
            f"❌ AI ERROR | "
            f"status={response.status_code} | "
            f"model={model}"
        )

        print(
            f"❌ OpenRouter response | "
            f"{response.text}"
        )

    # =====================================================
    # ВСІ МОДЕЛІ НЕ СПРАЦЮВАЛИ
    # =====================================================

    print(
        "❌ AI: усі доступні моделі "
        "тимчасово недоступні"
    )

    return (
        "❌ Зараз AI тимчасово "
        "недоступний. Спробуй ще раз "
        "через кілька секунд."
    )