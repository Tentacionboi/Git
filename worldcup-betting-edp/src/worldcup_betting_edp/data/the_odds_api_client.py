"""Small The Odds API client helpers.

API keys are intentionally read from environment variables by callers. Do not
pass keys through command-line flags because shell history and process listings
can leak them.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any, Callable
from urllib.request import Request, urlopen

from worldcup_betting_edp.data.the_odds_api import (
    THE_ODDS_API_H2H_MARKET,
    THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    build_the_odds_api_historical_odds_url,
)


THE_ODDS_API_KEY_ENV_VAR = "THE_ODDS_API_KEY"


UrlOpener = Callable[[Request, float], Any]


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
    with open_url(request, timeout_seconds) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("The Odds API response must be a JSON object")
    return payload
