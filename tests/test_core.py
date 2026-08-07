import math
import unittest

from airline_baggage_agent import BaggageRAGAgent, parse_item_text, verify_decision


class BaggageAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = BaggageRAGAgent()

    def test_mah_to_wh(self):
        item = parse_item_text("보조배터리 20,000mAh 3.7V 2개")
        self.assertAlmostEqual(item.watt_hours, 74.0)
        self.assertEqual(item.count, 2)

    def test_wh_calculation_rejects_non_finite_values(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.agent.calculate_wh(value, 3.7)

    def test_korean_air_power_bank(self):
        decision = self.agent.decide("대한항공", "보조배터리 20000mAh 3.7V 2개")
        self.assertEqual(decision.carry_on.status, "conditional")
        self.assertEqual(decision.checked.status, "prohibited")
        self.assertTrue(verify_decision(decision)["pass"])

    def test_large_power_bank_prohibited(self):
        decision = self.agent.decide("아시아나", "보조배터리 50000mAh 3.7V 1개")
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "prohibited")

    def test_international_liquid(self):
        decision = self.agent.decide("제주항공", "국제선 샴푸 150mL 1개")
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "allowed")

    def test_bottled_water_is_classified_as_liquid_without_data_changes(self):
        item = parse_item_text("생수 500ml")
        self.assertEqual(item.item_type, "liquid")
        decision = self.agent.decide(
            "대한항공",
            "생수 500ml",
            route_type="international",
        )
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "allowed")

    def test_water_keyword_does_not_match_unrelated_korean_word(self):
        item = parse_item_text("선물 500g")
        self.assertEqual(item.item_type, "unknown")

    def test_rule_aliases_are_used_by_item_classifier(self):
        decision = self.agent.decide("대한항공", "공구 1개")
        self.assertEqual(decision.item.item_type, "sharp_object")

    def test_domestic_liquid(self):
        decision = self.agent.decide("아시아나항공", "국내선 로션 150mL")
        self.assertEqual(decision.carry_on.status, "allowed")

    def test_sharp_object(self):
        decision = self.agent.decide("제주항공", "과도 1개")
        self.assertEqual(decision.carry_on.status, "prohibited")
        self.assertEqual(decision.checked.status, "allowed")

    def test_nonremovable_hair_iron(self):
        decision = self.agent.decide("대한항공", "배터리 분리 불가 무선 고데기")
        self.assertEqual(decision.overall, "prohibited")

    def test_unknown_item_is_not_guessed(self):
        decision = self.agent.decide("대한항공", "정체를 알 수 없는 장치")
        self.assertEqual(decision.overall, "needs_information")
        self.assertFalse(decision.matched_rule_ids)


if __name__ == "__main__":
    unittest.main()
