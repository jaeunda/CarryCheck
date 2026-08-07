import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from airline_baggage_agent.server.app import build_agent
from api import index as vercel_entry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VercelDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = build_agent("local")

    @staticmethod
    def _body(response):
        return json.loads(response.body.decode("utf-8"))

    def test_health_and_options_use_local_agent_without_external_clients(self):
        with patch.object(vercel_entry, "_get_agent", return_value=self.agent):
            health = vercel_entry.health()
            options = vercel_entry.options()

        health_body = self._body(health)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health_body["status"], "ok")
        self.assertEqual(health_body["retrieval"]["mode"], "local")
        self.assertEqual(options.status_code, 200)
        self.assertTrue(self._body(options)["airlines"])
        self.assertEqual(health.headers["cache-control"], "no-store")

    def test_decide_route_preserves_web_response_shape(self):
        request = {
            "airline": "KOREAN_AIR",
            "route_type": "international",
            "origin_country": "Korea",
            "destination_country": "Japan",
            "item_text": "생수 500ml",
        }
        with patch.object(vercel_entry, "_get_agent", return_value=self.agent):
            response = vercel_entry.decide(request)

        self.assertEqual(response.status_code, 200)
        body = self._body(response)
        self.assertEqual(body["decision"]["carry_on"]["status"], "prohibited")
        self.assertEqual(body["decision"]["checked"]["status"], "allowed")
        self.assertIn("country_checks", body)
        self.assertEqual(body["ai_answer"]["status"], "disabled")

    def test_decide_uses_configured_answer_agent(self):
        class AnswerGenerator:
            def __init__(self):
                self.calls = []

            def run(self, request, response):
                self.calls.append((request, response))
                return {
                    "enabled": True,
                    "status": "generated",
                    "verified": True,
                    "answer": "검증된 판정을 설명합니다.",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }

        answer_generator = AnswerGenerator()
        self.agent.answer_generator = answer_generator
        try:
            with patch.object(vercel_entry, "_get_agent", return_value=self.agent):
                response = vercel_entry.decide({
                    "airline": "KOREAN_AIR",
                    "origin_country": "Korea",
                    "destination_country": "Japan",
                    "item_text": "노트북 1개",
                })
        finally:
            self.agent.answer_generator = None

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response)["ai_answer"]["status"], "generated")
        self.assertEqual(len(answer_generator.calls), 1)

    def test_static_and_vercel_configuration_are_deployable(self):
        self.assertTrue((PROJECT_ROOT / "public" / "index.html").is_file())
        config = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))
        function = config["functions"]["api/index.py"]
        self.assertIn("src/airline_baggage_agent/data", function["includeFiles"])
        self.assertGreaterEqual(function["maxDuration"], 60)
        self.assertEqual(
            {route.path for route in vercel_entry.app.routes},
            {"/api/health", "/api/options", "/api/decide"},
        )

    def test_index_references_only_existing_static_assets(self):
        html = (PROJECT_ROOT / "public" / "index.html").read_text(encoding="utf-8")
        assets = set(re.findall(r'(?:src|href)="(/[^"#?]+)"', html))
        self.assertTrue(assets)
        for asset in assets:
            with self.subTest(asset=asset):
                self.assertTrue((PROJECT_ROOT / "public" / asset.lstrip("/")).is_file())

    def test_secret_and_local_state_patterns_are_ignored(self):
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        vercelignore = (PROJECT_ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
        for pattern in (".env", ".env.*", ".venv-*/", ".vercel/", "*.egg-info/", "*.pem", "*.key"):
            self.assertIn(pattern, gitignore)
        for pattern in (".env", ".env.*", ".venv-*", "**/*.egg-info", ".git"):
            self.assertIn(pattern, vercelignore)
        self.assertIn("!.env.example", gitignore)


if __name__ == "__main__":
    unittest.main()
