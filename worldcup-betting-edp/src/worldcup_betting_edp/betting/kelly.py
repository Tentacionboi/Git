"""Expected value, value-bet decisions, and fractional Kelly sizing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Simple risk buckets for single-outcome betting decisions."""

    NO_BET = "no_bet"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class BetSizingResult:
    """Kelly sizing output for a single bet."""

    full_kelly: float
    fractional_kelly: float
    capped_fraction: float

    def to_dict(self) -> dict[str, float]:
        return {
            "full_kelly": self.full_kelly,
            "fractional_kelly": self.fractional_kelly,
            "capped_fraction": self.capped_fraction,
        }


@dataclass(frozen=True)
class ValueBetDecision:
    """Decision record for a single outcome in one market."""

    is_value_bet: bool
    outcome: str
    model_probability: float
    market_probability: float
    decimal_odds: float
    probability_edge: float
    expected_value: float
    sizing: BetSizingResult
    risk_level: RiskLevel
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "is_value_bet": self.is_value_bet,
            "outcome": self.outcome,
            "model_probability": self.model_probability,
            "market_probability": self.market_probability,
            "decimal_odds": self.decimal_odds,
            "probability_edge": self.probability_edge,
            "expected_value": self.expected_value,
            "sizing": self.sizing.to_dict(),
            "risk_level": self.risk_level.value,
            "reason": self.reason,
        }


def _validate_probability(probability: float, name: str = "probability") -> None:
    if probability < 0.0 or probability > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def _validate_decimal_odds(decimal_odds: float) -> None:
    if decimal_odds <= 1.0:
        raise ValueError("decimal_odds must be greater than 1.0")


def expected_value(probability: float, decimal_odds: float) -> float:
    """Return expected profit per 1 unit staked."""
    _validate_probability(probability)
    _validate_decimal_odds(decimal_odds)
    return probability * decimal_odds - 1.0


def full_kelly_fraction(probability: float, decimal_odds: float) -> float:
    """Return full Kelly fraction, floored at zero for non-positive EV bets."""
    ev = expected_value(probability, decimal_odds)
    if ev <= 0.0:
        return 0.0
    return ev / (decimal_odds - 1.0)


def fractional_kelly_fraction(
    probability: float,
    decimal_odds: float,
    *,
    fraction: float = 0.25,
    cap: float = 0.02,
) -> BetSizingResult:
    """Return fractional Kelly sizing with a hard cap.

    Defaults are intentionally conservative: quarter Kelly capped at 2% of bankroll.
    """
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError("fraction must be in (0, 1]")
    if cap < 0.0 or cap > 1.0:
        raise ValueError("cap must be in [0, 1]")

    full = full_kelly_fraction(probability, decimal_odds)
    fractional = full * fraction
    capped = min(fractional, cap)
    return BetSizingResult(
        full_kelly=full,
        fractional_kelly=fractional,
        capped_fraction=capped,
    )


def classify_risk(probability: float, decimal_odds: float, is_value_bet: bool) -> RiskLevel:
    """Classify single-bet risk from probability and odds."""
    _validate_probability(probability)
    _validate_decimal_odds(decimal_odds)

    if not is_value_bet:
        return RiskLevel.NO_BET
    if decimal_odds >= 8.0 or probability < 0.12:
        return RiskLevel.EXTREME
    if decimal_odds >= 4.0 or probability < 0.25:
        return RiskLevel.HIGH
    if decimal_odds >= 2.5 or probability < 0.40:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def evaluate_value_bet(
    *,
    outcome: str,
    model_probability: float,
    market_probability: float,
    decimal_odds: float,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
) -> ValueBetDecision:
    """Evaluate whether one outcome is a value bet."""
    _validate_probability(model_probability, "model_probability")
    _validate_probability(market_probability, "market_probability")
    _validate_decimal_odds(decimal_odds)

    probability_edge = model_probability - market_probability
    ev = expected_value(model_probability, decimal_odds)
    sizing = fractional_kelly_fraction(
        model_probability,
        decimal_odds,
        fraction=kelly_fraction,
        cap=stake_cap,
    )

    is_value = (
        probability_edge >= probability_edge_threshold
        and ev >= ev_threshold
        and sizing.capped_fraction > 0.0
    )

    risk_level = classify_risk(model_probability, decimal_odds, is_value)

    if is_value:
        reason = (
            f"positive edge: model-market={probability_edge:.4f}, "
            f"EV={ev:.4f}, stake={sizing.capped_fraction:.4f}"
        )
    elif probability_edge < probability_edge_threshold:
        reason = (
            f"no bet: probability edge {probability_edge:.4f} below "
            f"threshold {probability_edge_threshold:.4f}"
        )
    elif ev < ev_threshold:
        reason = f"no bet: EV {ev:.4f} below threshold {ev_threshold:.4f}"
    else:
        reason = "no bet: Kelly sizing is zero after constraints"

    return ValueBetDecision(
        is_value_bet=is_value,
        outcome=outcome,
        model_probability=model_probability,
        market_probability=market_probability,
        decimal_odds=decimal_odds,
        probability_edge=probability_edge,
        expected_value=ev,
        sizing=sizing,
        risk_level=risk_level,
        reason=reason,
    )
