import grpc
import logging

from . import price_pb2
from . import price_pb2_grpc


GRPC_SERVER_ADDRESS = 'localhost:50051'


async def send_new_product(user_id: int, url: str, name: str, target_price: float):
    async with grpc.aio.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
        stub = price_pb2_grpc.PriceServiceStub(channel)

        request = price_pb2.CreateProductRequest(
            user_id=user_id,
            url=url,
            name=name,
            target_price=target_price
        )

        try:
            response = await stub.AddProduct(request)
            logging.info(f"gRPC Success: Product added with ID {response.product_id}")
            return response.product_id

        except grpc.aio.AioRpcError as e:
            logging.error(f"gRPC Error: {e.code()} - {e.details()}")
            return None