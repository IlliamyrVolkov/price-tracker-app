from aiogram import Router, F
from aiogram.types import Message

from services.grpc_client.client import grpc_client
from tg_bot.utils.messages import BTN_MY_PDT

router = Router()


@router.message(F.text == BTN_MY_PDT)
async def get_user_products(message: Message):
    if not message.from_user: return
    user_id = message.from_user.id
    products = await grpc_client.get_products(user_id)

    if not products:
        await message.answer(
            "У вас ще немає відстежуваних товарів. Натисніть ➕ Додати товар, щоб додати свій перший!"
        )
        return

    text = "Відстежені продукти:\n\n"
    for product in products:
        text += f"{product.name} - {product.target_price} - {product.url}\n"

    await message.answer(text, disable_web_page_preview=True)
