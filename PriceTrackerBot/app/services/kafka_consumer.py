import json
import logging
import asyncio
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from aiogram import Bot
from core.config import settings

from services.grpc_client.client import grpc_client


async def consume_price(bot: Bot):
    consumer = AIOKafkaConsumer(
        settings.kafka.topic,
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id="price_tracker_bot_group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    while True:
        try:
            await consumer.start()
            logging.info(f"Kafka Consumer started. Listening to topic: {settings.kafka.topic}")
            break
        except KafkaConnectionError:
            logging.warning("Kafka isn't ready yet. Wait 5 seconds and wake up again...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.warning(f"Error connecting to Kafka: {e}. Wait 5 seconds...")
            await asyncio.sleep(5)

    try:
        async for msg in consumer:
            data = msg.value
            logging.info(f"Kafka Event received: {data}")

            user_id = data.get("user_id")
            product_id = data.get("product_id")
            old_price = data.get("old_price")
            new_price = data.get("new_price")

            if user_id and product_id:
                product_name = f"Product #{product_id}"
                product_url = ""

                products = await grpc_client.get_products(user_id)
                if products:
                    for product in products:
                        if product.product_id == product_id:
                            product_name = product.name
                            product_url = product.url
                            break

                text = (f"Зниження ціни на <b>{product_name}</b>!" 
                        f"Стара ціна: {old_price}, Нова ціна: {new_price}"
                        f"🔗 <a href='{product_url}'>Product link</a>"
                )

                try:
                    await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Failed to send alert to {user_id}: {e}")
    finally:
        await consumer.stop()
