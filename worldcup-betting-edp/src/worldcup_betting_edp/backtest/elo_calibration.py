"""Calibration helpers for Elo-derived 1X2 probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Sequence

from worldcup_betting_edp.backtest.probability_evaluation import (
    ProbabilityEvaluationSummary,
    evaluate_1x2_probability_rows,
)
from worldcup_betting_edp.models import (
    EloMatchRating,
    EloProbabilityConfig,
    build_elo_probability_history,
)


DEFAULT_BASE_DRAW_PROBABILITIES = (
    0.18,
    0.20,
    0.22,
    0.24,
    0.26,
    0.28,
    0.30,
    0.32,
    0.34,
)
DEFAULT_DRAW_GAP_PENALTIES = (
    0.000,
    0.005,
    0.010,
    0.015,
    0.020,
    0.025,
    0.030,
    0.035,
    0.040,
    0.045,
    0.050,
)


@dataclass(frozen=True)
class EloCalibrationCandidate:
    """One candidate draw-configuration and its evaluation summary."""

    probability_config: EloProbabilityConfig
    summary: ProbabilityEvaluationSummary

    def objective_value(self, objective_metric: str) -> float:
        """Return the candidate value for the selected objective metric."""
        if objective_metric == "mean_log_loss":
            return self.summary.mean_log_loss
        if objective_metric == "mean_brier_score":
            return self.summary.mean_brier_score
        raise ValueError("objective_metric must be mean_log_loss or mean_brier_score")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready candidate payload."""
        return {
            "probability_config": {
                "base_draw_probability": self.probability_config.base_draw_probability,
                "draw_gap_penalty_per_100_elo": self.probability_config.draw_gap_penalty_per_100_elo,
                "min_draw_probability": self.probability_config.min_draw_probability,
                "max_draw_probability": self.probability_config.max_draw_probability,
            },
            "summary": self.summary.to_dict(),
        }


@dataclass(frozen=True)
class EloCalibrationResult:
    """Best Elo draw-calibration result from a candidate grid."""

    model_name: str
    objective_metric: str
    candidate_count: int
    best_candidate: EloCalibrationCandidate

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready calibration result."""
        return {
            "model_name": self.model_name,
            "objective_metric": self.objective_metric,
            "candidate_count": self.candidate_count,
            "best_candidate": self.best_candidate.to_dict(),
        }


def default_elo_probability_config_grid() -> list[EloProbabilityConfig]:
    """Return the default draw-probability grid used for MVP calibration."""
    return [
        EloProbabilityConfig(
            base_draw_probability=base_draw_probability,
            draw_gap_penalty_per_100_elo=draw_gap_penalty,
            min_draw_probability=0.08,
            max_draw_probability=0.40,
        )
        for base_draw_probability in DEFAULT_BASE_DRAW_PROBABILITIES
        for draw_gap_penalty in DEFAULT_DRAW_GAP_PENALTIES
    ]


def calibrate_elo_probability_config(
    rating_history: Iterable[EloMatchRating],
    *,
    model_name: str,
    candidate_configs: Sequence[EloProbabilityConfig] | None = None,
    objective_metric: str = "mean_log_loss",
) -> EloCalibrationResult:
    """Select the best draw-probability config from historical Elo rows."""
    rows = list(rating_history)
    if not rows:
        raise ValueError("cannot calibrate Elo probabilities with empty rating history")
    if objective_metric not in {"mean_log_loss", "mean_brier_score"}:
        raise ValueError("objective_metric must be mean_log_loss or mean_brier_score")

    configs = list(candidate_configs or default_elo_probability_config_grid())
    if not configs:
        raise ValueError("candidate_configs cannot be empty")

    candidates: list[EloCalibrationCandidate] = []
    for index, config in enumerate(configs):
        probabilities = build_elo_probability_history(rows, probability_config=config)
        summary = evaluate_1x2_probability_rows(
            (row.to_dict() for row in probabilities),
            model_name=f"{model_name}_candidate_{index}",
        )
        candidates.append(EloCalibrationCandidate(config, summary))

    best_candidate = min(
        candidates,
        key=lambda candidate: (
            candidate.objective_value(objective_metric),
            candidate.summary.mean_brier_score,
            -candidate.summary.accuracy,
        ),
    )
    return EloCalibrationResult(
        model_name=model_name,
        objective_metric=objective_metric,
        candidate_count=len(candidates),
        best_candidate=best_candidate,
    )


def filter_rating_history_by_date(
    rating_history: Iterable[EloMatchRating],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[EloMatchRating]:
    """Filter rating-history rows by inclusive ISO date bounds."""
    rows = list(rating_history)
    if start_date is None and end_date is None:
        return rows
    return [
        row
        for row in rows
        if (start_date is None or row.match_date >= start_date)
        and (end_date is None or row.match_date <= end_date)
    ]


def write_elo_calibration_report_json(
    calibration_result: EloCalibrationResult,
    destination_path: str | Path,
    *,
    validation_summary: ProbabilityEvaluationSummary | None = None,
    full_sample_summary: ProbabilityEvaluationSummary | None = None,
    notes: Sequence[str] | None = None,
) -> Path:
    """Write calibration result and optional holdout summaries to JSON."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "calibration": calibration_result.to_dict(),
        "notes": list(notes or []),
    }
    if validation_summary is not None:
        payload["validation_summary"] = validation_summary.to_dict()
    if full_sample_summary is not None:
        payload["full_sample_summary"] = full_sample_summary.to_dict()
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
