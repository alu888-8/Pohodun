import asyncio

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.ai_chat import ask_ai

from app.database.db import (
    get_city,
    get_location,
)

from app.services.alerts import (
    get_alerts,
)

from app.services.threats import (
    get_threats,
)

from app.handlers.threats import (
    find_nearby_threats,
    get_city_alert_status,
    get_city_oblast,
    get_active_oblast_raions,
    format_threat,
    THREAT_RADIUS_KM,
)


router = Router()


# =====================================================
# AI CHAT STATE
# =====================================================

class AIChatState(StatesGroup):

    chatting = State()


# =====================================================
# ВИЗНАЧЕННЯ ПИТАННЯ ПРО ЗАГРОЗИ
# =====================================================

def is_threat_question(
    text: str,
) -> bool:

    text = (
        text or ""
    ).strip().lower()

    if not text:
        return False

    threat_words = (
        "загроз",
        "загроза",
        "загрози",
        "шахед",
        "шахеди",
        "шахедів",
        "бпла",
        "дрон",
        "дрони",
        "дронів",
        "ракета",
        "ракети",
        "ракет",
        "балістика",
        "балістич",
        "каб",
        "каби",
        "кабів",
        "авіа",
        "авіаці",
        "літак",
        "літаки",
        "пуск",
        "пуски",
        "ціль",
        "цілі",
        "цілей",
    )

    alert_words = (
        "тривог",
        "тривога",
        "тривоги",
        "небезпек",
        "небезпечно",
        "небезпека",
        "зараз летить",
        "щось летить",
        "летить",
        "летять",
        "що летить",
        "що зараз",
        "що сьогодні",
    )

    return any(
        word in text
        for word in threat_words + alert_words
    )


# =====================================================
# ФОРМУВАННЯ АКТУАЛЬНИХ ЗАГРОЗ
#
# Використовуємо той самий механізм,
# що й кнопка 🛰 Загрози.
# =====================================================

async def get_threats_for_ai(
    user_id: int,
) -> str:

    # =================================================
    # ЛОКАЦІЯ
    # =================================================

    location = get_location(
        user_id
    )

    # Старий формат локації
    if not location:

        city = get_city(
            user_id
        )

        if city:

            location = {
                "key": city.lower(),
                "name": city,
            }

    print(
        f"🤖 AI THREATS | "
        f"user_id={user_id} | "
        f"location={location}"
    )

    if not location:

        return (
            "❌ Спочатку оберіть "
            "свою локацію в налаштуваннях."
        )

    city = (
        location.get("name")
        or get_city(user_id)
    )

    if not city:

        return (
            "❌ Не вдалося визначити "
            "вашу локацію."
        )

    # =================================================
    # API
    # =================================================

    threats_api = (
        await asyncio.to_thread(
            get_threats
        )
    )

    alerts_api = (
        await asyncio.to_thread(
            get_alerts
        )
    )

    # =================================================
    # ТРИВОГА В МОЇЙ ЛОКАЦІЇ
    # =================================================

    city_alert = (
        get_city_alert_status(
            city,
            alerts_api,
            location=location,
        )
    )

    # =================================================
    # ОБЛАСТЬ
    # =================================================

    city_oblast = get_city_oblast(
        city,
        location,
    )

    # =================================================
    # АКТИВНІ РАЙОНИ ОБЛАСТІ
    # =================================================

    active_oblast_raions = (
        get_active_oblast_raions(
            city_oblast,
            alerts_api,
        )
        if city_oblast
        else []
    )

    # =================================================
    # КОНКРЕТНІ ЗАГРОЗИ
    # =================================================

    threats_data = (
        threats_api.get(
            "threats",
            [],
        )
        if threats_api
        else []
    )

    nearby_threats = (
        find_nearby_threats(
            location,
            threats_data,
        )
    )

    print(
        f"🤖 AI THREATS STATUS | "
        f"city={city} | "
        f"city_alert={city_alert} | "
        f"oblast={city_oblast} | "
        f"active_raions="
        f"{len(active_oblast_raions)} | "
        f"nearby="
        f"{len(nearby_threats)}"
    )

    # =================================================
    # ТЕКСТ
    # =================================================

    text = (
        "🛰 <b>СТАН БЕЗПЕКИ</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
    )

    # =================================================
    # МОЯ ЛОКАЦІЯ
    # =================================================

    text += (
        "🚨 <b>МОЯ ЛОКАЦІЯ</b>\n"
    )

    if city_alert:

        text += (
            "🔴 Повітряна тривога: "
            "<b>АКТИВНА</b>\n\n"
        )

    else:

        text += (
            "🟢 Повітряної тривоги "
            "<b>НЕМАЄ</b>\n\n"
        )

    # =================================================
    # ОБЛАСТЬ
    # =================================================

    if city_oblast:

        text += (
            f"🗺 <b>"
            f"{city_oblast.upper()}"
            f"</b>\n"
        )

        if active_oblast_raions:

            text += (
                "🔴 У частині області "
                "<b>АКТИВНА ТРИВОГА</b>\n\n"
            )

            text += (
                "📍 <b>Активні райони:</b>\n"
            )

            for item in active_oblast_raions:

                text += (
                    f"• "
                    f"{item.get('name', 'Невідомий район')}"
                    f"\n"
                )

            text += "\n"

        else:

            text += (
                "🟢 Активної тривоги "
                "в області не виявлено.\n\n"
            )

    # =================================================
    # КОНКРЕТНІ ЗАГРОЗИ ПОБЛИЗУ
    # =================================================

    text += (
        "📡 <b>КОНКРЕТНІ ЗАГРОЗИ "
        "ПОБЛИЗУ</b>\n"
    )

    if nearby_threats:

        text += "\n"

        for item in nearby_threats:

            text += (
                format_threat(
                    item
                )
                + "\n\n"
            )

        text = text.rstrip()

    else:

        text += (
            "🟢 Конкретних активних "
            "загроз у радіусі "
            f"{THREAT_RADIUS_KM} км "
            "не виявлено."
        )

    # =================================================
    # ПОЯСНЕННЯ
    # =================================================

    if (
        not city_alert
        and active_oblast_raions
    ):

        text += (
            "\n\nℹ️ <b>Важливо:</b> "
            "тривога в іншому районі "
            "області не означає автоматично "
            f"тривогу в місті {city}."
        )

    # =================================================
    # ФІНАЛ
    # =================================================

    if city_alert:

        text += (
            "\n\n⚠️ <b>Перебувайте "
            "в безпечному місці.</b>"
        )

    elif nearby_threats:

        text += (
            "\n\n🟡 <b>Поблизу є "
            "конкретна активна загроза.</b>\n"
            "Слідкуйте за офіційними "
            "повідомленнями."
        )

    elif active_oblast_raions:

        text += (
            "\n\n🟡 <b>У вашій області "
            "є активна тривога в іншому "
            "районі.</b>\n"
            "Слідкуйте за офіційними "
            "повідомленнями."
        )

    else:

        text += (
            "\n\n🛡 <b>Залишайтеся "
            "уважними.</b>"
        )

    return text


# =====================================================
# ПОЧАТОК AI ЧАТУ
# =====================================================

@router.message(
    lambda message:
    message.text == "🤖 Поговорити з Pohodun"
)
async def start_ai_chat(
    message: Message,
    state: FSMContext,
):

    await state.set_state(
        AIChatState.chatting
    )

    await message.answer(
        "🤖 <b>Pohodun AI</b>\n\n"
        "Питай мене що завгодно 👇\n\n"
        "Якщо запитаєш про актуальні "
        "тривоги або загрози — "
        "я перевірю дані автоматично.\n\n"
        "Щоб вийти з AI-чату, натисни "
        "«⬅️ Назад».",
        parse_mode="HTML",
    )


# =====================================================
# ВИХІД З AI
# =====================================================

@router.message(
    AIChatState.chatting,
    lambda message:
    message.text == "⬅️ Назад"
)
async def exit_ai_chat(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    from app.keyboards.menu import (
        get_main_menu,
    )

    await message.answer(
        "🏠 <b>Головне меню</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu(
            message.from_user.id,
            message.chat.type,
        ),
    )


# =====================================================
# ПИТАННЯ ДО AI
# =====================================================

@router.message(
    AIChatState.chatting
)
async def ask_pohodun_ai(
    message: Message,
):

    question = (
        message.text or ""
    ).strip()

    if not question:
        return

    user_id = (
        message.from_user.id
    )

    print(
        f"🤖 AI CHAT | "
        f"user_id={user_id} | "
        f"question={question}"
    )

    # =================================================
    # ЗАПИТ ПРО ЗАГРОЗИ
    # =================================================

    if is_threat_question(
        question
    ):

        print(
            "🛰 AI CHAT | "
            "Запит визначено як "
            "питання про загрози"
        )

        thinking_message = (
            await message.answer(
                "🛰 Перевіряю актуальні "
                "загрози..."
            )
        )

        try:

            answer = (
                await get_threats_for_ai(
                    user_id
                )
            )

        except Exception as e:

            print(
                "❌ AI THREATS ERROR | "
                f"{type(e).__name__}: {e}"
            )

            answer = (
                "❌ Не вдалося отримати "
                "актуальні дані про загрози."
            )

        try:

            await thinking_message.delete()

        except Exception:

            pass

        await message.answer(
            answer,
            parse_mode="HTML",
        )

        return

    # =================================================
    # ЗВИЧАЙНИЙ AI
    # =================================================

    thinking_message = (
        await message.answer(
            "🤖 Думаю..."
        )
    )

    answer = await asyncio.to_thread(
        ask_ai,
        question,
    )

    try:

        await thinking_message.delete()

    except Exception:

        pass

    await message.answer(
        answer
    )

    print(
        f"✅ AI CHAT | "
        f"user_id={user_id}"
    )