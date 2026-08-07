import unittest
from types import SimpleNamespace

from airline_baggage_agent.services.answer_generation import (
    VerifiedJourneyAnswerAgent,
    _extract_json_object,
    compare_token_usage,
)


def _response(content, prompt=100, completion=20, **message_fields):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content, **message_fields),
            finish_reason="stop",
        )],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion),
    )


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.completions = _FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


class _FailingCompletions:
    def create(self, **_kwargs):
        raise RuntimeError("Furiosa API가 HTTP 401을 반환했습니다.")


class _FailingClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_FailingCompletions())


def _payload():
    return {
        "decision": {
            "airline_name": "제주항공",
            "item": {"item_name": "보조배터리", "watt_hours": 74.0, "count": 2},
            "overall": "conditional",
            "carry_on": {"status": "conditional", "reasons": ["100Wh 이하입니다."]},
            "checked": {"status": "prohibited", "reasons": ["위탁할 수 없습니다."]},
            "conditions": ["단자를 보호하세요."],
            "exceptions": [],
            "missing_information": [],
            "matched_rule_ids": ["TEST-RULE"],
            "retrieved_chunks": [
                {"rule_id": "TEST-RULE", "text": "100Wh 이하 기내 조건부", "source_url": "https://example.com"}
            ],
        },
        "country_checks": {
            "route_type": "international",
            "origin_country_name": "일본",
            "destination_country_name": "대한민국",
            "journey_status": "conditional",
            "entry_status": "not_applicable",
            "aviation_rules": [],
            "entry_rules": [],
            "retrieved_rules": [],
        },
    }


class VerifiedAnswerAgentTests(unittest.TestCase):
    def test_agent_uses_preverified_context_and_returns_structured_answer(self):
        final = (
            '{"final":{"answer":"74Wh 보조배터리는 단자를 보호하면 기내 반입할 수 있지만 위탁은 불가합니다.",'
            '"carry_on_status":"conditional","checked_status":"prohibited",'
            '"journey_status":"conditional","rule_ids":["TEST-RULE"]}}'
        )
        client = _FakeClient([_response(final, prompt=200, completion=40)])
        result = VerifiedJourneyAnswerAgent(client).run({"item_text": "보조배터리"}, _payload())
        self.assertEqual(result["status"], "generated")
        self.assertTrue(result["verified"])
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["usage"]["total_tokens"], 240)
        self.assertNotIn("response_format", client.completions.requests[0])
        self.assertNotIn("extra_body", client.completions.requests[0])
        self.assertNotIn("temperature", client.completions.requests[0])
        self.assertIn("verified_context", client.completions.requests[0]["messages"][1]["content"])

    def test_agent_reads_gpt_oss_json_from_reasoning_field(self):
        final = (
            '{"final":{"answer":"74Wh 보조배터리는 단자를 보호하면 기내 반입할 수 있지만 위탁은 불가합니다.",'
            '"carry_on_status":"conditional","checked_status":"prohibited",'
            '"journey_status":"conditional","rule_ids":["TEST-RULE"]}}'
        )
        client = _FakeClient([_response(None, reasoning_content=final)])
        result = VerifiedJourneyAnswerAgent(client).run({}, _payload())
        self.assertEqual(result["status"], "generated")
        self.assertTrue(result["verified"])
        self.assertEqual(result["trace"][1]["response_field"], "reasoning_content")

    def test_agent_reads_content_blocks(self):
        final = (
            '{"final":{"answer":"74Wh 보조배터리는 단자를 보호하면 기내 반입할 수 있지만 위탁은 불가합니다.",'
            '"carry_on_status":"conditional","checked_status":"prohibited",'
            '"journey_status":"conditional","rule_ids":["TEST-RULE"]}}'
        )
        client = _FakeClient([_response([SimpleNamespace(type="text", text=final)])])
        result = VerifiedJourneyAnswerAgent(client).run({}, _payload())
        self.assertEqual(result["status"], "generated")

    def test_empty_output_retries_until_structured_content_is_verified(self):
        final = (
            '{"final":{"answer":"규칙 엔진 검증 결과 기내 반입은 조건부 가능하고 위탁 수하물은 금지됩니다. 단자를 보호하세요.",'
            '"carry_on_status":"conditional","checked_status":"prohibited",'
            '"journey_status":"conditional","rule_ids":["TEST-RULE"]}}'
        )
        client = _FakeClient([
            _response(None),
            _response(final, prompt=200, completion=40),
        ])
        result = VerifiedJourneyAnswerAgent(client).run({}, _payload())
        self.assertEqual(result["status"], "generated")
        self.assertIn("기내 반입은 조건부 가능", result["answer"])
        self.assertEqual(result["iterations"], 2)
        self.assertNotIn("response_format", client.completions.requests[1])
        self.assertEqual(result["trace"][-1]["output_mode"], "validated_json")

    def test_plain_content_is_not_marked_as_verified(self):
        plain = "기내 반입과 위탁 수하물이 모두 가능하다는 검증되지 않은 모델 설명입니다."
        client = _FakeClient([_response(plain)])
        result = VerifiedJourneyAnswerAgent(
            client,
            max_iterations=1,
            fallback_on_error=False,
        ).run({}, _payload())
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["verified"])
        self.assertEqual(result["error_code"], "invalid_model_response")

    def test_status_mismatch_falls_back_to_rule_answer(self):
        invalid = (
            '{"final":{"answer":"잘못된 상태를 반환하는 충분히 긴 테스트 답변입니다.",'
            '"carry_on_status":"allowed","checked_status":"allowed",'
            '"journey_status":"allowed","rule_ids":[]}}'
        )
        client = _FakeClient([_response(invalid)])
        result = VerifiedJourneyAnswerAgent(client, max_iterations=1).run({}, _payload())
        self.assertEqual(result["status"], "fallback")
        self.assertIn("기내 반입은 조건부 가능", result["answer"])
        self.assertIn("carry_on_status", result["warning"])

    def test_strict_invalid_model_response_has_distinct_error_code(self):
        client = _FakeClient([_response("not json")])
        result = VerifiedJourneyAnswerAgent(
            client,
            max_iterations=1,
            fallback_on_error=False,
        ).run({}, _payload())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "invalid_model_response")
        self.assertIn("모델 응답 검증 실패", result["warning"])
        self.assertEqual(result["iterations"], 1)

    def test_strict_api_mode_returns_visible_error_instead_of_template(self):
        result = VerifiedJourneyAnswerAgent(
            _FailingClient(),
            fallback_on_error=False,
        ).run({}, _payload())
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["verified"])
        self.assertIsNone(result["answer"])
        self.assertEqual(result["error_code"], "chat_api_failed")
        self.assertIn("HTTP 401", result["warning"])
        self.assertEqual(result["usage"]["total_tokens"], 0)

    def test_parser_uses_first_object_when_model_emits_two(self):
        output = '{"tool":"get_verified_baggage_context","args":{}}\n{"final":{"answer":"premature"}}'
        parsed = _extract_json_object(output)
        self.assertEqual(parsed["tool"], "get_verified_baggage_context")

    def test_token_comparison_reports_negative_or_positive_truthfully(self):
        result = compare_token_usage({"total_tokens": 600}, {"total_tokens": 1000})
        self.assertEqual(result["saved_tokens"], 400)
        self.assertEqual(result["reduction_percent"], 40.0)


if __name__ == "__main__":
    unittest.main()
