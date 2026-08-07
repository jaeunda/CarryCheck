"""Small OpenAI-compatible clients with independent endpoint credentials."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import httpx


def build_endpoint_url(base_url: str, endpoint: str) -> str:
    """Join a shared API base URL with a relative endpoint path."""
    parsed = urlparse(endpoint)
    if parsed.scheme or parsed.netloc:
        raise ValueError("API endpoint는 공통 FURIOSA_BASE_URL 기준의 상대 경로여야 합니다.")
    if not endpoint.strip():
        raise ValueError("API endpoint가 비어 있습니다.")
    return f"{base_url.rstrip('/')}/{endpoint.strip().lstrip('/')}"


def _namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


class _JsonEndpoint:
    def __init__(self, base_url: str, endpoint: str, api_key: str, *, timeout: float = 30.0):
        self.url = build_endpoint_url(base_url, endpoint)
        self.api_key = api_key
        self.timeout = timeout

    def post(self, payload: dict[str, Any]) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(self.url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Furiosa API가 HTTP {exc.response.status_code}를 반환했습니다.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Furiosa API 연결에 실패했습니다: {type(exc).__name__}") from exc
        return _namespace(response.json())


class FuriosaEmbeddingClient:
    """Client shape expected by ``QwenEmbeddingAdapter``."""

    def __init__(self, base_url: str, endpoint: str, api_key: str, *, timeout: float = 30.0):
        self._endpoint = _JsonEndpoint(base_url, endpoint, api_key, timeout=timeout)
        self.embeddings = self

    def create(self, *, model: str, input: list[str]) -> Any:
        return self._endpoint.post({"model": model, "input": input})


class _ChatCompletions:
    def __init__(self, base_url: str, endpoint: str, api_key: str, *, timeout: float = 30.0):
        self._endpoint = _JsonEndpoint(base_url, endpoint, api_key, timeout=timeout)

    def create(self, **kwargs: Any) -> Any:
        extra_body = kwargs.pop("extra_body", None) or {}
        return self._endpoint.post({**kwargs, **extra_body})


class FuriosaChatClient:
    """Client shape expected by ``VerifiedJourneyAnswerAgent``."""

    def __init__(self, base_url: str, endpoint: str, api_key: str, *, timeout: float = 30.0):
        completions = _ChatCompletions(base_url, endpoint, api_key, timeout=timeout)
        self.chat = SimpleNamespace(completions=completions)


__all__ = [
    "FuriosaChatClient",
    "FuriosaEmbeddingClient",
    "build_endpoint_url",
]
