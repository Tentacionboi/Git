import json
import unittest

from worldcup_betting_edp.data import (
    fetch_the_odds_api_historical_odds_payload,
    get_the_odds_api_key_from_env,
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


class TheOddsApiClientTests(unittest.TestCase):
    def test_reads_api_key_from_environment_mapping(self) -> None:
        key = get_the_odds_api_key_from_env(environ={"THE_ODDS_API_KEY": " test_key "})

        self.assertEqual(key, "test_key")

    def test_rejects_missing_api_key(self) -> None:
        with self.assertRaises(ValueError):
            get_the_odds_api_key_from_env(environ={})

    def test_fetches_json_payload_with_decimal_h2h_request(self) -> None:
        calls = []

        def fake_opener(request, timeout):
            calls.append((request, timeout))
            return _FakeResponse({"timestamp": "2022-11-20T12:00:00Z", "data": []})

        payload = fetch_the_odds_api_historical_odds_payload(
            api_key="test_key",
            date="2022-11-20T12:00:00Z",
            regions="uk",
            timeout_seconds=12.0,
            opener=fake_opener,
        )

        self.assertEqual(payload["timestamp"], "2022-11-20T12:00:00Z")
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(timeout, 12.0)
        self.assertIn("soccer_fifa_world_cup", request.full_url)
        self.assertIn("markets=h2h", request.full_url)
        self.assertIn("oddsFormat=decimal", request.full_url)
        self.assertIn("apiKey=test_key", request.full_url)


if __name__ == "__main__":
    unittest.main()
