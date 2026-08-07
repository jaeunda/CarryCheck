import unittest

from airline_baggage_agent.policies.country_agent import (
    CountryAwareBaggageRAGAgent,
    infer_route_type,
)
from airline_baggage_agent.web_app import build_decision_payload


class CountryAwareBaggageAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = CountryAwareBaggageRAGAgent()

    def evaluate(self, item_text, *, origin, destination, airline="ASIANA", **kwargs):
        return self.agent.evaluate(
            airline,
            item_text,
            origin_country=origin,
            destination_country=destination,
            **kwargs,
        )

    def test_route_is_inferred_and_conflict_is_corrected(self):
        route, warnings = infer_route_type("China", "Thailand", "domestic")
        self.assertEqual(route, "international")
        self.assertEqual(len(warnings), 1)

    def test_china_domestic_power_bank_requires_ccc_confirmation(self):
        decision, context = self.evaluate(
            "보조배터리 20,000mAh 3.7V 1개",
            origin="China",
            destination="China",
        )
        self.assertEqual(context["route_type"], "domestic")
        self.assertEqual(decision.carry_on.status, "needs_information")
        self.assertTrue(any("CCC" in value for value in decision.missing_information))
        self.assertIn("CN-CAAC-CCC-DOMESTIC-2025", decision.matched_rule_ids)

    def test_china_domestic_power_bank_without_ccc_is_prohibited(self):
        decision, _ = self.evaluate(
            "보조배터리 20,000mAh 3.7V 1개",
            origin="China",
            destination="China",
            ccc_mark=False,
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "prohibited")
        self.assertEqual(decision.overall, "prohibited")

    def test_china_domestic_power_bank_with_ccc_can_be_carried(self):
        decision, _ = self.evaluate(
            "보조배터리 20,000mAh 3.7V 1개",
            origin="China",
            destination="China",
            ccc_mark=True,
        )
        self.assertEqual(decision.item.watt_hours, 74.0)
        self.assertEqual(decision.carry_on.status, "conditional")
        self.assertEqual(decision.checked.status, "prohibited")

    def test_china_international_power_bank_does_not_require_ccc(self):
        decision, _ = self.evaluate(
            "보조배터리 20,000mAh 3.7V 1개",
            origin="China",
            destination="Korea",
        )
        self.assertFalse(any("CCC" in value for value in decision.missing_information))
        self.assertNotEqual(decision.carry_on.status, "needs_information")

    def test_china_domestic_liquid_over_100ml_is_checked_only(self):
        decision, _ = self.evaluate(
            "로션 150mL 1개",
            origin="China",
            destination="China",
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "allowed")
        self.assertIn("CN-CAAC-LIQUID-DOMESTIC", decision.matched_rule_ids)

    def test_china_domestic_cosmetic_100ml_or_less_is_conditional(self):
        decision, _ = self.evaluate(
            "로션 80mL 1개",
            origin="China",
            destination="China",
        )
        self.assertEqual(decision.carry_on.status, "conditional")

    def test_thailand_liquid_rule_applies_to_domestic_flight(self):
        decision, _ = self.evaluate(
            "로션 150mL 1개",
            airline="JEJU_AIR",
            origin="Thailand",
            destination="Thailand",
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertIn("TH-CAAT-LAGS-2026", decision.matched_rule_ids)

    def test_thailand_liquid_100ml_or_less_is_conditional(self):
        decision, _ = self.evaluate(
            "로션 80mL 1개",
            airline="JEJU_AIR",
            origin="Thailand",
            destination="Korea",
        )
        self.assertEqual(decision.carry_on.status, "conditional")

    def test_thailand_entry_e_cigarette_is_prohibited(self):
        _, context = self.evaluate(
            "전자담배 1개",
            origin="Korea",
            destination="Thailand",
        )
        self.assertEqual(context["entry_status"], "prohibited")
        self.assertIn("TH-CUSTOMS-E-CIGARETTE", [rule["rule_id"] for rule in context["entry_rules"]])

    def test_thailand_alcohol_over_one_litre_requires_declaration(self):
        _, context = self.evaluate(
            "위스키 1,000mL 2병",
            origin="Korea",
            destination="Thailand",
        )
        alcohol = next(rule for rule in context["entry_rules"] if rule["rule_id"] == "TH-CUSTOMS-ALCOHOL")
        self.assertEqual(context["entry_status"], "declaration_required")
        self.assertEqual(alcohol["status"], "declaration_required")

    def test_country_rag_retrieves_involved_country_rules(self):
        _, context = self.evaluate(
            "보조배터리 10,000mAh 3.7V 1개",
            origin="China",
            destination="Thailand",
        )
        self.assertTrue(context["retrieved_rules"])
        self.assertTrue(all(rule["country"] in {"China", "Thailand"} for rule in context["retrieved_rules"]))

    def test_web_payload_returns_separate_country_checks(self):
        result = build_decision_payload(
            self.agent,
            {
                "airline": "KOREAN_AIR",
                "origin_country": "Korea",
                "destination_country": "Thailand",
                "item_text": "전자담배 1개",
                "overrides": {},
            },
        )
        self.assertEqual(result["country_checks"]["route_type"], "international")
        self.assertEqual(result["country_checks"]["entry_status"], "prohibited")
        self.assertTrue(result["verification"]["pass"])


if __name__ == "__main__":
    unittest.main()
