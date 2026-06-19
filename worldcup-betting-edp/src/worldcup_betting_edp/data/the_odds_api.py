"""The Odds API historical 1X2 odds adapter.

The adapter intentionally parses already-fetched JSON payloads instead of
fetching directly. That keeps API keys out of logs/tests and makes historical
odds ingestion reproducible from stored raw snapshots.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from worldcup_betting_edp.data.market_odds import MarketOddsSnapshot


THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
THE_ODDS_API_SOURCE = "the-odds-api"
THE_ODDS_API_WORLD_CUP_SPORT_KEY = "soccer_fifa_world_cup"
THE_ODDS_API_H2H_MARKET = "h2h"
THE_ODDS_API_DRAW_NAME = "draw"


def build_the_odds_api_historical_odds_url(
    *,
    api_key: str,
    date: str,
    sport_key: str = THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    regions: str = "us,uk,eu,au",
    markets: str = THE_ODDS_API_H2H_MARKET,
    odds_format: str = "decimal",
    base_url: str = THE_ODDS_API_BASE_URL,
) -> str:
    """Build a historical odds endpoint URL.

    The caller is responsible for not logging the returned URL if it contains a
    real API key.
    """
    if not api_key:
        raise ValueError("api_key cannot be empty")
    if not date:
        raise ValueError("date cannot be empty")
    if not sport_key:
        raise ValueError("sport_key cannot be empty")
    if odds_format != "decimal":
        raise ValueError("this project expects decimal odds from The Odds API")

    query = urlencode(
        {
            "apiKey": api_key,
            "date": date,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }
    )
    return f"{base_url}/historical/sports/{sport_key}/odds?{query}"


def parse_the_odds_api_historical_odds_response(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    odds_type: str = "historical_snapshot",
    source: str = THE_ODDS_API_SOURCE,
) -> list[MarketOddsSnapshot]:
    """Parse The Odds API historical response into canonical market snapshots.

    Supports the historical endpoint wrapper:

    ``{"timestamp": "...", "data": [event, ...]}``

    and a raw list of event objects with the same schema as the live odds API.
    Only complete soccer 1X2 ``h2h`` markets are converted. Incomplete markets
    are skipped because a two-outcome row would corrupt 1X2 devigging.
    """
    snapshot_timestamp, events = _extract_events(payload)
    snapshots: list[MarketOddsSnapshot] = []

    for event in events:
        event_id = _string_value(event, "id")
        home_team = _string_value(event, "home_team")
        away_team = _string_value(event, "away_team")
        if not event_id or not home_team or not away_team:
            continue

        event_source = _event_source(source=source, sport_key=_string_value(event, "sport_key"))
        for bookmaker in _mapping_sequence(event.get("bookmakers")):
            bookmaker_key = _string_value(bookmaker, "key") or _string_value(bookmaker, "title")
            if not bookmaker_key:
                continue
            captured_at = (
                snapshot_timestamp
                or _string_value(bookmaker, "last_update")
                or _string_value(event, "last_update")
                or _string_value(event, "commence_time")
            )

            for market in _mapping_sequence(bookmaker.get("markets")):
                if _string_value(market, "key") != THE_ODDS_API_H2H_MARKET:
                    continue
                market_captured_at = snapshot_timestamp or _string_value(market, "last_update") or captured_at
                odds = _extract_complete_1x2_odds(
                    market=market,
                    home_team=home_team,
                    away_team=away_team,
                )
                if odds is None or not market_captured_at:
                    continue
                snapshots.append(
                    MarketOddsSnapshot(
                        match_id=f"{THE_ODDS_API_SOURCE}:{event_id}",
                        bookmaker=bookmaker_key,
                        captured_at=market_captured_at,
                        home_odds=odds["home"],
                        draw_odds=odds["draw"],
                        away_odds=odds["away"],
                        odds_type=odds_type,
                        source=event_source,
                    )
                )

    return snapshots


def _extract_events(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> tuple[str, Sequence[Mapping[str, Any]]]:
    if isinstance(payload, Mapping):
        timestamp = _string_value(payload, "timestamp")
        data = payload.get("data")
        if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
            raise ValueError("The Odds API historical payload must contain a data list")
        return timestamp, _mapping_sequence(data)

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return "", _mapping_sequence(payload)

    raise ValueError("payload must be a mapping or a sequence of event mappings")


def _extract_complete_1x2_odds(
    *,
    market: Mapping[str, Any],
    home_team: str,
    away_team: str,
) -> dict[str, float] | None:
    prices: dict[str, float] = {}
    for outcome in _mapping_sequence(market.get("outcomes")):
        name = _string_value(outcome, "name")
        price = _decimal_price(outcome.get("price"))
        if price is None:
            continue
        if name == home_team:
            prices["home"] = price
        elif name == away_team:
            prices["away"] = price
        elif name.lower() == THE_ODDS_API_DRAW_NAME:
            prices["draw"] = price

    if {"home", "draw", "away"}.issubset(prices):
        return prices
    return None


def _decimal_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 1.0:
        raise ValueError("The Odds API parser expects decimal odds greater than 1.0")
    return price


def _event_source(*, source: str, sport_key: str) -> str:
    if sport_key:
        return f"{source}:{sport_key}"
    return source


def _string_value(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]
