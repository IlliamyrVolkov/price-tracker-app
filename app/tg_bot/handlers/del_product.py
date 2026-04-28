from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.grpc_client.client import grpc_client
from tg_bot.utils.formatters import get_formatted_products_text
from tg_bot.utils.messages import BTN_DEL, MSG_SERVER_ERROR

router = Router()


class DeleteProductStates(StatesGroup):
    waiting_for_product_id = State()


@router.message(F.text == BTN_DEL)
async def init_delete_product(message: Message, state: FSMContext):
    if not message.from_user: return
    products_text = await get_formatted_products_text(message.from_user.id)

    if not products_text:
        await message.answer(
            "У вас ще немає відстежуваних товарів. Натисніть ➕ Додати товар, щоб додати свій перший!"
        )
        return

    await message.answer(f"{products_text}\nВведи ID товару який хочеш видалити:")
    await state.set_state(DeleteProductStates.waiting_for_product_id)


@router.message(DeleteProductStates.waiting_for_product_id)
async def delete_product(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("ID має бути числом.")
        return

    if not message.from_user: return
    user_id = message.from_user.id
    product_id = int(message.text)
    del_prd = await grpc_client.del_product(product_id=product_id, user_id=user_id)
    if del_prd:
        await message.answer("Товар видалено успішно!")
    else:
        await message.answer(MSG_SERVER_ERROR)

    await state.clear()
