"""Prediction quality metrics for 1X2 probability forecasts."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from worldcup_betting_edp.data import SettledResult
from worldcup_betting_edp.domain import OUTCOMES_1X2, validate_probability_map
from worldcup_betting_edp.reports import PredictionReport


@dataclass(frozen=True)
class ScoredPrediction:
    """Quality metrics for one prediction report scored against one settled result."""

    match_id: str
    actual_result: str
    model_name: str
    model_brier_score: float
    market_brier_score: float
    model_log_loss: float
    market_log_loss: float
    model_probability_actual: float
    market_probability_actual: float
    model_predicted_outcome: str
    market_predicted_outcome: str

    def to_dict(self) -> dict[str, Any]:
        """Return a flat scoring row for reports and future backtests."""
        return {
            "match_id": self.match_id,
            "actual_result": self.actual_result,
            "model_name": self.model_name,
            "model_brier_score": self.model_brier_score,
            "market_brier_score": self.market_brier_score,
            "model_log_loss": self.model_log_loss,
            "market_log_loss": self.market_log_loss,
            "model_probability_actual": self.model_probability_actual,
            "market_probability_actual": self.market_probability_actual,
            "model_predicted_outcome": self.model_predicted_outcome,
            "market_predicted_outcome": self.market_predicted_outcome,
            "model_beats_market_brier": self.model_brier_score < self.market_brier_score,
            "model_beats_market_log_loss": self.model_log_loss < self.market_log_loss,
        }


def brier_score(probabilities: Mapping[str, float], actual_outcome: str) -> float:
    """Return the multiclass Brier score for a 1X2 probability forecast.

    This uses the sum of squared errors across home/draw/away. Lower is better;
    perfect is 0.0.
    """
    validate_probability_map(probabilities)
    _validate_actual_outcome(actual_outcome)
    return sum(
        (float(probabilities[outcome]) - (1.0 if outcome == actual_outcome else 0.0)) ** 2
        for outcome in OUTCOMES_1X2
    )


def log_loss(
    probabilities: Mapping[str, float],
    actual_outcome: str,
    *,
    epsilon: float = 1e-15,
) -> float:
    """Return clipped multiclass log loss for a 1X2 probability forecast."""
    validate_probability_map(probabilities)
    _validate_actual_outcome(actual_outcome)
    if epsilon <= 0.0 or epsilon >= 0.5:
        raise ValueError("epsilon must be in (0, 0.5)")
    probability = min(max(float(probabilities[actual_outcome]), epsilon), 1.0 - epsilon)
    return -math.log(probability)


def score_prediction_report(
    *,
    report: PredictionReport,
    settled_result: SettledResult,
    epsilon: float = 1e-15,
) -> ScoredPrediction:
    """Score model and market probabilities against one settled result."""
    if report.match.match_id != settled_result.match_id:
        raise ValueError("report and settled_result must have the same match_id")

    actual = settled_result.result_1x2
    model_probabilities = report.model_probabilities.probabilities
    market_probabilities = report.market_probabilities.probabilities

    return ScoredPrediction(
        match_id=report.match.match_id,
        actual_result=actual,
        model_name=report.model_probabilities.model_name,
        model_brier_score=brier_score(model_probabilities, actual),
        market_brier_score=brier_score(market_probabilities, actual),
        model_log_loss=log_loss(model_probabilities, actual, epsilon=epsilon),
        market_log_loss=log_loss(market_probabilities, actual, epsilon=epsilon),
        model_probability_actual=float(model_probabilities[actual]),
        market_probability_actual=float(market_probabilities[actual]),
        model_predicted_outcome=_argmax_outcome(model_probabilities),
        market_predicted_outcome=_argmax_outcome(market_probabilities),
    )


def _argmax_outcome(probabilities: Mapping[str, float]) -> str:
    validate_probability_map(probabilities)
    return max(OUTCOMES_1X2, key=lambda outcome: probabilities[outcome])


def _validate_actual_outcome(actual_outcome: str) -> None:
    if actual_outcome not in OUTCOMES_1X2:
        raise ValueError(f"actual_outcome must be one of {OUTCOMES_1X2}")
