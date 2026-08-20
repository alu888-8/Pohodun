import re
import time
import requests

from config import OPENROUTER_API_KEY


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# =====================================================
# МОДЕЛІ
# =====================================================

MODELS = [
    "openrouter/free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-30b-a3b:free",
    "meta-llama/llama-3.3-8b-instruct:free",
]


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 2
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

3. Не використовуй китайські, японські, корейські
   або інші випадкові символи.

4. Не вигадуй слова, факти або назви.

5. Не повторюй одне слово або фразу багато разів.

6. Не створюй довгі беззмістовні послідовності
   символів, слів або складів.

7. Не згадуй випадкові слова, які не мають
   відношення до питання користувача.

8. Не вигадуй, що ти бачиш телефон, комп'ютер,
   Telegram, файли або інші пристрої користувача.

9. Якщо користувач просто вітається —
   відповідай природно.

10. Якщо користувач питає "як справи?" —
    відповідай коротко, дружньо і по-людськи.

11. Якщо питання просте —
    відповідь теж має бути простою.

12. Не пиши величезні відповіді без потреби.

13. Не повторюй своє ім'я в кожній відповіді.

14. Не починай кожну відповідь словами
    "Привіт! Я Pohodun AI".

15. Можеш використовувати емодзі,
    але помірно.

16. Якщо користувач жартує —
    можеш відповісти з гумором.

17. Якщо користувач просить допомогти —
    допомагай конкретно.

18. Якщо не знаєш відповіді —
    чесно скажи, що не знаєш.

19. Не вигадуй актуальну інформацію про:
    - погоду;
    - тривоги;
    - загрози;
    - новини.

20. Актуальні тривоги та загрози отримуються
    окремо з системи Pohodun. Не вигадуй їх.

21. Якщо повідомлення дуже коротке, наприклад:
    "тю", "ту ту", "ага", "хаха", "мм",
    відповідай коротко і природно.
    Не вигадуй нову тему.

22. Якщо користувач сам переходить на флірт,
    романтичні або дорослі жарти —
    можеш відповідати грайливо, але не починай
    такий тон першим.

СТИЛЬ:

- природна українська;
- дружній тон;
- коротко і зрозуміло;
- без зайвої офіційності;
- без дивних фраз;
- без машинного стилю.

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
        "temperature": 0.3,
        "max_tokens": MAX_TOKENS,
        "frequency_penalty": 0.35,
        "presence_penalty": 0.0,
    }

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
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

def _get_retry_delay(
    response,
    attempt,
):
    retry_after = response.headers.get(
        "Retry-After"
    )

    if retry_after:
        try:
            value = float(
                retry_after
            )

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
# ОТРИМАННЯ ВІДПОВІДІ
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
# ЗАХИСТ ВІД СМІТТЯ
# =====================================================

def _is_gibberish(
    answer,
):
    """
    Перевіряє відповідь моделі до відправки
    користувачу.

    Повертає:
        True  -> відповідь схожа на сміття
        False -> відповідь нормальна
    """

    if not answer:
        return True

    text = str(
        answer
    ).strip()

    if len(text) < 2:
        return True

    # -------------------------------------------------
    # Заборонені CJK-символи.
    # -------------------------------------------------

    cjk_count = len(
        re.findall(
            r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]",
            text,
        )
    )

    if cjk_count >= 3:
        print(
            "⚠️ AI VALIDATION | "
            f"CJK symbols={cjk_count}"
        )

        return True

    # -------------------------------------------------
    # Надмірна кількість дивних символів.
    # -------------------------------------------------

    strange_count = len(
        re.findall(
            r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]",
            text,
        )
    )

    if strange_count:
        print(
            "⚠️ AI VALIDATION | "
            "control characters"
        )

        return True

    # -------------------------------------------------
    # Повторення однакових слів.
    # Наприклад:
    # "Diana Diana Diana Diana..."
    # -------------------------------------------------

    words = re.findall(
        r"[A-Za-zА-Яа-яІіЇїЄєҐґ']+",
        text.lower(),
    )

    if len(words) >= 8:

        # Найдовша серія одного слова.
        run = 1
        max_run = 1

        for index in range(
            1,
            len(words),
        ):

            if words[index] == words[index - 1]:
                run += 1
            else:
                run = 1

            max_run = max(
                max_run,
                run,
            )

        if max_run >= 5:

            print(
                "⚠️ AI VALIDATION | "
                f"repeated word run={max_run}"
            )

            return True

        # -------------------------------------------------
        # Повторення коротких фрагментів.
        # -------------------------------------------------

        unique_words = set(
            words
        )

        if (
            len(words) >= 20
            and len(unique_words)
            <= max(
                3,
                len(words) // 8,
            )
        ):

            print(
                "⚠️ AI VALIDATION | "
                "too few unique words"
            )

            return True

    # -------------------------------------------------
    # Підозріло довга відповідь із дуже малим
    # словниковим різноманіттям.
    # -------------------------------------------------

    if len(text) > 500:

        unique_chars = len(
            set(
                text.lower()
            )
        )

        if unique_chars < 25:

            print(
                "⚠️ AI VALIDATION | "
                "very low character diversity"
            )

            return True

    return False


# =====================================================
# AI
# =====================================================

def ask_ai(
    question: str,
):

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
                    f"{model}"
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

                # =================================================
                # ПЕРЕВІРКА ВІДПОВІДІ
                # =================================================

                if _is_gibberish(
                    answer
                ):

                    print(
                        f"⚠️ AI GIBBERISH | "
                        f"model={model} | "
                        f"відповідь відхилена"
                    )

                    # Пробуємо ще раз тією ж моделлю.
                    if attempt < MAX_RETRIES_PER_MODEL:

                        time.sleep(
                            RETRY_DELAY_SECONDS
                            * attempt
                        )

                        continue

                    # Після двох невдалих відповідей
                    # переходимо до наступної моделі.
                    break

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

                break

            # =================================================
            # ТИМЧАСОВІ ПОМИЛКИ
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

            break

    # =====================================================
    # ВСІ МОДЕЛІ НЕ СПРАЦЮВАЛИ
    # =====================================================

    print(
        "❌ AI: усі моделі "
        "не дали коректної відповіді"
    )

    return (
        "❌ Не вдалося отримати нормальну "
        "відповідь від AI. Спробуй ще раз."
    )