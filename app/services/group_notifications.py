import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.services.alerts import get_alerts
from app.services.weather import get_weather
from app.services.advice import get_advice
from app.utils.weather_icons import get_weather_icon


GROUP_CHAT_ID = -493936504
KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

_last_alert_state = None


async def send_to_group(bot: Bot, text: str):
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
        print("✅ Повідомлення відправлено в групу")
    except Exception as e:
        print(f"❌ Не вдалося відправити повідомлення в групу: {e}")


def is_kyiv_alert_active():
    data = get_alerts()

    if not data:
        return False

    for r in data.get("raions", []):
        text = (
            f"{r.get('name', '')} "
            f"{r.get('oblast', '')}"
        ).lower()

        if "київ" in text:
            return True

    return False


async def group_alert_monitor(bot: Bot):
    global _last_alert_state

    print("🚨 Моніторинг тривоги для групи запущений")

    while True:
        try:
            active = is_kyiv_alert_active()

            if _last_alert_state is None:
                _last_alert_state = active
                print(f"📡 Початковий стан тривоги: {active}")

            elif active and not _last_alert_state:
                await send_to_group(
                    bot,
                    "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                    "📍 Київ\n\n"
                    "⚠️ Перейдіть у безпечне місце."
                )
                _last_alert_state = True

            elif not active and _last_alert_state:
                await send_to_group(
                    bot,
                    "🟢 <b>ВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                    "📍 Київ\n\n"
                    "✅ Небезпека минула."
                )
                _last_alert_state = False

        except Exception as e:
            print(f"❌ Помилка моніторингу тривоги: {e}")

        await asyncio.sleep(60)


async def send_morning_weather(bot: Bot):
    """Відправляє погоду в групу щодня о 06:00 за Києвом."""

    try:
        city_ua = "Київ"
        city_api = "Kyiv"

        weather = get_weather(city_api)

        if weather is None:
            await send_to_group(
                bot,
                "❌ Не вдалося отримати ранкову погоду для Києва."
            )
            return

        temp = weather["temp"]
        feels = weather["feels_like"]
        humidity = weather["humidity"]
        wind = weather["wind"]
        description = weather["condition"]

        icon = get_weather_icon(description)
        advice = get_advice(temp, description)

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

        await send_to_group(bot, text)
        print("🌅 Ранкова погода відправлена")

    except Exception as e:
        print(f"❌ Помилка ранкової погоди: {e}")


async def morning_weather_scheduler(bot: Bot):
    """Запускає ранкову погоду щодня о 06:00 за Києвом."""

    print("🌅 Планувальник ранкової погоди запущений")

    while True:
        now = datetime.now(KYIV_TIMEZONE)

        # Наступні 06:00
        next_run = now.replace(
            hour=6,
            minute=0,
            second=0,
            microsecond=0
        )

        if next_run <= now:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()

        print(
            f"⏰ Наступна погода: "
            f"{next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await asyncio.sleep(wait_seconds)

        await send_morning_weather(bot)