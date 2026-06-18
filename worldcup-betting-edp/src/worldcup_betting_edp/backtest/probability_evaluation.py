"""Aggregate evaluation for 1X2 probability tables."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from worldcup_betting_edp.backtest.scoring import brier_score, log_loss
from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME


@dataclass(frozen=True)
class ProbabilityEvaluationSummary:
    """Aggregate quality metrics for a probability forecast table."""

    model_name: str
    match_count: int
    accuracy: float
    mean_brier_score: float
    mean_log_loss: float
    average_probability_actual: float
    outcome_counts: dict[str, int]
    predicted_outcome_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready summary."""
        return {
            "model_name": self.model_name,
            "match_count": self.match_count,
            "accuracy": self.accuracy,
            "mean_brier_score": self.mean_brier_score,
            "mean_log_loss": self.mean_log_loss,
            "average_probability_actual": self.average_probability_actual,
            "outcome_counts": self.outcome_counts,
            "predicted_outcome_counts": self.predicted_outcome_counts,
        }


def load_1x2_probability_rows_csv(path: str | Path) -> list[dict[str, object]]:
    """Load a flat 1X2 probability CSV into typed row dictionaries."""
    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("probability CSV must include a header row")
        required = {
            "match_id",
            "home_probability",
            "draw_probability",
            "away_probability",
            "actual_result",
        }
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise ValueError(f"probability CSV missing required columns: {missing}")
        for row_number, row in enumerate(reader, start=2):
            rows.append(_parse_probability_row(row, row_number=row_number))
    return rows


def evaluate_1x2_probability_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    model_name: str,
) -> ProbabilityEvaluationSummary:
    """Evaluate Brier score, log loss, and accuracy for 1X2 probability rows."""
    evaluated_rows = list(rows)
    if not evaluated_rows:
        raise ValueError("cannot evaluate an empty probability row set")

    brier_scores: list[float] = []
    log_losses: list[float] = []
    actual_probabilities: list[float] = []
    correct_predictions = 0
    outcome_counts = {outcome: 0 for outcome in OUTCOMES_1X2}
    predicted_counts = {outcome: 0 for outcome in OUTCOMES_1X2}

    for row in evaluated_rows:
        actual = str(row["actual_result"])
        probabilities = _row_probabilities(row)
        predicted = _argmax_outcome(probabilities)
        brier_scores.append(brier_score(probabilities, actual))
        log_losses.append(log_loss(probabilities, actual))
        actual_probabilities.append(probabilities[actual])
        outcome_counts[actual] += 1
        predicted_counts[predicted] += 1
        if predicted == actual:
            correct_predictions += 1

    match_count = len(evaluated_rows)
    return ProbabilityEvaluationSummary(
        model_name=model_name,
        match_count=match_count,
        accuracy=correct_predictions / match_count,
        mean_brier_score=sum(brier_scores) / match_count,
        mean_log_loss=sum(log_losses) / match_count,
        average_probability_actual=sum(actual_probabilities) / match_count,
        outcome_counts=outcome_counts,
        predicted_outcome_counts=predicted_counts,
    )


def write_probability_evaluation_json(
    summary: ProbabilityEvaluationSummary,
    destination_path: str | Path,
) -> Path:
    """Write an aggregate probability evaluation report to JSON."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary.to_dict(),
        "notes": [
            "Lower Brier score and log loss are better.",
            "This report evaluates probability quality only; it does not include odds or betting ROI.",
        ],
    }
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _parse_probability_row(row: Mapping[str, str], *, row_number: int) -> dict[str, object]:
    try:
        home_probability = float(_required(row, "home_probability"))
        draw_probability = float(_required(row, "draw_probability"))
        away_probability = float(_required(row, "away_probability"))
    except ValueError as exc:
        raise ValueError(f"invalid probability fields at row {row_number}") from exc

    return {
        **dict(row),
        "home_probability": home_probability,
        "draw_probability": draw_probability,
        "away_probability": away_probability,
        "actual_result": _required(row, "actual_result"),
    }


def _row_probabilities(row: Mapping[str, object]) -> dict[str, float]:
    return {
        OUTCOME_HOME: float(row["home_probability"]),
        OUTCOME_DRAW: float(row["draw_probability"]),
        OUTCOME_AWAY: float(row["away_probability"]),
    }


def _argmax_outcome(probabilities: Mapping[str, float]) -> str:
    return max(OUTCOMES_1X2, key=lambda outcome: probabilities[outcome])


def _required(row: Mapping[str, str], field_name: str) -> str:
    value = row.get(field_name)
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} cannot be empty")
    return str(value).strip()
