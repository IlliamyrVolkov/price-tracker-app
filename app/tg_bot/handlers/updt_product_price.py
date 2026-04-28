from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.grpc_client.client import grpc_client
from tg_bot.utils.formatters import get_formatted_products_text
from tg_bot.utils.messages import MSG_SERVER_ERROR, BTN_CHANGE

router = Router()


class UpdatePriceStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_new_price = State()


@router.message(F.text == BTN_CHANGE)
async def init_change_price(message: Message, state: FSMContext):
    if not message.from_user: return
    products_text = await get_formatted_products_text(message.from_user.id)

    if not products_text:
        await message.answer(
            "У вас ще немає відстежуваних товарів. Натисніть ➕ Додати товар, щоб додати свій перший!"
        )
        return

    await message.answer(f"{products_text}\nВведи ID товару який хочеш змінити:")
    await state.set_state(UpdatePriceStates.waiting_for_product_id)


@router.message(UpdatePriceStates.waiting_for_product_id)
async def product_id_for_update(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("ID має бути числом.")
        return

    await state.update_data(product_id = int(message.text))
    await message.answer("Введи нову ціну")
    await state.set_state(UpdatePriceStates.waiting_for_new_price)


@router.message(UpdatePriceStates.waiting_for_new_price)
async def update_price(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Ціна має бути числом.")
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
        await message.answer("Ціну оновлено успішно! ✨")
    else:
        await message.answer(MSG_SERVER_ERROR)

    await state.clear()
