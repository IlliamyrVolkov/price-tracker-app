import signal
from concurrent import futures

import grpc

from src.core.config import Config
from src.core.logger import logger
from src.exceptions import (
    InvalidUrlError,
    PriceFetchError,
    PriceFormatError,
    PriceNotFoundError,
)
from src.parser import Parser

from . import parser_pb2
from . import parser_pb2_grpc

MIN_TIMEOUT = 1.0

STATUS_CODES = {
    InvalidUrlError: grpc.StatusCode.INVALID_ARGUMENT,
    PriceNotFoundError: grpc.StatusCode.NOT_FOUND,
    PriceFormatError: grpc.StatusCode.NOT_FOUND,
    PriceFetchError: grpc.StatusCode.UNAVAILABLE,
}


def status_code_for(error: Exception) -> grpc.StatusCode:
    for error_type, code in STATUS_CODES.items():
        if isinstance(error, error_type):
            return code
    return grpc.StatusCode.INTERNAL


class PriceService(parser_pb2_grpc.GetPriceServicer):
    def __init__(self, config: Config) -> None:
        self._config = config

    def _timeout_for(self, context: grpc.ServicerContext) -> float:
        remaining = context.time_remaining()
        if remaining is None:
            return self._config.request_timeout
        if remaining <= 0:
            context.abort(
                grpc.StatusCode.DEADLINE_EXCEEDED,
                "the deadline expired before parsing started",
            )
        return max(min(self._config.request_timeout, remaining), MIN_TIMEOUT)

    def ParserWeb(self, request, context):
        url = request.url.strip()
        if not url:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "url is required")

        timeout = self._timeout_for(context)
        logger.info("Parsing %s with a %.1fs timeout", url, timeout)

        try:
            price = Parser(url, timeout=timeout).get_price()
        except Exception as error:
            code = status_code_for(error)
            if code is grpc.StatusCode.INTERNAL:
                logger.exception("Unexpected error while parsing %s", url)
                context.abort(code, "internal parser error")
            logger.warning("Parsing %s failed with %s: %s", url, code.name, error)
            context.abort(code, str(error))

        logger.info("Parsed %s, price is %.2f", url, price)
        return parser_pb2.ParseResponse(price=price)


def install_shutdown_handlers(server: grpc.Server, grace: float) -> None:
    def shutdown(signum, _frame):
        logger.info("Received %s, stopping the server", signal.Signals(signum).name)
        server.stop(grace)

    for received in (signal.SIGINT, signal.SIGTERM):
        signal.signal(received, shutdown)


def serve() -> None:
    config = Config.from_env()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=config.max_workers),
        maximum_concurrent_rpcs=config.max_workers,
    )
    parser_pb2_grpc.add_GetPriceServicer_to_server(PriceService(config), server)
    server.add_insecure_port(f"[::]:{config.port}")

    server.start()
    logger.info("gRPC server listening on port %s with %s workers", config.port, config.max_workers)

    install_shutdown_handlers(server, config.shutdown_grace)
    server.wait_for_termination()
    logger.info("gRPC server stopped")


if __name__ == "__main__":
    serve()
