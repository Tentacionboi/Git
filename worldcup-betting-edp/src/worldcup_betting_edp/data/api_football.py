"""API-Football odds adapters.

API-Football is treated as a candidate source until its World Cup odds coverage,
timestamp semantics, and licensing are verified against real responses.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from worldcup_betting_edp.data.market_odds import MarketOddsSnapshot


API_FOOTBALL_SOURCE = "api-football"
API_FOOTBALL_WORLD_CUP_LEAGUE_ID = 1
API_FOOTBALL_MATCH_WINNER_BET_NAMES = {"match winner", "1x2", "fulltime result"}
API_FOOTBALL_HOME_VALUES = {"home", "1"}
API_FOOTBALL_DRAW_VALUES = {"draw", "x"}
API_FOOTBALL_AWAY_VALUES = {"away", "2"}


def parse_api_football_odds_response(
    payload: Mapping[str, Any],
    *,
    odds_type: str = "api_football_odds",
    source: str = API_FOOTBALL_SOURCE,
) -> list[MarketOddsSnapshot]:
    """Parse API-Football odds payload into canonical 1X2 market snapshots.

    The expected API-Football odds shape is:

    ``response[].fixture.id``
    ``response[].update``
    ``response[].bookmakers[].bets[].name == Match Winner``
    ``response[].bookmakers[].bets[].values[]``

    Only complete home/draw/away bookmaker rows are converted.
    """
    response = payload.get("response")
    if not isinstance(response, Sequence) or isinstance(response, (str, bytes)):
        raise ValueError("API-Football odds payload must contain a response list")

    snapshots: list[MarketOddsSnapshot] = []
    for item in _mapping_sequence(response):
        fixture = item.get("fixture")
        if not isinstance(fixture, Mapping):
            continue
        fixture_id = _string_value(fixture, "id")
        captured_at = _string_value(item, "update") or _string_value(fixture, "date")
        if not fixture_id or not captured_at:
            continue

        league = item.get("league") if isinstance(item.get("league"), Mapping) else {}
        row_source = _row_source(
            source=source,
            league_id=_string_value(league, "id"),
            season=_string_value(league, "season"),
        )
        for bookmaker in _mapping_sequence(item.get("bookmakers")):
            bookmaker_name = _string_value(bookmaker, "name") or _string_value(bookmaker, "id")
            if not bookmaker_name:
                continue
            for bet in _mapping_sequence(bookmaker.get("bets")):
                if _string_value(bet, "name").lower() not in API_FOOTBALL_MATCH_WINNER_BET_NAMES:
                    continue
                odds = _extract_match_winner_values(bet)
                if odds is None:
                    continue
                snapshots.append(
                    MarketOddsSnapshot(
                        match_id=f"{API_FOOTBALL_SOURCE}:{fixture_id}",
                        bookmaker=bookmaker_name,
                        captured_at=captured_at,
                        home_odds=odds["home"],
                        draw_odds=odds["draw"],
                        away_odds=odds["away"],
                        odds_type=odds_type,
                        source=row_source,
                    )
                )
    return snapshots


def summarize_api_football_probe_payloads(payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Build a compact, key-free summary for API-Football probe responses."""
    summary: dict[str, Any] = {}
    for name, payload in payloads.items():
        response = payload.get("response")
        summary[name] = {
            "results": payload.get("results"),
            "errors": payload.get("errors"),
            "paging": payload.get("paging"),
            "response_count": len(response) if isinstance(response, list) else None,
        }
    return summary


def _extract_match_winner_values(bet: Mapping[str, Any]) -> dict[str, float] | None:
    prices: dict[str, float] = {}
    for value_row in _mapping_sequence(bet.get("values")):
        value_name = _string_value(value_row, "value").lower()
        price = _decimal_price(value_row.get("odd"))
        if price is None:
            continue
        if value_name in API_FOOTBALL_HOME_VALUES:
            prices["home"] = price
        elif value_name in API_FOOTBALL_DRAW_VALUES:
            prices["draw"] = price
        elif value_name in API_FOOTBALL_AWAY_VALUES:
            prices["away"] = price
    if {"home", "draw", "away"}.issubset(prices):
        return prices
    return None


def _decimal_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 1.0:
        raise ValueError("API-Football parser expects decimal odds greater than 1.0")
    return price


def _row_source(*, source: str, league_id: str, season: str) -> str:
    parts = [source]
    if league_id:
        parts.append(f"league:{league_id}")
    if season:
        parts.append(f"season:{season}")
    return ":".join(parts)


def _string_value(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]
