from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client
from tg_bot.utils.messages import (
    BTN_MY_PDT,
    BTN_ADD,
    BTN_DEL,
    BTN_CHANGE,
    BTN_CANCEL,
    MSG_SUCCESS_ADD,
    MSG_ASK_URL,
    MSG_ASK_NAME,
    MSG_ASK_PRICE,
    MSG_SERVER_ERROR
)

router = Router()


class AddProductStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()
    waiting_for_price = State()


@router.message(Command("add"))
@router.message(F.text == BTN_ADD)
async def cmd_add_product(message: Message, state: FSMContext) -> None:
    await message.answer(
        MSG_ASK_URL,
        reply_markup=kb.get_reply_keyboard(BTN_CANCEL)
    )
    await state.set_state(AddProductStates.waiting_for_url)


@router.message(AddProductStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext) -> None:
    await state.update_data(url=message.text)
    await message.answer(MSG_ASK_NAME)
    await state.set_state(AddProductStates.waiting_for_name)


@router.message(AddProductStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await message.answer(MSG_ASK_PRICE)
    await state.set_state(AddProductStates.waiting_for_price)


@router.message(AddProductStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("Ціна має бути числом!")
        return

    await state.update_data(target_price=int(message.text))

    data = await state.get_data()
    if not message.from_user: return
    user_id = message.from_user.id

    product_id = await grpc_client.new_product(
        user_id=user_id,
        url=data["url"],
        name=data["name"],
        target_price=data["target_price"]
    )

    if product_id:
        await message.answer(
            MSG_SUCCESS_ADD.format(product_id=product_id, name=data["name"]),
            reply_markup=kb.get_reply_keyboard(
                BTN_MY_PDT,
                BTN_ADD,
                BTN_DEL,
                BTN_CHANGE,
            )
        )
    else:
        await message.answer(
            MSG_SERVER_ERROR,
            reply_markup=kb.get_reply_keyboard(
                BTN_MY_PDT,
                BTN_ADD,
                BTN_DEL,
                BTN_CHANGE,
            )
        )

    await state.clear()
