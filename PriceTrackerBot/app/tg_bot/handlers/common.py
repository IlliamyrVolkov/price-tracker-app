import logging
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client
from tg_bot.utils.messages import (
    BTN_CANCEL,
    MSG_CANCELLED,
    MSG_NOTHING_TO_CANCEL,
    MSG_START,
)

router = Router()


@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text == BTN_CANCEL)
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    await state.clear()
    if current_state is not None:
        logging.info("Cancelling state %r", current_state)

    await message.answer(
        MSG_CANCELLED if current_state is not None else MSG_NOTHING_TO_CANCEL,
        reply_markup=kb.main_menu(),
    )


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user: return
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name or "unknown"

    await grpc_client.register_user(user_id, user_name)
    await message.answer(MSG_START, reply_markup=kb.main_menu())
