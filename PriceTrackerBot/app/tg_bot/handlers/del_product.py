from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.grpc_client.client import grpc_client
from tg_bot.filters import NOT_MENU_OR_COMMAND
from tg_bot.keyboards import builders as kb
from tg_bot.utils.products import ask_for_product, read_product_id
from tg_bot.utils.messages import BTN_DEL, MSG_ASK_DELETE_ID, MSG_DELETED, MSG_SERVER_ERROR

router = Router()


class DeleteProductStates(StatesGroup):
    waiting_for_product_id = State()


@router.message(F.text == BTN_DEL)
async def init_delete_product(message: Message, state: FSMContext):
    await ask_for_product(
        message, state, DeleteProductStates.waiting_for_product_id, MSG_ASK_DELETE_ID
    )


@router.message(DeleteProductStates.waiting_for_product_id, NOT_MENU_OR_COMMAND)
async def delete_product(message: Message, state: FSMContext):
    if not message.from_user: return
    product_id = await read_product_id(message, state)
    if product_id is None:
        return

    await state.clear()
    deleted = await grpc_client.del_product(product_id=product_id, user_id=message.from_user.id)
    await message.answer(
        MSG_DELETED if deleted else MSG_SERVER_ERROR,
        reply_markup=kb.main_menu(),
    )
