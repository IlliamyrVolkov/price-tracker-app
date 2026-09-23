from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, InlineKeyboardButton

from tg_bot.utils.messages import (
    BTN_CANCEL,
    MAIN_MENU_BUTTONS,
    PLACEHOLDER_MENU,
    PLACEHOLDER_URL,
)


def get_reply_keyboard(
        *btns: str,
        placeholder: str | None = None,
        sizes: tuple[int, ...] = (2,),
):
    keyboard = ReplyKeyboardBuilder()

    for text in btns:
        keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*sizes).as_markup(
        resize_keyboard=True,
        input_field_placeholder=placeholder
    )


def get_inline_keyboard(
        *,
        btns: dict[str, str],
        sizes: tuple[int, ...] = (2,)
):
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


def main_menu():
    return get_reply_keyboard(*MAIN_MENU_BUTTONS, placeholder=PLACEHOLDER_MENU)


def cancel_keyboard(placeholder: str | None = None):
    return get_reply_keyboard(BTN_CANCEL, placeholder=placeholder)


def url_keyboard():
    return cancel_keyboard(placeholder=PLACEHOLDER_URL)
