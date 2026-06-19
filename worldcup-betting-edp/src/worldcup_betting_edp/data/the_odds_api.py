"""The Odds API historical 1X2 odds adapter.

The adapter intentionally parses already-fetched JSON payloads instead of
fetching directly. That keeps API keys out of logs/tests and makes historical
odds ingestion reproducible from stored raw snapshots.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from worldcup_betting_edp.data.canonical_matches import CanonicalMatch
from worldcup_betting_edp.data.market_odds import MarketOddsSnapshot


THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
THE_ODDS_API_SOURCE = "the-odds-api"
THE_ODDS_API_WORLD_CUP_SPORT_KEY = "soccer_fifa_world_cup"
THE_ODDS_API_H2H_MARKET = "h2h"
THE_ODDS_API_DRAW_NAME = "draw"
THE_ODDS_API_EVENT_MAPPING_COLUMNS = (
    "source_event_id",
    "source_match_id",
    "canonical_match_id",
    "commence_time",
    "match_date",
    "source_home_team",
    "source_away_team",
    "canonical_home_team",
    "canonical_away_team",
    "orientation",
)
THE_ODDS_API_TEAM_ALIASES = {
    "usa": "united states",
}


@dataclass(frozen=True)
class TheOddsApiEventMapping:
    """Mapping from a The Odds API event id to a canonical project match id."""

    source_event_id: str
    source_match_id: str
    canonical_match_id: str
    commence_time: str
    match_date: str
    source_home_team: str
    source_away_team: str
    canonical_home_team: str
    canonical_away_team: str
    orientation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_event_id": self.source_event_id,
            "source_match_id": self.source_match_id,
            "canonical_match_id": self.canonical_match_id,
            "commence_time": self.commence_time,
            "match_date": self.match_date,
            "source_home_team": self.source_home_team,
            "source_away_team": self.source_away_team,
            "canonical_home_team": self.canonical_home_team,
            "canonical_away_team": self.canonical_away_team,
            "orientation": self.orientation,
        }


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


def build_the_odds_api_event_mapping(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    canonical_matches: Sequence[CanonicalMatch],
) -> list[TheOddsApiEventMapping]:
    """Map The Odds API event ids to canonical matches by date and teams."""
    _, events = _extract_events(payload)
    canonical_index = _build_canonical_match_index(canonical_matches)
    mappings: list[TheOddsApiEventMapping] = []
    for event in events:
        event_id = _string_value(event, "id")
        commence_time = _string_value(event, "commence_time")
        home_team = _string_value(event, "home_team")
        away_team = _string_value(event, "away_team")
        match_date = _date_from_iso_datetime(commence_time)
        if not event_id or not match_date or not home_team or not away_team:
            continue
        match, orientation = _find_canonical_match(
            canonical_index=canonical_index,
            match_date=match_date,
            source_home_team=home_team,
            source_away_team=away_team,
        )
        if match is None or orientation is None:
            continue
        mappings.append(
            TheOddsApiEventMapping(
                source_event_id=event_id,
                source_match_id=f"{THE_ODDS_API_SOURCE}:{event_id}",
                canonical_match_id=match.match_id,
                commence_time=commence_time,
                match_date=match.match_date,
                source_home_team=home_team,
                source_away_team=away_team,
                canonical_home_team=match.home_team,
                canonical_away_team=match.away_team,
                orientation=orientation,
            )
        )
    return mappings


def remap_the_odds_api_snapshots_to_canonical(
    snapshots: Sequence[MarketOddsSnapshot],
    mappings: Sequence[TheOddsApiEventMapping],
) -> list[MarketOddsSnapshot]:
    """Replace The Odds API source match ids with canonical match ids.

    If a source event uses the opposite home/away order from the canonical match
    table, home and away odds are swapped while draw odds remain unchanged.
    """
    mapping_by_source_match_id = {mapping.source_match_id: mapping for mapping in mappings}
    remapped: list[MarketOddsSnapshot] = []
    for snapshot in snapshots:
        mapping = mapping_by_source_match_id.get(snapshot.match_id)
        if mapping is None:
            continue
        if mapping.orientation == "same":
            home_odds = snapshot.home_odds
            away_odds = snapshot.away_odds
        elif mapping.orientation == "swapped":
            home_odds = snapshot.away_odds
            away_odds = snapshot.home_odds
        else:
            raise ValueError(f"unknown mapping orientation: {mapping.orientation}")
        remapped.append(
            MarketOddsSnapshot(
                match_id=mapping.canonical_match_id,
                bookmaker=snapshot.bookmaker,
                captured_at=snapshot.captured_at,
                home_odds=home_odds,
                draw_odds=snapshot.draw_odds,
                away_odds=away_odds,
                odds_type=snapshot.odds_type,
                source=snapshot.source,
            )
        )
    return remapped


def write_the_odds_api_event_mapping_csv(
    mappings: Sequence[TheOddsApiEventMapping],
    destination_path: str | Path,
) -> Path:
    """Write The Odds API event-to-canonical-match mapping rows."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(THE_ODDS_API_EVENT_MAPPING_COLUMNS))
        writer.writeheader()
        writer.writerows(mapping.to_dict() for mapping in mappings)
    return destination


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


def _canonical_match_key(match_date: str, home_team: str, away_team: str) -> tuple[str, str, str]:
    return (match_date, _normalize_team_name(home_team), _normalize_team_name(away_team))


def _normalize_team_name(value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    return THE_ODDS_API_TEAM_ALIASES.get(normalized, normalized)


def _build_canonical_match_index(
    canonical_matches: Sequence[CanonicalMatch],
) -> dict[tuple[str, str, str], CanonicalMatch]:
    return {
        _canonical_match_key(match.match_date, match.home_team, match.away_team): match
        for match in canonical_matches
    }


def _find_canonical_match(
    *,
    canonical_index: Mapping[tuple[str, str, str], CanonicalMatch],
    match_date: str,
    source_home_team: str,
    source_away_team: str,
) -> tuple[CanonicalMatch | None, str | None]:
    same = canonical_index.get(_canonical_match_key(match_date, source_home_team, source_away_team))
    if same is not None:
        return same, "same"
    swapped = canonical_index.get(_canonical_match_key(match_date, source_away_team, source_home_team))
    if swapped is not None:
        return swapped, "swapped"
    return None, None


def _date_from_iso_datetime(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return value[:10]


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
