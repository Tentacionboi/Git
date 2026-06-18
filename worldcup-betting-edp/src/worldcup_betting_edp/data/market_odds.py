"""Historical market odds loading for 1X2 World Cup evaluation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from worldcup_betting_edp.domain import OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME


MARKET_ODDS_COLUMNS = (
    "match_id",
    "bookmaker",
    "captured_at",
    "home_odds",
    "draw_odds",
    "away_odds",
    "odds_type",
    "source",
)


@dataclass(frozen=True)
class MarketOddsSnapshot:
    """One historical 1X2 decimal-odds snapshot for a match."""

    match_id: str
    bookmaker: str
    captured_at: str
    home_odds: float
    draw_odds: float
    away_odds: float
    odds_type: str = "closing"
    source: str = "unknown"

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.bookmaker:
            raise ValueError("bookmaker cannot be empty")
        if not self.captured_at:
            raise ValueError("captured_at cannot be empty")
        if not self.odds_type:
            raise ValueError("odds_type cannot be empty")
        if not self.source:
            raise ValueError("source cannot be empty")
        _validate_iso_datetime_or_date(self.captured_at)
        for name, odds in self.to_odds_map().items():
            if odds <= 1.0:
                raise ValueError(f"decimal odds for {name!r} must be greater than 1.0")

    def to_odds_map(self) -> dict[str, float]:
        """Return decimal odds keyed by canonical 1X2 outcome."""
        return {
            OUTCOME_HOME: self.home_odds,
            OUTCOME_DRAW: self.draw_odds,
            OUTCOME_AWAY: self.away_odds,
        }

    def to_dict(self) -> dict[str, object]:
        """Return a CSV/JSON-ready row."""
        return {
            "match_id": self.match_id,
            "bookmaker": self.bookmaker,
            "captured_at": self.captured_at,
            "home_odds": self.home_odds,
            "draw_odds": self.draw_odds,
            "away_odds": self.away_odds,
            "odds_type": self.odds_type,
            "source": self.source,
        }


def load_market_odds_csv(path: str | Path) -> list[MarketOddsSnapshot]:
    """Load historical 1X2 market odds from a canonical CSV file."""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("market odds CSV must include a header row")
        missing = sorted(set(MARKET_ODDS_COLUMNS).difference(reader.fieldnames))
        if missing:
            raise ValueError(f"market odds CSV missing required columns: {missing}")
        return [_parse_market_odds_row(row, row_number=index + 2) for index, row in enumerate(reader)]


def write_market_odds_csv(
    snapshots: Iterable[MarketOddsSnapshot],
    destination_path: str | Path,
) -> Path:
    """Write canonical market odds snapshots to CSV."""
    rows = list(snapshots)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MARKET_ODDS_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    return destination


def select_one_odds_per_match(
    snapshots: Iterable[MarketOddsSnapshot],
    *,
    preferred_odds_type: str = "closing",
) -> dict[str, MarketOddsSnapshot]:
    """Select one odds row per match, preferring the requested odds type."""
    selected: dict[str, MarketOddsSnapshot] = {}
    for snapshot in snapshots:
        existing = selected.get(snapshot.match_id)
        if existing is None:
            selected[snapshot.match_id] = snapshot
            continue
        if existing.odds_type != preferred_odds_type and snapshot.odds_type == preferred_odds_type:
            selected[snapshot.match_id] = snapshot
    return selected


def _parse_market_odds_row(row: dict[str, str], *, row_number: int) -> MarketOddsSnapshot:
    try:
        return MarketOddsSnapshot(
            match_id=_required(row, "match_id"),
            bookmaker=_required(row, "bookmaker"),
            captured_at=_required(row, "captured_at"),
            home_odds=float(_required(row, "home_odds")),
            draw_odds=float(_required(row, "draw_odds")),
            away_odds=float(_required(row, "away_odds")),
            odds_type=_required(row, "odds_type"),
            source=_required(row, "source"),
        )
    except ValueError as exc:
        raise ValueError(f"invalid market odds row {row_number}") from exc


def _required(row: dict[str, str], field_name: str) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _validate_iso_datetime_or_date(value: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
        return
    except ValueError:
        pass
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("captured_at must be an ISO datetime or YYYY-MM-DD date") from exc
