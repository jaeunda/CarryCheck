"""Deterministic departure and arrival policies for China and Thailand."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from ..domain.baggage import BaggageDecision
from .country_agent import (
    COUNTRY_CODES,
    COUNTRY_NAMES,
    ENTRY_STATUS_RANK,
    CountryRuleEvaluator,
    _public_rule,
)
from .country_agent import (
    CountryAwareBaggageRAGAgent as BaseCountryAwareBaggageRAGAgent,
)


def _alcohol_percent(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|퍼센트|도)", text, re.I)
    return float(match.group(1)) if match else None


def _quantity_before_or_after(text: str, noun: str, trailing_unit: str) -> Optional[int]:
    patterns = (
        rf"(\d[\d,]*)\s*(?:{noun})",
        rf"(?:{noun})\s*(\d[\d,]*)\s*(?:{trailing_unit})?",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _tobacco_quantities(text: str) -> tuple[Optional[int], Optional[int], Optional[float]]:
    cigarettes = _quantity_before_or_after(
        text,
        r"개비|개피|sticks?|cigarettes?|담배",
        r"개|갑",
    )
    cigars = _quantity_before_or_after(text, r"시가|cigars?", r"개")
    grams_match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(?:g|그램)\b", text, re.I)
    grams = float(grams_match.group(1).replace(",", "")) if grams_match else None
    return cigarettes, cigars, grams


class CompleteCountryRuleEvaluator(CountryRuleEvaluator):
    """Apply customs thresholds without asking the retrieval model to decide."""

    def _allowance_rule(
        self,
        rule: dict[str, Any],
        decision: BaggageDecision,
    ) -> dict[str, Any]:
        if rule["item_type"] == "alcohol":
            volume = self._alcohol_volume_ml(decision)
            if volume is None:
                return _public_rule(
                    rule,
                    status="review_required",
                    message=f"주류 총량을 확인해야 합니다. {rule['rule_text']}",
                )
            if rule["country"] == "Thailand":
                if volume > 1000:
                    return _public_rule(
                        rule,
                        status="declaration_required",
                        message=f"확인 총량 {volume:g}mL로 태국 면세 한도 1L를 초과합니다.",
                    )
                return _public_rule(
                    rule,
                    status="within_allowance",
                    message=f"확인 총량 {volume:g}mL가 1L 한도 이내입니다.",
                )

            if volume < 1500:
                return _public_rule(
                    rule,
                    status="within_allowance",
                    message=f"확인 총량 {volume:g}mL가 중국 신고 기준 1,500mL 미만입니다.",
                )
            percentage = _alcohol_percent(decision.item.raw_text)
            if percentage is None:
                return _public_rule(
                    rule,
                    status="review_required",
                    message=(
                        f"확인 총량 {volume:g}mL입니다. 중국 1,500mL 기준 적용을 위해 "
                        "알코올 도수(12% 이상 여부)를 확인하세요."
                    ),
                )
            if percentage >= 12:
                return _public_rule(
                    rule,
                    status="declaration_required",
                    message=(
                        f"확인 총량 {volume:g}mL·도수 {percentage:g}%로 "
                        "중국 세관 신고 기준에 해당합니다."
                    ),
                )
            return _public_rule(
                rule,
                status="within_allowance",
                message=(
                    f"확인 도수 {percentage:g}%로 이 규정의 12% 이상 주류 "
                    "신고 기준에는 해당하지 않습니다."
                ),
            )

        cigarettes, cigars, grams = _tobacco_quantities(decision.item.raw_text)
        if cigarettes is None and cigars is None and grams is None:
            return _public_rule(
                rule,
                status="review_required",
                message=f"담배 종류별 수량 또는 중량을 확인해야 합니다. {rule['rule_text']}",
            )
        if rule["country"] == "China":
            exceeds = any((
                cigarettes is not None and cigarettes >= 400,
                cigars is not None and cigars >= 100,
                grams is not None and grams >= 500,
            ))
            if exceeds:
                return _public_rule(
                    rule,
                    status="declaration_required",
                    message=rule["rule_text"],
                )
            return _public_rule(
                rule,
                status="within_allowance",
                message="확인한 담배 수량·중량이 중국 안내 신고 기준 미만입니다.",
            )

        if cigars is not None and grams is None:
            return _public_rule(
                rule,
                status="review_required",
                message="태국의 시가·연초 한도는 중량 기준이므로 총중량(g)을 확인하세요.",
            )
        if (
            (cigarettes is not None and cigarettes > 200)
            or (grams is not None and grams > 250)
        ):
            return _public_rule(
                rule,
                status="declaration_required",
                message=rule["rule_text"],
            )
        return _public_rule(
            rule,
            status="within_allowance",
            message="확인한 담배 수량·중량이 태국 면세 한도 이내입니다.",
        )

    def apply_customs(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        destination_country: Optional[str],
        route_type: Optional[str],
    ) -> tuple[str, list[dict[str, Any]]]:
        status, selected = super().apply_customs(
            decision,
            origin_country=origin_country,
            destination_country=destination_country,
            route_type=route_type,
        )
        if decision.item.item_type == "e_cigarette":
            selected = [
                rule
                for rule in selected
                if rule["rule_id"] != "TH-CUSTOMS-TOBACCO"
            ]
            status = max(
                (entry["status"] for entry in selected),
                key=lambda value: ENTRY_STATUS_RANK.get(value, 0),
                default="not_applicable",
            )
        return status, selected


def _journey_status(aviation_status: str, entry_status: str) -> str:
    if "prohibited" in {aviation_status, entry_status}:
        return "prohibited"
    if aviation_status == "needs_information" or entry_status == "review_required":
        return "needs_information"
    if aviation_status == "conditional" or entry_status in {
        "conditional",
        "declaration_required",
    }:
        return "conditional"
    return "allowed"


class CountryAwareBaggageRAGAgent(BaseCountryAwareBaggageRAGAgent):
    """Combine airline, China, and Thailand decisions into one journey result."""

    def __init__(
        self,
        data_path: str | Path | None = None,
        *,
        country_data_path: str | Path | None = None,
        embedding_client: Any = None,
        embedding_model: str = "furiosa-ai/Qwen3-Embedding-8B",
    ):
        super().__init__(
            data_path,
            country_data_path=country_data_path,
            embedding_client=embedding_client,
            embedding_model=embedding_model,
        )
        self.country_evaluator = CompleteCountryRuleEvaluator(
            self.country_dataset,
            embedding_client=embedding_client,
            embedding_model=embedding_model,
        )

    def evaluate(
        self,
        airline: str,
        item_text: str,
        **kwargs: Any,
    ) -> tuple[BaggageDecision, dict[str, Any]]:
        overrides = dict(kwargs)
        normalized = str(item_text or "").lower()
        alcohol_keywords = (
            "술",
            "주류",
            "와인",
            "위스키",
            "맥주",
            "소주",
            "alcohol",
            "wine",
            "whisky",
            "whiskey",
            "beer",
        )
        if "item_type" not in overrides and any(
            keyword in normalized for keyword in alcohol_keywords
        ):
            overrides["item_type"] = "liquid"

        decision, context = super().evaluate(airline, item_text, **overrides)
        if decision.carry_on.status == "prohibited":
            decision.missing_information = [
                value
                for value in decision.missing_information
                if "CCC(3C)" not in value
            ]
        context["journey_status"] = _journey_status(
            decision.overall,
            context["entry_status"],
        )
        return decision, context


__all__ = [
    "COUNTRY_CODES",
    "COUNTRY_NAMES",
    "CompleteCountryRuleEvaluator",
    "CountryAwareBaggageRAGAgent",
]
