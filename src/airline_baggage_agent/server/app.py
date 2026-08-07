"""Compose the unchanged web UI with either local or strict API runtime."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from typing import Literal, Sequence

from ..config import settings
from ..policies.japan_policy import CountryAwareBaggageRAGAgent
from ..services.answer_generation import VerifiedJourneyAnswerAgent
from .http import (
    BaggageWebHandler,
    RequestValidationError,
    build_decision_payload,
    build_options_payload,
    build_response_payload,
)

RuntimeMode = Literal["local", "api"]


def _api_client_types():
    """Import API-only dependencies only when the API runtime is selected."""
    from ..services.furiosa_clients import (  # noqa: PLC0415
        FuriosaChatClient,
        FuriosaEmbeddingClient,
        build_endpoint_url,
    )

    return FuriosaEmbeddingClient, FuriosaChatClient, build_endpoint_url


def _require_api_settings() -> None:
    missing = []
    if not settings.FURIOSA_EMBEDDING_API_KEY:
        missing.append("FURIOSA_EMBEDDING_API_KEY")
    if not settings.FURIOSA_CHAT_API_KEY:
        missing.append("FURIOSA_CHAT_API_KEY")
    if missing:
        raise RuntimeError("Missing .env values required by the API runtime: " + ", ".join(missing))


def build_agent(runtime: RuntimeMode = "local") -> CountryAwareBaggageRAGAgent:
    if runtime == "local":
        agent = CountryAwareBaggageRAGAgent()
        agent.answer_generator = None
        agent.runtime_model = {
            "provider": "local",
            "mode": "local",
            "profile": "local",
            "embedding_mode": "local",
            "embedding_model": None,
            "embedding_endpoint": None,
            "chat_mode": "disabled",
            "chat_model": None,
            "chat_endpoint": None,
        }
        return agent

    if runtime != "api":
        raise ValueError(f"Unsupported runtime mode: {runtime}")

    _require_api_settings()
    FuriosaEmbeddingClient, FuriosaChatClient, build_endpoint_url = _api_client_types()
    embedding_client = FuriosaEmbeddingClient(
        settings.FURIOSA_BASE_URL,
        settings.FURIOSA_EMBEDDING_ENDPOINT,
        settings.FURIOSA_EMBEDDING_API_KEY,
    )
    chat_client = FuriosaChatClient(
        settings.FURIOSA_BASE_URL,
        settings.FURIOSA_CHAT_ENDPOINT,
        settings.FURIOSA_CHAT_API_KEY,
    )
    agent = CountryAwareBaggageRAGAgent(
        embedding_client=embedding_client,
        embedding_model=settings.FURIOSA_EMBEDDING_MODEL,
    )
    agent.answer_generator = VerifiedJourneyAnswerAgent(
        chat_client,
        settings.FURIOSA_CHAT_MODEL,
        fallback_on_error=False,
    )
    agent.runtime_model = {
        "provider": "FuriosaAI",
        "mode": "api",
        "embedding_mode": "api",
        "embedding_model": settings.FURIOSA_EMBEDDING_MODEL,
        "embedding_endpoint": build_endpoint_url(
            settings.FURIOSA_BASE_URL,
            settings.FURIOSA_EMBEDDING_ENDPOINT,
        ),
        "chat_mode": "api",
        "chat_model": settings.FURIOSA_CHAT_MODEL,
        "chat_endpoint": build_endpoint_url(
            settings.FURIOSA_BASE_URL,
            settings.FURIOSA_CHAT_ENDPOINT,
        ),
    }
    return agent


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    runtime: RuntimeMode = "local",
) -> ThreadingHTTPServer:
    agent = build_agent(runtime)

    class ConfiguredBaggageWebHandler(BaggageWebHandler):
        pass

    ConfiguredBaggageWebHandler.agent = agent
    if runtime == "api":
        print("Runtime profile: API (embedding + Chat, no automatic local fallback)")
    else:
        print("Runtime profile: LOCAL (no external API calls)")
    return ThreadingHTTPServer((host, port), ConfiguredBaggageWebHandler)


def main(
    argv: Sequence[str] | None = None,
    *,
    default_runtime: RuntimeMode = "local",
    runtime_locked: bool = False,
) -> None:
    parser = argparse.ArgumentParser(description="CarryCheck airline baggage agent web server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    if not runtime_locked:
        parser.add_argument("--runtime", choices=("local", "api"), default=default_runtime)
    args = parser.parse_args(argv)
    runtime = default_runtime if runtime_locked else args.runtime
    server = create_server(args.host, args.port, runtime=runtime)
    print(f"CarryCheck web: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = [
    "BaggageWebHandler",
    "RequestValidationError",
    "build_agent",
    "build_decision_payload",
    "build_options_payload",
    "build_response_payload",
    "create_server",
    "main",
]


if __name__ == "__main__":
    main()
