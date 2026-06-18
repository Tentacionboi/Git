"""Compare model 1X2 probabilities against market-implied probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from worldcup_betting_edp.backtest.probability_evaluation import (
    ProbabilityEvaluationSummary,
    evaluate_1x2_probability_rows,
)
from worldcup_betting_edp.backtest.temporal_validation import (
    LEAKAGE_RISK_LOW,
    TIMING_MODE_PRE_MATCH,
    validate_odds_as_of_prediction,
)
from worldcup_betting_edp.data import MarketOddsSnapshot, select_one_odds_per_match
from worldcup_betting_edp.domain import OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME
from worldcup_betting_edp.market import proportional_devig


@dataclass(frozen=True)
class MarketComparisonRow:
    """One matched model-vs-market probability comparison row."""

    match_id: str
    actual_result: str
    bookmaker: str
    odds_type: str
    market_overround: float
    model_home_probability: float
    model_draw_probability: float
    model_away_probability: float
    market_home_probability: float
    market_draw_probability: float
    market_away_probability: float
    timing_valid: bool = True
    leakage_risk: str = LEAKAGE_RISK_LOW
    timing_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready comparison row."""
        return {
            "match_id": self.match_id,
            "actual_result": self.actual_result,
            "bookmaker": self.bookmaker,
            "odds_type": self.odds_type,
            "market_overround": self.market_overround,
            "model_home_probability": self.model_home_probability,
            "model_draw_probability": self.model_draw_probability,
            "model_away_probability": self.model_away_probability,
            "market_home_probability": self.market_home_probability,
            "market_draw_probability": self.market_draw_probability,
            "market_away_probability": self.market_away_probability,
            "timing_valid": self.timing_valid,
            "leakage_risk": self.leakage_risk,
            "timing_reasons": list(self.timing_reasons),
        }

    def model_probability_row(self) -> dict[str, object]:
        """Return a row compatible with probability evaluation helpers."""
        return {
            "match_id": self.match_id,
            "home_probability": self.model_home_probability,
            "draw_probability": self.model_draw_probability,
            "away_probability": self.model_away_probability,
            "actual_result": self.actual_result,
        }

    def market_probability_row(self) -> dict[str, object]:
        """Return the market row compatible with probability evaluation helpers."""
        return {
            "match_id": self.match_id,
            "home_probability": self.market_home_probability,
            "draw_probability": self.market_draw_probability,
            "away_probability": self.market_away_probability,
            "actual_result": self.actual_result,
        }


@dataclass(frozen=True)
class MarketComparisonSummary:
    """Aggregate model-vs-market comparison summary."""

    model_name: str
    market_name: str
    model_summary: ProbabilityEvaluationSummary
    market_summary: ProbabilityEvaluationSummary
    matched_match_count: int
    unmatched_model_match_count: int
    unmatched_market_match_count: int
    average_market_overround: float
    timing_valid_match_count: int
    timing_invalid_match_count: int
    leakage_risk_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready summary."""
        return {
            "model_name": self.model_name,
            "market_name": self.market_name,
            "matched_match_count": self.matched_match_count,
            "unmatched_model_match_count": self.unmatched_model_match_count,
            "unmatched_market_match_count": self.unmatched_market_match_count,
            "average_market_overround": self.average_market_overround,
            "timing_valid_match_count": self.timing_valid_match_count,
            "timing_invalid_match_count": self.timing_invalid_match_count,
            "leakage_risk_counts": self.leakage_risk_counts,
            "model_summary": self.model_summary.to_dict(),
            "market_summary": self.market_summary.to_dict(),
            "model_minus_market_brier": (
                self.model_summary.mean_brier_score - self.market_summary.mean_brier_score
            ),
            "model_minus_market_log_loss": (
                self.model_summary.mean_log_loss - self.market_summary.mean_log_loss
            ),
            "model_beats_market_brier": (
                self.model_summary.mean_brier_score < self.market_summary.mean_brier_score
            ),
            "model_beats_market_log_loss": (
                self.model_summary.mean_log_loss < self.market_summary.mean_log_loss
            ),
        }


def build_market_comparison_rows(
    model_probability_rows: Iterable[Mapping[str, object]],
    market_odds: Iterable[MarketOddsSnapshot],
    *,
    preferred_odds_type: str = "closing",
    kickoff_time_by_match_id: Mapping[str, str] | None = None,
    prediction_time_by_match_id: Mapping[str, str] | None = None,
    timing_mode: str = TIMING_MODE_PRE_MATCH,
    allow_closing: bool = False,
    include_timing_invalid: bool = False,
) -> tuple[list[MarketComparisonRow], int, int]:
    """Match model probability rows to market odds by `match_id`."""
    model_rows = list(model_probability_rows)
    odds_by_match_id = select_one_odds_per_match(
        market_odds,
        preferred_odds_type=preferred_odds_type,
    )
    model_ids = {str(row["match_id"]) for row in model_rows}
    comparison_rows: list[MarketComparisonRow] = []

    for row in model_rows:
        match_id = str(row["match_id"])
        odds = odds_by_match_id.get(match_id)
        if odds is None:
            continue
        timing_valid = True
        leakage_risk = LEAKAGE_RISK_LOW
        timing_reasons: tuple[str, ...] = ()
        if kickoff_time_by_match_id is not None or prediction_time_by_match_id is not None:
            timing = validate_odds_as_of_prediction(
                odds_captured_at=odds.captured_at,
                kickoff_time=(
                    kickoff_time_by_match_id.get(match_id)
                    if kickoff_time_by_match_id is not None
                    else None
                ),
                prediction_time=(
                    prediction_time_by_match_id.get(match_id)
                    if prediction_time_by_match_id is not None
                    else None
                ),
                odds_type=odds.odds_type,
                mode=timing_mode,
                allow_closing=allow_closing,
            )
            timing_valid = timing.valid
            leakage_risk = timing.leakage_risk
            timing_reasons = timing.reasons
            if not timing.valid and not include_timing_invalid:
                continue
        devig = proportional_devig(odds.to_odds_map())
        market_probabilities = devig.fair_probabilities
        comparison_rows.append(
            MarketComparisonRow(
                match_id=match_id,
                actual_result=str(row["actual_result"]),
                bookmaker=odds.bookmaker,
                odds_type=odds.odds_type,
                market_overround=devig.overround,
                model_home_probability=float(row["home_probability"]),
                model_draw_probability=float(row["draw_probability"]),
                model_away_probability=float(row["away_probability"]),
                market_home_probability=market_probabilities[OUTCOME_HOME],
                market_draw_probability=market_probabilities[OUTCOME_DRAW],
                market_away_probability=market_probabilities[OUTCOME_AWAY],
                timing_valid=timing_valid,
                leakage_risk=leakage_risk,
                timing_reasons=timing_reasons,
            )
        )

    matched_ids = {row.match_id for row in comparison_rows}
    unmatched_model_count = len(model_ids.difference(matched_ids))
    unmatched_market_count = len(set(odds_by_match_id).difference(matched_ids))
    return comparison_rows, unmatched_model_count, unmatched_market_count


def evaluate_market_comparison(
    comparison_rows: Iterable[MarketComparisonRow],
    *,
    model_name: str,
    market_name: str,
    unmatched_model_match_count: int = 0,
    unmatched_market_match_count: int = 0,
) -> MarketComparisonSummary:
    """Evaluate matched model-vs-market probability rows."""
    rows = list(comparison_rows)
    if not rows:
        raise ValueError("cannot evaluate market comparison without matched rows")

    model_summary = evaluate_1x2_probability_rows(
        (row.model_probability_row() for row in rows),
        model_name=model_name,
    )
    market_summary = evaluate_1x2_probability_rows(
        (row.market_probability_row() for row in rows),
        model_name=market_name,
    )
    return MarketComparisonSummary(
        model_name=model_name,
        market_name=market_name,
        model_summary=model_summary,
        market_summary=market_summary,
        matched_match_count=len(rows),
        unmatched_model_match_count=unmatched_model_match_count,
        unmatched_market_match_count=unmatched_market_match_count,
        average_market_overround=sum(row.market_overround for row in rows) / len(rows),
        timing_valid_match_count=sum(1 for row in rows if row.timing_valid),
        timing_invalid_match_count=sum(1 for row in rows if not row.timing_valid),
        leakage_risk_counts=_leakage_risk_counts(rows),
    )


def write_market_comparison_report_json(
    summary: MarketComparisonSummary,
    destination_path: str | Path,
    *,
    notes: Iterable[str] | None = None,
) -> Path:
    """Write a model-vs-market comparison report to JSON."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary.to_dict(),
        "notes": list(notes or []),
    }
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _leakage_risk_counts(rows: Iterable[MarketComparisonRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.leakage_risk] = counts.get(row.leakage_risk, 0) + 1
    return counts
