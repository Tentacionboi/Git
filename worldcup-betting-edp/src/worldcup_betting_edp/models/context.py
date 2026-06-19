"""Context-adjusted Elo probability layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from worldcup_betting_edp.domain import (
    OUTCOMES_1X2,
    OUTCOME_AWAY,
    OUTCOME_DRAW,
    OUTCOME_HOME,
    validate_probability_map,
)
from worldcup_betting_edp.evidence import (
    EVIDENCE_AVAILABLE,
    EVIDENCE_PARTIAL,
    EVIDENCE_STALE,
    EVIDENCE_STATUSES,
)
from worldcup_betting_edp.models.elo import EloBasePrediction


CONTEXT_FACTOR_REST = "rest"
CONTEXT_FACTOR_TRAVEL = "travel"
CONTEXT_FACTOR_HOST = "host"
CONTEXT_FACTOR_FORM = "form"
CONTEXT_FACTOR_LINEUP = "lineup"
CONTEXT_FACTOR_NAMES = (
    CONTEXT_FACTOR_REST,
    CONTEXT_FACTOR_TRAVEL,
    CONTEXT_FACTOR_HOST,
    CONTEXT_FACTOR_FORM,
    CONTEXT_FACTOR_LINEUP,
)
CONTEXT_USABLE_STATUSES = {EVIDENCE_AVAILABLE, EVIDENCE_PARTIAL, EVIDENCE_STALE}


@dataclass(frozen=True)
class ContextAdjustmentConfig:
    """Conservative context adjustment weights.

    Factor values are signed home-team advantages. A positive value favors the
    home/canonical home side; a negative value favors away.
    """

    rest_weight: float = 0.006
    travel_weight: float = 0.004
    host_weight: float = 0.020
    form_weight: float = 0.010
    lineup_weight: float = 0.015
    max_factor_adjustment: float = 0.025
    max_total_adjustment_per_outcome: float = 0.060
    min_probability: float = 0.01

    def __post_init__(self) -> None:
        for name, value in self.to_weight_map().items():
            if value < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if self.max_factor_adjustment < 0.0:
            raise ValueError("max_factor_adjustment cannot be negative")
        if self.max_total_adjustment_per_outcome < 0.0:
            raise ValueError("max_total_adjustment_per_outcome cannot be negative")
        if self.min_probability < 0.0:
            raise ValueError("min_probability cannot be negative")
        if self.min_probability * len(OUTCOMES_1X2) >= 1.0:
            raise ValueError("min_probability leaves no probability mass to allocate")

    def to_weight_map(self) -> dict[str, float]:
        return {
            CONTEXT_FACTOR_REST: self.rest_weight,
            CONTEXT_FACTOR_TRAVEL: self.travel_weight,
            CONTEXT_FACTOR_HOST: self.host_weight,
            CONTEXT_FACTOR_FORM: self.form_weight,
            CONTEXT_FACTOR_LINEUP: self.lineup_weight,
        }


@dataclass(frozen=True)
class ContextFactor:
    """One signed context factor and its evidence status."""

    name: str
    value: float | None
    status: str
    source: str = "unknown"
    detail: str = ""

    def __post_init__(self) -> None:
        if self.name not in CONTEXT_FACTOR_NAMES:
            raise ValueError(f"unsupported context factor: {self.name!r}")
        if self.status not in EVIDENCE_STATUSES:
            raise ValueError(f"unsupported context factor status: {self.status!r}")
        if not self.source:
            raise ValueError("context factor source cannot be empty")

    @property
    def usable_for_probability(self) -> bool:
        return self.value is not None and self.status in CONTEXT_USABLE_STATUSES

    def to_dict(self, *, adjustment: float = 0.0) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "detail": self.detail,
            "adjustment": adjustment,
            "usable_for_probability": self.usable_for_probability,
        }


@dataclass(frozen=True)
class ContextAdjustedEloPrediction:
    """Fundamental probability after bounded context adjustment to Elo."""

    match_id: str
    model_name: str
    elo_base: EloBasePrediction
    factors: tuple[ContextFactor, ...]
    factor_adjustments: dict[str, float]
    total_home_away_adjustment: float
    probabilities: dict[str, float]
    config: ContextAdjustmentConfig

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        validate_probability_map(self.probabilities)

    def to_dict(self) -> dict[str, object]:
        return {
            "match_id": self.match_id,
            "model_name": self.model_name,
            "elo_base": self.elo_base.to_dict(),
            "factors": {
                factor.name: factor.to_dict(
                    adjustment=self.factor_adjustments.get(factor.name, 0.0)
                )
                for factor in self.factors
            },
            "total_home_away_adjustment": self.total_home_away_adjustment,
            "probabilities": dict(self.probabilities),
            "config": {
                "weights": self.config.to_weight_map(),
                "max_factor_adjustment": self.config.max_factor_adjustment,
                "max_total_adjustment_per_outcome": self.config.max_total_adjustment_per_outcome,
                "min_probability": self.config.min_probability,
            },
        }


def build_context_adjusted_elo_prediction(
    *,
    elo_base: EloBasePrediction,
    factors: Sequence[ContextFactor] = (),
    config: ContextAdjustmentConfig | None = None,
    model_name: str = "context_adjusted_elo",
) -> ContextAdjustedEloPrediction:
    """Apply bounded context adjustments to Elo base probabilities."""
    active_config = config or ContextAdjustmentConfig()
    weights = active_config.to_weight_map()
    factor_adjustments: dict[str, float] = {}
    total = 0.0
    for factor in factors:
        if not factor.usable_for_probability:
            factor_adjustments[factor.name] = 0.0
            continue
        adjustment = weights[factor.name] * float(factor.value)
        adjustment = _clip(
            adjustment,
            lower=-active_config.max_factor_adjustment,
            upper=active_config.max_factor_adjustment,
        )
        factor_adjustments[factor.name] = adjustment
        total += adjustment

    total = _clip(
        total,
        lower=-active_config.max_total_adjustment_per_outcome,
        upper=active_config.max_total_adjustment_per_outcome,
    )
    probabilities = _apply_home_away_adjustment(
        elo_base.probabilities,
        home_away_adjustment=total,
        min_probability=active_config.min_probability,
    )
    return ContextAdjustedEloPrediction(
        match_id=elo_base.match_id,
        model_name=model_name,
        elo_base=elo_base,
        factors=tuple(factors),
        factor_adjustments=factor_adjustments,
        total_home_away_adjustment=total,
        probabilities=probabilities,
        config=active_config,
    )


def default_missing_context_factors() -> tuple[ContextFactor, ...]:
    """Return the MVP context factor set with missing status and no adjustment."""
    return tuple(
        ContextFactor(
            name=name,
            value=None,
            status="missing",
            source="not_configured",
            detail="context data not supplied",
        )
        for name in CONTEXT_FACTOR_NAMES
    )


def _apply_home_away_adjustment(
    probabilities: Mapping[str, float],
    *,
    home_away_adjustment: float,
    min_probability: float,
) -> dict[str, float]:
    proposed = {
        OUTCOME_HOME: probabilities[OUTCOME_HOME] + home_away_adjustment,
        OUTCOME_DRAW: probabilities[OUTCOME_DRAW],
        OUTCOME_AWAY: probabilities[OUTCOME_AWAY] - home_away_adjustment,
    }
    proposed = {outcome: max(min_probability, proposed[outcome]) for outcome in OUTCOMES_1X2}
    total = sum(proposed.values())
    result = {outcome: proposed[outcome] / total for outcome in OUTCOMES_1X2}
    validate_probability_map(result)
    return result


def _clip(value: float, *, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
