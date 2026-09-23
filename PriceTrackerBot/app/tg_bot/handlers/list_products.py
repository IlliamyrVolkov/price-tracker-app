from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tg_bot.utils.messages import BTN_MY_PDT
from tg_bot.utils.products import show_user_products

router = Router()


@router.message(Command("list"))
@router.message(F.text == BTN_MY_PDT)
async def get_user_products(message: Message, state: FSMContext):
    await state.clear()
    await show_user_products(message)
