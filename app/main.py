from aiokafka import AIOKafkaConsumer
from aiogram import Bot, Dispatcher
import asyncio

from core.config import settings


async def consume_kafka():
    consumer = AIOKafkaConsumer(
        'my_topic', 'my_other_topic',
        bootstrap_servers='localhost:9092',
        group_id="my-group")

    await consumer.start()
    try:
        async for msg in consumer:
            print("consumed: ", msg.topic, msg.partition, msg.offset,
                  msg.key, msg.value, msg.timestamp)
    finally:
        await consumer.stop()


async def main():
    bot = Bot(token=settings.bot_token)
    disp = Dispatcher()

    kafka_task = asyncio.create_task(consume_kafka())

    print("Bot is starting...")

    await disp.start_polling(bot)


asyncio.run(consume_kafka())


if __name__ == "__main__":
    asyncio.run(main())