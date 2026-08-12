import asyncio
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


# =====================================================
# НАЛАШТУВАННЯ
# =====================================================

GROUP_CHAT_ID = -493936504

KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")


# =====================================================
# СТАН ТРИВОГ
# =====================================================

_last_alert_states = {}


# =====================================================
# СТАН ЗАГРОЗ
# =====================================================

_last_threat_states = {}


# =====================================================
# ВІДПРАВКА В ГРУПУ
# =====================================================

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
            f"❌ Не вдалося відправити "
            f"повідомлення в групу: {e}"
        )


# =====================================================
# ОТРИМУЄМО МІСТА КОРИСТУВАЧІВ
# =====================================================

def get_users_cities():

    """
    Отримує всі унікальні міста,
    які вибрали користувачі.
    """

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

            cities.append(
                row[0]
            )

    return cities


# =====================================================
# ПЕРЕВІРКА ТРИВОГИ ДЛЯ МІСТА
# =====================================================

def is_city_alert_active(
    city,
    data
):

    """
    Перевіряє актуальний статус
    повітряної тривоги для міста.
    """

    if not data:
        return False


    # =================================================
    # КИЇВ
    # =================================================

    if city == "Київ":

        for r in data.get(
            "raions",
            []
        ):

            name = (
                r.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            oblast = (
                r.get(
                    "oblast",
                    ""
                )
                .strip()
                .lower()
            )

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


    # =================================================
    # ІНШІ МІСТА
    # =================================================

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    keywords = [
        word.lower()
        for word in keywords
    ]

    for r in data.get(
        "raions",
        []
    ):

        name = (
            r.get(
                "name",
                ""
            )
            .strip()
            .lower()
        )

        oblast = (
            r.get(
                "oblast",
                ""
            )
            .strip()
            .lower()
        )

        text = (
            f"{name} {oblast}"
        )

        if any(
            word in text
            for word in keywords
        ):

            return True

    return False


# =====================================================
# ОТРИМУЄМО ЗАГРОЗИ ДЛЯ КОНКРЕТНОГО МІСТА
# =====================================================

def get_city_threats(
    city,
    data
):

    """
    Повертає тільки ті загрози,
    які стосуються конкретного міста.
    """

    if not data:
        return []

    threats = data.get(
        "threats",
        []
    )

    if not threats:
        return []


    # =================================================
    # КЛЮЧОВІ СЛОВА МІСТА
    # =================================================

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    keywords = [
        word.lower()
        for word in keywords
    ]

    result = []


    # =================================================
    # ПЕРЕБИРАЄМО ЗАГРОЗИ
    # =================================================

    for threat in threats:

        region = (
            threat.get(
                "region",
                ""
            )
            or ""
        )

        district = (
            threat.get(
                "district",
                ""
            )
            or ""
        )

        locality = (
            threat.get(
                "locality",
                ""
            )
            or ""
        )

        title = (
            threat.get(
                "title",
                ""
            )
            or ""
        )

        explanation = (
            threat.get(
                "explanationShort",
                ""
            )
            or ""
        )

        search_text = (
            f"{region} "
            f"{district} "
            f"{locality} "
            f"{title} "
            f"{explanation}"
        ).lower()

        if any(
            word in search_text
            for word in keywords
        ):

            result.append(
                threat
            )

    return result


# =====================================================
# СТАБІЛЬНИЙ СТАН ЗАГРОЗ
# =====================================================

def get_threat_signature(
    threats
):

    """
    Створює стабільний підпис загроз.

    Порядок загроз не має значення.

    Якщо змінився:
    - текст
    - тип
    - район
    - населений пункт

    стан вважається зміненим.
    """

    signatures = []

    for threat in threats:

        signature = (
            str(
                threat.get(
                    "type",
                    ""
                )
            ),

            str(
                threat.get(
                    "title",
                    ""
                )
            ),

            str(
                threat.get(
                    "region",
                    ""
                )
            ),

            str(
                threat.get(
                    "district",
                    ""
                )
            ),

            str(
                threat.get(
                    "locality",
                    ""
                )
            ),

            str(
                threat.get(
                    "explanationShort",
                    ""
                )
            ),
        )

        signatures.append(
            signature
        )

    return tuple(
        sorted(signatures)
    )


# =====================================================
# ІКОНКА ЗАГРОЗИ
# =====================================================

def get_threat_icon(
    threat_type
):

    return {
        "uav": "🛸",
        "missile": "🚀",
        "ballistic": "💥",
        "kab": "💣",
        "mig31k": "✈️",
        "recon": "👀",
        "unknown": "❓"
    }.get(
        threat_type,
        "❓"
    )


# =====================================================
# ФОРМУЄМО ТЕКСТ ЗАГРОЗ
# =====================================================

def format_threats(
    city,
    threats
):

    if not threats:

        return (
            "🟢 <b>ЗАГРОЗ ПОБЛИЗУ НЕМАЄ</b>\n\n"
            f"📍 <b>{city}</b>"
        )

    lines = [
        f"🛰 <b>ЗАГРОЗИ ДЛЯ {city.upper()}</b>",
        ""
    ]

    for threat in threats:

        icon = get_threat_icon(
            threat.get(
                "type"
            )
        )

        title = (
            threat.get(
                "title",
                "Невідома загроза"
            )
            or "Невідома загроза"
        )

        region = (
            threat.get(
                "region",
                ""
            )
            or ""
        )

        locality = (
            threat.get(
                "locality",
                ""
            )
            or ""
        )

        explanation = (
            threat.get(
                "explanationShort",
                ""
            )
            or ""
        )

        lines.append(
            f"{icon} <b>{title}</b>"
        )

        if region:

            lines.append(
                f"📍 {region}"
            )

        if locality:

            lines.append(
                f"📌 {locality}"
            )

        if explanation:

            lines.append(
                explanation
            )

        lines.append("")

    return "\n".join(
        lines
    ).strip()


# =====================================================
# МОНІТОРИНГ ТРИВОГ + ЗАГРОЗ
# =====================================================

async def group_alert_monitor(
    bot: Bot
):

    global _last_alert_states
    global _last_threat_states

    print(
        "🚨 Моніторинг тривог та загроз "
        "для всіх міст запущений"
    )

    while True:

        try:

            # =========================================
            # ОТРИМУЄМО ТРИВОГИ
            # =========================================

            alerts_data = await asyncio.to_thread(
                get_alerts
            )


            # =========================================
            # ОТРИМУЄМО ЗАГРОЗИ
            # =========================================

            threats_data = await asyncio.to_thread(
                get_threats
            )


            # =========================================
            # ОТРИМУЄМО МІСТА
            # =========================================

            cities = get_users_cities()

            print(
                f"📍 Моніторимо міста: {cities}"
            )


            # =========================================
            # ОБРОБКА КОЖНОГО МІСТА
            # =========================================

            for city in cities:

                # =====================================
                # ТРИВОГИ
                # =====================================

                if alerts_data is not None:

                    active = is_city_alert_active(
                        city,
                        alerts_data
                    )

                    previous = _last_alert_states.get(
                        city
                    )


                    # ---------------------------------
                    # ПЕРШИЙ ЗАПУСК
                    # ---------------------------------

                    if previous is None:

                        _last_alert_states[
                            city
                        ] = active

                        print(
                            f"📡 Початковий стан "
                            f"тривоги {city}: {active}"
                        )


                    # ---------------------------------
                    # ПОЧАТОК ТРИВОГИ
                    # ---------------------------------

                    elif (
                        active
                        and not previous
                    ):

                        await send_to_group(
                            bot,

                            "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "⚠️ Негайно перейдіть "
                            "у безпечне місце."
                        )

                        _last_alert_states[
                            city
                        ] = True

                        print(
                            f"🔴 Початок тривоги: "
                            f"{city}"
                        )


                    # ---------------------------------
                    # ВІДБІЙ
                    # ---------------------------------

                    elif (
                        not active
                        and previous
                    ):

                        await send_to_group(
                            bot,

                            "🟢 <b>ВІДБІЙ "
                            "ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "✅ Небезпека минула."
                        )

                        _last_alert_states[
                            city
                        ] = False

                        print(
                            f"🟢 Відбій тривоги: "
                            f"{city}"
                        )


                # =====================================
                # ЗАГРОЗИ
                # =====================================

                if threats_data is not None:

                    city_threats = get_city_threats(
                        city,
                        threats_data
                    )

                    current_signature = (
                        get_threat_signature(
                            city_threats
                        )
                    )

                    previous_signature = (
                        _last_threat_states.get(
                            city
                        )
                    )


                    # ---------------------------------
                    # ПЕРШИЙ ЗАПУСК
                    # ---------------------------------

                    if previous_signature is None:

                        _last_threat_states[
                            city
                        ] = current_signature

                        print(
                            f"📡 Початковий стан "
                            f"загроз {city}: "
                            f"{len(city_threats)}"
                        )


                    # ---------------------------------
                    # ЗАГРОЗИ ЗМІНИЛИСЯ
                    # ---------------------------------

                    elif (
                        current_signature
                        != previous_signature
                    ):

                        # =================================
                        # ЗАГРОЗИ З'ЯВИЛИСЯ
                        # =================================

                        if (
                            not previous_signature
                            and current_signature
                        ):

                            threats_text = format_threats(
                                city,
                                city_threats
                            )

                            text = (
                                "🚨 <b>НОВІ ЗАГРОЗИ!</b>\n\n"
                                f"{threats_text}\n\n"
                                "⚠️ Будьте уважні."
                            )


                        # =================================
                        # ЗАГРОЗИ ЗНИКЛИ
                        # =================================

                        elif (
                            previous_signature
                            and not current_signature
                        ):

                            text = (
                                "🟢 <b>ЗАГРОЗ ПОБЛИЗУ "
                                "НЕМАЄ</b>\n\n"
                                f"📍 <b>{city}</b>\n\n"
                                "✅ Активних загроз "
                                "не виявлено."
                            )


                        # =================================
                        # ЗАГРОЗИ ЗМІНИЛИСЯ
                        # =================================

                        else:

                            threats_text = format_threats(
                                city,
                                city_threats
                            )

                            text = (
                                "🛰 <b>ОНОВЛЕННЯ ЗАГРОЗ</b>\n\n"
                                f"{threats_text}"
                            )


                        await send_to_group(
                            bot,
                            text
                        )

                        _last_threat_states[
                            city
                        ] = current_signature

                        print(
                            f"🛰 Загрози змінилися: "
                            f"{city} | "
                            f"кількість={len(city_threats)}"
                        )


        except Exception as e:

            print(
                f"❌ Помилка моніторингу: {e}"
            )


        # =========================================
        # ПЕРЕВІРКА КОЖНІ 60 СЕКУНД
        # =========================================

        await asyncio.sleep(
            60
        )


# =====================================================
# РАНКОВА ПОГОДА
# =====================================================

async def send_morning_weather(
    bot: Bot
):

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


# =====================================================
# ПЛАНУВАЛЬНИК РАНКОВОЇ ПОГОДИ
# =====================================================

async def morning_weather_scheduler(
    bot: Bot
):

    """
    Запускає ранкову погоду
    щодня о 06:00 за Києвом.
    """

    print(
        "🌅 Планувальник ранкової "
        "погоди запущений"
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
            "⏰ Наступна погода: "
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