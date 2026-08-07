"""Runtime profiles and Furiosa API settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Explicit shell values take precedence; the project-root .env only fills missing values.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


FURIOSA_BASE_URL = os.environ.get(
    "FURIOSA_BASE_URL",
    "https://endpoint.access.furiosa.dev/v1",
).strip().rstrip("/")
FURIOSA_EMBEDDING_ENDPOINT = os.environ.get(
    "FURIOSA_EMBEDDING_ENDPOINT",
    "/embeddings",
).strip()
FURIOSA_EMBEDDING_API_KEY = os.environ.get("FURIOSA_EMBEDDING_API_KEY", "").strip()
FURIOSA_EMBEDDING_MODEL = os.environ.get(
    "FURIOSA_EMBEDDING_MODEL",
    "furiosa-ai/Qwen3-Embedding-8B",
).strip()
FURIOSA_CHAT_ENDPOINT = os.environ.get(
    "FURIOSA_CHAT_ENDPOINT",
    "/chat/completions",
).strip()
FURIOSA_CHAT_API_KEY = os.environ.get("FURIOSA_CHAT_API_KEY", "").strip()
FURIOSA_CHAT_MODEL = os.environ.get(
    "FURIOSA_CHAT_MODEL",
    "furiosa-ai/gpt-oss-120b",
).strip()


def endpoint_url(endpoint: str) -> str:
    """Return the configured absolute URL for diagnostics and validation."""
    return f"{FURIOSA_BASE_URL}/{endpoint.lstrip('/')}"
