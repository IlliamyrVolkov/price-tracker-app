import logging
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

router = Router()


@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()

    await message.answer(
        "Action cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )
