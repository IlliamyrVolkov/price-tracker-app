import asyncio
import json
import logging
from dataclasses import dataclass
from html import escape
from typing import Any

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from core.config import settings
from core.validators import is_http_url
from services.grpc_client.client import grpc_client

logger = logging.getLogger(__name__)

CONSUMER_GROUP_ID = "price_tracker_bot_group"

_START_RETRY_DELAY = 5
_MAX_RETRY_DELAY = 60
_SEND_ATTEMPTS = 3
_MAX_RETRY_AFTER = 60


@dataclass(frozen=True, slots=True)
class PriceDropEvent:
    user_id: int
    product_id: int
    old_price: float | None
    new_price: float | None


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_event(raw: bytes | None) -> PriceDropEvent:
    if not raw:
        raise ValueError("empty message")

    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object, got {type(payload).__name__}")

    user_id = int(payload["user_id"])
    product_id = int(payload["product_id"])
    if user_id <= 0 or product_id <= 0:
        raise ValueError(f"invalid ids: user_id={user_id}, product_id={product_id}")

    return PriceDropEvent(
        user_id=user_id,
        product_id=product_id,
        old_price=_parse_price(payload.get("old_price")),
        new_price=_parse_price(payload.get("new_price")),
    )


def _format_price(value: float | None) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")


def _build_alert(event: PriceDropEvent, name: str, url: str) -> str:
    lines = [
        f"📉 Ціна знизилась на <b>{escape(name)}</b>",
        f"Була: {_format_price(event.old_price)}",
        f"Стала: <b>{_format_price(event.new_price)}</b>",
    ]
    if is_http_url(url):
        lines.append(f'🔗 <a href="{escape(url, quote=True)}">Перейти до товару</a>')
    return "\n".join(lines)


async def _resolve_product(event: PriceDropEvent) -> tuple[str, str]:
    fallback_name = f"Товар #{event.product_id}"
    try:
        products = await grpc_client.get_products(event.user_id)
    except Exception:
        logger.exception("Failed to resolve product %s", event.product_id)
        return fallback_name, ""

    for product in products or ():
        if product.product_id == event.product_id:
            return product.name or fallback_name, product.url or ""

    logger.warning("Product %s not found for user %s", event.product_id, event.user_id)
    return fallback_name, ""


async def _send_alert(bot: Bot, event: PriceDropEvent, text: str) -> None:
    for attempt in range(1, _SEND_ATTEMPTS + 1):
        try:
            await bot.send_message(chat_id=event.user_id, text=text, parse_mode="HTML")
            return
        except TelegramRetryAfter as error:
            delay = min(error.retry_after, _MAX_RETRY_AFTER)
            logger.warning("Rate limited for user %s, retrying in %ss", event.user_id, delay)
            await asyncio.sleep(delay)
        except TelegramForbiddenError:
            logger.info("User %s has blocked the bot, alert dropped", event.user_id)
            return
        except TelegramBadRequest as error:
            logger.error("Telegram rejected the alert for user %s: %s", event.user_id, error)
            return
        except Exception:
            logger.exception(
                "Failed to send an alert to user %s (attempt %s/%s)",
                event.user_id, attempt, _SEND_ATTEMPTS,
            )
            if attempt < _SEND_ATTEMPTS:
                await asyncio.sleep(_START_RETRY_DELAY)

    logger.error("Giving up on the alert for user %s", event.user_id)


def _build_consumer() -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        settings.kafka.topic,
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id=CONSUMER_GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset="latest",
    )


async def _start_consumer(consumer: AIOKafkaConsumer) -> None:
    delay = _START_RETRY_DELAY
    while True:
        try:
            await consumer.start()
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Kafka is not ready, retrying in %ss", delay, exc_info=True)
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_RETRY_DELAY)


async def _stop_consumer(consumer: AIOKafkaConsumer) -> None:
    try:
        await consumer.stop()
    except Exception:
        logger.warning("Failed to stop the Kafka consumer cleanly", exc_info=True)


async def _consume(bot: Bot, consumer: AIOKafkaConsumer) -> None:
    async for message in consumer:
        try:
            event = _parse_event(message.value)
        except (ValueError, KeyError, TypeError) as error:
            logger.error(
                "Skipping malformed message %s[%s]@%s: %s",
                message.topic, message.partition, message.offset, error,
            )
        else:
            logger.info("Price drop event received: %s", event)
            name, url = await _resolve_product(event)
            await _send_alert(bot, event, _build_alert(event, name, url))

        try:
            await consumer.commit()
        except KafkaError:
            logger.exception("Failed to commit offset %s", message.offset)


async def consume_price(bot: Bot) -> None:
    delay = _START_RETRY_DELAY
    while True:
        consumer = _build_consumer()
        try:
            await _start_consumer(consumer)
            logger.info("Kafka consumer started, listening to topic %s", settings.kafka.topic)
            delay = _START_RETRY_DELAY
            await _consume(bot, consumer)
            logger.warning("Kafka consumer stopped, reconnecting in %ss", delay)
        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            raise
        except Exception:
            logger.exception("Kafka consumer crashed, reconnecting in %ss", delay)
        finally:
            await _stop_consumer(consumer)

        await asyncio.sleep(delay)
        delay = min(delay * 2, _MAX_RETRY_DELAY)
