import logging
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client

router = Router()


@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()

    await message.answer(
        "Action cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    if not message.from_user: return
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    await grpc_client.register_user(user_id, user_name)
    await message.answer(
        "Hello! I am a bot for price updates. What do you want to do?",
        reply_markup=kb.get_reply_keyboard(
            "📋 My products",
            "➕ Add product",
            "🗑️ Delete product",
            "✨ Change product",
        )
    )
