"""Elo rating engine for historical national-team matches."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from worldcup_betting_edp.data import CanonicalMatch
from worldcup_betting_edp.domain import (
    OUTCOME_AWAY,
    OUTCOME_DRAW,
    OUTCOME_HOME,
    validate_probability_map,
)


DEFAULT_TOURNAMENT_MULTIPLIERS = {
    "FIFA World Cup": 1.50,
    "FIFA World Cup qualification": 1.25,
    "UEFA Euro": 1.35,
    "UEFA Euro qualification": 1.15,
    "Copa America": 1.30,
    "CONCACAF Championship": 1.20,
    "African Cup of Nations": 1.20,
    "AFC Asian Cup": 1.20,
    "Oceania Nations Cup": 1.15,
    "Friendly": 0.75,
}

ELO_RATING_HISTORY_COLUMNS = (
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "tournament",
    "neutral",
    "home_rating_pre",
    "away_rating_pre",
    "expected_home_score",
    "actual_home_score",
    "rating_delta",
    "home_rating_post",
    "away_rating_post",
)

CURRENT_ELO_RATING_COLUMNS = (
    "team",
    "rating",
    "matches_played",
    "last_match_date",
)

ELO_1X2_PROBABILITY_COLUMNS = (
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "tournament",
    "neutral",
    "home_rating_pre",
    "away_rating_pre",
    "rating_gap",
    "expected_home_score",
    "home_probability",
    "draw_probability",
    "away_probability",
    "actual_result",
)


@dataclass(frozen=True)
class EloConfig:
    """Configuration for a deterministic Elo update pass."""

    base_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 0.0
    tournament_multipliers: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_TOURNAMENT_MULTIPLIERS)
    )

    def __post_init__(self) -> None:
        if self.k_factor <= 0.0:
            raise ValueError("k_factor must be positive")
        if self.base_rating <= 0.0:
            raise ValueError("base_rating must be positive")
        for tournament, multiplier in self.tournament_multipliers.items():
            if not tournament:
                raise ValueError("tournament multiplier names cannot be empty")
            if multiplier <= 0.0:
                raise ValueError("tournament multipliers must be positive")


@dataclass(frozen=True)
class EloProbabilityConfig:
    """Configuration for splitting Elo expected score into 1X2 probabilities."""

    base_draw_probability: float = 0.27
    draw_gap_penalty_per_100_elo: float = 0.025
    min_draw_probability: float = 0.12
    max_draw_probability: float = 0.34

    def __post_init__(self) -> None:
        if not 0.0 < self.base_draw_probability < 1.0:
            raise ValueError("base_draw_probability must be in (0, 1)")
        if self.draw_gap_penalty_per_100_elo < 0.0:
            raise ValueError("draw_gap_penalty_per_100_elo cannot be negative")
        if not 0.0 <= self.min_draw_probability <= self.max_draw_probability < 1.0:
            raise ValueError("draw probability bounds must satisfy 0 <= min <= max < 1")


@dataclass(frozen=True)
class EloMatchRating:
    """One match's Elo state before and after applying the result."""

    match_id: str
    match_date: str
    home_team: str
    away_team: str
    tournament: str
    neutral: bool
    home_rating_pre: float
    away_rating_pre: float
    expected_home_score: float
    actual_home_score: float
    rating_delta: float
    home_rating_post: float
    away_rating_post: float

    def to_dict(self) -> dict[str, object]:
        """Return a flat row for CSV, JSON, or dashboard rendering."""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "tournament": self.tournament,
            "neutral": self.neutral,
            "home_rating_pre": self.home_rating_pre,
            "away_rating_pre": self.away_rating_pre,
            "expected_home_score": self.expected_home_score,
            "actual_home_score": self.actual_home_score,
            "rating_delta": self.rating_delta,
            "home_rating_post": self.home_rating_post,
            "away_rating_post": self.away_rating_post,
        }


@dataclass(frozen=True)
class EloMatchProbabilities:
    """One match's Elo-derived 1X2 probability row."""

    match_id: str
    match_date: str
    home_team: str
    away_team: str
    tournament: str
    neutral: bool
    home_rating_pre: float
    away_rating_pre: float
    rating_gap: float
    expected_home_score: float
    probabilities: dict[str, float]
    actual_result: str

    def __post_init__(self) -> None:
        validate_probability_map(self.probabilities)

    def to_dict(self) -> dict[str, object]:
        """Return a flat row for CSV, JSON, or dashboard rendering."""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "tournament": self.tournament,
            "neutral": self.neutral,
            "home_rating_pre": self.home_rating_pre,
            "away_rating_pre": self.away_rating_pre,
            "rating_gap": self.rating_gap,
            "expected_home_score": self.expected_home_score,
            "home_probability": self.probabilities[OUTCOME_HOME],
            "draw_probability": self.probabilities[OUTCOME_DRAW],
            "away_probability": self.probabilities[OUTCOME_AWAY],
            "actual_result": self.actual_result,
        }


def expected_home_score(
    home_rating: float,
    away_rating: float,
    *,
    home_advantage: float = 0.0,
) -> float:
    """Return the Elo expected score for the home side."""
    adjusted_home_rating = home_rating + home_advantage
    return 1.0 / (1.0 + 10.0 ** ((away_rating - adjusted_home_rating) / 400.0))


def draw_probability_from_rating_gap(
    rating_gap: float,
    *,
    config: EloProbabilityConfig | None = None,
) -> float:
    """Estimate draw probability from absolute Elo gap using a simple heuristic."""
    active_config = config or EloProbabilityConfig()
    draw_probability = (
        active_config.base_draw_probability
        - active_config.draw_gap_penalty_per_100_elo * abs(rating_gap) / 100.0
    )
    return _clip(
        draw_probability,
        lower=active_config.min_draw_probability,
        upper=active_config.max_draw_probability,
    )


def elo_1x2_probabilities(
    *,
    home_rating: float,
    away_rating: float,
    neutral: bool = True,
    elo_config: EloConfig | None = None,
    probability_config: EloProbabilityConfig | None = None,
) -> dict[str, float]:
    """Convert two Elo ratings into home/draw/away probabilities.

    Elo directly estimates expected score, not 1X2 probabilities. This function
    applies a transparent draw heuristic, then allocates the remaining mass so
    that `P(home) + 0.5 * P(draw)` equals the Elo expected home score.
    """
    active_elo_config = elo_config or EloConfig()
    active_probability_config = probability_config or EloProbabilityConfig()
    home_advantage = 0.0 if neutral else active_elo_config.home_advantage
    expected = expected_home_score(
        home_rating,
        away_rating,
        home_advantage=home_advantage,
    )
    rating_gap = home_rating + home_advantage - away_rating
    draw_probability = draw_probability_from_rating_gap(
        rating_gap,
        config=active_probability_config,
    )

    max_draw_probability = 2.0 * min(expected, 1.0 - expected)
    draw_probability = min(draw_probability, max_draw_probability)
    home_probability = expected - 0.5 * draw_probability
    away_probability = 1.0 - expected - 0.5 * draw_probability

    probabilities = {
        OUTCOME_HOME: home_probability,
        OUTCOME_DRAW: draw_probability,
        OUTCOME_AWAY: away_probability,
    }
    validate_probability_map(probabilities, tolerance=1e-8)
    return probabilities


def actual_home_score(result_1x2: str) -> float:
    """Map a 1X2 result into the Elo actual-score convention."""
    if result_1x2 == OUTCOME_HOME:
        return 1.0
    if result_1x2 == OUTCOME_DRAW:
        return 0.5
    if result_1x2 == OUTCOME_AWAY:
        return 0.0
    raise ValueError(f"unsupported result_1x2: {result_1x2!r}")


def tournament_multiplier(tournament: str, config: EloConfig | None = None) -> float:
    """Return the configured K-factor multiplier for a tournament."""
    active_config = config or EloConfig()
    return active_config.tournament_multipliers.get(tournament, 1.0)


def update_elo_ratings(
    *,
    home_rating: float,
    away_rating: float,
    result_1x2: str,
    tournament: str = "",
    neutral: bool = True,
    config: EloConfig | None = None,
) -> tuple[float, float, float, float, float]:
    """Apply one match result and return post ratings plus diagnostics.

    Returns:
        `(home_post, away_post, expected_home, actual_home, rating_delta)`.
    """
    active_config = config or EloConfig()
    home_advantage = 0.0 if neutral else active_config.home_advantage
    expected = expected_home_score(
        home_rating,
        away_rating,
        home_advantage=home_advantage,
    )
    actual = actual_home_score(result_1x2)
    multiplier = tournament_multiplier(tournament, active_config)
    rating_delta = active_config.k_factor * multiplier * (actual - expected)
    return (
        home_rating + rating_delta,
        away_rating - rating_delta,
        expected,
        actual,
        rating_delta,
    )


def build_elo_rating_history(
    matches: Iterable[CanonicalMatch],
    *,
    config: EloConfig | None = None,
) -> list[EloMatchRating]:
    """Run chronological Elo updates over canonical historical matches."""
    active_config = config or EloConfig()
    ratings: dict[str, float] = {}
    history: list[EloMatchRating] = []

    for match in sorted(matches, key=_match_sort_key):
        home_pre = ratings.get(match.home_team, active_config.base_rating)
        away_pre = ratings.get(match.away_team, active_config.base_rating)
        home_post, away_post, expected, actual, rating_delta = update_elo_ratings(
            home_rating=home_pre,
            away_rating=away_pre,
            result_1x2=match.result_1x2,
            tournament=match.tournament,
            neutral=match.neutral,
            config=active_config,
        )
        ratings[match.home_team] = home_post
        ratings[match.away_team] = away_post
        history.append(
            EloMatchRating(
                match_id=match.match_id,
                match_date=match.match_date,
                home_team=match.home_team,
                away_team=match.away_team,
                tournament=match.tournament,
                neutral=match.neutral,
                home_rating_pre=home_pre,
                away_rating_pre=away_pre,
                expected_home_score=expected,
                actual_home_score=actual,
                rating_delta=rating_delta,
                home_rating_post=home_post,
                away_rating_post=away_post,
            )
        )

    return history


def current_elo_ratings(
    matches: Iterable[CanonicalMatch],
    *,
    config: EloConfig | None = None,
) -> dict[str, float]:
    """Return latest ratings after replaying all supplied matches."""
    ratings: dict[str, float] = {}
    for row in build_elo_rating_history(matches, config=config):
        ratings[row.home_team] = row.home_rating_post
        ratings[row.away_team] = row.away_rating_post
    return ratings


def build_elo_probability_history(
    rating_history: Iterable[EloMatchRating],
    *,
    elo_config: EloConfig | None = None,
    probability_config: EloProbabilityConfig | None = None,
) -> list[EloMatchProbabilities]:
    """Build historical 1X2 probability rows from pre-match Elo ratings."""
    active_elo_config = elo_config or EloConfig()
    rows: list[EloMatchProbabilities] = []
    for rating in rating_history:
        home_advantage = 0.0 if rating.neutral else active_elo_config.home_advantage
        rating_gap = rating.home_rating_pre + home_advantage - rating.away_rating_pre
        probabilities = elo_1x2_probabilities(
            home_rating=rating.home_rating_pre,
            away_rating=rating.away_rating_pre,
            neutral=rating.neutral,
            elo_config=active_elo_config,
            probability_config=probability_config,
        )
        rows.append(
            EloMatchProbabilities(
                match_id=rating.match_id,
                match_date=rating.match_date,
                home_team=rating.home_team,
                away_team=rating.away_team,
                tournament=rating.tournament,
                neutral=rating.neutral,
                home_rating_pre=rating.home_rating_pre,
                away_rating_pre=rating.away_rating_pre,
                rating_gap=rating_gap,
                expected_home_score=rating.expected_home_score,
                probabilities=probabilities,
                actual_result=_result_from_actual_score(rating.actual_home_score),
            )
        )
    return rows


def current_elo_table(history: Iterable[EloMatchRating]) -> list[dict[str, object]]:
    """Return latest ratings with match counts and last observed dates."""
    ratings: dict[str, float] = {}
    match_counts: dict[str, int] = {}
    last_dates: dict[str, str] = {}

    for row in history:
        ratings[row.home_team] = row.home_rating_post
        ratings[row.away_team] = row.away_rating_post
        match_counts[row.home_team] = match_counts.get(row.home_team, 0) + 1
        match_counts[row.away_team] = match_counts.get(row.away_team, 0) + 1
        last_dates[row.home_team] = row.match_date
        last_dates[row.away_team] = row.match_date

    return [
        {
            "team": team,
            "rating": ratings[team],
            "matches_played": match_counts[team],
            "last_match_date": last_dates[team],
        }
        for team in sorted(ratings, key=lambda name: (-ratings[name], name))
    ]


def write_elo_rating_history_csv(
    history: Iterable[EloMatchRating],
    destination_path: str | Path,
) -> Path:
    """Write full Elo match history to CSV with sidecar metadata."""
    rows = list(history)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ELO_RATING_HISTORY_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    dates = [row.match_date for row in rows]
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
        "columns": list(ELO_RATING_HISTORY_COLUMNS),
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def write_current_elo_ratings_csv(
    current_ratings: Iterable[dict[str, object]],
    destination_path: str | Path,
) -> Path:
    """Write latest team Elo ratings to CSV with sidecar metadata."""
    rows = list(current_ratings)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CURRENT_ELO_RATING_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "columns": list(CURRENT_ELO_RATING_COLUMNS),
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def write_elo_probability_history_csv(
    probabilities: Iterable[EloMatchProbabilities],
    destination_path: str | Path,
) -> Path:
    """Write Elo-derived 1X2 probability history to CSV with sidecar metadata."""
    rows = list(probabilities)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ELO_1X2_PROBABILITY_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    dates = [row.match_date for row in rows]
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
        "columns": list(ELO_1X2_PROBABILITY_COLUMNS),
        "model_note": "Simple heuristic split of Elo expected score into 1X2 probabilities; not market-validated.",
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _match_sort_key(match: CanonicalMatch) -> tuple[str, int, str]:
    return (match.match_date, _source_index(match.source_match_id), match.match_id)


def _source_index(source_match_id: str) -> int:
    try:
        return int(source_match_id.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return 0


def _result_from_actual_score(actual_score: float) -> str:
    if actual_score == 1.0:
        return OUTCOME_HOME
    if actual_score == 0.5:
        return OUTCOME_DRAW
    if actual_score == 0.0:
        return OUTCOME_AWAY
    raise ValueError(f"unsupported Elo actual score: {actual_score!r}")


def _clip(value: float, *, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
