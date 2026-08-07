import unittest

from airline_baggage_agent.policies.country_policy import CountryAwareBaggageRAGAgent
from airline_baggage_agent.web_app import build_decision_payload, build_options_payload


class CompleteCountryPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = CountryAwareBaggageRAGAgent()

    def evaluate(self, item_text, *, origin="Korea", destination="Thailand", **kwargs):
        return self.agent.evaluate(
            "KOREAN_AIR",
            item_text,
            origin_country=origin,
            destination_country=destination,
            **kwargs,
        )

    def test_entry_prohibition_controls_journey_status(self):
        _, context = self.evaluate("전자담배 1개")
        self.assertEqual(context["entry_status"], "prohibited")
        self.assertEqual(context["journey_status"], "prohibited")
        self.assertNotIn("TH-CUSTOMS-TOBACCO", [rule["rule_id"] for rule in context["entry_rules"]])

    def test_china_alcohol_requires_strength_at_declaration_volume(self):
        _, context = self.evaluate("위스키 750mL 2병", destination="China")
        alcohol = next(rule for rule in context["entry_rules"] if rule["rule_id"] == "CN-CUSTOMS-ALCOHOL")
        self.assertEqual(alcohol["status"], "review_required")
        self.assertEqual(context["journey_status"], "needs_information")

    def test_china_alcohol_twelve_percent_and_1500ml_is_declarable(self):
        _, context = self.evaluate("와인 12% 750mL 2병", destination="China")
        alcohol = next(rule for rule in context["entry_rules"] if rule["rule_id"] == "CN-CUSTOMS-ALCOHOL")
        self.assertEqual(alcohol["status"], "declaration_required")
        self.assertEqual(context["journey_status"], "conditional")

    def test_china_cigar_threshold_is_parsed(self):
        _, context = self.evaluate("시가 100개", destination="China")
        tobacco = next(rule for rule in context["entry_rules"] if rule["rule_id"] == "CN-CUSTOMS-TOBACCO")
        self.assertEqual(tobacco["status"], "declaration_required")

    def test_thailand_one_litre_is_within_limit(self):
        _, context = self.evaluate("위스키 1,000mL 1병")
        alcohol = next(rule for rule in context["entry_rules"] if rule["rule_id"] == "TH-CUSTOMS-ALCOHOL")
        self.assertEqual(alcohol["status"], "within_allowance")

    def test_web_response_includes_journey_status(self):
        response = build_decision_payload(
            self.agent,
            {
                "airline": "KOREAN_AIR",
                "origin_country": "Korea",
                "destination_country": "Thailand",
                "item_text": "전자담배 1개",
            },
        )
        self.assertEqual(response["country_checks"]["journey_status"], "prohibited")

    def test_every_example_uses_a_supported_airline(self):
        options = build_options_payload(self.agent)
        supported = {airline["code"] for airline in options["airlines"]}
        self.assertTrue(all(example["airline"] in supported for example in options["examples"]))


if __name__ == "__main__":
    unittest.main()
