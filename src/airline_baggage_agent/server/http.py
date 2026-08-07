"""CarryCheck local web server with country-aware baggage decisions."""

from __future__ import annotations

import json
import logging
import math
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..domain.baggage import (
    ITEM_NAMES,
    STATUS_KO,
    airline_display_name,
    verify_decision,
)
from ..policies.japan_policy import (
    COUNTRY_CODES,
    COUNTRY_NAMES,
    CountryAwareBaggageRAGAgent,
)

WEB_ROOT = Path(__file__).resolve().parents[3] / "public"
MAX_REQUEST_BYTES = 64 * 1024
NUMBER_FIELDS = {
    "watt_hours",
    "milliamp_hours",
    "voltage",
    "container_ml",
    "total_ml",
    "weight_kg",
}
INTEGER_FIELDS = {"count"}
TRISTATE_FIELDS = {"removable_battery", "physical_disconnect", "heat_safety_mode"}
BOOLEAN_FIELDS = {"damaged", "medical_exception", "duty_free", "torch_lighter"}
ROUTE_TYPES = {"domestic", "international"}
COUNTRIES = set(COUNTRY_CODES)
COUNTRY_TRISTATE_FIELDS = {"ccc_mark"}
COUNTRY_BOOLEAN_FIELDS = {"recalled_battery"}
LOGGER = logging.getLogger(__name__)


class RequestValidationError(ValueError):
    """Raised when a client request does not satisfy the public API contract."""


def _nonempty_string(value: Any, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestValidationError(f"{field} 값을 입력해 주세요.")
    result = value.strip()
    if len(result) > max_length:
        raise RequestValidationError(f"{field} 값은 {max_length}자 이하여야 합니다.")
    return result


def _optional_choice(value: Any, field: str, choices: set[str]) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or value not in choices:
        raise RequestValidationError(f"올바르지 않은 {field} 값입니다.")
    return value


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise RequestValidationError(f"{field} 값은 숫자여야 합니다.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise RequestValidationError(f"{field} 값은 숫자여야 합니다.") from exc
    if not math.isfinite(result) or result <= 0 or result > 10_000_000:
        raise RequestValidationError(f"{field} 값은 0보다 큰 현실적인 숫자여야 합니다.")
    return result


def _validated_overrides(raw_overrides: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if raw_overrides in (None, ""):
        raw_overrides = {}
    if not isinstance(raw_overrides, dict):
        raise RequestValidationError("상세 설정 형식이 올바르지 않습니다.")

    allowed_fields = (
        {"item_type"}
        | NUMBER_FIELDS
        | INTEGER_FIELDS
        | TRISTATE_FIELDS
        | BOOLEAN_FIELDS
        | COUNTRY_TRISTATE_FIELDS
        | COUNTRY_BOOLEAN_FIELDS
    )
    unknown_fields = sorted(set(raw_overrides) - allowed_fields)
    if unknown_fields:
        raise RequestValidationError(
            "지원하지 않는 상세 설정입니다: " + ", ".join(unknown_fields)
        )

    item_overrides: dict[str, Any] = {}
    country_overrides: dict[str, Any] = {}
    item_type = raw_overrides.get("item_type")
    if item_type not in (None, ""):
        if not isinstance(item_type, str) or item_type not in ITEM_NAMES:
            raise RequestValidationError("올바르지 않은 물품 유형입니다.")
        item_overrides["item_type"] = item_type

    for field in NUMBER_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            item_overrides[field] = _positive_number(value, field)

    for field in INTEGER_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            number = _positive_number(value, field)
            if not number.is_integer():
                raise RequestValidationError(f"{field} 값은 정수여야 합니다.")
            item_overrides[field] = int(number)

    for field in TRISTATE_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            if not isinstance(value, bool):
                raise RequestValidationError(f"{field} 값은 참 또는 거짓이어야 합니다.")
            item_overrides[field] = value

    for field in BOOLEAN_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            if not isinstance(value, bool):
                raise RequestValidationError(f"{field} 값은 참 또는 거짓이어야 합니다.")
            item_overrides[field] = value

    for field in COUNTRY_TRISTATE_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            if not isinstance(value, bool):
                raise RequestValidationError(f"{field} 값은 참 또는 거짓이어야 합니다.")
            country_overrides[field] = value

    for field in COUNTRY_BOOLEAN_FIELDS:
        value = raw_overrides.get(field)
        if value not in (None, ""):
            if not isinstance(value, bool):
                raise RequestValidationError(f"{field} 값은 참 또는 거짓이어야 합니다.")
            country_overrides[field] = value

    return item_overrides, country_overrides


def _disabled_ai_answer() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "disabled",
        "verified": False,
        "answer": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def build_decision_payload(
    agent: CountryAwareBaggageRAGAgent,
    payload: Any,
) -> dict[str, Any]:
    """Validate a web request and return airline, departure, and entry decisions."""
    if not isinstance(payload, dict):
        raise RequestValidationError("요청 본문은 JSON 객체여야 합니다.")

    airline = _nonempty_string(payload.get("airline"), "항공사", max_length=80)
    item_text = _nonempty_string(payload.get("item_text"), "물품 설명", max_length=1200)
    route_type = _optional_choice(payload.get("route_type"), "노선", ROUTE_TYPES)
    origin_country = _optional_choice(payload.get("origin_country"), "출발 국가", COUNTRIES)
    destination_country = _optional_choice(payload.get("destination_country"), "도착 국가", COUNTRIES)
    transit_country = _optional_choice(payload.get("transit_country"), "경유 국가", COUNTRIES)
    item_overrides, country_overrides = _validated_overrides(payload.get("overrides"))

    decision, country_checks = agent.evaluate(
        airline,
        item_text,
        route_type=route_type,
        origin_country=origin_country,
        destination_country=destination_country,
        transit_country=transit_country,
        **country_overrides,
        **item_overrides,
    )
    return {
        "decision": decision.to_dict(),
        "verification": verify_decision(decision),
        "status_labels": STATUS_KO,
        "country_checks": country_checks,
    }


def build_response_payload(agent: Any, payload: Any) -> dict[str, Any]:
    """Build the complete response shared by local HTTP and Vercel adapters."""
    response = build_decision_payload(agent, payload)
    answer_generator = getattr(agent, "answer_generator", None)
    response["ai_answer"] = (
        _disabled_ai_answer()
        if answer_generator is None
        else answer_generator.run(payload, response)
    )
    return response


def build_options_payload(agent: CountryAwareBaggageRAGAgent) -> dict[str, Any]:
    aliases = agent.dataset["dataset"]["airline_aliases"]
    airlines = [
        {
            "code": code,
            "name": airline_display_name(code, agent.rules),
            "aliases": values,
        }
        for code, values in aliases.items()
    ]
    item_types = [
        {"value": value, "label": label}
        for value, label in ITEM_NAMES.items()
        if value != "unknown"
    ]
    countries = [
        {"code": country["code"], "name": country["name_ko"]}
        for country in agent.country_dataset["countries"]
    ]
    return {
        "airlines": airlines,
        "item_types": item_types,
        "countries": countries,
        "dataset": {
            **agent.dataset["dataset"],
            "country_verified_date": agent.country_dataset["dataset"]["verified_date"],
            "country_scope": agent.country_dataset["dataset"]["scope"],
        },
        "examples": [
            {
                "label": "중국 국내선 보조배터리",
                "airline": "ASIANA",
                "route_type": "domestic",
                "origin_country": "China",
                "destination_country": "China",
                "item_text": "CCC 표시가 있는 보조배터리 20,000mAh 3.7V 1개",
            },
            {
                "label": "태국 출발 로션",
                "airline": "JEJU_AIR",
                "route_type": "international",
                "origin_country": "Thailand",
                "destination_country": "Korea",
                "item_text": "로션 80mL 1개",
            },
            {
                "label": "태국 입국 전자담배",
                "airline": "KOREAN_AIR",
                "route_type": "international",
                "origin_country": "Korea",
                "destination_country": "Thailand",
                "item_text": "전자담배 1개",
            },
            {
                "label": "중국 입국 주류",
                "airline": "ASIANA",
                "route_type": "international",
                "origin_country": "Korea",
                "destination_country": "China",
                "item_text": "위스키 750mL 2병",
            },
            {
                "label": "일본 국내선 보조배터리",
                "airline": "ASIANA",
                "route_type": "domestic",
                "origin_country": "Japan",
                "destination_country": "Japan",
                "item_text": "보조배터리 20,000mAh 3.7V 2개",
            },
            {
                "label": "일본 출발 국제선 액체",
                "airline": "KOREAN_AIR",
                "route_type": "international",
                "origin_country": "Japan",
                "destination_country": "Korea",
                "item_text": "로션 150mL 1개",
            },
            {
                "label": "일본 입국 육가공품",
                "airline": "JEJU_AIR",
                "route_type": "international",
                "origin_country": "Korea",
                "destination_country": "Japan",
                "item_text": "진공 포장 소시지 1개",
            },
            {
                "label": "일본 입국 주류",
                "airline": "ASIANA",
                "route_type": "international",
                "origin_country": "Korea",
                "destination_country": "Japan",
                "item_text": "위스키 750mL 4병",
            },
        ],
    }


def build_health_payload(agent: CountryAwareBaggageRAGAgent) -> dict[str, Any]:
    """Build the runtime diagnostics shared by local and serverless adapters."""
    runtime_model = getattr(agent, "runtime_model", {
        "provider": "local",
        "mode": "local",
        "embedding_model": None,
        "chat_model": None,
    })
    return {
        "status": "ok",
        "countries": [COUNTRY_NAMES[code] for code in sorted(COUNTRY_CODES)],
        "country_rules_verified": agent.country_dataset["dataset"]["verified_date"],
        "retrieval": {
            **runtime_model,
            "airline_rules": agent.retriever.dense_mode,
            "country_rules": agent.country_evaluator.retriever.dense_mode,
            "rank_fusion": "BM25 + dense RRF",
        },
    }


class BaggageWebHandler(BaseHTTPRequestHandler):
    """Serve the country-aware UI and JSON API."""

    agent: CountryAwareBaggageRAGAgent
    server_version = "CarryCheck/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: HTTPStatus) -> None:
        self._send_json({"error": message}, status)

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        try:
            target = (WEB_ROOT / relative).resolve()
            target.relative_to(WEB_ROOT.resolve())
        except (OSError, ValueError):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = target.read_bytes()
        content_type, _ = mimetypes.guess_type(target.name)
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(build_health_payload(self.agent))
            return
        if path == "/api/options":
            self._send_json(build_options_payload(self.agent))
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/decide":
            self._send_error_json("존재하지 않는 API입니다.", HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_json("Content-Length가 올바르지 않습니다.", HTTPStatus.BAD_REQUEST)
            return
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self._send_error_json("요청 크기가 올바르지 않습니다.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            response = build_response_payload(self.agent, payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error_json("올바른 JSON 요청이 아닙니다.", HTTPStatus.BAD_REQUEST)
            return
        except (RequestValidationError, ValueError) as exc:
            self._send_error_json(str(exc), HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        except Exception:
            LOGGER.exception("CarryCheck decision failed")
            self._send_error_json("판정 중 오류가 발생했습니다.", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json(response)
