import random
import re
from datetime import datetime
from functools import lru_cache
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

from app.data.cities import CITY_API
from app.services.weather import get_weather


WIKIMEDIA_URL = (
    "https://uk.wikipedia.org/api/rest_v1/feed/onthisday"
)

OPEN_METEO_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)

KYIV_TZ = ZoneInfo("Europe/Kyiv")


MONTHS_UA = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}


# =====================================================
# КООРДИНАТИ МІСТА
# =====================================================

def _city_coordinates(city):

    value = CITY_API.get(city)

    if not value and city == "Київ":
        value = CITY_API.get("Kyiv")

    if not value and city:

        city_lower = city.strip().lower()

        for key, coordinates in CITY_API.items():

            if str(key).strip().lower() == city_lower:

                value = coordinates
                break

    if not value:
        return None

    try:

        lat, lon = value.split(",")

        return (
            float(lat.strip()),
            float(lon.strip())
        )

    except (
        ValueError,
        AttributeError
    ):

        return None


# =====================================================
# ОЧИЩЕННЯ ТЕКСТУ
# =====================================================

def _clean_text(value):

    if not value:
        return ""

    return " ".join(
        str(value)
        .replace("\n", " ")
        .split()
    )


# =====================================================
# WIKIMEDIA
# =====================================================

@lru_cache(maxsize=128)
def _get_wikimedia(month, day):

    result = {
        "births": [],
        "events": [],
    }

    for kind in (
        "births",
        "events",
    ):

        url = (
            f"{WIKIMEDIA_URL}/"
            f"{kind}/"
            f"{month:02d}/"
            f"{day:02d}"
        )

        try:

            response = requests.get(
                url,
                headers={
                    "User-Agent": "Pohodun/1.0"
                },
                timeout=15,
            )

            if response.status_code != 200:

                print(
                    f"⚠️ Wikimedia {kind}: "
                    f"HTTP {response.status_code}"
                )

                continue

            data = response.json()

            result[kind] = data.get(
                kind,
                []
            )

        except Exception as e:

            print(
                f"⚠️ Wikimedia {kind} error: {e}"
            )

    return result


# =====================================================
# ІСТОРИЧНА ПОГОДА
# =====================================================

@lru_cache(maxsize=128)
def _get_weather_records(
    lat,
    lon,
    year_from,
    year_to,
    month,
    day
):

    start = (
        f"{year_from:04d}-"
        f"{month:02d}-"
        f"{day:02d}"
    )

    end = (
        f"{year_to:04d}-"
        f"{month:02d}-"
        f"{day:02d}"
    )

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min"
        ),
        "temperature_unit": "celsius",
        "timezone": "auto",
    }

    try:

        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=20,
        )

        if response.status_code != 200:

            print(
                f"⚠️ Open-Meteo: "
                f"HTTP {response.status_code}"
            )

            return None

        data = response.json()

        daily = data.get(
            "daily",
            {}
        )

        dates = daily.get(
            "time",
            []
        )

        highs = daily.get(
            "temperature_2m_max",
            []
        )

        lows = daily.get(
            "temperature_2m_min",
            []
        )

        values = []

        for dt, high, low in zip(
            dates,
            highs,
            lows
        ):

            if not dt:
                continue

            try:

                if (
                    len(dt) >= 10
                    and int(dt[5:7]) == month
                    and int(dt[8:10]) == day
                ):

                    if high is not None:

                        values.append(
                            {
                                "date": dt,
                                "type": "high",
                                "value": float(high),
                            }
                        )

                    if low is not None:

                        values.append(
                            {
                                "date": dt,
                                "type": "low",
                                "value": float(low),
                            }
                        )

            except (
                ValueError,
                TypeError
            ):

                continue

        return values

    except Exception as e:

        print(
            f"⚠️ Open-Meteo error: {e}"
        )

        return None


# =====================================================
# 🎂 НАРОДЖЕНІ
# =====================================================

@lru_cache(maxsize=256)
def _get_person_description(title):
    """
    Отримує короткий опис людини з української Вікіпедії.
    Якщо description недоступний — пробуємо перше речення extract.
    """

    if not title:
        return ""

    try:
        page_title = title.replace(" ", "_")
        encoded_title = quote(page_title, safe="")

        url = (
            "https://uk.wikipedia.org/api/rest_v1/page/summary/"
            f"{encoded_title}"
        )

        response = requests.get(
            url,
            headers={
                "User-Agent": "Pohodun/1.0"
            },
            timeout=10,
        )

        if response.status_code != 200:
            print(
                f"⚠️ Wikipedia person {title}: "
                f"HTTP {response.status_code}"
            )
            return ""

        data = response.json()

        description = _clean_text(
            data.get("description", "")
        )

        if description:
            return description[:220]

        extract = _clean_text(
            data.get("extract", "")
        )

        if not extract:
            return ""

        first_sentence = re.split(
            r"(?<=[.!?])\s+",
            extract,
            maxsplit=1,
        )[0].strip()

        return first_sentence[:220]

    except Exception as e:
        print(
            f"⚠️ Помилка опису людини "
            f"{title}: {e}"
        )
        return ""


def _format_people(
    items,
    limit=4,
):
    """
    Формує до limit людей.
    Для кожного показує:
    - ім'я;
    - рік народження;
    - коротко хто це.
    """

    result = []
    people_count = 0

    for item in items:

        if people_count >= limit:
            break

        year = item.get("year")
        pages = item.get("pages") or []
        title = ""

        if pages:
            title = (
                pages[0].get("normalizedtitle")
                or pages[0].get("title")
                or ""
            )

        title = _clean_text(title)

        if title.isdigit():
            continue

        if not title:
            text_clean = _clean_text(
                item.get("text", "")
            )

            if text_clean:
                result.append(
                    f"• {escape(text_clean[:180], quote=False)}"
                )
                people_count += 1

            continue

        description = _get_person_description(
            title
        )

        safe_title = escape(
            title,
            quote=False,
        )

        if year:
            result.append(
                f"• <b>{safe_title}</b> — {year} р."
            )
        else:
            result.append(
                f"• <b>{safe_title}</b>"
            )

        if description:
            result.append(
                "  👤 "
                f"{escape(description, quote=False)}"
            )

        people_count += 1

    return result


# =====================================================
# 🇺🇦 КЛЮЧОВІ СЛОВА УКРАЇНИ
# =====================================================

UKRAINE_KEYWORDS = (

    "україн",
    "україна",
    "київ",
    "київськ",
    "львів",
    "львівськ",
    "харків",
    "харківськ",
    "одес",
    "одеськ",
    "дніпро",
    "дніпропетров",
    "запоріж",
    "черніг",
    "черкас",
    "полтав",
    "волин",
    "поділ",
    "поділь",
    "галичин",
    "буковин",
    "закарпат",
    "донбас",
    "донец",
    "луган",
    "крим",
    "херсон",
    "миколаїв",
    "житомир",
    "рівн",
    "терноп",
    "хмельниць",
    "івано-франків",
    "вінниц",
    "сум",
    "чернів",
    "майдан",
    "козац",
    "запороз",
    "гетьман",
    "гетьманщин",
    "українська народна республіка",
    "зунр",
    "упа",
    "оун",
    "українська повстанська армія",
    "незалежність україни",
    "державність україни",
    "атo",
    "ато",
    "зсу",
    "збройні сили україни",
)


# =====================================================
# 🇷🇺 РОСІЙСЬКІ / РАДЯНСЬКІ КЛЮЧОВІ СЛОВА
# =====================================================

RUSSIA_KEYWORDS = (

    "росі",
    "російськ",
    "росія",
    "москва",
    "москов",
    "санкт-петербург",
    "ленінград",
    "срср",
    "радянськ",
    "совєтськ",
    "більшовик",
    "більшовиць",
    "кремл",
    "російська імперія",
    "російської імперії",
    "російсько-імпер",
    "рсфрр",
    "кгб",
    "нквс",
    "червона армія",
)


# =====================================================
# ТЕКСТ ПОДІЇ
# =====================================================

def _event_text(item):

    year = item.get(
        "year"
    )

    text = _clean_text(
        item.get(
            "text",
            ""
        )
    )

    pages = (
        item.get("pages")
        or []
    )

    page_titles = []

    for page in pages:

        title = (
            page.get(
                "normalizedtitle"
            )
            or
            page.get(
                "title"
            )
            or
            ""
        )

        if title:

            page_titles.append(
                _clean_text(title)
            )

    return _clean_text(
        f"{year or ''} "
        f"{text} "
        f"{' '.join(page_titles)}"
    )


# =====================================================
# ПЕРЕВІРКА УКРАЇНСЬКОЇ ПОДІЇ
# =====================================================

def _is_ukraine_event(item):

    text = _event_text(
        item
    ).lower()

    return any(
        keyword in text
        for keyword in UKRAINE_KEYWORDS
    )


# =====================================================
# ПЕРЕВІРКА РОСІЙСЬКОЇ ПОДІЇ
# =====================================================

def _is_russia_event(item):

    text = _event_text(
        item
    ).lower()

    return any(
        keyword in text
        for keyword in RUSSIA_KEYWORDS
    )


# =====================================================
# 📜 ФОРМУВАННЯ ПОДІЙ
# =====================================================

def _format_events(
    items,
    limit=3
):

    # -----------------------------------------------
    # Спочатку шукаємо українські події
    # -----------------------------------------------

    ukrainian_events = []

    # -----------------------------------------------
    # Потім нейтральні світові
    # -----------------------------------------------

    world_events = []

    for item in items:

        text = _clean_text(
            item.get(
                "text",
                ""
            )
        )

        if not text:
            continue

        # Російські / радянські події
        # взагалі не показуємо.
        if _is_russia_event(item):

            print(
                "🚫 DAY FACTS | "
                "Російську/радянську "
                f"подію відфільтровано: {text[:120]}"
            )

            continue

        if _is_ukraine_event(item):

            ukrainian_events.append(
                item
            )

        else:

            world_events.append(
                item
            )

    # -----------------------------------------------
    # Українські події мають пріоритет
    # -----------------------------------------------

    selected = []

    for item in ukrainian_events:

        selected.append(
            item
        )

        if len(selected) >= limit:
            break

    # -----------------------------------------------
    # Якщо українських мало —
    # додаємо нейтральні світові.
    # -----------------------------------------------

    if len(selected) < limit:

        for item in world_events:

            if item in selected:
                continue

            selected.append(
                item
            )

            if len(selected) >= limit:
                break

    # -----------------------------------------------
    # Формуємо текст
    # -----------------------------------------------

    result = []

    for item in selected:

        year = item.get(
            "year"
        )

        text = _clean_text(
            item.get(
                "text",
                ""
            )
        )

        if not text:
            continue

        text = escape(
            text[:220],
            quote=False
        )

        if year:

            result.append(
                f"• <b>{year}</b> — "
                f"{text}"
            )

        else:

            result.append(
                f"• {text}"
            )

    return result


# =====================================================
# 😄 АНЕКДОТИ
# =====================================================

JOKES = [

    (
        "— Лікарю, у мене проблема з пам'яттю.\n"
        "— Давно?\n"
        "— Що давно?"
    ),

    (
        "— Ти чому такий сумний?\n"
        "— Зарплату отримав.\n"
        "— І що?\n"
        "— Тепер знаю, за що я так багато працюю."
    ),

    (
        "— Як у тебе справи?\n"
        "— Стабільно.\n"
        "— Це добре?\n"
        "— Ні. Стабільно немає грошей."
    ),

    (
        "Доросле життя — це коли відкриваєш холодильник "
        "не тому, що голодний, а раптом там з'явилося щось нове."
    ),

    (
        "— У тебе є план на майбутнє?\n"
        "— Є.\n"
        "— Який?\n"
        "— Не панікувати.\n"
        "— І як?\n"
        "— План поки не працює."
    ),

    (
        "Найстрашніші слова дорослої людини:\n"
        "«Треба серйозно поговорити».\n"
        "Особливо коли ти сам ще не знаєш, про що."
    ),

    (
        "— Чому ти не відповідав на телефон?\n"
        "— Я був зайнятий.\n"
        "— Чим?\n"
        "— Дивився на телефон і думав, відповідати чи ні."
    ),

    (
        "Мій організм о 23:00: «Треба спати».\n"
        "Мій мозок о 02:37: «А пам'ятаєш той крінж із 2014 року?»"
    ),

    (
        "— Ти економиш гроші?\n"
        "— Так.\n"
        "— Як?\n"
        "— Дивлюся на ціни й нічого не купую."
    ),

    (
        "Чорний гумор — це коли життя підкидає тобі лимони, "
        "а ти питаєш: «А сіль є? Бо текіла теж закінчилася»."
    ),

    (
        "— У мене нерви як канати.\n"
        "— Міцні?\n"
        "— Ні. Вже давно на межі."
    ),

    (
        "Кажуть: «Не відкладай на завтра те, що можеш зробити сьогодні».\n"
        "Мудрі люди просто не знали про післязавтра."
    ),

    (
        "— Ти виспався?\n"
        "— Ні.\n"
        "— А чому не ліг раніше?\n"
        "— Хотів трохи пожити перед сном."
    ),

    (
        "Життя — це коли купив щось зі знижкою 50%, "
        "а потім три дні думаєш, чи треба було взагалі це купувати."
    ),

    (
        "— У тебе стрес?\n"
        "— Ні.\n"
        "— А чому око сіпається?\n"
        "— Воно просто теж працює."
    ),

    (
        "Мій фінансовий план на місяць:\n"
        "1. Не витрачати зайвого.\n"
        "2. Побачити щось зі знижкою.\n"
        "3. Забути пункт перший."
    ),

    (
        "Іноді хочеться просто втекти від усіх проблем.\n"
        "А потім згадуєш, що проблеми теж поїдуть за тобою."
    ),

    (
        "— Як настрій?\n"
        "— Як Wi-Fi у підвалі: наче є, але користі нуль."
    ),

    (
        "Дорослість — це коли слово «відпочинок» "
        "викликає думку: «А хто за це заплатить?»"
    ),

    (
        "— Чому ти мовчиш?\n"
        "— Економлю слова. Раптом до зарплати не вистачить."
    ),

]


# =====================================================
# ☀️ ПРАКТИЧНІ ПОРАДИ
# =====================================================

GENERAL_TIPS = [

    "☀️ Якщо сьогодні є можливість — "
    "знайди хоча б 20 хвилин для прогулянки.",

    "☕ Зроби сьогодні одну нормальну перерву "
    "без телефону. Кава теж рахується.",

    "🚶 Якщо треба кудись недалеко — "
    "спробуй пройтися пішки.",

    "💧 Навіть коли не дуже спекотно, "
    "не забувай пити воду.",

    "😎 Не обов'язково мати великий план на день. "
    "Іноді достатньо просто зробити одну корисну справу.",

    "🌳 Якщо поруч є парк — "
    "сьогодні непоганий день, щоб туди заглянути.",

    "🔋 Не забувай заряджати не тільки телефон, "
    "а й себе — зроби невелику паузу.",

]


COLD_TIPS = [

    "🧥 Сьогодні краще взяти додатковий шар одягу.",

    "🧣 Не забудь захистити шию та руки від холоду.",

    "☕ Гарячий напій сьогодні точно не буде зайвим.",

]


HOT_TIPS = [

    "💧 Тримай воду поруч, особливо якщо плануєш довго бути надворі.",

    "🧢 У спеку краще не забувати про головний убір.",

    "☀️ Якщо можеш, плануй довгі прогулянки на ранок або вечір.",

]


RAIN_TIPS = [

    "☔ Якщо виходиш надовго — захопи парасолю.",

    "👟 Сьогодні краще обрати взуття, яке не боїться води.",

]


WIND_TIPS = [

    "💨 Через вітер може відчуватися холодніше, ніж показує термометр.",

    "🧥 Легка вітрозахисна куртка сьогодні буде доречною.",

]


# =====================================================
# ВИБІР ПОРАДИ
# =====================================================

def _get_practical_tip(city):

    try:

        city_api = CITY_API.get(
            city,
            city
        )

        if city == "Київ":

            city_api = (
                CITY_API.get("Київ")
                or
                CITY_API.get("Kyiv")
                or
                city
            )

        weather = get_weather(
            city_api
        )

        if not weather:

            return random.choice(
                GENERAL_TIPS
            )

        temp = float(
            weather.get(
                "temp",
                15
            )
        )

        feels = float(
            weather.get(
                "feels_like",
                temp
            )
        )

        wind = float(
            weather.get(
                "wind",
                0
            )
        )

        condition = str(
            weather.get(
                "condition",
                ""
            )
        ).lower()

        if (
            temp >= 28
            or feels >= 30
        ):

            return random.choice(
                HOT_TIPS
            )

        if (
            temp <= 5
            or feels <= 3
        ):

            return random.choice(
                COLD_TIPS
            )

        if any(
            word in condition
            for word in (
                "дощ",
                "rain",
                "drizzle",
                "злива",
                "мряка"
            )
        ):

            return random.choice(
                RAIN_TIPS
            )

        if wind >= 7:

            return random.choice(
                WIND_TIPS
            )

        return random.choice(
            GENERAL_TIPS
        )

    except Exception as e:

        print(
            f"⚠️ Помилка практичної "
            f"поради: {e}"
        )

        return random.choice(
            GENERAL_TIPS
        )


# =====================================================
# ОСНОВНА ФУНКЦІЯ
# =====================================================

def get_day_facts(city):

    now = datetime.now(
        KYIV_TZ
    )

    month = now.month
    day = now.day
    year = now.year

    city_data = _city_coordinates(
        city
    )

    wiki = _get_wikimedia(
        month,
        day
    )

    text = (
        f"📅 <b>ЦЕЙ ДЕНЬ — "
        f"{day} {MONTHS_UA[month]}</b>\n\n"
    )

    # =================================================
    # 🎂 НАРОДЖЕНІ
    # =================================================

    births = _format_people(
        wiki.get(
            "births",
            []
        ),
        limit=4
    )

    text += (
        "🎂 <b>Хто народився "
        "цього дня</b>\n"
    )

    if births:

        text += "\n".join(
            births
        )

    else:

        text += (
            "Інформацію не знайдено."
        )

    text += "\n\n"

    # =================================================
    # 🌡️ ТЕМПЕРАТУРНІ РЕКОРДИ
    # =================================================

    text += (
        "🌡️ <b>Температурний "
        "рекорд цього дня</b>\n"
    )

    if city_data:

        lat, lon = city_data

        records = _get_weather_records(
            round(lat, 4),
            round(lon, 4),
            1940,
            year - 1,
            month,
            day
        )

        if records:

            highs = [
                item
                for item in records
                if item["type"] == "high"
            ]

            lows = [
                item
                for item in records
                if item["type"] == "low"
            ]

            if highs:

                max_record = max(
                    highs,
                    key=lambda item:
                    item["value"]
                )

                max_year = (
                    max_record["date"][:4]
                )

                text += (
                    "🔥 Найвища: "
                    f"<b>"
                    f"{max_record['value']:.1f}"
                    "°C</b> "
                    f"({max_year} р.)\n"
                )

            if lows:

                min_record = min(
                    lows,
                    key=lambda item:
                    item["value"]
                )

                min_year = (
                    min_record["date"][:4]
                )

                text += (
                    "🥶 Найнижча: "
                    f"<b>"
                    f"{min_record['value']:.1f}"
                    "°C</b> "
                    f"({min_year} р.)\n"
                )

            text += (
                "ℹ️ Історичні дані: "
                "Open-Meteo."
            )

        else:

            text += (
                "Історичні дані "
                "недоступні."
            )

    else:

        text += (
            "Для цього міста "
            "немає координат."
        )

    text += "\n\n"

    # =================================================
    # 📜 ПОДІЇ
    # =================================================

    events = _format_events(
        wiki.get(
            "events",
            []
        ),
        limit=3
    )

    text += (
        "📜 <b>Цікаве цього дня</b>\n"
    )

    if events:

        text += "\n".join(
            events
        )

    else:

        text += (
            "Українських або нейтральних "
            "подій цього дня не знайдено."
        )

    text += "\n\n"

    # =================================================
    # 😄 АНЕКДОТ
    # =================================================

    joke = random.choice(
        JOKES
    )

    text += (
        "😄 <b>На гарний настрій</b>\n"
        f"{escape(joke, quote=False)}\n\n"
    )

    # =================================================
    # ☀️ ПОРАДА
    # =================================================

    tip = _get_practical_tip(
        city
    )

    text += (
        "☀️ <b>Порада на сьогодні</b>\n"
        f"{escape(tip, quote=False)}\n\n"
    )

    text += (
        "🌤 <i>Погодун бажає "
        "гарного дня!</i>"
    )

    return text