import grpc
import logging

from . import price_pb2
from . import price_pb2_grpc
from core.config import settings


class PriceClient:
    def __init__(self, host: str, port: int):
        self.address = f'{host}:{port}'

    async def register_user(self, user_id: int, user_name: str):
        async with grpc.aio.insecure_channel(self.address) as channel:
            stub = price_pb2_grpc.PriceServiceStub(channel)
            request = price_pb2.CreateUser(user_id=user_id, user_name=user_name)

            try:
                response = await stub.AddUser(request)
                logging.info(f"gRPC Success: User added with ID {response.user_id} and name {response.user_name}")
                return response.user_id, response.user_name

            except grpc.aio.AioRpcError as e:
                logging.error(f"gRPC Error: {e.code()} - {e.details()}")
                return None

    async def new_product(self, user_id: int, url: str, name: str, target_price: float):
        async with grpc.aio.insecure_channel(self.address) as channel:
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

    async def get_products(self, user_id: int):
        async with grpc.aio.insecure_channel(self.address) as channel:
            stub = price_pb2_grpc.PriceServiceStub(channel)
            request = price_pb2.GetUser(user_id=user_id)

            try:
                response = await stub.GetUserProducts(request)
                logging.info(f"gRPC Success: Products received {response.products}")
                return response.products

            except grpc.aio.AioRpcError as e:
                logging.error(f"gRPC Error: {e.code()} - {e.details()}")
                return None

    async def del_product(self, product_id: int, user_id: int):
        async with grpc.aio.insecure_channel(self.address) as channel:
            stub = price_pb2_grpc.PriceServiceStub(channel)
            request = price_pb2.DeleteProductRequest(product_id=product_id, user_id=user_id)

            try:
                response = await stub.Delete(request)
                logging.info(f"gRPC Success: Product has delete {response.status}")
                return response.status

            except grpc.aio.AioRpcError as e:
                logging.error(f"gRPC Error: {e.code()} - {e.details()}")
                return None


grpc_client = PriceClient(
    host=settings.rpc.host,
    port=settings.rpc.port
)