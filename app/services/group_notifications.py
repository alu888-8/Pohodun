from aiogram import Bot


GROUP_CHAT_ID = -493936504


async def send_to_group(bot: Bot, text: str):
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text
        )
        print("✅ Повідомлення відправлено в групу")
    except Exception as e:
        print(f"❌ Не вдалося відправити повідомлення в групу: {e}")