import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from src.core.logger import logger

T = TypeVar("T")


def _env(name: str, default: T, cast: Callable[[str], T]) -> T:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return cast(raw.strip())
    except ValueError:
        logger.warning("Invalid value %r for %s, using %r instead", raw, name, default)
        return default


@dataclass(frozen=True, slots=True)
class Config:
    port: int = 50051
    max_workers: int = 10
    request_timeout: float = 15.0
    shutdown_grace: float = 10.0

    @classmethod
    def from_env(cls) -> "Config":
        defaults = cls()
        return cls(
            port=_env("GRPC_PORT", defaults.port, int),
            max_workers=_env("GRPC_MAX_WORKERS", defaults.max_workers, int),
            request_timeout=_env("PARSER_REQUEST_TIMEOUT", defaults.request_timeout, float),
            shutdown_grace=_env("GRPC_SHUTDOWN_GRACE", defaults.shutdown_grace, float),
        )
