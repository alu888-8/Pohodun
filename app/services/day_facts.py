import calendar
from datetime import date
from functools import lru_cache

import requests

from app.data.cities import CITY_API


WIKIMEDIA_URL = "https://uk.wikipedia.org/api/rest_v1/feed/onthisday"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


MONTHS_UA = {
    1: "січня", 2: "лютого", 3: "березня",
    4: "квітня", 5: "травня", 6: "червня",
    7: "липня", 8: "серпня", 9: "вересня",
    10: "жовтня", 11: "листопада", 12: "грудня",
}


def _city_coordinates(city):
    value = CITY_API.get(city)
    if not value:
        return None

    try:
        lat, lon = value.split(",")
        return float(lat.strip()), float(lon.strip())
    except (ValueError, AttributeError):
        return None


def _clean_text(value):
    if not value:
        return ""

    return " ".join(
        str(value)
        .replace("\n", " ")
        .split()
    )


@lru_cache(maxsize=128)
def _get_wikimedia(month, day):
    """
    Wikimedia On This Day:
    births/events for the selected day.
    """
    result = {
        "births": [],
        "events": [],
    }

    for kind in ("births", "events"):
        url = f"{WIKIMEDIA_URL}/{kind}/{month:02d}/{day:02d}"

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

            result[kind] = data.get(kind, [])

        except Exception as e:
            print(
                f"⚠️ Wikimedia {kind} error: {e}"
            )

    return result


@lru_cache(maxsize=128)
def _get_weather_records(lat, lon, year_from, year_to, month, day):
    """
    Історичні добові максимуми/мінімуми.
    Open-Meteo Archive базується на історичних
    реаналізах, тому в повідомленні прямо вказуємо джерело.
    """
    start = f"{year_from:04d}-{month:02d}-{day:02d}"
    end = f"{year_to:04d}-{month:02d}-{day:02d}"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_max,temperature_2m_min",
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
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])

        values = []

        for dt, high, low in zip(
            dates,
            highs,
            lows,
        ):
            if not dt:
                continue

            # Запит іде на один і той самий місяць/день
            # у кожному році, тому достатньо перевірити дату.
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

        return values

    except Exception as e:
        print(
            f"⚠️ Open-Meteo error: {e}"
        )
        return None


def _format_people(items, limit=4):
    result = []

    for item in items:
        year = item.get("year")
        text = item.get("text", "")
        pages = item.get("pages") or []

        title = ""

        if pages:
            title = (
                pages[0].get("normalizedtitle")
                or pages[0].get("title")
                or ""
            )

        title = _clean_text(title)

        if not title:
            # Wikimedia інколи віддає текст без title.
            text_clean = _clean_text(text)
            if text_clean:
                result.append(
                    f"• {text_clean[:180]}"
                )
            continue

        if year:
            result.append(
                f"• <b>{title}</b> — {year} р."
            )
        else:
            result.append(
                f"• <b>{title}</b>"
            )

        if len(result) >= limit:
            break

    return result


def _format_events(items, limit=3):
    result = []

    for item in items:
        year = item.get("year")
        text = _clean_text(
            item.get("text", "")
        )

        if not text:
            continue

        if year:
            result.append(
                f"• <b>{year}</b> — {text[:220]}"
            )
        else:
            result.append(
                f"• {text[:220]}"
            )

        if len(result) >= limit:
            break

    return result


def get_day_facts(city):
    """
    Формує готовий текст для кнопки «📅 Цей день».
    Працює для міста, яке вже вибрав користувач.
    """
    today = date.today()

    month = today.month
    day = today.day
    year = today.year

    city_data = _city_coordinates(city)

    wiki = _get_wikimedia(
        month,
        day,
    )

    text = (
        f"📅 <b>ЦЕЙ ДЕНЬ — "
        f"{day} {MONTHS_UA[month]}</b>\n\n"
    )

    # =====================================================
    # НАРОДИЛИСЯ
    # =====================================================

    births = _format_people(
        wiki.get("births", []),
        limit=4,
    )

    text += "🎂 <b>Хто народився цього дня</b>\n"

    if births:
        text += "\n".join(births)
    else:
        text += "Не вдалося отримати список."

    text += "\n\n"

    # =====================================================
    # ІСТОРИЧНА ПОГОДА
    # =====================================================

    text += "🌡️ <b>Якою була погода цього дня</b>\n"

    if city_data:
        lat, lon = city_data

        # До повного попереднього року.
        records = _get_weather_records(
            round(lat, 4),
            round(lon, 4),
            1940,
            year - 1,
            month,
            day,
        )

        if records:
            highs = [
                x for x in records
                if x["type"] == "high"
            ]

            lows = [
                x for x in records
                if x["type"] == "low"
            ]

            if highs:
                max_record = max(
                    highs,
                    key=lambda x: x["value"],
                )

                max_date = max_record["date"][:4]

                text += (
                    f"🔥 Найвища: "
                    f"<b>{max_record['value']:.1f}°C</b> "
                    f"({max_date} р.)\n"
                )

            if lows:
                min_record = min(
                    lows,
                    key=lambda x: x["value"],
                )

                min_date = min_record["date"][:4]

                text += (
                    f"🥶 Найнижча: "
                    f"<b>{min_record['value']:.1f}°C</b> "
                    f"({min_date} р.)\n"
                )

            text += (
                "ℹ️ Дані: історичний архів "
                "Open-Meteo (реаналіз)."
            )

        else:
            text += (
                "Історичні дані зараз недоступні."
            )

    else:
        text += (
            "Для цього міста поки немає координат."
        )

    text += "\n\n"

    # =====================================================
    # ПОДІЇ
    # =====================================================

    events = _format_events(
        wiki.get("events", []),
        limit=3,
    )

    text += "📜 <b>Цікаве з історії</b>\n"

    if events:
        text += "\n".join(events)
    else:
        text += "Історичних подій не знайдено."

    text += "\n\n"

    text += (
        "☀️ <i>Погодун пам'ятає, "
        "що сьогодні вже траплялося.</i>"
    )

    return text