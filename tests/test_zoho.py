import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from creator_migration_helper.zoho import ZohoAPIError, ZohoClient


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ZohoClientTests(unittest.TestCase):
    def test_get_forms_uses_expected_endpoint_and_environment_header(self) -> None:
        calls = {}

        def fake_urlopen(req, timeout):
            calls["url"] = req.full_url
            headers = {key.lower(): value for key, value in req.header_items()}
            calls["auth"] = headers.get("authorization")
            calls["environment"] = headers.get("environment")
            calls["timeout"] = timeout
            return FakeHTTPResponse({"code": 3000, "forms": [{"link_name": "Vehicles"}]})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client = ZohoClient(
                base_url="www.zohoapis.com",
                owner="owner",
                app="fleet_hub",
                token="TOKEN123",
                environment="development",
            )
            forms = client.get_forms()

        self.assertEqual(forms, [{"link_name": "Vehicles"}])
        self.assertEqual(
            calls["url"],
            "https://www.zohoapis.com/creator/v2.1/meta/owner/fleet_hub/form",
        )
        self.assertEqual(calls["auth"], "Zoho-oauthtoken TOKEN123")
        self.assertEqual(calls["environment"], "development")
        self.assertEqual(calls["timeout"], 30)

    def test_http_error_surface_message(self) -> None:
        http_error = HTTPError(
            url="https://www.zohoapis.com/test",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"code": 1030, "message": "invalid oauth token"}'),
        )

        with patch("urllib.request.urlopen", side_effect=http_error):
            client = ZohoClient(
                base_url="www.zohoapis.com",
                owner="owner",
                app="fleet_hub",
                token="BAD_TOKEN",
            )
            with self.assertRaises(ZohoAPIError) as ctx:
                client.get_forms()

        self.assertIn("401", str(ctx.exception))
        self.assertIn("invalid oauth token", str(ctx.exception))

    def test_string_success_code_is_supported(self) -> None:
        with patch(
            "urllib.request.urlopen",
            return_value=FakeHTTPResponse({"code": "3000", "fields": [{"field_name": "vehicle_id"}]}),
        ):
            client = ZohoClient(
                base_url="www.zohoapis.com",
                owner="owner",
                app="fleet_hub",
                token="TOKEN",
            )
            fields = client.get_fields("Vehicles")

        self.assertEqual(fields[0]["field_name"], "vehicle_id")


if __name__ == "__main__":
    unittest.main()
