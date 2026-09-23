from html import escape

from aiogram import Bot, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.chat_action import ChatActionSender

from core.validators import parse_price
from tg_bot.filters import NOT_MENU_OR_COMMAND, extract_url, has_url
from tg_bot.keyboards import builders as kb
from services.grpc_client.client import grpc_client
from tg_bot.utils.formatters import format_price
from tg_bot.utils.messages import (
    BTN_ADD,
    MSG_SUCCESS_ADD,
    MSG_ASK_URL,
    MSG_ASK_NAME,
    MSG_ASK_PRICE,
    MSG_BAD_NAME,
    MSG_BAD_PRICE,
    MSG_BAD_URL,
    MSG_SERVER_ERROR
)

router = Router()

MAX_NAME_LENGTH = 100


class AddProductStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()
    waiting_for_price = State()


@router.message(Command("add"))
@router.message(F.text == BTN_ADD)
async def cmd_add_product(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddProductStates.waiting_for_url)
    await message.answer(MSG_ASK_URL, reply_markup=kb.url_keyboard())


@router.message(StateFilter(None), has_url)
async def link_outside_of_flow(message: Message, state: FSMContext, url: str) -> None:
    """A link sent without pressing "add" starts adding it right away."""
    await _accept_url(message, state, url)


@router.message(AddProductStates.waiting_for_url, NOT_MENU_OR_COMMAND)
async def process_url(message: Message, state: FSMContext) -> None:
    url = extract_url(message)
    if url is None:
        await message.answer(MSG_BAD_URL)
        return
    await _accept_url(message, state, url)


async def _accept_url(message: Message, state: FSMContext, url: str) -> None:
    await state.update_data(url=url)
    await state.set_state(AddProductStates.waiting_for_name)
    await message.answer(MSG_ASK_NAME, reply_markup=kb.cancel_keyboard())


@router.message(AddProductStates.waiting_for_name, NOT_MENU_OR_COMMAND)
async def process_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        await message.answer(MSG_BAD_NAME.format(max_length=MAX_NAME_LENGTH))
        return

    await state.update_data(name=name)
    await state.set_state(AddProductStates.waiting_for_price)
    await message.answer(MSG_ASK_PRICE)


@router.message(AddProductStates.waiting_for_price, NOT_MENU_OR_COMMAND)
async def process_price(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.from_user: return
    target_price = parse_price(message.text)
    if target_price is None:
        await message.answer(MSG_BAD_PRICE)
        return

    data = await state.get_data()
    await state.clear()

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        product_id = await grpc_client.new_product(
            user_id=message.from_user.id,
            url=data["url"],
            name=data["name"],
            target_price=target_price
        )

    if product_id is None:
        await message.answer(MSG_SERVER_ERROR, reply_markup=kb.main_menu())
        return

    await message.answer(
        MSG_SUCCESS_ADD.format(name=escape(data["name"]), target_price=format_price(target_price)),
        reply_markup=kb.main_menu(),
    )
