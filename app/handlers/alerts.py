import asyncio

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.services.alerts import get_alerts


router = Router()

KYIV_TZ = ZoneInfo("Europe/Kyiv")


# ============================================================
# ТОЧНИЙ РАЙОН ДЛЯ КОЖНОГО МІСТА
# ============================================================

CITY_ALERT_KEYS = {
    "Вінниця": "вінницький",
    "Луцьк": "луцький",
    "Дніпро": "дніпровський",
    "Донецьк": "донецький",
    "Житомир": "житомирський",
    "Ужгород": "ужгородський",
    "Запоріжжя": "запорізький",
    "Івано-Франківськ": "івано-франківський",
    "Кропивницький": "кропивницький",
    "Луганськ": "луганський",
    "Львів": "львівський",
    "Миколаїв": "миколаївський",
    "Одеса": "одеський",
    "Полтава": "полтавський",
    "Рівне": "рівненський",
    "Суми": "сумський",
    "Тернопіль": "тернопільський",
    "Харків": "харківський",
    "Херсон": "херсонський",
    "Хмельницький": "хмельницький",
    "Черкаси": "черкаський",
    "Чернівці": "чернівецький",
    "Чернігів": "чернігівський",
}


# ============================================================
# ОБРОБКА ЧАСУ
# ============================================================

def get_duration(since_value):

    if not since_value:
        return "невідомо", "невідомо"

    try:

        utc_time = datetime.fromisoformat(
            since_value.replace(
                "Z",
                "+00:00"
            )
        )

        local_time = utc_time.astimezone(
            KYIV_TZ
        )

        now = datetime.now(
            KYIV_TZ
        )

        duration = now - local_time

        minutes = max(
            0,
            int(
                duration.total_seconds() // 60
            )
        )

        if minutes < 60:

            duration_text = (
                f"{minutes} хв"
            )

        else:

            hours = minutes // 60
            mins = minutes % 60

            if mins:

                duration_text = (
                    f"{hours} год "
                    f"{mins} хв"
                )

            else:

                duration_text = (
                    f"{hours} год"
                )

        since = local_time.strftime(
            "%H:%M"
        )

        return (
            since,
            duration_text
        )

    except Exception as e:

        print(
            f"❌ Помилка обробки часу "
            f"тривоги: {e}"
        )

        return (
            "невідомо",
            "невідомо"
        )


# ============================================================
# ПОШУК АКТИВНОЇ ТРИВОГИ ДЛЯ МІСТА
# ============================================================

def get_city_alert(
    city,
    data
):

    if not data:
        return None


    raions = data.get(
        "raions",
        []
    )

    oblasts = data.get(
        "oblasts",
        []
    )


    # ========================================================
    # КИЇВ — ОКРЕМО
    # ========================================================

    if city == "Київ":

        for item in raions:

            key = (
                item.get(
                    "key",
                    ""
                )
                .strip()
                .lower()
            )

            name = (
                item.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            oblast = (
                item.get(
                    "oblast",
                    ""
                )
                .strip()
                .lower()
            )


            # Приймаємо тільки власне Київ

            if key in (
                "київ",
                "м. київ",
                "м-київ",
                "місто київ"
            ):

                return item


            if name in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                if oblast in (
                    "",
                    "м. київ",
                    "київ",
                    "місто київ"
                ):

                    return item


        # На випадок, якщо API повертає Київ
        # в oblasts

        for item in oblasts:

            key = (
                item.get(
                    "key",
                    ""
                )
                .strip()
                .lower()
            )

            name = (
                item.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            if key in (
                "київ",
                "м. київ",
                "м-київ",
                "місто київ"
            ):

                return item

            if name in (
                "київ",
                "м. київ",
                "місто київ"
            ):

                return item


        return None


    # ========================================================
    # ІНШІ МІСТА
    # ========================================================

    target_key = CITY_ALERT_KEYS.get(
        city
    )

    if not target_key:

        print(
            f"⚠️ Немає точного ключа "
            f"тривоги для міста: {city}"
        )

        return None


    target_key = target_key.lower()


    # Шукаємо ТІЛЬКИ точний район

    for item in raions:

        key = (
            item.get(
                "key",
                ""
            )
            .strip()
            .lower()
        )

        if key == target_key:

            print(
                f"🔴 Знайдено точну тривогу "
                f"{city}: {item}"
            )

            return item


    # Додатковий варіант через точну назву

    target_name = (
        f"{target_key} район"
    )


    for item in raions:

        name = (
            item.get(
                "name",
                ""
            )
            .strip()
            .lower()
        )

        if name == target_name:

            print(
                f"🔴 Знайдено тривогу "
                f"{city} по name: {item}"
            )

            return item


    # ========================================================
    # ОБЛАСТЬ ЯК ЗАПАСНИЙ ВАРІАНТ
    #
    # Наприклад, якщо API не має району,
    # але має активну всю область.
    # ========================================================

    city_oblasts = {
        "Вінниця": "вінницька область",
        "Луцьк": "волинська область",
        "Дніпро": "дніпропетровська область",
        "Донецьк": "донецька область",
        "Житомир": "житомирська область",
        "Ужгород": "закарпатська область",
        "Запоріжжя": "запорізька область",
        "Івано-Франківськ": "івано-франківська область",
        "Кропивницький": "кіровоградська область",
        "Луганськ": "луганська область",
        "Львів": "львівська область",
        "Миколаїв": "миколаївська область",
        "Одеса": "одеська область",
        "Полтава": "полтавська область",
        "Рівне": "рівненська область",
        "Суми": "сумська область",
        "Тернопіль": "тернопільська область",
        "Харків": "харківська область",
        "Херсон": "херсонська область",
        "Хмельницький": "хмельницька область",
        "Черкаси": "черкаська область",
        "Чернівці": "чернівецька область",
        "Чернігів": "чернігівська область",
    }


    target_oblast = city_oblasts.get(
        city
    )


    if target_oblast:

        for item in oblasts:

            name = (
                item.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            oblast = (
                item.get(
                    "oblast",
                    ""
                )
                .strip()
                .lower()
            )

            if (
                name == target_oblast
                or oblast == target_oblast
            ):

                print(
                    f"🔴 Знайдено активну "
                    f"область для {city}: "
                    f"{item}"
                )

                return item


    return None


# ============================================================
# КНОПКА ТРИВОГИ
# ============================================================

@router.message(
    lambda message:
    message.text == "🚨 Тривоги"
)
async def alerts(
    message: Message
):

    user_id = (
        message.from_user.id
    )


    city = await asyncio.to_thread(
        get_city,
        user_id
    )


    print(
        f"🚨 Перевірка тривоги | "
        f"user_id={user_id} | "
        f"city={city}"
    )


    # ========================================================
    # API
    # ========================================================

    data = await asyncio.to_thread(
        get_alerts
    )


    if data is None:

        await message.answer(
            "❌ Не вдалося отримати "
            "актуальну інформацію "
            "про тривоги."
        )

        return


    print(
        f"🚨 API | "
        f"raions="
        f"{len(data.get('raions', []))} | "
        f"oblasts="
        f"{len(data.get('oblasts', []))}"
    )


    # ========================================================
    # ШУКАЄМО ТОЧНИЙ ЗАПИС
    # ========================================================

    region_alert = get_city_alert(
        city,
        data
    )


    # ========================================================
    # АКТИВНА ТРИВОГА
    # ========================================================

    if region_alert:

        since_value = region_alert.get(
            "since"
        )


        since, duration_text = (
            get_duration(
                since_value
            )
        )


        text = (
            "🚨 <b>Повітряна тривога</b>\n\n"
            f"📍 <b>{city}</b>\n\n"
            "🔴 Статус: <b>Активна</b>\n"
            f"🕒 Початок: <b>{since}</b>\n"
            f"⏱ Триває: "
            f"<b>{duration_text}</b>\n\n"
            "⚠️ Будьте в безпечному місці."
        )


    # ========================================================
    # ТРИВОГИ НЕМАЄ
    # ========================================================

    else:

        print(
            f"🟢 Активної тривоги "
            f"не знайдено | "
            f"city={city}"
        )


        text = (
            f"🟢 <b>{city}</b>\n\n"
            "✅ Повітряної тривоги немає\n\n"
            "🛡 Залишайтеся уважними."
        )


    await message.answer(
        text,
        parse_mode="HTML"
    )