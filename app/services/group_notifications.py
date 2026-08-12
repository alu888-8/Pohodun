import asyncio
import json
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.services.alerts import get_alerts
from app.services.threats import get_threats

from app.services.weather import get_weather
from app.services.advice import get_advice

from app.utils.weather_icons import get_weather_icon
from app.data.regions import CITY_REGIONS


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

GROUP_CHAT_ID = -493936504

KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

# Перевірка тривог/загроз кожні 15 секунд
MONITOR_INTERVAL = 15


# ============================================================
# СТАНИ МОНІТОРИНГУ
# ============================================================

# Наприклад:
#
# {
#     "Київ": {
#         "alert": True,
#         "threats": "...",
#     },
#     "Одеса": {
#         "alert": False,
#         "threats": "...",
#     }
# }

_city_states = {}


# ============================================================
# ВІДПРАВКА В ГРУПУ
# ============================================================

async def send_to_group(bot: Bot, text: str):

    try:

        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )

        print("✅ Повідомлення відправлено в групу")

    except Exception as e:

        print(
            f"❌ Не вдалося відправити повідомлення в групу: {e}"
        )


# ============================================================
# ОТРИМАННЯ МІСТ КОРИСТУВАЧІВ
# ============================================================

def get_users_cities():

    """
    Отримує всі УНІКАЛЬНІ міста,
    які зараз вибрали користувачі.

    Якщо:
        користувач 1 -> Київ
        користувач 2 -> Київ
        користувач 3 -> Одеса

    результат:

        ["Київ", "Одеса"]
    """

    try:

        conn = sqlite3.connect(
            "app/database/users.db"
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT city
            FROM users
            WHERE city IS NOT NULL
            AND TRIM(city) != ''
            """
        )

        rows = cursor.fetchall()

        conn.close()

        cities = []

        for row in rows:

            city = row[0]

            if city:

                city = city.strip()

                if city and city not in cities:
                    cities.append(city)

        return cities

    except Exception as e:

        print(
            f"❌ Помилка отримання міст користувачів: {e}"
        )

        return []


# ============================================================
# НОРМАЛІЗАЦІЯ ТЕКСТУ
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# ПЕРЕВІРКА МІСТА ДЛЯ ТРИВОГ
# ============================================================

def get_city_alert_item(city, data):

    """
    Повертає запис API для конкретного міста.

    Важливо:
    Київ НЕ плутаємо з Київською областю.
    """

    if not data:
        return None

    city_normalized = normalize_text(city)

    raions = data.get("raions", [])
    oblasts = data.get("oblasts", [])

    items = raions + oblasts

    # ========================================================
    # КИЇВ
    # ========================================================

    if city_normalized in (
        "київ",
        "м. київ",
        "місто київ"
    ):

        for item in items:

            name = normalize_text(
                item.get("name")
            )

            oblast = normalize_text(
                item.get("oblast")
            )

            key = normalize_text(
                item.get("key")
            )

            if name in (
                "м. київ",
                "київ",
                "місто київ"
            ):

                if oblast in (
                    "",
                    "м. київ",
                    "київ",
                    "місто київ"
                ):

                    return item

            if key in (
                "м. київ",
                "київ",
                "місто київ"
            ):

                return item

            if (
                name == "київський район"
                and oblast == "м. київ"
            ):

                return item

        return None

    # ========================================================
    # ІНШІ МІСТА
    # ========================================================

    keywords = CITY_REGIONS.get(
        city,
        [city_normalized]
    )

    keywords = [
        normalize_text(word)
        for word in keywords
        if word
    ]

    for item in items:

        name = normalize_text(
            item.get("name")
        )

        oblast = normalize_text(
            item.get("oblast")
        )

        key = normalize_text(
            item.get("key")
        )

        search_text = (
            f"{name} "
            f"{oblast} "
            f"{key}"
        )

        for word in keywords:

            if word and word in search_text:

                return item

    return None


# ============================================================
# СТАН ТРИВОГИ
# ============================================================

def is_city_alert_active(city, data):

    item = get_city_alert_item(
        city,
        data
    )

    if item is None:
        return False

    return True


# ============================================================
# НОРМАЛІЗАЦІЯ ЗАГРОЗ
# ============================================================

def normalize_threats_data(data):

    """
    Робить стабільний JSON для порівняння.

    Це важливо, щоб бот не писав
    "ОНОВЛЕННЯ ЗАГРОЗ" кожні 15 секунд,
    якщо фактично нічого не змінилося.
    """

    if data is None:
        return ""

    try:

        return json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":")
        )

    except Exception:

        return str(data)


# ============================================================
# ПОШУК ЗАГРОЗ ДЛЯ МІСТА
# ============================================================

def get_city_threats(city, data):

    """
    Витягує загрози, які стосуються конкретного міста.

    Функція спеціально зроблена досить універсально,
    тому що API загроз може містити різні поля.
    """

    if not data:
        return []

    city_normalized = normalize_text(city)

    keywords = CITY_REGIONS.get(
        city,
        [city_normalized]
    )

    keywords = [
        normalize_text(word)
        for word in keywords
        if word
    ]

    # Для Києва не беремо Київську область
    kyiv = city_normalized in (
        "київ",
        "м. київ",
        "місто київ"
    )

    result = []

    # ========================================================
    # ВИЗНАЧАЄМО СПИСОК ЗАГРОЗ
    # ========================================================

    if isinstance(data, list):

        threats = data

    elif isinstance(data, dict):

        threats = (
            data.get("threats")
            or data.get("items")
            or data.get("data")
            or data.get("alerts")
            or []
        )

        if isinstance(threats, dict):

            threats = [
                threats
            ]

    else:

        threats = []

    # ========================================================
    # ПЕРЕБИРАЄМО ЗАГРОЗИ
    # ========================================================

    for threat in threats:

        if not isinstance(threat, dict):
            continue

        # Збираємо весь текст запису
        # для пошуку міста/області

        values = []

        for key, value in threat.items():

            if isinstance(value, (str, int, float)):

                values.append(
                    str(value)
                )

            elif isinstance(value, list):

                for x in value:

                    if isinstance(
                        x,
                        (str, int, float)
                    ):

                        values.append(
                            str(x)
                        )

        search_text = normalize_text(
            " ".join(values)
        )

        # ====================================================
        # КИЇВ
        # ====================================================

        if kyiv:

            # Київ повинен бути присутній,
            # але не просто "Київська область"

            if (
                "київська область" in search_text
                and "київ" not in search_text.replace(
                    "київська область",
                    ""
                )
            ):

                continue

            if (
                "м. київ" in search_text
                or "місто київ" in search_text
                or "курс" in search_text
                and "київ" in search_text
                or search_text.endswith("київ")
                or "київ." in search_text
                or "київ," in search_text
            ):

                result.append(threat)

                continue

            if (
                "київ" in search_text
                and "київська область" not in search_text
            ):

                result.append(threat)

                continue

        # ====================================================
        # ІНШІ МІСТА
        # ====================================================

        else:

            if any(
                keyword in search_text
                for keyword in keywords
            ):

                result.append(threat)

    return result


# ============================================================
# ФОРМУВАННЯ ТЕКСТУ ЗАГРОЗ
# ============================================================

def format_threats(city, threats):

    """
    Формує красиве повідомлення
    для групи.
    """

    if not threats:

        return (
            "🛰 <b>ЗАГРОЗ ПОБЛИЗУ НЕМАЄ</b>\n\n"
            f"📍 <b>{city}</b>\n\n"
            "✅ Активних загроз не виявлено."
        )

    lines = [
        "🛰 <b>ОНОВЛЕННЯ ЗАГРОЗ</b>",
        "",
        f"🛰 <b>ЗАГРОЗИ ДЛЯ {city.upper()}</b>",
        ""
    ]

    for threat in threats:

        if not isinstance(threat, dict):
            continue

        # Найчастіші поля API

        threat_type = (
            threat.get("type")
            or threat.get("title")
            or threat.get("name")
            or "⚠️ Загроза"
        )

        region = (
            threat.get("oblast")
            or threat.get("region")
            or threat.get("area")
            or ""
        )

        location = (
            threat.get("city")
            or threat.get("settlement")
            or threat.get("location")
            or threat.get("place")
            or ""
        )

        description = (
            threat.get("description")
            or threat.get("text")
            or threat.get("message")
            or ""
        )

        confirmed = (
            threat.get("confirmed")
            or threat.get("confirmations")
            or threat.get("confirmation")
        )

        lines.append(
            f"🛸 <b>{threat_type}</b>"
        )

        if region:

            lines.append(
                f"📍 {region}"
            )

        if location:

            lines.append(
                f"📌 {location}"
            )

        if description:

            lines.append(
                str(description)
            )

        if confirmed is not None:

            lines.append(
                f"Підтверджень: {confirmed}."
            )

        lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# ОЧИЩЕННЯ СТАНІВ МІСТ
# ============================================================

def cleanup_old_cities(active_cities):

    """
    Якщо користувач більше не вибирає місто,
    його стан видаляється.

    Наприклад:

    було:
        Київ
        Одеса
        Львів

    всі користувачі пішли з Одеси.

    стає:
        Київ
        Львів
    """

    active_set = set(
        active_cities
    )

    old_cities = list(
        _city_states.keys()
    )

    for city in old_cities:

        if city not in active_set:

            del _city_states[city]

            print(
                f"🗑 Місто прибрано з моніторингу: {city}"
            )


# ============================================================
# ОСНОВНИЙ МОНІТОРИНГ
# ============================================================

async def group_alert_monitor(bot: Bot):

    print(
        "🚨 Моніторинг тривог та загроз запущений"
    )

    print(
        f"⏱ Інтервал перевірки: "
        f"{MONITOR_INTERVAL} секунд"
    )

    while True:

        try:

            # =================================================
            # 1. ОТРИМУЄМО МІСТА КОРИСТУВАЧІВ
            # =================================================

            cities = await asyncio.to_thread(
                get_users_cities
            )

            print(
                f"📍 Міста для моніторингу: {cities}"
            )

            # Якщо немає користувачів
            # просто чекаємо наступної перевірки

            if not cities:

                print(
                    "ℹ️ Немає міст для моніторингу"
                )

                await asyncio.sleep(
                    MONITOR_INTERVAL
                )

                continue

            cleanup_old_cities(
                cities
            )

            # =================================================
            # 2. ОДИН ЗАПИТ ТРИВОГ
            # =================================================

            alerts_data = await asyncio.to_thread(
                get_alerts
            )

            if alerts_data is None:

                print(
                    "⚠️ Не вдалося отримати API тривог"
                )

            # =================================================
            # 3. ОДИН ЗАПИТ ЗАГРОЗ
            # =================================================

            threats_data = await asyncio.to_thread(
                get_threats
            )

            if threats_data is None:

                print(
                    "⚠️ Не вдалося отримати API загроз"
                )

            # =================================================
            # 4. КОЖНЕ МІСТО ОКРЕМО
            # =================================================

            for city in cities:

                try:

                    # Створюємо початковий стан

                    if city not in _city_states:

                        _city_states[city] = {
                            "alert": None,
                            "threats": None
                        }

                    state = _city_states[city]

                    # =================================================
                    # ТРИВОГА
                    # =================================================

                    if alerts_data is not None:

                        active = is_city_alert_active(
                            city,
                            alerts_data
                        )

                        previous = state["alert"]

                        # ---------------------------------------------
                        # ПЕРШИЙ ЗАПУСК
                        # ---------------------------------------------

                        if previous is None:

                            state["alert"] = active

                            print(
                                f"📡 Початковий стан "
                                f"{city}: "
                                f"тривога={active}"
                            )

                        # ---------------------------------------------
                        # ПОЧАТОК ТРИВОГИ
                        # ---------------------------------------------

                        elif active and not previous:

                            await send_to_group(
                                bot,

                                "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                                f"📍 <b>{city}</b>\n\n"
                                "⚠️ Негайно перейдіть "
                                "у безпечне місце."
                            )

                            state["alert"] = True

                            print(
                                f"🚨 Початок тривоги: {city}"
                            )

                        # ---------------------------------------------
                        # ВІДБІЙ
                        # ---------------------------------------------

                        elif not active and previous:

                            await send_to_group(
                                bot,

                                "🟢 <b>ВІДБІЙ "
                                "ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                                f"📍 <b>{city}</b>\n\n"
                                "✅ Небезпека минула."
                            )

                            state["alert"] = False

                            print(
                                f"🟢 Відбій тривоги: {city}"
                            )

                    # =================================================
                    # ЗАГРОЗИ
                    # =================================================

                    if threats_data is not None:

                        city_threats = get_city_threats(
                            city,
                            threats_data
                        )

                        threats_signature = (
                            normalize_threats_data(
                                city_threats
                            )
                        )

                        previous_threats = (
                            state["threats"]
                        )

                        # ---------------------------------------------
                        # ПЕРШИЙ ЗАПУСК
                        # ---------------------------------------------

                        if previous_threats is None:

                            state["threats"] = (
                                threats_signature
                            )

                            print(
                                f"📡 Початковий стан загроз: "
                                f"{city} | "
                                f"{len(city_threats)}"
                            )

                        # ---------------------------------------------
                        # ЗАГРОЗИ ЗМІНИЛИСЯ
                        # ---------------------------------------------

                        elif (
                            threats_signature
                            != previous_threats
                        ):

                            text = format_threats(
                                city,
                                city_threats
                            )

                            await send_to_group(
                                bot,
                                text
                            )

                            state["threats"] = (
                                threats_signature
                            )

                            print(
                                f"🔄 Загрози змінилися: "
                                f"{city} | "
                                f"{len(city_threats)}"
                            )

                except Exception as city_error:

                    print(
                        f"❌ Помилка моніторингу "
                        f"{city}: {city_error}"
                    )

        except Exception as e:

            print(
                f"❌ Помилка моніторингу: {e}"
            )

        # =====================================================
        # НАСТУПНА ПЕРЕВІРКА
        # =====================================================

        await asyncio.sleep(
            MONITOR_INTERVAL
        )


# ============================================================
# РАНКОВА ПОГОДА
# ============================================================

async def send_morning_weather(bot: Bot):

    """
    Відправляє погоду в групу
    щодня о 08:00 за Києвом.
    """

    try:

        city_ua = "Київ"
        city_api = "Kyiv"

        weather = await asyncio.to_thread(
            get_weather,
            city_api
        )

        if weather is None:

            await send_to_group(
                bot,

                "❌ Не вдалося отримати "
                "ранкову погоду для Києва."
            )

            return

        temp = weather["temp"]
        feels = weather["feels_like"]
        humidity = weather["humidity"]
        wind = weather["wind"]
        description = weather["condition"]

        icon = get_weather_icon(
            description
        )

        advice = await asyncio.to_thread(
            get_advice,
            temp,
            description,
            city_ua,
            feels,
            wind,
            humidity
        )

        text = (
            f"🌅 <b>Доброго ранку!</b>\n\n"
            f"🌤 <b>Погодун — погода на ранок</b>\n\n"
            f"📍 <b>{city_ua}</b>\n\n"
            f"{icon} <b>{description}</b>\n\n"
            f"🌡 Температура: <b>{temp}°C</b>\n"
            f"🤗 Відчувається: <b>{feels}°C</b>\n"
            f"💨 Вітер: <b>{wind} м/с</b>\n"
            f"💧 Вологість: <b>{humidity}%</b>\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"👕 <b>Порада:</b>\n"
            f"{advice}"
        )

        await send_to_group(
            bot,
            text
        )

        print(
            "🌅 Ранкова погода відправлена"
        )

    except Exception as e:

        print(
            f"❌ Помилка ранкової погоди: {e}"
        )


# ============================================================
# ПЛАНУВАЛЬНИК РАНКОВОЇ ПОГОДИ
# ============================================================

async def morning_weather_scheduler(bot: Bot):

    """
    Запускає ранкову погоду щодня
    о 08:00 за Києвом.
    """

    print(
        "🌅 Планувальник ранкової погоди запущений"
    )

    while True:

        now = datetime.now(
            KYIV_TIMEZONE
        )

        next_run = now.replace(
            hour=8,
            minute=0,
            second=0,
            microsecond=0
        )

        if next_run <= now:

            next_run += timedelta(
                days=1
            )

        wait_seconds = (
            next_run - now
        ).total_seconds()

        print(
            f"⏰ Наступна погода: "
            f"{next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await asyncio.sleep(
            wait_seconds
        )

        await send_morning_weather(
            bot
        )