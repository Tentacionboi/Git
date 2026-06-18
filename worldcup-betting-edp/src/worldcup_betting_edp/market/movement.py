"""Market odds movement features for 1X2 odds time series."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from worldcup_betting_edp.data import MarketOddsSnapshot
from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME
from worldcup_betting_edp.market.devig import proportional_devig


MARKET_MOVEMENT_COLUMNS = (
    "match_id",
    "bookmaker",
    "start_odds_type",
    "end_odds_type",
    "start_captured_at",
    "end_captured_at",
    "start_overround",
    "end_overround",
    "overround_delta",
    "home_probability_start",
    "home_probability_end",
    "home_probability_delta",
    "draw_probability_start",
    "draw_probability_end",
    "draw_probability_delta",
    "away_probability_start",
    "away_probability_end",
    "away_probability_delta",
    "favorite_start",
    "favorite_end",
    "favorite_changed",
    "favorite_probability_delta",
    "largest_probability_move_outcome",
    "largest_probability_move",
)


@dataclass(frozen=True)
class MarketMovementFeatures:
    """Feature row describing a movement between two odds snapshots."""

    match_id: str
    bookmaker: str
    start_odds_type: str
    end_odds_type: str
    start_captured_at: str
    end_captured_at: str
    start_overround: float
    end_overround: float
    probabilities_start: dict[str, float]
    probabilities_end: dict[str, float]

    @property
    def probability_deltas(self) -> dict[str, float]:
        """Return end-minus-start probability deltas by outcome."""
        return {
            outcome: self.probabilities_end[outcome] - self.probabilities_start[outcome]
            for outcome in OUTCOMES_1X2
        }

    @property
    def favorite_start(self) -> str:
        """Return the outcome with the highest start probability."""
        return _argmax_outcome(self.probabilities_start)

    @property
    def favorite_end(self) -> str:
        """Return the outcome with the highest end probability."""
        return _argmax_outcome(self.probabilities_end)

    @property
    def favorite_changed(self) -> bool:
        """Return whether the market favorite changed over the interval."""
        return self.favorite_start != self.favorite_end

    @property
    def favorite_probability_delta(self) -> float:
        """Return probability movement for the starting favorite."""
        favorite = self.favorite_start
        return self.probabilities_end[favorite] - self.probabilities_start[favorite]

    @property
    def largest_probability_move_outcome(self) -> str:
        """Return the outcome with the largest absolute probability movement."""
        deltas = self.probability_deltas
        return max(OUTCOMES_1X2, key=lambda outcome: abs(deltas[outcome]))

    @property
    def largest_probability_move(self) -> float:
        """Return the largest signed probability movement."""
        return self.probability_deltas[self.largest_probability_move_outcome]

    def to_dict(self) -> dict[str, object]:
        """Return a flat row for CSV, JSON, or modeling."""
        deltas = self.probability_deltas
        return {
            "match_id": self.match_id,
            "bookmaker": self.bookmaker,
            "start_odds_type": self.start_odds_type,
            "end_odds_type": self.end_odds_type,
            "start_captured_at": self.start_captured_at,
            "end_captured_at": self.end_captured_at,
            "start_overround": self.start_overround,
            "end_overround": self.end_overround,
            "overround_delta": self.end_overround - self.start_overround,
            "home_probability_start": self.probabilities_start[OUTCOME_HOME],
            "home_probability_end": self.probabilities_end[OUTCOME_HOME],
            "home_probability_delta": deltas[OUTCOME_HOME],
            "draw_probability_start": self.probabilities_start[OUTCOME_DRAW],
            "draw_probability_end": self.probabilities_end[OUTCOME_DRAW],
            "draw_probability_delta": deltas[OUTCOME_DRAW],
            "away_probability_start": self.probabilities_start[OUTCOME_AWAY],
            "away_probability_end": self.probabilities_end[OUTCOME_AWAY],
            "away_probability_delta": deltas[OUTCOME_AWAY],
            "favorite_start": self.favorite_start,
            "favorite_end": self.favorite_end,
            "favorite_changed": self.favorite_changed,
            "favorite_probability_delta": self.favorite_probability_delta,
            "largest_probability_move_outcome": self.largest_probability_move_outcome,
            "largest_probability_move": self.largest_probability_move,
        }


def build_market_movement_feature(
    start: MarketOddsSnapshot,
    end: MarketOddsSnapshot,
) -> MarketMovementFeatures:
    """Build one market movement feature row from two odds snapshots."""
    if start.match_id != end.match_id:
        raise ValueError("start and end snapshots must have the same match_id")
    if start.bookmaker != end.bookmaker:
        raise ValueError("start and end snapshots must have the same bookmaker")
    if _timestamp_sort_key(start.captured_at) > _timestamp_sort_key(end.captured_at):
        raise ValueError("start snapshot must not be after end snapshot")

    start_devig = proportional_devig(start.to_odds_map())
    end_devig = proportional_devig(end.to_odds_map())
    return MarketMovementFeatures(
        match_id=start.match_id,
        bookmaker=start.bookmaker,
        start_odds_type=start.odds_type,
        end_odds_type=end.odds_type,
        start_captured_at=start.captured_at,
        end_captured_at=end.captured_at,
        start_overround=start_devig.overround,
        end_overround=end_devig.overround,
        probabilities_start=start_devig.fair_probabilities,
        probabilities_end=end_devig.fair_probabilities,
    )


def build_market_movement_features(
    snapshots: Iterable[MarketOddsSnapshot],
    *,
    start_odds_type: str = "opening",
    end_odds_type: str = "current",
) -> list[MarketMovementFeatures]:
    """Build movement features for each match/bookmaker with both snapshots."""
    grouped: dict[tuple[str, str], list[MarketOddsSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault((snapshot.match_id, snapshot.bookmaker), []).append(snapshot)

    features: list[MarketMovementFeatures] = []
    for group in grouped.values():
        start = _select_by_odds_type(group, start_odds_type)
        end = _select_by_odds_type(group, end_odds_type)
        if start is None or end is None:
            continue
        features.append(build_market_movement_feature(start, end))
    return sorted(features, key=lambda row: (row.match_id, row.bookmaker, row.end_captured_at))


def write_market_movement_features_csv(
    features: Iterable[MarketMovementFeatures],
    destination_path: str | Path,
) -> Path:
    """Write market movement features to CSV."""
    rows = list(features)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MARKET_MOVEMENT_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    return destination


def _select_by_odds_type(
    snapshots: Iterable[MarketOddsSnapshot],
    odds_type: str,
) -> MarketOddsSnapshot | None:
    candidates = [snapshot for snapshot in snapshots if snapshot.odds_type == odds_type]
    if not candidates:
        return None
    return sorted(candidates, key=lambda snapshot: _timestamp_sort_key(snapshot.captured_at))[-1]


def _argmax_outcome(probabilities: dict[str, float]) -> str:
    return max(OUTCOMES_1X2, key=lambda outcome: probabilities[outcome])


def _timestamp_sort_key(value: str) -> tuple[datetime, bool]:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized), False
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d"), True
