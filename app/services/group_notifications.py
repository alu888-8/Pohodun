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

# Перевірка кожні 10 секунд
CHECK_INTERVAL = 10


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
            f"❌ Помилка відправки в групу: {e}"
        )


# =====================================================
# МІСТА КОРИСТУВАЧІВ
# =====================================================

def get_users_cities():

    try:

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

    except Exception as e:

        print(
            f"❌ Помилка отримання міст: {e}"
        )

        return []


# =====================================================
# НОРМАЛІЗАЦІЯ ТЕКСТУ
# =====================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip().lower()


# =====================================================
# ПЕРЕВІРКА ТРИВОГИ ДЛЯ МІСТА
# =====================================================

def is_city_alert_active(
    city,
    data
):

    """
    Перевіряє саме статус тривоги міста.

    Київ і Київська область
    розглядаються окремо.
    """

    if not data:

        return False


    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )


    # =================================================
    # КИЇВ
    # =================================================

    if city == "Київ":

        for item in raions + oblasts:

            name = normalize(
                item.get("name")
            )

            key = normalize(
                item.get("key")
            )

            oblast = normalize(
                item.get("oblast")
            )


            # Сам Київ

            if name in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                return True


            if key in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                return True


            # Київський район,
            # якщо API повертає його саме як
            # частину міста Київ

            if (
                name == "київський район"
                and oblast == "м. київ"
            ):

                return True


        return False


    # =================================================
    # ІНШІ МІСТА
    # =================================================

    city_normalized = normalize(
        city
    )


    # Спочатку шукаємо точну назву міста

    for item in raions + oblasts:

        name = normalize(
            item.get("name")
        )

        key = normalize(
            item.get("key")
        )


        if name in (
            city_normalized,
            f"м. {city_normalized}",
            f"місто {city_normalized}"
        ):

            return True


        if key in (
            city_normalized,
            f"м. {city_normalized}"
        ):

            return True


    # =================================================
    # ПОШУК ЧЕРЕЗ CITY_REGIONS
    # =================================================

    keywords = CITY_REGIONS.get(
        city,
        [city_normalized]
    )


    keywords = [
        normalize(word)
        for word in keywords
    ]


    for item in raions:

        name = normalize(
            item.get("name")
        )

        oblast = normalize(
            item.get("oblast")
        )


        search_text = (
            f"{name} {oblast}"
        )


        if any(
            word in search_text
            for word in keywords
            if word
        ):

            return True


    return False


# =====================================================
# ОТРИМАТИ ЗАГРОЗИ ДЛЯ МІСТА
# =====================================================

def get_city_threats(
    city,
    data
):

    if not data:

        return []


    threats = data.get(
        "threats",
        []
    )


    if not threats:

        return []


    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )


    keywords = [
        normalize(word)
        for word in keywords
    ]


    # Для Києва додаємо явні варіанти

    if city == "Київ":

        keywords = list(
            set(
                keywords
                + [
                    "київ",
                    "м. київ"
                ]
            )
        )


    result = []


    for threat in threats:

        region = normalize(
            threat.get("region")
        )

        district = normalize(
            threat.get("district")
        )

        locality = normalize(
            threat.get("locality")
        )

        title = normalize(
            threat.get("title")
        )

        explanation = normalize(
            threat.get("explanationShort")
        )


        search_text = (
            f"{region} "
            f"{district} "
            f"{locality} "
            f"{title} "
            f"{explanation}"
        )


        if any(
            word in search_text
            for word in keywords
            if word
        ):

            result.append(
                threat
            )


    return result


# =====================================================
# ПІДПИС ЗАГРОЗ
# =====================================================

def get_threat_signature(
    threats
):

    signatures = []


    for threat in threats:

        signature = (

            normalize(
                threat.get("type")
            ),

            normalize(
                threat.get("title")
            ),

            normalize(
                threat.get("region")
            ),

            normalize(
                threat.get("district")
            ),

            normalize(
                threat.get("locality")
            ),

            normalize(
                threat.get("explanationShort")
            ),

            normalize(
                threat.get("confirmed")
            )

        )

        signatures.append(
            signature
        )


    signatures.sort()


    return tuple(
        signatures
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
# ФОРМУВАННЯ ПОВІДОМЛЕННЯ ЗАГРОЗ
# =====================================================

def format_threats(
    city,
    threats
):

    if not threats:

        return (
            f"🛰 <b>ЗАГРОЗИ — {city}</b>\n\n"
            "🟢 Активних загроз не виявлено."
        )


    lines = [

        f"🛰 <b>ЗАГРОЗИ — {city}</b>",

        ""

    ]


    for threat in threats:

        icon = get_threat_icon(
            threat.get("type")
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


        if district:

            lines.append(
                f"📌 {district}"
            )


        if locality:

            lines.append(
                f"📍 {locality}"
            )


        if explanation:

            lines.append(
                str(explanation)
            )


        lines.append("")


    return "\n".join(
        lines
    ).strip()


# =====================================================
# МОНІТОРИНГ ТРИВОГ І ЗАГРОЗ
# =====================================================

async def group_alert_monitor(
    bot: Bot
):

    print(
        "🚨 Моніторинг тривог та загроз "
        "запущений"
    )


    while True:

        try:

            # =================================================
            # ОТРИМУЄМО ТРИВОГИ
            # =================================================

            alerts_data = await asyncio.to_thread(
                get_alerts
            )


            # =================================================
            # ОТРИМУЄМО ЗАГРОЗИ
            # =================================================

            threats_data = await asyncio.to_thread(
                get_threats
            )


            # =================================================
            # МІСТА
            # =================================================

            cities = get_users_cities()


            print(
                f"📍 Моніторимо міста: {cities}"
            )


            # =================================================
            # ОБРОБКА КОЖНОГО МІСТА
            # =================================================

            for city in cities:

                # =================================================
                # ТРИВОГА
                # =================================================

                if alerts_data is not None:

                    alert_active = (
                        is_city_alert_active(
                            city,
                            alerts_data
                        )
                    )


                    previous_alert = (
                        _last_alert_states.get(
                            city
                        )
                    )


                    # =============================================
                    # ПЕРШИЙ ЗАПУСК
                    # =============================================

                    if previous_alert is None:

                        _last_alert_states[
                            city
                        ] = alert_active


                        print(
                            f"📡 Початковий стан "
                            f"{city}: "
                            f"тривога={alert_active}"
                        )

                    else:

                        # =========================================
                        # ПОЧАТОК ТРИВОГИ
                        # =========================================

                        if (
                            alert_active
                            and not previous_alert
                        ):

                            await send_to_group(
                                bot,

                                "🚨 <b>ПОВІТРЯНА ТРИВОГА</b>\n\n"
                                f"📍 <b>{city}</b>\n\n"
                                "⚠️ Негайно перейдіть "
                                "у безпечне місце."
                            )


                            _last_alert_states[
                                city
                            ] = True


                            print(
                                f"🚨 Почалася тривога: "
                                f"{city}"
                            )


                            # =========================================
                            # ОДРАЗУ ПІСЛЯ ПОЧАТКУ ТРИВОГИ
                            # ПОКАЗУЄМО АКТУАЛЬНІ ЗАГРОЗИ
                            # =========================================

                            if threats_data is not None:

                                city_threats = (
                                    get_city_threats(
                                        city,
                                        threats_data
                                    )
                                )


                                signature = (
                                    get_threat_signature(
                                        city_threats
                                    )
                                )


                                _last_threat_states[
                                    city
                                ] = signature


                                if city_threats:

                                    threats_text = (
                                        format_threats(
                                            city,
                                            city_threats
                                        )
                                    )


                                    await send_to_group(
                                        bot,

                                        "🛰 <b>АКТУАЛЬНІ ЗАГРОЗИ</b>\n\n"
                                        f"{threats_text}"
                                    )


                                    print(
                                        f"🛰 Актуальні загрози "
                                        f"відправлено: "
                                        f"{city}"
                                    )


                        # =========================================
                        # ВІДБІЙ ТРИВОГИ
                        # =========================================

                        elif (
                            not alert_active
                            and previous_alert
                        ):

                            await send_to_group(
                                bot,

                                "🟢 <b>ВІДБІЙ</b>\n"
                                f"📍 <b>{city}</b>"
                            )


                            _last_alert_states[
                                city
                            ] = False


                            # Після відбою
                            # старі загрози більше не мають значення

                            _last_threat_states.pop(
                                city,
                                None
                            )


                            print(
                                f"🟢 Відбій: "
                                f"{city}"
                            )


                # =================================================
                # МОНІТОРИНГ ЗАГРОЗ
                #
                # ПРАЦЮЄ ТІЛЬКИ ПРИ АКТИВНІЙ ТРИВОЗІ
                # =================================================

                if (
                    threats_data is not None
                    and alerts_data is not None
                    and _last_alert_states.get(
                        city,
                        False
                    )
                ):

                    city_threats = (
                        get_city_threats(
                            city,
                            threats_data
                        )
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


                    # =================================================
                    # ПЕРШИЙ СТАН ЗАГРОЗ
                    # =================================================

                    if previous_signature is None:

                        _last_threat_states[
                            city
                        ] = current_signature


                        print(
                            f"📡 Початковий стан "
                            f"загроз {city}: "
                            f"{len(city_threats)}"
                        )


                    # =================================================
                    # ЗАГРОЗИ ЗМІНИЛИСЯ
                    # =================================================

                    elif (
                        current_signature
                        != previous_signature
                    ):

                        # =============================================
                        # З'ЯВИЛИСЯ НОВІ ЗАГРОЗИ
                        # =============================================

                        if (
                            not previous_signature
                            and current_signature
                        ):

                            threats_text = (
                                format_threats(
                                    city,
                                    city_threats
                                )
                            )


                            text = (
                                "🛰 <b>НОВІ ЗАГРОЗИ</b>\n\n"
                                f"{threats_text}"
                            )


                            await send_to_group(
                                bot,
                                text
                            )


                            print(
                                f"🛰 Нові загрози: "
                                f"{city}"
                            )


                        # =============================================
                        # ВСІ ЗАГРОЗИ ЗНИКЛИ
                        #
                        # АЛЕ ТРИВОГА ЩЕ АКТИВНА
                        # ТОМУ ЦЕ НЕ ВІДБІЙ
                        # =============================================

                        elif (
                            previous_signature
                            and not current_signature
                        ):

                            text = (
                                "🛰 <b>ОНОВЛЕННЯ ЗАГРОЗ</b>\n\n"
                                f"📍 <b>{city}</b>\n\n"
                                "🟢 Активних загроз "
                                "не виявлено.\n\n"
                                "🚨 Повітряна тривога "
                                "ще триває."
                            )


                            await send_to_group(
                                bot,
                                text
                            )


                            print(
                                f"🟢 Загрози зникли, "
                                f"але тривога ще активна: "
                                f"{city}"
                            )


                        # =============================================
                        # ЗМІНИВСЯ СПИСОК ЗАГРОЗ
                        # =============================================

                        else:

                            threats_text = (
                                format_threats(
                                    city,
                                    city_threats
                                )
                            )


                            text = (
                                "🛰 <b>ОНОВЛЕННЯ ЗАГРОЗ</b>\n\n"
                                f"{threats_text}"
                            )


                            await send_to_group(
                                bot,
                                text
                            )


                            print(
                                f"🔄 Загрози змінилися: "
                                f"{city}"
                            )


                        _last_threat_states[
                            city
                        ] = current_signature


        except Exception as e:

            print(
                f"❌ Помилка моніторингу: {e}"
            )


        # =================================================
        # ЧЕКАЄМО 10 СЕКУНД
        # =================================================

        await asyncio.sleep(
            CHECK_INTERVAL
        )


# =====================================================
# РАНКОВА ПОГОДА
# =====================================================

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
    щодня о 08:00 за Києвом.
    """

    print(
        "🌅 Планувальник ранкової "
        "погоди запущений"
    )


    while True:

        now = datetime.now(
            KYIV_TIMEZONE
        )


        # =================================================
        # 08:00
        # =================================================

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