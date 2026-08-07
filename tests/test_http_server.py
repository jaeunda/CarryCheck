import http.client
import json
import threading
import unittest

from airline_baggage_agent.server.app import create_server


class LocalHttpIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0, runtime="local")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_static_page_and_options_are_served(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"CarryCheck", body)

        status, headers, body = self.request("GET", "/api/options")
        options = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("Japan", {country["code"] for country in options["countries"]})

    def test_decide_uses_the_shared_complete_response(self):
        request = json.dumps({
            "airline": "KOREAN_AIR",
            "origin_country": "Korea",
            "destination_country": "Japan",
            "item_text": "생수 500mL",
        }).encode("utf-8")
        status, _, body = self.request(
            "POST",
            "/api/decide",
            request,
            {"Content-Type": "application/json", "Content-Length": str(len(request))},
        )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["decision"]["carry_on"]["status"], "prohibited")
        self.assertEqual(payload["ai_answer"]["status"], "disabled")

    def test_invalid_json_and_missing_static_files_are_rejected(self):
        status, _, body = self.request(
            "POST",
            "/api/decide",
            b"{not-json",
            {"Content-Type": "application/json", "Content-Length": "9"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

        status, _, _ = self.request("GET", "/does-not-exist")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
