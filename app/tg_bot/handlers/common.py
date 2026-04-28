import logging
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client
from tg_bot.utils.messages import (
    BTN_MY_PDT,
    BTN_ADD,
    BTN_DEL,
    BTN_CHANGE,
    BTN_CANCEL,
)

router = Router()


@router.message(StateFilter("*"), Command(BTN_CANCEL))
@router.message(StateFilter("*"), F.text == BTN_CANCEL)
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()

    await message.answer(
        "Запис скасовано.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    if not message.from_user: return
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    await grpc_client.register_user(user_id, user_name)
    await message.answer(
        "Привіт! Я бот для оновлення цін. Що ти хочеш зробити?",
        reply_markup=kb.get_reply_keyboard(
            BTN_MY_PDT,
            BTN_ADD,
            BTN_DEL,
            BTN_CHANGE,
        )
    )
