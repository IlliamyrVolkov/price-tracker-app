"""Handlers for whatever no other router took. Include this router last."""
import logging

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, Message

from tg_bot.keyboards import builders as kb
from tg_bot.utils.messages import MSG_UNEXPECTED_ERROR, MSG_UNKNOWN

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(MSG_UNKNOWN)


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, state: FSMContext | None = None) -> bool:
    logger.error("Failed to handle update %s", event.update.update_id, exc_info=event.exception)

    # The flow that failed would otherwise keep the user in a half finished state.
    if state is not None:
        await state.clear()

    message = event.update.message
    if message is not None:
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=MSG_UNEXPECTED_ERROR,
                reply_markup=kb.main_menu(),
            )
        except Exception:
            logger.warning("Failed to tell the user about the error", exc_info=True)
    return True
