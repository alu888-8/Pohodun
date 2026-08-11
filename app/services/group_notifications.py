import asyncio

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.services.alerts import get_alerts
from app.services.weather import get_weather
from app.services.advice import get_advice
from app.utils.weather_icons import get_weather_icon
from app.data.regions import CITY_REGIONS


GROUP_CHAT_ID = -493936504
KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

# Стан тривоги для кожного міста
_last_alert_states = {}


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


def get_users_cities():
    """
    Отримує всі унікальні міста,
    які вибрали користувачі.
    """

    import sqlite3

    conn = sqlite3.connect(
        "app/database/users.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT city FROM users"
    )

    rows = cursor.fetchall()

    conn.close()

    cities = []

    for row in rows:
        if row[0]:
            cities.append(row[0])

    return cities


def is_city_alert_active(city, data):
    """
    Перевіряє актуальний статус тривоги
    для конкретного міста.
    """

    if not data:
        return False

    # ==========================================
    # КИЇВ
    # ==========================================

    if city == "Київ":

        for r in data.get("raions", []):

            name = r.get(
                "name",
                ""
            ).strip().lower()

            oblast = r.get(
                "oblast",
                ""
            ).strip().lower()

            if name in (
                "м. київ",
                "київ"
            ):

                if oblast in (
                    "",
                    "м. київ",
                    "київ"
                ):
                    return True

            if (
                name == "київський район"
                and oblast == "м. київ"
            ):
                return True

        return False

    # ==========================================
    # ІНШІ МІСТА
    # ==========================================

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    for r in data.get("raions", []):

        name = r.get(
            "name",
            ""
        ).strip().lower()

        oblast = r.get(
            "oblast",
            ""
        ).strip().lower()

        text = f"{name} {oblast}"

        if any(
            word.lower() in text
            for word in keywords
        ):
            return True

    return False


async def group_alert_monitor(bot: Bot):

    global _last_alert_states

    print(
        "🚨 Моніторинг тривог для всіх міст запущений"
    )

    while True:

        try:

            # Отримуємо актуальні дані API
            # в окремому потоці, щоб не блокувати бота
            data = await asyncio.to_thread(
                get_alerts
            )

            if data is None:

                print(
                    "⚠️ Не вдалося отримати "
                    "актуальні дані про тривоги"
                )

            else:

                cities = get_users_cities()

                print(
                    f"📍 Моніторимо міста: {cities}"
                )

                for city in cities:

                    active = is_city_alert_active(
                        city,
                        data
                    )

                    previous = _last_alert_states.get(
                        city
                    )

                    # ==================================
                    # ПЕРШИЙ ЗАПУСК
                    # ==================================

                    if previous is None:

                        _last_alert_states[city] = active

                        print(
                            f"📡 Початковий стан "
                            f"{city}: {active}"
                        )

                        continue

                    # ==================================
                    # ПОЧАТОК ТРИВОГИ
                    # ==================================

                    if active and not previous:

                        await send_to_group(
                            bot,

                            "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "⚠️ Негайно перейдіть "
                            "у безпечне місце."
                        )

                        _last_alert_states[city] = True

                    # ==================================
                    # ВІДБІЙ
                    # ==================================

                    elif not active and previous:

                        await send_to_group(
                            bot,

                            "🟢 <b>ВІДБІЙ "
                            "ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "✅ Небезпека минула."
                        )

                        _last_alert_states[city] = False

        except Exception as e:

            print(
                f"❌ Помилка моніторингу тривог: {e}"
            )

        # Перевірка кожні 60 секунд
        await asyncio.sleep(60)


async def send_morning_weather(bot: Bot):

    """
    Відправляє погоду в групу
    щодня о 06:00 за Києвом.
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

        icon = get_weather_icon(description)

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


async def morning_weather_scheduler(bot: Bot):

    """
    Запускає ранкову погоду щодня
    о 06:00 за Києвом.
    """

    print(
        "🌅 Планувальник ранкової погоди запущений"
    )

    while True:

        now = datetime.now(
            KYIV_TIMEZONE
        )

        next_run = now.replace(
            hour=6,
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