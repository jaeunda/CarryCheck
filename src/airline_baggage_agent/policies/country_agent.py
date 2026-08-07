"""Country-aware layer for China and Thailand departure and entry policies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from ..domain.baggage import (
    BaggageDecision,
    BaggageRAGAgent,
    HybridRuleRetriever,
    QwenEmbeddingAdapter,
)
from ..domain.data_validation import load_json_dataset, validate_country_dataset

COUNTRY_NAMES = {"Korea": "대한민국", "China": "중국", "Thailand": "태국"}
COUNTRY_CODES = frozenset(COUNTRY_NAMES)

ENTRY_STATUS_RANK = {
    "not_applicable": 0,
    "information": 1,
    "within_allowance": 1,
    "conditional": 2,
    "review_required": 3,
    "declaration_required": 4,
    "prohibited": 5,
}


def load_country_rule_dataset(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else Path(__file__).resolve().parents[1] / "data" / "country_rules.json"
    dataset = load_json_dataset(target)
    validate_country_dataset(dataset, source=str(target))
    return dataset


def build_country_rule_chunks(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for rule in rules:
        direction = "출발 보안" if rule["direction"] == "departure" else "도착 세관·검역"
        text = (
            f"국가 {rule['country_name']} ({rule['country']}) | {direction} | "
            f"영역 {rule['domain']} | 노선 {rule['route_scope']} | 물품 {rule['item_type']}\n"
            f"{rule['rule_text']}\n조건: {' '.join(rule.get('conditions', []))}\n"
            f"검색어: {' '.join(rule.get('keywords', []))}"
        )
        chunks.append({
            "chunk_id": f"{rule['rule_id']}::country",
            "rule_id": rule["rule_id"],
            "airline": "IATA",
            "airline_name": rule["country_name"],
            "country": rule["country"],
            "domain": rule["domain"],
            "direction": rule["direction"],
            "item_type": rule["item_type"],
            "route_scope": rule["route_scope"],
            "section": "country_rule",
            "text": text,
            "source_url": rule["source_url"],
        })
    return chunks


def infer_route_type(
    origin_country: Optional[str],
    destination_country: Optional[str],
    requested_route_type: Optional[str],
) -> tuple[Optional[str], list[str]]:
    warnings: list[str] = []
    inferred: Optional[str] = None
    if origin_country and destination_country:
        inferred = "domestic" if origin_country == destination_country else "international"
    if inferred and requested_route_type and inferred != requested_route_type:
        warnings.append("출발·도착 국가와 선택한 노선이 달라 국가 기준으로 노선을 자동 보정했습니다.")
    return inferred or requested_route_type, warnings


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _recompute_overall(decision: BaggageDecision) -> None:
    statuses = {decision.carry_on.status, decision.checked.status}
    if statuses == {"prohibited"}:
        decision.overall = "prohibited"
    elif "needs_information" in statuses:
        decision.overall = "needs_information"
    elif "conditional" in statuses:
        decision.overall = "conditional"
    else:
        decision.overall = "allowed"


def _rule_source(rule: dict[str, Any]) -> dict[str, str]:
    return {
        "rule_id": rule["rule_id"],
        "title": rule["source_title"],
        "url": rule["source_url"],
        "verified_date": rule["verified_date"],
    }


def _public_rule(rule: dict[str, Any], *, status: Optional[str] = None, message: Optional[str] = None) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "country": rule["country"],
        "country_name": rule["country_name"],
        "domain": rule["domain"],
        "status": status or rule["status"],
        "message": message or rule["rule_text"],
        "conditions": list(rule.get("conditions", [])),
        "effective_from": rule.get("effective_from"),
        "source": _rule_source(rule),
    }


class CountryRuleEvaluator:
    def __init__(
        self,
        dataset: dict[str, Any],
        *,
        embedding_client: Any = None,
        embedding_model: str = "furiosa-ai/Qwen3-Embedding-8B",
    ):
        self.dataset = dataset
        self.rules = dataset["rules"]
        self.rule_by_id = {rule["rule_id"]: rule for rule in self.rules}
        chunks = build_country_rule_chunks(self.rules)
        embedder = QwenEmbeddingAdapter(embedding_client, embedding_model) if embedding_client else None
        self.retriever = HybridRuleRetriever(chunks, embedder=embedder)

    def _apply_source(self, decision: BaggageDecision, rule_id: str) -> dict[str, Any]:
        rule = self.rule_by_id[rule_id]
        if rule_id not in decision.matched_rule_ids:
            decision.matched_rule_ids.append(rule_id)
        if not any(source["rule_id"] == rule_id for source in decision.sources):
            decision.sources.append(_rule_source(rule))
        return rule

    @staticmethod
    def _remove_domestic_liquid_reason(decision: BaggageDecision) -> None:
        decision.carry_on.reasons = [
            reason for reason in decision.carry_on.reasons
            if "국내선에는 국제선 100mL 보안 제한" not in reason
        ]

    def _apply_china_power_bank(
        self,
        decision: BaggageDecision,
        route_type: Optional[str],
        ccc_mark: Optional[bool],
        recalled_battery: bool,
    ) -> list[dict[str, Any]]:
        applied = [_public_rule(self._apply_source(decision, "CN-CAAC-POWER-BANK"))]
        if route_type != "domestic":
            return applied

        rule = self._apply_source(decision, "CN-CAAC-CCC-DOMESTIC-2025")
        applied.append(_public_rule(rule))
        if recalled_battery:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("중국 국내선에서 리콜 대상 보조배터리는 기내 반입이 금지됩니다.")
        elif ccc_mark is False:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("중국 국내선 필수 조건인 명확한 CCC(3C) 표시가 없습니다.")
        elif ccc_mark is None:
            if decision.carry_on.status != "prohibited":
                decision.carry_on.status = "needs_information"
            _append_unique(decision.missing_information, "중국 국내선용 CCC(3C) 표시 및 리콜 여부")
        else:
            decision.carry_on.reasons.append("중국 국내선용 CCC(3C) 표시를 확인했습니다.")
        return applied

    def _apply_china_liquid(self, decision: BaggageDecision, route_type: Optional[str]) -> list[dict[str, Any]]:
        rule_id = "CN-CAAC-LIQUID-DOMESTIC" if route_type == "domestic" else "CN-CAAC-LIQUID-INTERNATIONAL"
        rule = self._apply_source(decision, rule_id)
        if route_type != "domestic":
            return [_public_rule(rule)]

        self._remove_domestic_liquid_reason(decision)
        text = decision.item.raw_text.lower()
        medical_or_infant = decision.item.medical_exception or any(
            keyword in text for keyword in ("의약품", "처방약", "유아식", "분유", "baby food", "medicine")
        )
        cosmetic = any(keyword in text for keyword in (
            "화장품", "로션", "크림", "샴푸", "린스", "향수", "치약", "면도", "마스카라",
            "cosmetic", "lotion", "toothpaste", "shaving",
        ))

        if medical_or_infant:
            decision.carry_on.status = "conditional"
            decision.carry_on.reasons.append("중국 국내선 의약품·유아용 액체 예외는 보안검색 확인이 필요합니다.")
        elif not cosmetic:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("중국 국내선은 일반 액체류의 기내 반입을 허용하지 않습니다.")
        elif decision.item.container_ml is None:
            decision.carry_on.status = "needs_information"
            _append_unique(decision.missing_information, "중국 국내선 화장품 용기의 표시 용량")
        elif decision.item.container_ml > 100:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("중국 국내선 화장품 용기가 100mL 상한을 초과합니다.")
        elif decision.item.count is not None and decision.item.count > 1:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("중국 국내선 여행용 화장품은 같은 종류당 1개만 허용됩니다.")
        else:
            decision.carry_on.status = "conditional"
            decision.carry_on.reasons.append("100mL 이하 여행용 화장품 1개로, 개봉 보안검색을 조건으로 합니다.")
        return [_public_rule(rule)]

    def _apply_thailand_liquid(self, decision: BaggageDecision) -> list[dict[str, Any]]:
        rule = self._apply_source(decision, "TH-CAAT-LAGS-2026")
        self._remove_domestic_liquid_reason(decision)
        item = decision.item
        text = item.raw_text.lower()
        exempt = item.medical_exception or any(
            keyword in text for keyword in ("유아식", "분유", "baby food", "infant formula")
        )
        decision.carry_on.reasons = [
            reason for reason in decision.carry_on.reasons
            if "면세품 예외" not in reason
        ]
        if exempt:
            decision.carry_on.status = "conditional"
            decision.carry_on.reasons.append("태국 출발 의약품·영유아식 예외는 증빙과 보안검색이 필요합니다.")
        elif item.container_ml is None:
            decision.carry_on.status = "needs_information"
            _append_unique(decision.missing_information, "태국 출발편 액체 용기의 표시 용량")
        elif item.container_ml > 100:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("태국 출발편의 액체 용기 상한 100mL를 초과합니다.")
        elif item.total_ml is not None and item.total_ml > 1000:
            decision.carry_on.status = "prohibited"
            decision.carry_on.reasons.append("태국 출발편의 승객당 액체 총량 1L를 초과합니다.")
        else:
            decision.carry_on.status = "conditional"
            decision.carry_on.reasons.append("태국 출발 기준인 용기당 100mL·총 1L 이내입니다.")
        return [_public_rule(rule)]

    def apply_aviation(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        route_type: Optional[str],
        ccc_mark: Optional[bool],
        recalled_battery: bool,
    ) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        item_type = decision.item.item_type
        if origin_country == "China":
            if item_type == "power_bank":
                applied.extend(self._apply_china_power_bank(decision, route_type, ccc_mark, recalled_battery))
            elif item_type == "liquid":
                applied.extend(self._apply_china_liquid(decision, route_type))
        elif origin_country == "Thailand":
            if item_type in {"power_bank", "spare_battery"}:
                rule = self._apply_source(decision, "TH-CAAT-LITHIUM-BATTERY")
                applied.append(_public_rule(rule))
            elif item_type == "liquid":
                applied.extend(self._apply_thailand_liquid(decision))
        _recompute_overall(decision)
        return applied

    @staticmethod
    def _matches(rule: dict[str, Any], text: str, item_type: str) -> bool:
        if rule["item_type"] == item_type:
            return True
        return any(keyword.lower() in text for keyword in rule.get("keywords", []))

    @staticmethod
    def _alcohol_volume_ml(decision: BaggageDecision) -> Optional[float]:
        item = decision.item
        if item.total_ml is not None:
            return item.total_ml
        if item.container_ml is not None:
            return item.container_ml * (item.count or 1)
        return None

    @staticmethod
    def _tobacco_quantity(text: str) -> tuple[Optional[int], Optional[float]]:
        sticks_match = re.search(r"(\d[\d,]*)\s*(?:개비|개피|sticks?|cigarettes?)", text, re.I)
        grams_match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(?:g|그램)\b", text, re.I)
        sticks = int(sticks_match.group(1).replace(",", "")) if sticks_match else None
        grams = float(grams_match.group(1).replace(",", "")) if grams_match else None
        return sticks, grams

    def _allowance_rule(self, rule: dict[str, Any], decision: BaggageDecision) -> dict[str, Any]:
        if rule["item_type"] == "alcohol":
            volume = self._alcohol_volume_ml(decision)
            threshold = 1500.0 if rule["country"] == "China" else 1000.0
            if volume is None:
                return _public_rule(rule, status="review_required", message=f"주류 총량을 확인해야 합니다. {rule['rule_text']}")
            if volume >= threshold if rule["country"] == "China" else volume > threshold:
                return _public_rule(rule, status="declaration_required", message=f"확인 총량 {volume:g}mL: {rule['rule_text']}")
            return _public_rule(rule, status="within_allowance", message=f"확인 총량 {volume:g}mL가 안내 한도 이내입니다.")

        sticks, grams = self._tobacco_quantity(decision.item.raw_text)
        stick_limit = 400 if rule["country"] == "China" else 200
        gram_limit = 500.0 if rule["country"] == "China" else 250.0
        if sticks is None and grams is None:
            return _public_rule(rule, status="review_required", message=f"담배 개비 수 또는 중량을 확인해야 합니다. {rule['rule_text']}")
        exceeds = (sticks is not None and sticks >= stick_limit if rule["country"] == "China" else sticks is not None and sticks > stick_limit)
        exceeds = exceeds or (grams is not None and grams >= gram_limit if rule["country"] == "China" else grams is not None and grams > gram_limit)
        if exceeds:
            return _public_rule(rule, status="declaration_required", message=rule["rule_text"])
        return _public_rule(rule, status="within_allowance", message="확인 수량이 안내 한도 이내입니다.")

    def apply_customs(
        self,
        decision: BaggageDecision,
        *,
        origin_country: Optional[str],
        destination_country: Optional[str],
        route_type: Optional[str],
    ) -> tuple[str, list[dict[str, Any]]]:
        if not destination_country or route_type != "international" or origin_country == destination_country:
            return "not_applicable", []
        if destination_country not in {"China", "Thailand"}:
            return "not_applicable", []

        rules = [
            rule for rule in self.rules
            if rule["country"] == destination_country and rule["domain"] == "customs"
        ]
        text = decision.item.raw_text.lower()
        selected: list[dict[str, Any]] = []
        for rule in rules:
            if rule["item_type"] == "all":
                selected.append(_public_rule(rule))
            elif self._matches(rule, text, decision.item.item_type):
                if rule["item_type"] in {"alcohol", "tobacco"}:
                    selected.append(self._allowance_rule(rule, decision))
                else:
                    selected.append(_public_rule(rule))

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
        involved &= {"China", "Thailand"}
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
        return [result for result in results if result["country"] in involved][:8]


class CountryAwareBaggageRAGAgent(BaggageRAGAgent):
    """Deterministically apply China and Thailand policies after airline rules."""

    def __init__(
        self,
        data_path: str | Path | None = None,
        *,
        country_data_path: str | Path | None = None,
        embedding_client: Any = None,
        embedding_model: str = "furiosa-ai/Qwen3-Embedding-8B",
    ):
        super().__init__(data_path, embedding_client=embedding_client, embedding_model=embedding_model)
        self.country_dataset = load_country_rule_dataset(country_data_path)
        self.country_evaluator = CountryRuleEvaluator(
            self.country_dataset,
            embedding_client=embedding_client,
            embedding_model=embedding_model,
        )

    def evaluate(
        self,
        airline: str,
        item_text: str,
        *,
        route_type: Optional[str] = None,
        origin_country: Optional[str] = None,
        destination_country: Optional[str] = None,
        transit_country: Optional[str] = None,
        ccc_mark: Optional[bool] = None,
        recalled_battery: bool = False,
        **item_overrides: Any,
    ) -> tuple[BaggageDecision, dict[str, Any]]:
        effective_route, route_warnings = infer_route_type(origin_country, destination_country, route_type)
        decision = super().decide(
            airline,
            item_text,
            route_type=effective_route,
            origin_country=origin_country,
            **item_overrides,
        )
        aviation_rules = self.country_evaluator.apply_aviation(
            decision,
            origin_country=origin_country,
            route_type=effective_route,
            ccc_mark=ccc_mark,
            recalled_battery=recalled_battery,
        )
        entry_status, entry_rules = self.country_evaluator.apply_customs(
            decision,
            origin_country=origin_country,
            destination_country=destination_country,
            route_type=effective_route,
        )
        transit_notices: list[str] = []
        if transit_country in {"China", "Thailand"}:
            transit_notices.append(
                f"{COUNTRY_NAMES[transit_country]}에서 환승 보안검색을 다시 받으면 해당 국가의 출발 규정이 적용될 수 있습니다."
            )
        retrieved = self.country_evaluator.retrieve(
            decision,
            origin_country=origin_country,
            destination_country=destination_country,
            transit_country=transit_country,
            route_type=effective_route,
        )
        context = {
            "origin_country": origin_country,
            "origin_country_name": COUNTRY_NAMES.get(origin_country or "", origin_country),
            "destination_country": destination_country,
            "destination_country_name": COUNTRY_NAMES.get(destination_country or "", destination_country),
            "transit_country": transit_country,
            "transit_country_name": COUNTRY_NAMES.get(transit_country or "", transit_country),
            "route_type": effective_route,
            "route_warnings": route_warnings,
            "aviation_status": decision.overall if aviation_rules else "not_applicable",
            "aviation_rules": aviation_rules,
            "entry_status": entry_status,
            "entry_rules": entry_rules,
            "transit_notices": transit_notices,
            "retrieved_rules": retrieved,
            "notice": self.country_dataset["dataset"]["notice"],
        }
        return decision, context


__all__ = [
    "COUNTRY_CODES",
    "COUNTRY_NAMES",
    "CountryAwareBaggageRAGAgent",
    "CountryRuleEvaluator",
    "build_country_rule_chunks",
    "infer_route_type",
    "load_country_rule_dataset",
]
