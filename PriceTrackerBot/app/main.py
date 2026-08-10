import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher

from core.config import settings
from services.grpc_client.client import grpc_client
from services.kafka_consumer import consume_price
from tg_bot.handlers import (
    add_product,
    common,
    del_product,
    list_products,
    updt_product_price,
)

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
RESTART_DELAY = 5


def setup_logging(level_name: str) -> None:
    level = logging.getLevelNamesMapping().get(level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format=LOG_FORMAT)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_routers(
        common.router,
        add_product.router,
        list_products.router,
        del_product.router,
        updt_product_price.router,
    )
    dispatcher.shutdown.register(grpc_client.close)
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

    bot = Bot(token=settings.tg.token)
    dispatcher = build_dispatcher()

    consumer_task = asyncio.create_task(
        supervise("kafka-consumer", lambda: consume_price(bot)),
        name="kafka-consumer",
    )

    logger.info("Bot is starting")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await cancel(consumer_task)
        logger.info("Bot has stopped")


if __name__ == "__main__":
    asyncio.run(main())
