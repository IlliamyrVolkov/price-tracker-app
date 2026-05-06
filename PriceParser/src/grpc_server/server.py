import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import grpc
from concurrent import futures
import parser_pb2
import parser_pb2_grpc
from src.parser import Parser
from src.core.logger import logger


class PriceService(parser_pb2_grpc.GetPriceServicer):

    def ParserWeb(self, request, context):
        try:
            url = request.url
            logger.info(f"Parsing request received: {url}")
            parser = Parser(url)
            price_result = parser.get_price()
            logger.info(f"Successfully parsed price: {price_result}")

            return parser_pb2.ParseResponse(price=price_result)

        except Exception as e:
            logger.error(f"Price error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

            return parser_pb2.ParseResponse(price=0.0)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    parser_pb2_grpc.add_GetPriceServicer_to_server(PriceService(), server)

    port = "50051"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(f"gRPC server running on port {port}...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()