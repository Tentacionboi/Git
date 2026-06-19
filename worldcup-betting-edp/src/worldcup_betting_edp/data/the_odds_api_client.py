"""Small The Odds API client helpers.

API keys are intentionally read from environment variables by callers. Do not
pass keys through command-line flags because shell history and process listings
can leak them.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from worldcup_betting_edp.data.the_odds_api import (
    THE_ODDS_API_H2H_MARKET,
    THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    build_the_odds_api_historical_odds_url,
)


THE_ODDS_API_KEY_ENV_VAR = "THE_ODDS_API_KEY"


UrlOpener = Callable[[Request, float], Any]


@dataclass(frozen=True)
class TheOddsApiRequestError(Exception):
    """Sanitized The Odds API request failure."""

    message: str
    status_code: int | None = None
    response_body: str = ""

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.response_body:
            parts.append(f"response_body={self.response_body}")
        return "; ".join(parts)


def load_dotenv_file(
    path: str | Path = ".env",
    *,
    environ: dict[str, str] | None = None,
    override: bool = False,
) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a local .env file.

    This intentionally implements only the small subset needed by the project:
    comments, blank lines, optional ``export`` prefix, and simple quoted values.
    Existing environment variables win unless ``override`` is true.
    """
    destination = environ if environ is not None else os.environ
    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        parsed_value = _strip_dotenv_quotes(value.strip())
        if override or key not in destination:
            destination[key] = parsed_value
            loaded[key] = parsed_value
    return loaded


def get_the_odds_api_key_from_env(
    *,
    env_var: str = THE_ODDS_API_KEY_ENV_VAR,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Read a The Odds API key from the environment."""
    source = environ if environ is not None else os.environ
    value = source.get(env_var, "").strip()
    if not value:
        raise ValueError(f"{env_var} is not set")
    return value


def fetch_the_odds_api_historical_odds_payload(
    *,
    api_key: str,
    date: str,
    sport_key: str = THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    regions: str = "us,uk,eu,au",
    markets: str = THE_ODDS_API_H2H_MARKET,
    timeout_seconds: float = 30.0,
    opener: UrlOpener | None = None,
) -> dict[str, Any]:
    """Fetch one historical odds JSON payload from The Odds API."""
    url = build_the_odds_api_historical_odds_url(
        api_key=api_key,
        date=date,
        sport_key=sport_key,
        regions=regions,
        markets=markets,
        odds_format="decimal",
    )
    request = Request(url, headers={"Accept": "application/json"})
    open_url = opener or urlopen
    try:
        with open_url(request, timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise TheOddsApiRequestError(
            "The Odds API request failed",
            status_code=exc.code,
            response_body=_read_error_body(exc),
        ) from exc
    except URLError as exc:
        raise TheOddsApiRequestError(f"The Odds API network error: {exc.reason}") from exc
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("The Odds API response must be a JSON object")
    return payload


def _strip_dotenv_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _read_error_body(exc: HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")[:1000]
    except Exception:
        return ""
