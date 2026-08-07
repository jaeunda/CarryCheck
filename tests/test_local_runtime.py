import unittest
from types import SimpleNamespace
from unittest.mock import patch

from airline_baggage_agent.server import app


class LocalRuntimeTests(unittest.TestCase):
    def test_local_agent_never_constructs_external_api_clients(self):
        with patch.object(app, "_api_client_types") as api_client_types:
            agent = app.build_agent("local")

        api_client_types.assert_not_called()
        self.assertIsNone(agent.answer_generator)
        self.assertEqual(agent.runtime_model["mode"], "local")
        self.assertEqual(agent.runtime_model["profile"], "local")
        self.assertEqual(agent.runtime_model["embedding_mode"], "local")
        self.assertEqual(agent.runtime_model["chat_mode"], "disabled")

    def test_api_profile_composes_embedding_and_answer_services(self):
        class FakeEmbeddingClient:
            def __init__(self, *_args):
                self.embeddings = self

            def create(self, *, model, input):
                return SimpleNamespace(
                    data=[SimpleNamespace(embedding=[1.0, 0.0]) for _ in input]
                )

        class FakeChatClient:
            def __init__(self, *_args):
                self.chat = SimpleNamespace(completions=SimpleNamespace())

        clients = (
            FakeEmbeddingClient,
            FakeChatClient,
            lambda base, endpoint: f"{base}/{endpoint.lstrip('/')}",
        )
        with (
            patch.object(app.settings, "FURIOSA_EMBEDDING_API_KEY", "embedding-key"),
            patch.object(app.settings, "FURIOSA_CHAT_API_KEY", "chat-key"),
            patch.object(app, "_api_client_types", return_value=clients),
        ):
            agent = app.build_agent("api")

        self.assertEqual(agent.runtime_model["mode"], "api")
        self.assertEqual(agent.retriever.dense_mode, "Qwen3-Embedding-8B")
        self.assertIsNotNone(agent.answer_generator)

    def test_api_profile_requires_both_credentials(self):
        with (
            patch.object(app.settings, "FURIOSA_EMBEDDING_API_KEY", ""),
            patch.object(app.settings, "FURIOSA_CHAT_API_KEY", ""),
            self.assertRaisesRegex(RuntimeError, "FURIOSA_EMBEDDING_API_KEY"),
        ):
            app.build_agent("api")


if __name__ == "__main__":
    unittest.main()
