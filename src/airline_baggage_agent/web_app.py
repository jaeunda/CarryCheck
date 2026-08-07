"""Backward-compatible module entry point for the safe local runtime."""

from .server.app import create_server, main
from .server.http import (
    BaggageWebHandler,
    RequestValidationError,
    build_decision_payload,
    build_health_payload,
    build_options_payload,
    build_response_payload,
)

__all__ = [
    "BaggageWebHandler",
    "RequestValidationError",
    "build_decision_payload",
    "build_health_payload",
    "build_options_payload",
    "build_response_payload",
    "create_server",
    "main",
]


if __name__ == "__main__":
    main(default_runtime="local", runtime_locked=True)
