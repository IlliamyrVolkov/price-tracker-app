from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.validators import parse_price
from services.grpc_client.client import grpc_client
from tg_bot.filters import NOT_MENU_OR_COMMAND
from tg_bot.keyboards import builders as kb
from tg_bot.utils.formatters import format_price
from tg_bot.utils.products import ask_for_product, read_product_id
from tg_bot.utils.messages import (
    BTN_CHANGE,
    MSG_ASK_NEW_PRICE,
    MSG_ASK_UPDATE_ID,
    MSG_BAD_PRICE,
    MSG_PRICE_UPDATED,
    MSG_SERVER_ERROR,
)

router = Router()


class UpdatePriceStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_new_price = State()


@router.message(F.text == BTN_CHANGE)
async def init_change_price(message: Message, state: FSMContext):
    await ask_for_product(
        message, state, UpdatePriceStates.waiting_for_product_id, MSG_ASK_UPDATE_ID
    )


@router.message(UpdatePriceStates.waiting_for_product_id, NOT_MENU_OR_COMMAND)
async def product_id_for_update(message: Message, state: FSMContext):
    product_id = await read_product_id(message, state)
    if product_id is None:
        return

    await state.update_data(product_id=product_id)
    await state.set_state(UpdatePriceStates.waiting_for_new_price)
    await message.answer(MSG_ASK_NEW_PRICE)


@router.message(UpdatePriceStates.waiting_for_new_price, NOT_MENU_OR_COMMAND)
async def update_price(message: Message, state: FSMContext):
    if not message.from_user: return
    target_price = parse_price(message.text)
    if target_price is None:
        await message.answer(MSG_BAD_PRICE)
        return

    data = await state.get_data()
    await state.clear()

    updated = await grpc_client.update_product_price(
        user_id=message.from_user.id,
        product_id=data["product_id"],
        target_price=target_price
    )
    if updated:
        text = MSG_PRICE_UPDATED.format(target_price=format_price(target_price))
    else:
        text = MSG_SERVER_ERROR
    await message.answer(text, reply_markup=kb.main_menu())
