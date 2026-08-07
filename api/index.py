"""Vercel FastAPI adapter for the strict Furiosa API runtime."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

from airline_baggage_agent.server.app import build_agent
from airline_baggage_agent.server.http import (
    RequestValidationError,
    build_health_payload,
    build_options_payload,
    build_response_payload,
)

LOGGER = logging.getLogger(__name__)
NO_STORE_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}

app = FastAPI(
    title="CarryCheck API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@lru_cache(maxsize=1)
def _get_agent():
    """Initialize the API agent once per warm Vercel function instance."""
    return build_agent("api")


def _json(payload: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status_code, headers=NO_STORE_HEADERS)


@app.get("/api/health")
def health() -> JSONResponse:
    return _json(build_health_payload(_get_agent()))


@app.get("/api/options")
def options() -> JSONResponse:
    return _json(build_options_payload(_get_agent()))


@app.post("/api/decide")
def decide(payload: Any = Body(...)) -> JSONResponse:
    try:
        return _json(build_response_payload(_get_agent(), payload))
    except (RequestValidationError, ValueError) as exc:
        return _json({"error": str(exc)}, status_code=422)
    except Exception:
        LOGGER.exception("CarryCheck decision failed")
        return _json({"error": "판정 중 오류가 발생했습니다."}, status_code=500)
