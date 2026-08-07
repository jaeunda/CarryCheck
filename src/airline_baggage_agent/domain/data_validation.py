"""Fail-fast validation for the versioned rule datasets."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

BAGGAGE_STATUSES = {"allowed", "conditional", "prohibited", "needs_information"}
COUNTRY_STATUSES = {
    "information",
    "conditional",
    "review_required",
    "declaration_required",
    "prohibited",
}
ROUTE_SCOPES = {"all", "domestic", "international"}


def load_json_dataset(path: str | Path) -> dict[str, Any]:
    """Load a JSON object while rejecting duplicate keys at every nesting level."""
    target = Path(path)

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"{target} contains a duplicate JSON key: {key}")
            value[key] = item
        return value

    result = json.loads(
        target.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    return _require_mapping(result, str(target))


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _require_string_list(value: Any, label: str) -> list[str]:
    items = _require_list(value, label)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{label} must contain only non-empty strings")
    return items


def _require_fields(value: dict[str, Any], fields: Iterable[str], label: str) -> None:
    missing = sorted(field for field in fields if value.get(field) in (None, ""))
    if missing:
        raise ValueError(f"{label} is missing required fields: {', '.join(missing)}")


def _validate_date(value: Any, label: str) -> None:
    try:
        date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format") from exc


def _validate_source(rule: dict[str, Any], label: str) -> None:
    parsed = urlparse(str(rule["source_url"]))
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label}.source_url must be an absolute HTTPS URL")
    _validate_date(rule["verified_date"], f"{label}.verified_date")
    if rule.get("effective_from"):
        _validate_date(rule["effective_from"], f"{label}.effective_from")


def _validate_common(dataset: Any, source: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = _require_mapping(dataset, source)
    metadata = _require_mapping(root.get("dataset"), f"{source}.dataset")
    _require_fields(metadata, ("name", "version", "verified_date", "scope", "notice"), f"{source}.dataset")
    _validate_date(metadata["version"], f"{source}.dataset.version")
    _validate_date(metadata["verified_date"], f"{source}.dataset.verified_date")
    rules = _require_list(root.get("rules"), f"{source}.rules")
    if not rules:
        raise ValueError(f"{source}.rules must not be empty")

    ids: set[str] = set()
    for index, raw_rule in enumerate(rules):
        rule = _require_mapping(raw_rule, f"{source}.rules[{index}]")
        rule_id = str(rule.get("rule_id") or "")
        if not rule_id:
            raise ValueError(f"{source}.rules[{index}] is missing rule_id")
        if rule_id in ids:
            raise ValueError(f"{source} has duplicate rule_id: {rule_id}")
        ids.add(rule_id)
    return root, rules


def validate_baggage_dataset(dataset: Any, *, source: str = "baggage dataset") -> None:
    """Validate airline baggage rules before constructing indexes."""
    root, rules = _validate_common(dataset, source)
    aliases = _require_mapping(root["dataset"].get("airline_aliases"), f"{source}.dataset.airline_aliases")
    if not aliases:
        raise ValueError(f"{source}.dataset.airline_aliases must not be empty")
    for airline, values in aliases.items():
        _require_string_list(values, f"{source}.dataset.airline_aliases.{airline}")

    required = (
        "rule_id", "airline", "airline_name", "item_type", "item_name", "route_scope",
        "rule_text", "carry_on", "checked", "source_title", "source_url", "verified_date",
    )
    for index, rule in enumerate(rules):
        label = f"{source}.rules[{index}]"
        _require_fields(rule, required, label)
        if rule["route_scope"] not in ROUTE_SCOPES:
            raise ValueError(f"{label}.route_scope is invalid")
        for field in ("carry_on", "checked"):
            if rule[field] not in BAGGAGE_STATUSES:
                raise ValueError(f"{label}.{field} is invalid")
        for field in ("aliases", "conditions", "exceptions"):
            _require_string_list(rule.get(field), f"{label}.{field}")
        for field in ("capacity_limits", "count_limits"):
            _require_mapping(rule.get(field), f"{label}.{field}")
        _validate_source(rule, label)


def validate_country_dataset(dataset: Any, *, source: str = "country dataset") -> None:
    """Validate departure-security and arrival-policy rules."""
    root, rules = _validate_common(dataset, source)
    countries = root.get("countries")
    if countries is None and root.get("country") is not None:
        countries = [root["country"]]
    countries = _require_list(countries, f"{source}.countries")
    country_codes = set()
    for index, country in enumerate(countries):
        country = _require_mapping(country, f"{source}.countries[{index}]")
        _require_fields(country, ("code", "name_ko"), f"{source}.countries[{index}]")
        if country["code"] in country_codes:
            raise ValueError(f"{source} has duplicate country code: {country['code']}")
        country_codes.add(country["code"])

    required = (
        "rule_id", "country", "country_name", "direction", "domain", "item_type",
        "route_scope", "status", "rule_text", "source_title", "source_url", "verified_date",
    )
    for index, rule in enumerate(rules):
        label = f"{source}.rules[{index}]"
        _require_fields(rule, required, label)
        if rule["country"] not in country_codes:
            raise ValueError(f"{label}.country is not declared in countries")
        if rule["direction"] not in {"departure", "arrival"}:
            raise ValueError(f"{label}.direction is invalid")
        if rule["route_scope"] not in ROUTE_SCOPES:
            raise ValueError(f"{label}.route_scope is invalid")
        if rule["status"] not in COUNTRY_STATUSES:
            raise ValueError(f"{label}.status is invalid")
        for field in ("keywords", "conditions"):
            _require_string_list(rule.get(field), f"{label}.{field}")
        _validate_source(rule, label)


__all__ = ["load_json_dataset", "validate_baggage_dataset", "validate_country_dataset"]
