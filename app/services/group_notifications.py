import asyncio
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.services.alerts import get_alerts
from app.services.weather import get_weather
from app.services.advice import get_advice

from app.utils.weather_icons import get_weather_icon
from app.data.regions import CITY_REGIONS


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

GROUP_CHAT_ID = -493936504

KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

# Перевіряємо стан тривог кожні 15 секунд
MONITOR_INTERVAL = 15


# ============================================================
# СТАН ТРИВОГ ПО МІСТАХ
# ============================================================

# Приклад:
#
# {
#     "Київ": True,
#     "Одеса": False,
#     "Львів": False
# }

_city_alert_states = {}


# ============================================================
# ВІДПРАВКА ПОВІДОМЛЕННЯ В ГРУПУ
# ============================================================

async def send_to_group(
    bot: Bot,
    text: str
):

    try:

        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )

        print(
            "✅ Повідомлення відправлено в групу"
        )

    except Exception as e:

        print(
            f"❌ Помилка відправки повідомлення "
            f"в групу: {e}"
        )


# ============================================================
# МІСТА КОРИСТУВАЧІВ
# ============================================================

def get_users_cities():

    """
    Отримує всі унікальні міста,
    які зараз вибрали користувачі.

    Наприклад:

    Користувач 1 -> Київ
    Користувач 2 -> Одеса
    Користувач 3 -> Київ

    Результат:

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
            f"❌ Помилка отримання міст: {e}"
        )

        return []


# ============================================================
# НОРМАЛІЗАЦІЯ
# ============================================================

def normalize_text(value):

    if value is None:

        return ""

    return str(
        value
    ).strip().lower()


# ============================================================
# ПОШУК ТРИВОГИ ДЛЯ МІСТА
# ============================================================

def get_city_alert_item(
    city,
    data
):

    """
    Повертає запис API, який відповідає місту.

    Київ окремо від Київської області.
    """

    if not data:

        return None


    city_normalized = normalize_text(
        city
    )


    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )

    items = (
        raions
        + oblasts
    )


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

            key = normalize_text(
                item.get("key")
            )

            oblast = normalize_text(
                item.get("oblast")
            )


            # Саме місто Київ

            if name in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                if oblast in (
                    "",
                    "київ",
                    "м. київ",
                    "місто київ"
                ):

                    return item


            # Точний key Києва

            if key in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                return item


            # Якщо API віддає Київський район
            # саме для м. Києва

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
        normalize_text(
            word
        )
        for word in keywords
        if word
    ]


    for item in items:

        name = normalize_text(
            item.get("name")
        )

        key = normalize_text(
            item.get("key")
        )

        oblast = normalize_text(
            item.get("oblast")
        )


        search_text = (
            f"{name} "
            f"{oblast} "
            f"{key}"
        )


        for word in keywords:

            if (
                word
                and word in search_text
            ):

                return item


    return None


# ============================================================
# ПЕРЕВІРКА СТАНУ ТРИВОГИ
# ============================================================

def is_city_alert_active(
    city,
    data
):

    item = get_city_alert_item(
        city,
        data
    )

    if item is None:

        return False

    return True


# ============================================================
# ОЧИЩЕННЯ СТАРИХ МІСТ
# ============================================================

def cleanup_old_cities(
    active_cities
):

    """
    Якщо місто більше не вибране
    жодним користувачем — забираємо
    його з пам'яті монітора.
    """

    active_set = set(
        active_cities
    )


    old_cities = list(
        _city_alert_states.keys()
    )


    for city in old_cities:

        if city not in active_set:

            del _city_alert_states[
                city
            ]

            print(
                f"🗑 Прибрано місто "
                f"з моніторингу: {city}"
            )


# ============================================================
# МОНІТОРИНГ ПОЧАТКУ / ВІДБОЮ
# ============================================================

async def group_alert_monitor(
    bot: Bot
):

    print(
        "🚨 Моніторинг початку "
        "та відбою тривог запущений"
    )

    print(
        f"⏱ Інтервал перевірки: "
        f"{MONITOR_INTERVAL} секунд"
    )


    while True:

        try:

            # ====================================================
            # ОТРИМУЄМО ПОТОЧНІ МІСТА
            # ====================================================

            cities = await asyncio.to_thread(
                get_users_cities
            )


            print(
                f"📍 Міста для моніторингу: "
                f"{cities}"
            )


            if not cities:

                print(
                    "ℹ️ Немає міст "
                    "для моніторингу"
                )

                await asyncio.sleep(
                    MONITOR_INTERVAL
                )

                continue


            # Видаляємо міста,
            # які більше ніхто не вибирає

            cleanup_old_cities(
                cities
            )


            # ====================================================
            # ОДИН ЗАПИТ ДО API ТРИВОГ
            # ====================================================

            alerts_data = await asyncio.to_thread(
                get_alerts
            )


            if alerts_data is None:

                print(
                    "⚠️ Не вдалося отримати "
                    "актуальні дані тривог"
                )

                await asyncio.sleep(
                    MONITOR_INTERVAL
                )

                continue


            # ====================================================
            # ПЕРЕВІРЯЄМО КОЖНЕ МІСТО
            # ====================================================

            for city in cities:

                try:

                    # Якщо місто бачимо вперше

                    if city not in _city_alert_states:

                        active = is_city_alert_active(
                            city,
                            alerts_data
                        )


                        _city_alert_states[
                            city
                        ] = active


                        print(
                            f"📡 Початковий стан "
                            f"{city}: "
                            f"тривога={active}"
                        )


                        # Важливо:
                        # при першому запуску НЕ відправляємо
                        # повідомлення в групу.

                        continue


                    previous = (
                        _city_alert_states[
                            city
                        ]
                    )


                    active = is_city_alert_active(
                        city,
                        alerts_data
                    )


                    # =================================================
                    # НЕМАЄ ЗМІН
                    # =================================================

                    if active == previous:

                        continue


                    # =================================================
                    # ПОЧАТОК ТРИВОГИ
                    # =================================================

                    if (
                        active
                        and not previous
                    ):

                        await send_to_group(
                            bot,

                            "🚨 <b>ПОВІТРЯНА ТРИВОГА</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "⚠️ Негайно перейдіть "
                            "у безпечне місце."
                        )


                        _city_alert_states[
                            city
                        ] = True


                        print(
                            f"🚨 Початок тривоги: "
                            f"{city}"
                        )


                    # =================================================
                    # ВІДБІЙ
                    # =================================================

                    elif (
                        not active
                        and previous
                    ):

                        await send_to_group(
                            bot,

                            "🟢 <b>ВІДБІЙ</b>\n"
                            f"📍 <b>{city}</b>"
                        )


                        _city_alert_states[
                            city
                        ] = False


                        print(
                            f"🟢 Відбій тривоги: "
                            f"{city}"
                        )


                except Exception as city_error:

                    print(
                        f"❌ Помилка моніторингу "
                        f"{city}: {city_error}"
                    )


        except Exception as e:

            print(
                f"❌ Помилка моніторингу "
                f"тривог: {e}"
            )


        # ====================================================
        # НАСТУПНА ПЕРЕВІРКА
        # ====================================================

        await asyncio.sleep(
            MONITOR_INTERVAL
        )


# ============================================================
# РАНКОВА ПОГОДА
# ============================================================

async def send_morning_weather(
    bot: Bot
):

    """
    Відправляє ранкову погоду
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

            print(
                "❌ Не вдалося отримати "
                "ранкову погоду для Києва"
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
            "🌅 Ранкова погода "
            "відправлена"
        )


    except Exception as e:

        print(
            f"❌ Помилка ранкової погоди: {e}"
        )


# ============================================================
# ПЛАНУВАЛЬНИК РАНКОВОЇ ПОГОДИ
# ============================================================

async def morning_weather_scheduler(
    bot: Bot
):

    """
    Ранкова погода щодня о 08:00
    за київським часом.
    """

    print(
        "🌅 Планувальник ранкової "
        "погоди запущений"
    )


    while True:

        try:

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
                "⏰ Наступна ранкова погода: "
                + next_run.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )


            await asyncio.sleep(
                wait_seconds
            )


            await send_morning_weather(
                bot
            )

        except Exception as e:

            print(
                f"❌ Помилка планувальника "
                f"ранкової погоди: {e}"
            )

            # Якщо сталася помилка,
            # не вбиваємо планувальник.

            await asyncio.sleep(
                60
            )