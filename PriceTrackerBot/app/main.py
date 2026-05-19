from aiogram import Bot, Dispatcher
import asyncio

from core.config import settings
from services.kafka_consumer import consume_price
from tg_bot.handlers import (
    add_product,
    common,
    list_products,
    del_product,
    updt_product_price
)



async def main():
    bot = Bot(token=settings.tg.token)
    disp = Dispatcher()

    disp.include_router(common.router)
    disp.include_router(add_product.router)
    disp.include_router(list_products.router)
    disp.include_router(del_product.router)
    disp.include_router(updt_product_price.router)

    kafka_task = asyncio.create_task(consume_price(bot))

    try:
        await disp.start_polling(bot)
    finally:
        try:
            await disp.stop_polling()
        except RuntimeError:
            pass

        kafka_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())