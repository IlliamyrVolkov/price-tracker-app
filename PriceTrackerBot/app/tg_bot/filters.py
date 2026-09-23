from aiogram import F
from aiogram.enums import MessageEntityType
from aiogram.types import Message

from core.validators import normalize_url
from tg_bot.utils.messages import MAIN_MENU_BUTTONS

# FSM steps accept free text. Without this filter a step would take a menu
# button or a command pressed in the middle of a flow as its answer.
NOT_MENU_OR_COMMAND = ~(F.text.in_(MAIN_MENU_BUTTONS) | F.text.startswith("/"))


def extract_url(message: Message) -> str | None:
    """Return the first link in the message text or caption.

    Links shared from shop apps usually come with extra text around them,
    so the link is taken from the entities Telegram detected.
    """
    text = message.text or message.caption
    if not text:
        return None

    for entity in message.entities or message.caption_entities or ():
        if entity.type == MessageEntityType.TEXT_LINK:
            url = normalize_url(entity.url)
        elif entity.type == MessageEntityType.URL:
            url = normalize_url(entity.extract_from(text))
        else:
            continue
        if url:
            return url

    text = text.strip()
    if text.startswith(("http://", "https://")) and not any(char.isspace() for char in text):
        return normalize_url(text)
    return None


def has_url(message: Message) -> dict[str, str] | bool:
    url = extract_url(message)
    return {"url": url} if url else False
