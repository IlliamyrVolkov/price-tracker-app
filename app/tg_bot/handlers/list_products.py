from aiogram import Router, F
from aiogram.types import Message

from services.grpc_client.client import grpc_client

router = Router()


@router.message(F.text == "📋 My products")
async def get_user_products(message: Message):
    user_id = message.from_user.id
    products = await grpc_client.get_products(user_id)

    if not products:
        await message.answer(
            "You don't have any tracked products yet. Click ➕ Add product to add your first one!"
        )
        return

    text = "Your tracked products:\n\n"
    for product in products:
        text += f"{product.name} - {product.target_price} - {product.url}\n"

    await message.answer(text, disable_web_page_preview=True)
