from aiokafka import AIOKafkaConsumer
from aiogram import Bot, Dispatcher
import asyncio

from core.config import settings
from tg_bot.handlers import (
    add_product,
    common,
    list_products,
    del_product,
    updt_product_price
)



async def consume_kafka():
    consumer = AIOKafkaConsumer(
        'my_topic', 'my_other_topic',
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id="my-group")

    await consumer.start()
    try:
        async for msg in consumer:
            print("consumed: ", msg.topic, msg.partition, msg.offset,
                  msg.key, msg.value, msg.timestamp)
    finally:
        await consumer.stop()


async def main():
    bot = Bot(token=settings.tg.token)
    disp = Dispatcher()

    disp.include_router(common.router)
    disp.include_router(add_product.router)
    disp.include_router(list_products.router)
    disp.include_router(del_product.router)
    disp.include_router(updt_product_price.router)

    kafka_task = asyncio.create_task(consume_kafka())

    print("Bot is starting...")

    try:
        await disp.start_polling(bot)
    finally:
        await disp.stop_polling()
        kafka_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())