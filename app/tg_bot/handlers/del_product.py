from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.grpc_client.client import grpc_client
from tg_bot.utils.formatters import get_formatted_products_text

router = Router()


class DeleteProductStates(StatesGroup):
    waiting_for_product_id = State()


@router.message(F.text == "🗑️ Delete product")
async def init_delete_product(message: Message, state: FSMContext):
    if not message.from_user: return
    products_text = await get_formatted_products_text(message.from_user.id)

    if not products_text:
        await message.answer(
            "You don't have any tracked products yet. Click ➕ Add product to add your first one!"
        )
        return

    await message.answer(f"{products_text}\nEnter the product ID you want to delete:")
    await state.set_state(DeleteProductStates.waiting_for_product_id)


@router.message(DeleteProductStates.waiting_for_product_id)
async def delete_product(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("ID must be an integer. Try again or type 'Cancel'")
        return

    if not message.from_user: return
    user_id = message.from_user.id
    product_id = int(message.text)
    del_prd = await grpc_client.del_product(product_id=product_id, user_id=user_id)
    if del_prd:
        await message.answer("Product deleted successfully!")
    else:
        await message.answer("Look, there's a problem on the server. Try again later.")

    await state.clear()
