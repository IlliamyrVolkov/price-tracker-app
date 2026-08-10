import asyncio
import logging
from typing import Any

import grpc

from core.config import settings

from . import price_pb2
from . import price_pb2_grpc

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0
MAX_ATTEMPTS = 2
RETRY_DELAY = 0.5
RETRIABLE_CODES = frozenset({
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
})
CHANNEL_OPTIONS = [
    ("grpc.keepalive_time_ms", 30_000),
    ("grpc.keepalive_timeout_ms", 10_000),
    ("grpc.keepalive_permit_without_calls", 1),
]


class PriceClient:
    def __init__(self, host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._address = f"{host}:{port}"
        self._timeout = timeout
        self._channel: grpc.aio.Channel | None = None
        self._stub: price_pb2_grpc.PriceServiceStub | None = None
        self._lock = asyncio.Lock()

    async def _get_stub(self) -> price_pb2_grpc.PriceServiceStub:
        if self._stub is None:
            async with self._lock:
                if self._stub is None:
                    self._channel = grpc.aio.insecure_channel(
                        self._address, options=CHANNEL_OPTIONS
                    )
                    self._stub = price_pb2_grpc.PriceServiceStub(self._channel)
                    logger.info("gRPC channel opened to %s", self._address)
        return self._stub

    async def close(self) -> None:
        async with self._lock:
            if self._channel is not None:
                await self._channel.close()
                logger.info("gRPC channel to %s closed", self._address)
            self._channel = None
            self._stub = None

    async def _call(self, method_name: str, request: Any) -> Any | None:
        stub = await self._get_stub()
        method = getattr(stub, method_name)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return await method(request, timeout=self._timeout)
            except asyncio.CancelledError:
                raise
            except grpc.aio.AioRpcError as error:
                logger.error(
                    "gRPC %s failed (attempt %s/%s): %s - %s",
                    method_name, attempt, MAX_ATTEMPTS, error.code().name, error.details(),
                )
                if error.code() not in RETRIABLE_CODES or attempt == MAX_ATTEMPTS:
                    return None
                await asyncio.sleep(RETRY_DELAY)
            except Exception:
                logger.exception("gRPC %s raised an unexpected error", method_name)
                return None
        return None

    async def register_user(self, user_id: int, user_name: str) -> bool:
        response = await self._call(
            "AddUser",
            price_pb2.CreateUser(user_id=user_id, user_name=user_name),
        )
        if response is None:
            return False
        logger.info("User %s registered as %r", user_id, response.user_name)
        return True

    async def new_product(
        self, user_id: int, url: str, name: str, target_price: float
    ) -> int | None:
        response = await self._call(
            "AddProduct",
            price_pb2.CreateProductRequest(
                user_id=user_id,
                url=url,
                name=name,
                target_price=target_price,
            ),
        )
        if response is None:
            return None
        logger.info("Product %s created for user %s", response.product_id, user_id)
        return response.product_id

    async def get_products(self, user_id: int) -> list[price_pb2.Product] | None:
        response = await self._call("GetUserProducts", price_pb2.GetUser(user_id=user_id))
        if response is None:
            return None
        return list(response.products)

    async def del_product(self, product_id: int, user_id: int) -> bool:
        response = await self._call(
            "Delete",
            price_pb2.DeleteProductRequest(product_id=product_id, user_id=user_id),
        )
        return response is not None

    async def update_product_price(
        self, user_id: int, product_id: int, target_price: float
    ) -> bool:
        response = await self._call(
            "UpdateTargetPrice",
            price_pb2.UpdateRequest(
                user_id=user_id,
                product_id=product_id,
                target_price=target_price,
            ),
        )
        return response is not None


grpc_client = PriceClient(
    host=settings.rpc.host,
    port=settings.rpc.port,
)
