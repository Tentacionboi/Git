import json
from io import BytesIO
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from worldcup_betting_edp.data import (
    ApiFootballRequestError,
    build_api_football_url,
    fetch_api_football_payload,
    get_api_football_key_from_env,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class ApiFootballClientTests(unittest.TestCase):
    def test_builds_api_football_url(self) -> None:
        url = build_api_football_url("/fixtures", params={"league": 1, "season": 2022})

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "v3.football.api-sports.io")
        self.assertEqual(parsed.path, "/fixtures")
        self.assertEqual(query["league"], ["1"])
        self.assertEqual(query["season"], ["2022"])

    def test_reads_api_football_key_from_env_mapping(self) -> None:
        key = get_api_football_key_from_env(environ={"API_FOOTBALL_KEY": " test_key "})

        self.assertEqual(key, "test_key")

    def test_fetches_payload_with_key_header(self) -> None:
        calls = []

        def fake_opener(request, *, timeout):
            calls.append((request, timeout))
            return _FakeResponse({"results": 1, "response": []})

        payload = fetch_api_football_payload(
            api_key="test_key",
            endpoint="/fixtures",
            params={"league": 1, "season": 2022},
            timeout_seconds=12.0,
            opener=fake_opener,
        )

        self.assertEqual(payload["results"], 1)
        request, timeout = calls[0]
        self.assertEqual(timeout, 12.0)
        self.assertEqual(request.headers["X-apisports-key"], "test_key")
        self.assertIn("league=1", request.full_url)

    def test_sanitizes_http_error_without_leaking_key(self) -> None:
        def fake_opener(request, *, timeout):
            raise HTTPError(
                url=request.full_url,
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=BytesIO(b'{"message":"bad key"}'),
            )

        with self.assertRaises(ApiFootballRequestError) as raised:
            fetch_api_football_payload(
                api_key="secret_key",
                endpoint="/fixtures",
                opener=fake_opener,
            )

        rendered = str(raised.exception)
        self.assertIn("status_code=401", rendered)
        self.assertIn("bad key", rendered)
        self.assertNotIn("secret_key", rendered)


if __name__ == "__main__":
    unittest.main()
