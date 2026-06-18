"""Core domain schemas for the single-match MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


OUTCOME_HOME = "home"
OUTCOME_DRAW = "draw"
OUTCOME_AWAY = "away"
OUTCOMES_1X2 = (OUTCOME_HOME, OUTCOME_DRAW, OUTCOME_AWAY)


def validate_probability_map(
    probabilities: Mapping[str, float],
    *,
    expected_outcomes: tuple[str, ...] = OUTCOMES_1X2,
    tolerance: float = 1e-9,
) -> None:
    """Validate a complete probability map for the expected outcomes."""
    missing = [outcome for outcome in expected_outcomes if outcome not in probabilities]
    if missing:
        raise ValueError(f"missing probabilities for outcomes: {missing}")

    for outcome in expected_outcomes:
        probability = probabilities[outcome]
        if probability < 0.0 or probability > 1.0:
            raise ValueError(f"probability for {outcome!r} must be in [0, 1]")

    total = sum(probabilities[outcome] for outcome in expected_outcomes)
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"probabilities must sum to 1.0, got {total:.12f}")


@dataclass(frozen=True)
class Match:
    """A football match as known before prediction time."""

    match_id: str
    match_time: datetime
    home_team: str
    away_team: str
    competition: str = "FIFA World Cup"
    stage: str = "unknown"
    neutral: bool = True

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.home_team:
            raise ValueError("home_team cannot be empty")
        if not self.away_team:
            raise ValueError("away_team cannot be empty")
        if self.home_team == self.away_team:
            raise ValueError("home_team and away_team must be different")


@dataclass(frozen=True)
class OddsSnapshot:
    """A timestamped decimal-odds snapshot for a 1X2 market."""

    match_id: str
    captured_at: datetime
    bookmaker: str
    home: float
    draw: float
    away: float
    market: str = "1X2"

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.bookmaker:
            raise ValueError("bookmaker cannot be empty")
        if self.market != "1X2":
            raise ValueError("MVP supports only the 1X2 market")
        for name, price in self.to_odds_map().items():
            if price <= 1.0:
                raise ValueError(f"decimal odds for {name!r} must be greater than 1.0")

    def to_odds_map(self) -> dict[str, float]:
        """Return odds keyed by canonical 1X2 outcome."""
        return {
            OUTCOME_HOME: self.home,
            OUTCOME_DRAW: self.draw,
            OUTCOME_AWAY: self.away,
        }


@dataclass(frozen=True)
class MarketProbabilities:
    """Market-implied probabilities after removing bookmaker margin."""

    match_id: str
    method: str
    odds: dict[str, float]
    implied_probabilities: dict[str, float]
    probabilities: dict[str, float]
    overround: float

    def __post_init__(self) -> None:
        validate_probability_map(self.probabilities)


@dataclass(frozen=True)
class ModelProbabilities:
    """A model probability vector for the 1X2 market."""

    match_id: str
    model_name: str
    probabilities: dict[str, float]

    def __post_init__(self) -> None:
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        validate_probability_map(self.probabilities)

    @classmethod
    def from_1x2(
        cls,
        *,
        match_id: str,
        model_name: str,
        home: float,
        draw: float,
        away: float,
    ) -> "ModelProbabilities":
        """Build model probabilities from explicit home/draw/away values."""
        return cls(
            match_id=match_id,
            model_name=model_name,
            probabilities={
                OUTCOME_HOME: home,
                OUTCOME_DRAW: draw,
                OUTCOME_AWAY: away,
            },
        )

