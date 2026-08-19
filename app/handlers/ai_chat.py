import asyncio

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.ai_chat import ask_ai


router = Router()


# =====================================================
# СТАН AI ЧАТУ
# =====================================================

class AIChatState(StatesGroup):
    chatting = State()


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

    from app.keyboards.menu import get_main_menu

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

    print(
        f"🤖 AI CHAT | "
        f"user_id={message.from_user.id} | "
        f"question={question}"
    )

    thinking_message = await message.answer(
        "🤖 Думаю..."
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
        f"user_id={message.from_user.id}"
    )