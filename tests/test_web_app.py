import math
import unittest

from airline_baggage_agent.server.app import build_agent
from airline_baggage_agent.web_app import RequestValidationError, build_decision_payload


class BaggageWebAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = build_agent("local")

    def test_web_payload_uses_form_overrides(self):
        result = build_decision_payload(
            self.agent,
            {
                "airline": "KOREAN_AIR",
                "item_text": "보조배터리",
                "route_type": "international",
                "origin_country": "Korea",
                "overrides": {
                    "milliamp_hours": 20000,
                    "voltage": 3.7,
                    "count": 2,
                },
            },
        )
        decision = result["decision"]
        self.assertEqual(decision["carry_on"]["status"], "conditional")
        self.assertEqual(decision["checked"]["status"], "prohibited")
        self.assertAlmostEqual(decision["item"]["watt_hours"], 74.0)
        self.assertTrue(result["verification"]["pass"])

    def test_invalid_route_is_rejected(self):
        with self.assertRaises(RequestValidationError):
            build_decision_payload(
                self.agent,
                {
                    "airline": "KOREAN_AIR",
                    "item_text": "노트북",
                    "route_type": "space",
                },
            )

    def test_empty_item_text_is_rejected(self):
        with self.assertRaises(RequestValidationError):
            build_decision_payload(
                self.agent,
                {"airline": "KOREAN_AIR", "item_text": "   "},
            )

    def test_non_finite_numeric_override_is_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(RequestValidationError):
                build_decision_payload(
                    self.agent,
                    {
                        "airline": "KOREAN_AIR",
                        "item_text": "보조배터리",
                        "overrides": {"watt_hours": value},
                    },
                )

    def test_unknown_override_is_rejected(self):
        with self.assertRaises(RequestValidationError):
            build_decision_payload(
                self.agent,
                {
                    "airline": "KOREAN_AIR",
                    "item_text": "보조배터리",
                    "overrides": {"wat_hours": 74},
                },
            )


if __name__ == "__main__":
    unittest.main()
