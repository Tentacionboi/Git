import json
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from worldcup_betting_edp.data import (
    TheOddsApiRequestError,
    fetch_the_odds_api_historical_odds_payload,
    get_the_odds_api_key_from_env,
    load_dotenv_file,
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
    def test_loads_dotenv_without_overwriting_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "# local secrets",
                        "THE_ODDS_API_KEY=file_key",
                        "export OTHER_VALUE='quoted value'",
                    ]
                ),
                encoding="utf-8",
            )
            environ = {"THE_ODDS_API_KEY": "existing_key"}

            loaded = load_dotenv_file(env_path, environ=environ)

            self.assertEqual(loaded, {"OTHER_VALUE": "quoted value"})
            self.assertEqual(environ["THE_ODDS_API_KEY"], "existing_key")
            self.assertEqual(environ["OTHER_VALUE"], "quoted value")

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

    def test_sanitizes_http_error_without_leaking_url(self) -> None:
        def fake_opener(request, timeout):
            raise HTTPError(
                url=request.full_url,
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=BytesIO(b'{"message":"historical odds not available"}'),
            )

        with self.assertRaises(TheOddsApiRequestError) as raised:
            fetch_the_odds_api_historical_odds_payload(
                api_key="secret_key",
                date="2022-11-20T12:00:00Z",
                opener=fake_opener,
            )

        rendered = str(raised.exception)
        self.assertIn("status_code=403", rendered)
        self.assertIn("historical odds not available", rendered)
        self.assertNotIn("secret_key", rendered)


if __name__ == "__main__":
    unittest.main()
