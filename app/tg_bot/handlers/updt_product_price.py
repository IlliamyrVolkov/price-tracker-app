from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.grpc_client.client import grpc_client
from tg_bot.utils.formatters import get_formatted_products_text

router = Router()


class UpdatePriceStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_new_price = State()


@router.message(F.text == "✨ Change product")
async def init_change_price(message: Message, state: FSMContext):
    if not message.from_user: return
    products_text = await get_formatted_products_text(message.from_user.id)

    if not products_text:
        await message.answer(
            "You don't have any tracked products yet. Click ➕ Add product to add your first one!"
        )
        return

    await message.answer(f"{products_text}\nEnter the product ID you want to change price for:")
    await state.set_state(UpdatePriceStates.waiting_for_product_id)


@router.message(UpdatePriceStates.waiting_for_product_id)
async def product_id_for_update(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("ID must be an integer. Try again or type 'Cancel'")
        return

    await state.update_data(product_id = int(message.text))
    await message.answer("Enter a new price")
    await state.set_state(UpdatePriceStates.waiting_for_new_price)


@router.message(UpdatePriceStates.waiting_for_new_price)
async def update_price(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Price must be an integer. Try again or type 'Cancel'")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    target_price = int(message.text)

    if not message.from_user: return
    user_id = message.from_user.id

    result = await grpc_client.update_product_price(
        user_id=user_id,
        product_id=product_id,
        target_price=target_price
    )
    if result:
        await message.answer("Price updated successfully! ✨")
    else:
        await message.answer("Server error. Try again later.")

    await state.clear()
