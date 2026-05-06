from services.grpc_client.client import grpc_client


async def get_formatted_products_text(user_id: int) -> str | None:
    products = await grpc_client.get_products(user_id)

    if not products:
        return None

    text = "Your products:\n\n"
    for product in products:
        text += f"ID: {product.product_id} | {product.name}\n"

    return text