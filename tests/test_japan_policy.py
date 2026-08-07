import unittest

from airline_baggage_agent.policies.japan_policy import CountryAwareBaggageRAGAgent
from airline_baggage_agent.web_app import build_decision_payload, build_options_payload


class JapanCountryPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = CountryAwareBaggageRAGAgent()

    def evaluate(self, item_text, *, origin="Korea", destination="Japan", airline="ASIANA", **kwargs):
        return self.agent.evaluate(
            airline,
            item_text,
            origin_country=origin,
            destination_country=destination,
            **kwargs,
        )

    @staticmethod
    def entry_rule(context, rule_id):
        return next(rule for rule in context["entry_rules"] if rule["rule_id"] == rule_id)

    def test_japan_is_in_country_dataset(self):
        countries = {country["code"] for country in self.agent.country_dataset["countries"]}
        self.assertIn("Japan", countries)

    def test_japan_domestic_power_bank_is_limited_to_two(self):
        decision, context = self.evaluate(
            "보조배터리 74Wh 3개",
            origin="Japan",
            destination="Japan",
        )
        self.assertEqual(context["route_type"], "domestic")
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.overall, "prohibited")
        self.assertIn("JP-MLIT-POWER-BANK-2026", decision.matched_rule_ids)

    def test_japan_power_bank_two_under_160wh_is_carry_on_only(self):
        decision, _ = self.evaluate(
            "보조배터리 74Wh 2개",
            origin="Japan",
            destination="Korea",
        )
        self.assertEqual(decision.carry_on.status, "conditional")
        self.assertEqual(decision.checked.status, "prohibited")
        self.assertTrue(any("충전" in condition for condition in decision.conditions))

    def test_japan_power_bank_over_160wh_is_prohibited(self):
        decision, _ = self.evaluate(
            "보조배터리 161Wh 1개",
            origin="Japan",
            destination="Korea",
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "prohibited")

    def test_japan_power_bank_needs_count(self):
        decision, _ = self.evaluate(
            "보조배터리 74Wh",
            origin="Japan",
            destination="Korea",
        )
        self.assertEqual(decision.carry_on.status, "needs_information")
        self.assertTrue(any("수량" in value for value in decision.missing_information))

    def test_japan_international_liquid_over_100ml_is_checked_only(self):
        decision, _ = self.evaluate(
            "로션 150mL 1개",
            origin="Japan",
            destination="Korea",
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "allowed")
        self.assertIn("JP-MLIT-LIQUID-INTERNATIONAL", decision.matched_rule_ids)

    def test_japan_domestic_liquid_does_not_use_international_100ml_limit(self):
        decision, _ = self.evaluate(
            "로션 150mL 1개",
            origin="Japan",
            destination="Japan",
        )
        self.assertEqual(decision.carry_on.status, "allowed")
        self.assertIn("JP-DOMESTIC-LIQUID-INFO", decision.matched_rule_ids)

    def test_japan_alcohol_three_bottles_is_within_allowance(self):
        _, context = self.evaluate("위스키 750mL 3병")
        rule = self.entry_rule(context, "JP-CUSTOMS-ALCOHOL")
        self.assertEqual(rule["status"], "within_allowance")

    def test_japan_alcohol_four_bottles_requires_declaration(self):
        _, context = self.evaluate("위스키 750mL 4병")
        rule = self.entry_rule(context, "JP-CUSTOMS-ALCOHOL")
        self.assertEqual(rule["status"], "declaration_required")
        self.assertEqual(context["entry_status"], "declaration_required")

    def test_japan_cigarette_boundary(self):
        _, within = self.evaluate("담배 200개비")
        _, over = self.evaluate("담배 201개비")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-TOBACCO")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-TOBACCO")["status"], "declaration_required")
        self.assertNotIn("JP-MAFF-PLANT-QUARANTINE", [rule["rule_id"] for rule in over["entry_rules"]])

    def test_japan_cigar_boundary(self):
        _, within = self.evaluate("시가 50개")
        _, over = self.evaluate("시가 51개")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-TOBACCO")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-TOBACCO")["status"], "declaration_required")

    def test_japan_heated_tobacco_boundary(self):
        _, within = self.evaluate("아이코스 가열식 담배 10팩")
        _, over = self.evaluate("아이코스 가열식 담배 11팩")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-TOBACCO")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-TOBACCO")["status"], "declaration_required")

    def test_japan_perfume_boundary(self):
        _, within = self.evaluate("향수 총 56mL")
        _, over = self.evaluate("향수 총 60mL")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-PERFUME")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-PERFUME")["status"], "declaration_required")

    def test_japan_other_goods_200000_yen_boundary(self):
        _, within = self.evaluate("선물용 가방 199,999엔")
        _, over = self.evaluate("선물용 가방 200,000엔")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-OTHER-GOODS")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-OTHER-GOODS")["status"], "declaration_required")

    def test_japan_currency_over_one_million_yen_requires_declaration(self):
        _, within = self.evaluate("현금 1,000,000엔")
        _, over = self.evaluate("현금 1,000,001엔")
        self.assertEqual(self.entry_rule(within, "JP-CUSTOMS-CURRENCY-GOLD")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-CUSTOMS-CURRENCY-GOLD")["status"], "declaration_required")

    def test_japan_gold_is_declared_regardless_of_quantity(self):
        _, context = self.evaluate("골드바 100g")
        self.assertEqual(self.entry_rule(context, "JP-CUSTOMS-CURRENCY-GOLD")["status"], "declaration_required")

    def test_japan_meat_product_is_prohibited(self):
        _, context = self.evaluate("진공 포장 소시지 1개")
        self.assertEqual(self.entry_rule(context, "JP-MAFF-MEAT-QUARANTINE")["status"], "prohibited")
        self.assertEqual(context["journey_status"], "prohibited")

    def test_japan_fruit_is_prohibited_and_seed_needs_review(self):
        _, fruit = self.evaluate("사과 2개")
        _, seed = self.evaluate("꽃 씨앗 1봉지")
        self.assertEqual(self.entry_rule(fruit, "JP-MAFF-PLANT-QUARANTINE")["status"], "prohibited")
        self.assertEqual(self.entry_rule(seed, "JP-MAFF-PLANT-QUARANTINE")["status"], "review_required")

    def test_japan_prescription_medicine_month_limit(self):
        _, within = self.evaluate("처방약 1개월분")
        _, over = self.evaluate("처방약 2개월분")
        self.assertEqual(self.entry_rule(within, "JP-MHLW-MEDICINE")["status"], "within_allowance")
        self.assertEqual(self.entry_rule(over, "JP-MHLW-MEDICINE")["status"], "review_required")

    def test_japan_transit_notice_is_returned(self):
        _, context = self.agent.evaluate(
            "KOREAN_AIR",
            "보조배터리 74Wh 1개",
            origin_country="Korea",
            destination_country="Thailand",
            transit_country="Japan",
        )
        self.assertTrue(any("일본" in notice for notice in context["transit_notices"]))

    def test_japan_rules_are_retrieved_by_country_rag(self):
        _, context = self.evaluate("보조배터리 74Wh 1개", origin="Japan", destination="Korea")
        self.assertTrue(any(rule["country"] == "Japan" for rule in context["retrieved_rules"]))

    def test_web_options_and_payload_include_japan(self):
        options = build_options_payload(self.agent)
        self.assertIn("Japan", {country["code"] for country in options["countries"]})
        self.assertTrue(any(example["origin_country"] == "Japan" for example in options["examples"]))
        response = build_decision_payload(
            self.agent,
            {
                "airline": "ASIANA",
                "origin_country": "Japan",
                "destination_country": "Japan",
                "item_text": "보조배터리 74Wh 3개",
            },
        )
        self.assertEqual(response["country_checks"]["journey_status"], "prohibited")


if __name__ == "__main__":
    unittest.main()
