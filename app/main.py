from aiokafka import AIOKafkaConsumer
from aiogram import Bot, Dispatcher
import asyncio

from core.config import settings


async def consume_kafka():
    consumer = AIOKafkaConsumer(
        'my_topic', 'my_other_topic',
        bootstrap_servers=settings.kafka.kafka_bootstrap_servers,
        group_id="my-group")

    await consumer.start()
    try:
        async for msg in consumer:
            print("consumed: ", msg.topic, msg.partition, msg.offset,
                  msg.key, msg.value, msg.timestamp)
    finally:
        await consumer.stop()


async def main():
    bot = Bot(token=settings.tg.bot_token)
    disp = Dispatcher()
    # disp.include_router(router)
    kafka_task = asyncio.create_task(consume_kafka())

    print("Bot is starting...")

    try:
        await disp.start_polling(bot)
    finally:
        await disp.stop_polling()
        kafka_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())