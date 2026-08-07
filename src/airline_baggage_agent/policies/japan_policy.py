"""Add Japan aviation, customs, and quarantine rules to the country layer."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Optional

from ..domain.baggage import BaggageDecision
from ..domain.data_validation import load_json_dataset, validate_country_dataset
from .country_agent import (
    COUNTRY_NAMES as BASE_COUNTRY_NAMES,
)
from .country_agent import (
    ENTRY_STATUS_RANK,
    _append_unique,
    _public_rule,
    _recompute_overall,
)
from .country_policy import (
    CompleteCountryRuleEvaluator as BaseCompleteCountryRuleEvaluator,
)
from .country_policy import (
    CountryAwareBaggageRAGAgent as BaseCountryAwareBaggageRAGAgent,
)

COUNTRY_NAMES = {**BASE_COUNTRY_NAMES, "Japan": "일본"}
COUNTRY_CODES = frozenset(COUNTRY_NAMES)


def load_japan_rule_dataset(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else Path(__file__).resolve().parents[1] / "data" / "japan_rules.json"
    dataset = load_json_dataset(target)
    validate_country_dataset(dataset, source=str(target))
    return dataset


def _contains(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _is_actual_plant(text: str) -> bool:
    """Avoid substring matches such as the ``배`` in ``담배``."""
    normalized = text.lower()
    explicit = (
        "과일", "사과", "감귤", "귤", "망고", "리치", "채소", "고추", "씨앗",
        "묘목", "꽃", "곡물", "콩", "흙", "토양", "fruit", "vegetable", "seed",
        "plant", "soil",
    )
    return any(word in normalized for word in explicit) or bool(
        re.search(r"(?:^|\s)배\s*(?:\d+\s*개|과일|fruit|$)", normalized)
    )


def _integer(patterns: tuple[str, ...], text: str) -> Optional[int]:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _number(pattern: str, text: str) -> Optional[float]:
    match = re.search(pattern, text, re.I)
    return float(match.group(1).replace(",", "")) if match else None


def _public_with(rule: dict[str, Any], status: str, message: str) -> dict[str, Any]:
    return _public_rule(rule, status=status, message=message)


class JapanCountryRuleEvaluator(BaseCompleteCountryRuleEvaluator):
    """Deterministically apply Japan departure and entry thresholds."""

    def apply_aviation(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        route_type: Optional[str],
        ccc_mark: Optional[bool],
        recalled_battery: bool,
    ) -> list[dict[str, Any]]:
        applied = super().apply_aviation(
            decision,
            origin_country=origin_country,
            route_type=route_type,
            ccc_mark=ccc_mark,
            recalled_battery=recalled_battery,
        )
        if origin_country != "Japan":
            return applied

        item = decision.item
        if item.item_type == "power_bank":
            rule = self._apply_source(decision, "JP-MLIT-POWER-BANK-2026")
            applied.append(_public_rule(rule))
            if item.watt_hours is not None and item.watt_hours > 160:
                decision.carry_on.status = "prohibited"
                decision.carry_on.reasons.append("일본 출발편 보조배터리 상한 160Wh를 초과합니다.")
            if item.count is None:
                if decision.carry_on.status != "prohibited":
                    decision.carry_on.status = "needs_information"
                _append_unique(decision.missing_information, "일본 출발편 보조배터리 수량")
            elif item.count > 2:
                decision.carry_on.status = "prohibited"
                decision.carry_on.reasons.append("2026년 4월 24일 시행된 일본 기준의 승객당 최대 2개를 초과합니다.")
            else:
                decision.carry_on.reasons.append(f"보조배터리 {item.count}개가 일본 출발편 수량 상한 이내입니다.")
            _append_unique(decision.conditions, "기내에서 보조배터리를 충전하거나 보조배터리로 다른 기기를 충전하지 않습니다.")
            _append_unique(decision.conditions, "보조배터리는 머리 위 선반이 아닌 상태를 확인할 수 있는 곳에 보관합니다.")
        elif item.item_type == "liquid":
            rule_id = "JP-MLIT-LIQUID-INTERNATIONAL" if route_type == "international" else "JP-DOMESTIC-LIQUID-INFO"
            rule = self._apply_source(decision, rule_id)
            applied.append(_public_rule(rule))
        _recompute_overall(decision)
        return applied

    @staticmethod
    def _japan_alcohol(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        count = decision.item.count
        if count is None:
            return _public_with(rule, "review_required", "일본 주류 면세 한도는 병 수 기준이므로 약 760mL들이 병 수를 확인하세요.")
        if count > 3:
            return _public_with(rule, "declaration_required", f"확인 수량 {count}병으로 일본 주류 면세 한도 3병을 초과합니다.")
        return _public_with(rule, "within_allowance", f"확인 수량 {count}병이 일본 주류 면세 한도 이내입니다.")

    @staticmethod
    def _japan_tobacco(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        text = decision.item.raw_text
        normalized = text.lower()
        if any(word in normalized for word in ("가열식 담배", "아이코스", "iqos", "glo", "ploom")):
            heated_packages = _integer((
                r"(\d[\d,]*)\s*(?:갑|팩|packages?)",
                r"(?:가열식\s*담배|아이코스|iqos|glo|ploom)\s*(\d[\d,]*)\s*(?:갑|팩|개|packages?)?",
            ), text)
            if heated_packages is None:
                return _public_with(rule, "review_required", "가열식 담배의 개별 포장 수를 확인하세요.")
            if heated_packages > 10:
                return _public_with(
                    rule,
                    "declaration_required",
                    f"가열식 담배 {heated_packages}개 포장으로 일본 면세 한도 10개 포장을 초과합니다.",
                )
            return _public_with(
                rule,
                "within_allowance",
                f"가열식 담배 {heated_packages}개 포장이 일본 면세 한도 이내입니다.",
            )

        cigarettes = _integer((
            r"(\d[\d,]*)\s*(?:개비|개피|sticks?|cigarettes?)",
            r"(?:담배|궐련|cigarettes?)\s*(\d[\d,]*)\s*(?:개비|개피|개|sticks?)?",
        ), text)
        cigars = _integer((
            r"(\d[\d,]*)\s*(?:시가|cigars?)",
            r"(?:시가|cigars?)\s*(\d[\d,]*)\s*(?:개)?",
        ), text)
        grams = _number(r"(\d[\d,]*(?:\.\d+)?)\s*(?:g|그램)\b", text)
        known = [value for value in (cigarettes, cigars, grams) if value is not None]
        if not known:
            return _public_with(rule, "review_required", "담배 종류와 개비·포장 수 또는 중량을 확인하세요.")
        types = sum(value is not None for value in (cigarettes, cigars, grams))
        if types > 1:
            return _public_with(rule, "review_required", "여러 종류의 담배는 250g 상당 합산 한도를 세관에 확인해야 합니다.")
        exceeds = any((
            cigarettes is not None and cigarettes > 200,
            cigars is not None and cigars > 50,
            grams is not None and grams > 250,
        ))
        if exceeds:
            return _public_with(rule, "declaration_required", rule["rule_text"])
        return _public_with(rule, "within_allowance", "확인한 담배 수량·중량이 일본 면세 한도 이내입니다.")

    @staticmethod
    def _japan_perfume(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        total = decision.item.total_ml
        if total is None and decision.item.container_ml is not None:
            total = decision.item.container_ml * (decision.item.count or 1)
        if total is None:
            return _public_with(rule, "review_required", "향수 총량을 mL 또는 온스로 확인하세요.")
        if total > 56:
            return _public_with(rule, "declaration_required", f"확인 총량 {total:g}mL로 일본 향수 면세 한도 약 56mL를 초과합니다.")
        return _public_with(rule, "within_allowance", f"확인 총량 {total:g}mL가 일본 향수 면세 한도 이내입니다.")

    @staticmethod
    def _japan_valued_goods(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        value = _number(r"(\d[\d,]*(?:\.\d+)?)\s*(?:엔|円|jpy|yen)\b", decision.item.raw_text)
        if value is None:
            return _public_with(rule, "review_required", "일반 물품의 해외 시가 합계와 단일 물품 가격을 엔화로 확인하세요.")
        if value >= 200000:
            return _public_with(rule, "declaration_required", f"확인 가격 {value:,.0f}엔으로 일반 물품 면세 기준 200,000엔 미만을 충족하지 않습니다.")
        return _public_with(rule, "within_allowance", f"확인 가격 {value:,.0f}엔이 일반 물품 합계 면세 기준 미만입니다.")

    @staticmethod
    def _japan_currency_gold(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        text = decision.item.raw_text
        if _contains(text, ["금괴", "골드바", "금 제품", "gold bullion"]):
            weight = decision.item.weight_kg
            if weight is not None and weight > 1:
                return _public_with(rule, "declaration_required", "금제품 휴대품 신고와 함께 순도 90% 이상 금괴 1kg 초과 지급수단 신고 여부를 확인하세요.")
            return _public_with(rule, "declaration_required", "금괴·금제품은 수량과 무관하게 일본 휴대품 신고서에 표시해야 합니다.")
        value = _number(r"(\d[\d,]*(?:\.\d+)?)\s*(?:엔|円|jpy|yen)\b", text)
        if value is None:
            return _public_with(rule, "review_required", "현금·수표·유가증권의 엔화 환산 총액을 확인하세요.")
        if value > 1000000:
            return _public_with(rule, "declaration_required", f"확인 금액 {value:,.0f}엔으로 100만 엔 초과 지급수단 신고 대상입니다.")
        return _public_with(rule, "within_allowance", f"확인 금액 {value:,.0f}엔이 지급수단 별도 신고 경계값 이하입니다.")

    @staticmethod
    def _japan_plant(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        text = decision.item.raw_text
        if _contains(text, ["흙", "토양", "soil", "사과", "배 ", "감귤", "망고", "리치", "고추"]):
            return _public_with(rule, "prohibited", "입력한 품목은 일본의 대표적인 반입 금지 토양·과일·채소 범주에 해당합니다. 생산국별 조건을 최종 확인하세요.")
        return _public_with(rule, "review_required", rule["rule_text"])

    @staticmethod
    def _japan_medicine(rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        text = decision.item.raw_text
        months = _number(r"(\d[\d,]*(?:\.\d+)?)\s*(?:개월|months?)", text)
        prescription = _contains(text, ["처방약", "처방 의약품", "prescription", "주사제", "주사기"])
        cosmetic = _contains(text, ["화장품", "cosmetic"])
        if cosmetic and decision.item.count is not None:
            if decision.item.count > 24:
                return _public_with(rule, "review_required", f"화장품 {decision.item.count}개로 품목당 24개 무신고 범위를 초과합니다. 수입확인을 준비하세요.")
            return _public_with(rule, "within_allowance", f"화장품 {decision.item.count}개가 품목당 24개 범위 이내입니다.")
        if months is None:
            return _public_with(rule, "review_required", "의약품 종류, 성분과 여행 중 사용할 개월분을 확인하세요.")
        limit = 1 if prescription else 2
        if months > limit:
            return _public_with(rule, "review_required", f"확인 수량 {months:g}개월분으로 무신고 범위 {limit}개월분을 초과합니다. 출발 전 Import Confirmation을 신청하세요.")
        return _public_with(rule, "within_allowance", f"확인 수량 {months:g}개월분이 안내된 개인 사용 범위 이내입니다. 통제 성분 여부는 별도 확인하세요.")

    def apply_customs(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        destination_country: Optional[str],
        route_type: Optional[str],
    ) -> tuple[str, list[dict[str, Any]]]:
        if destination_country != "Japan":
            return super().apply_customs(
                decision,
                origin_country=origin_country,
                destination_country=destination_country,
                route_type=route_type,
            )
        if route_type != "international" or origin_country == destination_country:
            return "not_applicable", []

        text = decision.item.raw_text
        selected: list[dict[str, Any]] = []
        for rule in self.rules:
            if rule["country"] != "Japan" or rule["domain"] != "customs":
                continue
            rule_id = rule["rule_id"]
            matches = rule["item_type"] == "all" or _contains(text, rule.get("keywords", []))
            if not matches:
                continue
            if rule_id == "JP-CUSTOMS-ALCOHOL":
                selected.append(self._japan_alcohol(rule, decision))
            elif rule_id == "JP-CUSTOMS-TOBACCO":
                if decision.item.item_type != "e_cigarette":
                    selected.append(self._japan_tobacco(rule, decision))
            elif rule_id == "JP-CUSTOMS-PERFUME":
                selected.append(self._japan_perfume(rule, decision))
            elif rule_id == "JP-CUSTOMS-OTHER-GOODS":
                if not _contains(text, ["현금", "수표", "유가증권", "금괴", "골드바"]):
                    selected.append(self._japan_valued_goods(rule, decision))
            elif rule_id == "JP-CUSTOMS-CURRENCY-GOLD":
                selected.append(self._japan_currency_gold(rule, decision))
            elif rule_id == "JP-MAFF-PLANT-QUARANTINE":
                selected.append(self._japan_plant(rule, decision))
            elif rule_id == "JP-MHLW-MEDICINE":
                selected.append(self._japan_medicine(rule, decision))
            else:
                selected.append(_public_rule(rule))

        if not _is_actual_plant(text):
            selected = [
                entry for entry in selected
                if entry["rule_id"] != "JP-MAFF-PLANT-QUARANTINE"
            ]

        status = max(
            (entry["status"] for entry in selected),
            key=lambda value: ENTRY_STATUS_RANK.get(value, 0),
            default="not_applicable",
        )
        return status, selected

    def retrieve(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        destination_country: Optional[str],
        transit_country: Optional[str],
        route_type: Optional[str],
    ) -> list[dict[str, Any]]:
        involved = {country for country in (origin_country, destination_country, transit_country) if country}
        involved &= set(COUNTRY_CODES) - {"Korea"}
        if not involved:
            return []
        query = " ".join(filter(None, [
            decision.airline_name,
            decision.item.raw_text,
            COUNTRY_NAMES.get(origin_country or "", origin_country),
            "출발",
            COUNTRY_NAMES.get(destination_country or "", destination_country),
            "도착",
            COUNTRY_NAMES.get(transit_country or "", transit_country),
            "경유" if transit_country else None,
        ]))
        results = self.retriever.search(query, route_type=route_type, top_k=len(self.rules))
        return [result for result in results if result["country"] in involved][:10]


class CountryAwareBaggageRAGAgent(BaseCountryAwareBaggageRAGAgent):
    """Provide country decisions for Korea, China, Thailand, and Japan routes."""

    def __init__(
        self,
        data_path: str | Path | None = None,
        *,
        country_data_path: str | Path | None = None,
        japan_data_path: str | Path | None = None,
        embedding_client: Any = None,
        embedding_model: str = "furiosa-ai/Qwen3-Embedding-8B",
    ):
        super().__init__(
            data_path,
            country_data_path=country_data_path,
            embedding_client=embedding_client,
            embedding_model=embedding_model,
        )
        japan_dataset = load_japan_rule_dataset(japan_data_path)
        merged = copy.deepcopy(self.country_dataset)
        merged["countries"].append(japan_dataset["country"])
        merged["rules"].extend(japan_dataset["rules"])
        merged["dataset"]["name"] = "중국·태국·일본 출발 보안 및 입국 규정"
        merged["dataset"]["scope"] = "중국·태국·일본 출발 보안과 세 국가 입국 시 주요 세관·검역 규정"
        merged["dataset"]["notice"] = japan_dataset["dataset"]["notice"]
        merged["dataset"]["verified_date"] = max(
            merged["dataset"]["verified_date"],
            japan_dataset["dataset"]["verified_date"],
        )
        validate_country_dataset(merged, source="merged country dataset")
        self.country_dataset = merged
        self.country_evaluator = JapanCountryRuleEvaluator(
            merged,
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
        if "count" not in overrides:
            count_match = re.search(r"(\d+)\s*(?:items?|bottles?|packs?|units?)\b", normalized)
            if count_match:
                overrides["count"] = int(count_match.group(1))
        if "item_type" not in overrides:
            if any(word in normalized for word in ("mobile battery", "モバイルバッテリー")):
                overrides["item_type"] = "power_bank"
            elif any(
                word in normalized
                for word in ("lotion", "perfume", "shampoo", "beverage", "ローション", "香水", "液体")
            ):
                overrides["item_type"] = "liquid"

        decision, context = super().evaluate(airline, item_text, **overrides)
        context["origin_country_name"] = COUNTRY_NAMES.get(context.get("origin_country") or "", context.get("origin_country"))
        context["destination_country_name"] = COUNTRY_NAMES.get(context.get("destination_country") or "", context.get("destination_country"))
        context["transit_country_name"] = COUNTRY_NAMES.get(context.get("transit_country") or "", context.get("transit_country"))
        if context.get("transit_country") == "Japan":
            notice = "일본에서 환승 보안검색을 다시 받으면 일본의 보조배터리·액체 규정이 적용될 수 있습니다."
            if notice not in context["transit_notices"]:
                context["transit_notices"].append(notice)
        return decision, context


__all__ = [
    "COUNTRY_CODES",
    "COUNTRY_NAMES",
    "CountryAwareBaggageRAGAgent",
    "JapanCountryRuleEvaluator",
    "load_japan_rule_dataset",
]
