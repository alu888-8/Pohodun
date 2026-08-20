import time
import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# =====================================================
# МОДЕЛІ
# =====================================================
#
# Порядок важливий:
# 1. автоматичний вибір безкоштовної моделі;
# 2. резервні безкоштовні моделі.
#

MODELS = [
    "openrouter/free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-30b-a3b:free",
    "meta-llama/llama-3.3-8b-instruct:free",
]


# =====================================================
# НАЛАШТУВАННЯ ПОВТОРІВ
# =====================================================

# Скільки разів повторювати запит до тієї самої моделі
# при тимчасовій помилці.
MAX_RETRIES_PER_MODEL = 2

# Базова пауза між повторними спробами.
RETRY_DELAY_SECONDS = 2

# Максимальна довжина відповіді.
MAX_TOKENS = 500


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
        "max_tokens": MAX_TOKENS,
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
# RETRY-AFTER
# =====================================================

def _get_retry_delay(response, attempt):
    """
    Якщо OpenRouter передав Retry-After — використовуємо його.
    Інакше використовуємо коротку експоненціальну паузу.
    """

    retry_after = response.headers.get(
        "Retry-After"
    )

    if retry_after:
        try:
            value = float(
                retry_after
            )

            # Не зависаємо на дуже великому значенні.
            return min(
                max(value, 1.0),
                15.0,
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return min(
        RETRY_DELAY_SECONDS * attempt,
        6,
    )


# =====================================================
# ПЕРЕВІРКА ВІДПОВІДІ
# =====================================================

def _extract_answer(data):
    if not isinstance(
        data,
        dict,
    ):
        return None

    choices = data.get(
        "choices",
        [],
    )

    if not choices:
        return None

    first = choices[0]

    if not isinstance(
        first,
        dict,
    ):
        return None

    message = first.get(
        "message",
        {},
    )

    if not isinstance(
        message,
        dict,
    ):
        return None

    answer = message.get(
        "content"
    )

    if answer is None:
        return None

    # Деякі провайдери можуть повернути список
    # контент-блоків замість звичайного рядка.
    if isinstance(
        answer,
        list,
    ):
        parts = []

        for item in answer:
            if isinstance(
                item,
                dict,
            ):
                part = item.get(
                    "text"
                )

                if part:
                    parts.append(
                        str(part)
                    )
            elif item:
                parts.append(
                    str(item)
                )

        answer = "".join(
            parts
        )

    answer = str(
        answer
    ).strip()

    if not answer:
        return None

    return answer


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

    for model_index, model in enumerate(
        MODELS,
        start=1,
    ):

        print(
            f"🤖 AI MODEL {model_index}/"
            f"{len(MODELS)} | "
            f"{model}"
        )

        for attempt in range(
            1,
            MAX_RETRIES_PER_MODEL + 1,
        ):

            print(
                f"🔄 AI ATTEMPT | "
                f"model={model} | "
                f"attempt={attempt}/"
                f"{MAX_RETRIES_PER_MODEL}"
            )

            try:

                response = _request_model(
                    model,
                    question,
                )

            except requests.Timeout:

                print(
                    f"⏱️ AI TIMEOUT | "
                    f"{model} | "
                    f"attempt={attempt}"
                )

                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(
                        RETRY_DELAY_SECONDS
                        * attempt
                    )

                continue

            except requests.RequestException as e:

                print(
                    f"❌ AI NETWORK ERROR | "
                    f"{model} | {e}"
                )

                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(
                        RETRY_DELAY_SECONDS
                        * attempt
                    )

                continue

            except Exception as e:

                print(
                    f"❌ AI REQUEST ERROR | "
                    f"{model} | "
                    f"{type(e).__name__}: {e}"
                )

                break

            print(
                f"🤖 AI RESPONSE | "
                f"model={model} | "
                f"status={response.status_code}"
            )

            # =================================================
            # 200
            # =================================================

            if response.status_code == 200:

                try:
                    data = response.json()

                except Exception as e:

                    print(
                        f"❌ AI JSON ERROR | "
                        f"{model} | {e}"
                    )

                    if attempt < MAX_RETRIES_PER_MODEL:
                        time.sleep(
                            RETRY_DELAY_SECONDS
                            * attempt
                        )

                    continue

                answer = _extract_answer(
                    data
                )

                if not answer:

                    print(
                        f"❌ AI EMPTY ANSWER | "
                        f"{model}"
                    )

                    if attempt < MAX_RETRIES_PER_MODEL:
                        time.sleep(
                            RETRY_DELAY_SECONDS
                            * attempt
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
            # =================================================

            if response.status_code == 429:

                print(
                    f"⚠️ AI RATE LIMIT | "
                    f"{model} | "
                    f"attempt={attempt}"
                )

                print(
                    f"⚠️ OpenRouter response | "
                    f"{response.text}"
                )

                if attempt < MAX_RETRIES_PER_MODEL:

                    delay = _get_retry_delay(
                        response,
                        attempt,
                    )

                    print(
                        f"⏳ AI RETRY | "
                        f"model={model} | "
                        f"через {delay:.1f} сек."
                    )

                    time.sleep(
                        delay
                    )

                    continue

                # Ця модель не відповіла —
                # переходимо до наступної.
                break

            # =================================================
            # 408 / 409 / 425 / 5XX
            #
            # Тимчасові помилки.
            # =================================================

            if (
                response.status_code in (
                    408,
                    409,
                    425,
                )
                or response.status_code >= 500
            ):

                print(
                    f"⚠️ AI TEMP ERROR | "
                    f"status={response.status_code} | "
                    f"{model}"
                )

                print(
                    f"⚠️ OpenRouter response | "
                    f"{response.text}"
                )

                if attempt < MAX_RETRIES_PER_MODEL:

                    delay = _get_retry_delay(
                        response,
                        attempt,
                    )

                    print(
                        f"⏳ AI RETRY | "
                        f"model={model} | "
                        f"через {delay:.1f} сек."
                    )

                    time.sleep(
                        delay
                    )

                    continue

                break

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

            # Для невідомої помилки немає сенсу
            # повторювати ту саму модель.
            break

    # =====================================================
    # ВСІ МОДЕЛІ НЕ СПРАЦЮВАЛИ
    # =====================================================

    print(
        "❌ AI: усі доступні моделі "
        "тимчасово недоступні"
    )

    return (
        "❌ Зараз AI перевантажений. "
        "Спробуй ще раз через кілька секунд."
    )