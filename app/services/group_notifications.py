import asyncio

from aiogram import Bot

from app.services.alerts import get_alerts
from app.data.regions import CITY_REGIONS


GROUP_CHAT_ID = -493936504

# Останній стан тривоги
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

    keywords = CITY_REGIONS.get("Київ", ["київ"])

    for r in data.get("raions", []):
        text = (
            f"{r.get('name', '')} "
            f"{r.get('oblast', '')}"
        ).lower()

        if any(word in text for word in keywords):
            return True

    return False


async def group_alert_monitor(bot: Bot):
    global _last_alert_state

    print("🚨 Моніторинг тривоги для групи запущений")

    while True:
        try:
            active = is_kyiv_alert_active()

            # Перша перевірка — просто запам'ятовуємо стан
            if _last_alert_state is None:
                _last_alert_state = active
                print(f"📡 Початковий стан тривоги: {active}")

            # Тривога почалась
            elif active and not _last_alert_state:
                await send_to_group(
                    bot,
                    "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                    "📍 Київ\n\n"
                    "⚠️ Перейдіть у безпечне місце."
                )
                _last_alert_state = True

            # Тривога закінчилась
            elif not active and _last_alert_state:
                await send_to_group(
                    bot,
                    "🟢 <b>ВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                    "📍 Київ\n\n"
                    "✅ Небезпека минула."
                )
                _last_alert_state = False

        except Exception as e:
            print(f"❌ Помилка моніторингу: {e}")

        # Перевірка кожні 60 секунд
        await asyncio.sleep(60)