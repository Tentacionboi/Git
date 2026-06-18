"""Odds conversion and margin removal utilities.

The MVP uses proportional devig as the default market baseline. It is simple,
transparent, and hard to overfit. More complex methods such as Shin can be
added later only after they are tested against this baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


ProbabilityMap = dict[str, float]
OddsMap = Mapping[str, float]


@dataclass(frozen=True)
class DevigResult:
    """Result of converting decimal odds into devigged market probabilities."""

    method: str
    odds: dict[str, float]
    implied_probabilities: ProbabilityMap
    fair_probabilities: ProbabilityMap
    overround: float

    @property
    def margin_percent(self) -> float:
        """Return bookmaker margin as a percentage value."""
        return self.overround * 100.0


def _validate_decimal_odds(odds: OddsMap) -> None:
    if not odds:
        raise ValueError("odds cannot be empty")

    for outcome, price in odds.items():
        if price <= 1.0:
            raise ValueError(f"decimal odds for {outcome!r} must be greater than 1.0")


def implied_probabilities(odds: OddsMap) -> ProbabilityMap:
    """Convert decimal odds to raw implied probabilities."""
    _validate_decimal_odds(odds)
    return {outcome: 1.0 / price for outcome, price in odds.items()}


def overround(odds: OddsMap) -> float:
    """Return the bookmaker overround from decimal odds."""
    return sum(implied_probabilities(odds).values()) - 1.0


def normalize_probabilities(probabilities: Mapping[str, float]) -> ProbabilityMap:
    """Normalize positive probability-like values so they sum to one."""
    if not probabilities:
        raise ValueError("probabilities cannot be empty")

    total = sum(probabilities.values())
    if total <= 0.0:
        raise ValueError("probabilities must have a positive total")

    normalized: ProbabilityMap = {}
    for outcome, probability in probabilities.items():
        if probability < 0.0:
            raise ValueError(f"probability for {outcome!r} cannot be negative")
        normalized[outcome] = probability / total

    return normalized


def proportional_devig(odds: OddsMap) -> DevigResult:
    """Remove bookmaker margin by proportional normalization."""
    raw = implied_probabilities(odds)
    fair = normalize_probabilities(raw)
    return DevigResult(
        method="proportional",
        odds=dict(odds),
        implied_probabilities=raw,
        fair_probabilities=fair,
        overround=sum(raw.values()) - 1.0,
    )


def fair_odds(probability: float) -> float:
    """Return fair decimal odds for a probability."""
    if probability <= 0.0 or probability > 1.0:
        raise ValueError("probability must be in the interval (0, 1]")
    return 1.0 / probability

