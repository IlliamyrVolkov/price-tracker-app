from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client

router = Router()


class AddProductStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()
    waiting_for_price = State()


@router.message(Command("add"))
@router.message(F.text == "➕ Add product")
async def cmd_add_product(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Send a link to the product:",
        reply_markup=kb.get_reply_keyboard("Cancel")
    )
    await state.set_state(AddProductStates.waiting_for_url)


@router.message(AddProductStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext) -> None:
    await state.update_data(url=message.text)
    await message.answer("To name a product:")
    await state.set_state(AddProductStates.waiting_for_name)


@router.message(AddProductStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await message.answer("Enter the desired price:")
    await state.set_state(AddProductStates.waiting_for_price)


@router.message(AddProductStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Price must be an integer")
        return

    await state.update_data(target_price=int(message.text))

    data = await state.get_data()
    user_id = message.from_user.id

    product_id = await grpc_client.send_new_product(
        user_id=user_id,
        url=data["url"],
        name=data["name"],
        target_price=data["target_price"]
    )

    if product_id:
        await message.answer(
            f"Successfully added your product (ID: {product_id})\n{data['name']}",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "Look, there's a problem on the server. Try again later.",
            reply_markup=ReplyKeyboardRemove()
        )

    await state.clear()
