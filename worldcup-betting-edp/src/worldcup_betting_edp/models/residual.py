"""Market-residual probability model for World Cup 1X2 pricing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from worldcup_betting_edp.domain import (
    OUTCOMES_1X2,
    OUTCOME_AWAY,
    OUTCOME_DRAW,
    OUTCOME_HOME,
    ModelProbabilities,
    validate_probability_map,
)
from worldcup_betting_edp.market import MarketMovementFeatures


@dataclass(frozen=True)
class ResidualEdgeConfig:
    """Conservative configuration for market-residual adjustment."""

    model_name: str = "market_residual_mvp"
    fundamental_gap_weight: float = 0.25
    market_movement_weight: float = 0.0
    max_abs_adjustment_per_outcome: float = 0.05
    min_probability: float = 0.01

    def __post_init__(self) -> None:
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if self.fundamental_gap_weight < 0.0:
            raise ValueError("fundamental_gap_weight must be non-negative")
        if self.market_movement_weight < 0.0:
            raise ValueError("market_movement_weight must be non-negative")
        if self.max_abs_adjustment_per_outcome < 0.0:
            raise ValueError("max_abs_adjustment_per_outcome must be non-negative")
        if self.min_probability < 0.0:
            raise ValueError("min_probability must be non-negative")
        if self.min_probability * len(OUTCOMES_1X2) >= 1.0:
            raise ValueError("min_probability leaves no probability mass to allocate")


@dataclass(frozen=True)
class MarketResidualPrediction:
    """Final probability vector built as market probability plus residual adjustment."""

    match_id: str
    model_name: str
    market_probabilities: dict[str, float]
    fundamental_probabilities: dict[str, float]
    movement_probability_deltas: dict[str, float]
    residual_adjustments: dict[str, float]
    probabilities: dict[str, float]
    config: ResidualEdgeConfig

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        validate_probability_map(self.market_probabilities)
        validate_probability_map(self.fundamental_probabilities)
        validate_probability_map(self.probabilities)
        for outcome in OUTCOMES_1X2:
            if outcome not in self.movement_probability_deltas:
                raise ValueError(f"missing movement delta for {outcome!r}")
            if outcome not in self.residual_adjustments:
                raise ValueError(f"missing residual adjustment for {outcome!r}")

    @property
    def largest_adjustment_outcome(self) -> str:
        """Return the outcome with the largest absolute final adjustment."""
        return max(OUTCOMES_1X2, key=lambda outcome: abs(self.residual_adjustments[outcome]))

    @property
    def largest_adjustment(self) -> float:
        """Return the largest signed final adjustment."""
        return self.residual_adjustments[self.largest_adjustment_outcome]

    def to_model_probabilities(self) -> ModelProbabilities:
        """Return the final probabilities as a generic model probability object."""
        return ModelProbabilities(
            match_id=self.match_id,
            model_name=self.model_name,
            probabilities=dict(self.probabilities),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a flat JSON/CSV-ready row."""
        return {
            "match_id": self.match_id,
            "model_name": self.model_name,
            "market_home_probability": self.market_probabilities[OUTCOME_HOME],
            "market_draw_probability": self.market_probabilities[OUTCOME_DRAW],
            "market_away_probability": self.market_probabilities[OUTCOME_AWAY],
            "fundamental_home_probability": self.fundamental_probabilities[OUTCOME_HOME],
            "fundamental_draw_probability": self.fundamental_probabilities[OUTCOME_DRAW],
            "fundamental_away_probability": self.fundamental_probabilities[OUTCOME_AWAY],
            "movement_home_probability_delta": self.movement_probability_deltas[OUTCOME_HOME],
            "movement_draw_probability_delta": self.movement_probability_deltas[OUTCOME_DRAW],
            "movement_away_probability_delta": self.movement_probability_deltas[OUTCOME_AWAY],
            "home_residual_adjustment": self.residual_adjustments[OUTCOME_HOME],
            "draw_residual_adjustment": self.residual_adjustments[OUTCOME_DRAW],
            "away_residual_adjustment": self.residual_adjustments[OUTCOME_AWAY],
            "final_home_probability": self.probabilities[OUTCOME_HOME],
            "final_draw_probability": self.probabilities[OUTCOME_DRAW],
            "final_away_probability": self.probabilities[OUTCOME_AWAY],
            "largest_adjustment_outcome": self.largest_adjustment_outcome,
            "largest_adjustment": self.largest_adjustment,
            "fundamental_gap_weight": self.config.fundamental_gap_weight,
            "market_movement_weight": self.config.market_movement_weight,
            "max_abs_adjustment_per_outcome": self.config.max_abs_adjustment_per_outcome,
            "min_probability": self.config.min_probability,
        }


def build_market_residual_prediction(
    *,
    match_id: str,
    market_probabilities: Mapping[str, float],
    fundamental_probabilities: Mapping[str, float],
    movement_features: MarketMovementFeatures | None = None,
    config: ResidualEdgeConfig | None = None,
) -> MarketResidualPrediction:
    """Build a final 1X2 probability vector from market probability plus residuals.

    The model is deliberately conservative: market probability is the anchor, while
    fundamental and market-movement signals can only make bounded adjustments.
    """
    if not match_id:
        raise ValueError("match_id cannot be empty")
    config = config or ResidualEdgeConfig()
    market = _probability_dict(market_probabilities)
    fundamental = _probability_dict(fundamental_probabilities)
    movement = _movement_deltas(match_id, movement_features)

    raw_adjustments = {
        outcome: (
            config.fundamental_gap_weight * (fundamental[outcome] - market[outcome])
            + config.market_movement_weight * movement[outcome]
        )
        for outcome in OUTCOMES_1X2
    }
    centered_adjustments = _center_adjustments(raw_adjustments)
    capped_adjustments = _scale_to_cap(
        centered_adjustments,
        max_abs_adjustment=config.max_abs_adjustment_per_outcome,
    )
    final_probabilities = _apply_adjustments(
        market,
        capped_adjustments,
        min_probability=config.min_probability,
    )
    final_adjustments = {
        outcome: final_probabilities[outcome] - market[outcome] for outcome in OUTCOMES_1X2
    }
    return MarketResidualPrediction(
        match_id=match_id,
        model_name=config.model_name,
        market_probabilities=market,
        fundamental_probabilities=fundamental,
        movement_probability_deltas=movement,
        residual_adjustments=final_adjustments,
        probabilities=final_probabilities,
        config=config,
    )


def _probability_dict(probabilities: Mapping[str, float]) -> dict[str, float]:
    result = {outcome: float(probabilities[outcome]) for outcome in OUTCOMES_1X2}
    validate_probability_map(result)
    return result


def _movement_deltas(
    match_id: str,
    movement_features: MarketMovementFeatures | None,
) -> dict[str, float]:
    if movement_features is None:
        return {outcome: 0.0 for outcome in OUTCOMES_1X2}
    if movement_features.match_id != match_id:
        raise ValueError("movement_features must have the same match_id")
    return {outcome: movement_features.probability_deltas[outcome] for outcome in OUTCOMES_1X2}


def _center_adjustments(adjustments: Mapping[str, float]) -> dict[str, float]:
    mean_adjustment = sum(float(adjustments[outcome]) for outcome in OUTCOMES_1X2) / len(
        OUTCOMES_1X2
    )
    return {outcome: float(adjustments[outcome]) - mean_adjustment for outcome in OUTCOMES_1X2}


def _scale_to_cap(
    adjustments: Mapping[str, float],
    *,
    max_abs_adjustment: float,
) -> dict[str, float]:
    if max_abs_adjustment == 0.0:
        return {outcome: 0.0 for outcome in OUTCOMES_1X2}
    current_max = max(abs(float(adjustments[outcome])) for outcome in OUTCOMES_1X2)
    if current_max <= max_abs_adjustment:
        return {outcome: float(adjustments[outcome]) for outcome in OUTCOMES_1X2}
    scale = max_abs_adjustment / current_max
    return {outcome: float(adjustments[outcome]) * scale for outcome in OUTCOMES_1X2}


def _apply_adjustments(
    market_probabilities: Mapping[str, float],
    adjustments: Mapping[str, float],
    *,
    min_probability: float,
) -> dict[str, float]:
    proposed = {
        outcome: max(min_probability, market_probabilities[outcome] + adjustments[outcome])
        for outcome in OUTCOMES_1X2
    }
    total = sum(proposed.values())
    return {outcome: proposed[outcome] / total for outcome in OUTCOMES_1X2}
