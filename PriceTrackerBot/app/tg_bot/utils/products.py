from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from core.validators import parse_id
from services.grpc_client.client import grpc_client
from services.grpc_client.price_pb2 import Product
from tg_bot.keyboards import builders as kb
from tg_bot.utils.formatters import render_products
from tg_bot.utils.messages import MSG_BAD_ID, MSG_NO_PRODUCTS, MSG_SERVER_ERROR


async def show_user_products(message: Message) -> list[Product] | None:
    """Send the user's product list.

    Returns None when there is nothing to pick from: the list is empty or
    could not be loaded. The user has been told why in both cases.
    """
    if not message.from_user:
        return None

    products = await grpc_client.get_products(message.from_user.id)
    if products is None:
        await message.answer(MSG_SERVER_ERROR, reply_markup=kb.main_menu())
        return None
    if not products:
        await message.answer(MSG_NO_PRODUCTS, reply_markup=kb.main_menu())
        return None

    for text in render_products(products):
        await message.answer(text)
    return products


async def ask_for_product(
        message: Message,
        state: FSMContext,
        next_state: State,
        prompt: str,
) -> None:
    """Show the user's products and wait for the ID of one of them."""
    await state.clear()
    products = await show_user_products(message)
    if not products:
        return

    await state.set_state(next_state)
    await state.update_data(product_ids=[product.product_id for product in products])
    await message.answer(prompt, reply_markup=kb.cancel_keyboard())


async def read_product_id(message: Message, state: FSMContext) -> int | None:
    """Return the ID the user picked, if it is one of the products shown by ``ask_for_product``."""
    product_id = parse_id(message.text)
    data = await state.get_data()
    if product_id is None or product_id not in data.get("product_ids", ()):
        await message.answer(MSG_BAD_ID)
        return None
    return product_id
