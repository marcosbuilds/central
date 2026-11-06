import io
import json
import os
import unittest
from unittest.mock import patch

from central_gateway import application


class GatewayTests(unittest.TestCase):
    def call(self, path="/healthz", method="GET"):
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(
            application(
                {
                    "PATH_INFO": path,
                    "REQUEST_METHOD": method,
                    "wsgi.input": io.BytesIO(),
                },
                start_response,
            )
        )
        return captured, json.loads(body)

    def test_health_does_not_expose_environment_values(self):
        with patch.dict(
            os.environ,
            {
                "CENTRAL_SUPABASE_URL": "https://central.example",
                "CENTRAL_SUPABASE_PUBLISHABLE_KEY": "publishable-secret-value",
            },
            clear=False,
        ):
            response, payload = self.call()

        self.assertEqual(response["status"], "200 OK")
        self.assertTrue(payload["configuration"]["supabase_url_configured"])
        self.assertTrue(payload["configuration"]["supabase_publishable_key_configured"])
        self.assertNotIn("central.example", json.dumps(payload))
        self.assertNotIn("publishable-secret-value", json.dumps(payload))

    def test_capabilities_are_explicitly_limited(self):
        response, payload = self.call("/v1/capabilities")

        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(payload["available"], ["health"])
        self.assertIn("continuous_sse", payload["not_available"])
        self.assertEqual(payload["control_plane"]["files"], "syncthing_p2p")

    def test_unknown_path_and_method_are_rejected(self):
        response, payload = self.call("/does-not-exist")
        self.assertEqual(response["status"], "404 Not Found")
        self.assertEqual(payload["error"], "not_found")

        response, payload = self.call("/healthz", "POST")
        self.assertEqual(response["status"], "405 Method Not Allowed")
        self.assertEqual(payload["allowed"], ["GET"])


if __name__ == "__main__":
    unittest.main()
