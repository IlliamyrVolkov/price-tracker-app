import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from core.config import settings
from services.grpc_client.client import grpc_client
from services.kafka_consumer import consume_price
from tg_bot.handlers import (
    add_product,
    common,
    del_product,
    fallback,
    list_products,
    updt_product_price,
)

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
RESTART_DELAY = 5

BOT_COMMANDS = [
    BotCommand(command="start", description="Головне меню"),
    BotCommand(command="add", description="Додати товар"),
    BotCommand(command="list", description="Мої товари"),
    BotCommand(command="cancel", description="Скасувати поточну дію"),
]


def setup_logging(level_name: str) -> None:
    level = logging.getLevelNamesMapping().get(level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format=LOG_FORMAT)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)


async def set_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(BOT_COMMANDS)
    except Exception:
        logger.warning("Failed to set the bot commands", exc_info=True)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_routers(
        common.router,
        add_product.router,
        list_products.router,
        del_product.router,
        updt_product_price.router,
        fallback.router,
    )
    dispatcher.startup.register(set_commands)
    return dispatcher


async def supervise(name: str, start: Callable[[], Awaitable[None]]) -> None:
    while True:
        try:
            await start()
            logger.warning("%s finished unexpectedly", name)
        except asyncio.CancelledError:
            logger.info("%s cancelled", name)
            raise
        except Exception:
            logger.exception("%s crashed", name)

        logger.info("Restarting %s in %ss", name, RESTART_DELAY)
        await asyncio.sleep(RESTART_DELAY)


async def cancel(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def main() -> None:
    setup_logging(settings.log_level)

    bot = Bot(
        token=settings.tg.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dispatcher = build_dispatcher()

    consumer_task = asyncio.create_task(
        supervise("kafka-consumer", lambda: consume_price(bot)),
        name="kafka-consumer",
    )

    logger.info("Bot is starting")
    try:
        await dispatcher.start_polling(bot)
    finally:
        # The consumer still calls gRPC, so it has to stop before the channel closes.
        await cancel(consumer_task)
        await grpc_client.close()
        logger.info("Bot has stopped")


if __name__ == "__main__":
    asyncio.run(main())
