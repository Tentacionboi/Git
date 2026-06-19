"""Time-sliced market backtests with as-of odds selection."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from worldcup_betting_edp.backtest.probability_evaluation import evaluate_1x2_probability_rows
from worldcup_betting_edp.backtest.temporal_validation import (
    TIMING_MODE_PRE_MATCH,
    parse_timestamp,
    validate_odds_as_of_prediction,
)
from worldcup_betting_edp.data import (
    MarketOddsSnapshot,
    MatchTiming,
    load_market_odds_csv,
    load_match_timing_csv,
)
from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME
from worldcup_betting_edp.market import proportional_devig
from worldcup_betting_edp.models import ResidualEdgeConfig, build_market_residual_prediction


SELECTION_EARLIEST_BEFORE_KICKOFF = "earliest_before_kickoff"
SELECTION_LATEST_BEFORE_PREDICTION = "latest_before_prediction"


@dataclass(frozen=True)
class OddsTimeSlice:
    """Definition of one as-of market backtest slice."""

    name: str
    selection_mode: str = SELECTION_LATEST_BEFORE_PREDICTION
    hours_before_kickoff: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.selection_mode not in {
            SELECTION_EARLIEST_BEFORE_KICKOFF,
            SELECTION_LATEST_BEFORE_PREDICTION,
        }:
            raise ValueError("selection_mode is not supported")
        if (
            self.selection_mode == SELECTION_LATEST_BEFORE_PREDICTION
            and self.hours_before_kickoff is None
        ):
            raise ValueError("latest-before-prediction slices require hours_before_kickoff")
        if self.hours_before_kickoff is not None and self.hours_before_kickoff < 0.0:
            raise ValueError("hours_before_kickoff must be non-negative")


def default_world_cup_time_slices() -> tuple[OddsTimeSlice, ...]:
    """Return the standard MVP pre-match odds time slices."""
    return (
        OddsTimeSlice("open", selection_mode=SELECTION_EARLIEST_BEFORE_KICKOFF),
        OddsTimeSlice("24h_before", hours_before_kickoff=24.0),
        OddsTimeSlice("6h_before", hours_before_kickoff=6.0),
        OddsTimeSlice("1h_before", hours_before_kickoff=1.0),
        OddsTimeSlice("close", hours_before_kickoff=0.0),
    )


def run_market_time_slice_backtest_from_csv(
    *,
    market_odds_path: str | Path,
    model_probabilities_path: str | Path,
    match_timing_path: str | Path,
    slices: Sequence[OddsTimeSlice] | None = None,
    residual_config: ResidualEdgeConfig | None = None,
) -> dict[str, Any]:
    """Load CSV inputs and run a time-sliced market backtest."""
    return run_market_time_slice_backtest(
        market_odds=load_market_odds_csv(market_odds_path),
        model_probability_rows=_load_probability_rows(model_probabilities_path),
        match_timings=load_match_timing_csv(match_timing_path),
        slices=slices,
        residual_config=residual_config,
    )


def run_market_time_slice_backtest(
    *,
    market_odds: Sequence[MarketOddsSnapshot],
    model_probability_rows: Sequence[Mapping[str, object]],
    match_timings: Sequence[MatchTiming],
    slices: Sequence[OddsTimeSlice] | None = None,
    residual_config: ResidualEdgeConfig | None = None,
) -> dict[str, Any]:
    """Evaluate model, market, and market-residual probabilities by odds time slice."""
    residual_config = residual_config or ResidualEdgeConfig()
    slice_definitions = tuple(slices or default_world_cup_time_slices())
    if not slice_definitions:
        raise ValueError("at least one time slice is required")

    model_by_match_id = {str(row["match_id"]): row for row in model_probability_rows}
    timing_by_match_id = {timing.match_id: timing for timing in match_timings}
    odds_by_match_id = _group_odds_by_match(market_odds)
    common_match_ids = sorted(
        set(model_by_match_id).intersection(timing_by_match_id).intersection(odds_by_match_id),
        key=lambda match_id: (
            str(model_by_match_id[match_id].get("match_date", "")),
            match_id,
        ),
    )

    slice_payloads = []
    for time_slice in slice_definitions:
        rows = []
        market_eval_rows = []
        model_eval_rows = []
        residual_eval_rows = []
        timing_valid_count = 0
        selected_odds_count = 0

        for match_id in common_match_ids:
            timing = timing_by_match_id[match_id]
            kickoff = _parse_exact_datetime(timing.kickoff_time, field_name="kickoff_time")
            prediction_time = _prediction_time_for_slice(time_slice, kickoff)
            selected_odds = _select_odds_for_slice(
                odds_by_match_id[match_id],
                time_slice=time_slice,
                kickoff_time=kickoff,
                prediction_time=prediction_time,
            )
            valid_selected_odds = [
                odds
                for odds in selected_odds
                if validate_odds_as_of_prediction(
                    odds_captured_at=odds.captured_at,
                    kickoff_time=timing.kickoff_time,
                    prediction_time=prediction_time.isoformat(),
                    odds_type=odds.odds_type,
                    mode=TIMING_MODE_PRE_MATCH,
                    allow_closing=True,
                ).valid
            ]
            if not valid_selected_odds:
                continue

            selected_odds_count += len(valid_selected_odds)
            timing_valid_count += 1
            market_probabilities, average_overround = _average_market_probabilities(
                valid_selected_odds
            )
            model_probabilities = _probabilities_from_row(model_by_match_id[match_id])
            actual = str(model_by_match_id[match_id]["actual_result"])
            residual = build_market_residual_prediction(
                match_id=match_id,
                market_probabilities=market_probabilities,
                fundamental_probabilities=model_probabilities,
                config=residual_config,
            )

            market_eval_rows.append(_probability_row(match_id, market_probabilities, actual))
            model_eval_rows.append(_probability_row(match_id, model_probabilities, actual))
            residual_eval_rows.append(_probability_row(match_id, residual.probabilities, actual))
            rows.append(
                {
                    "slice_name": time_slice.name,
                    "match_id": match_id,
                    "match_date": model_by_match_id[match_id].get("match_date"),
                    "home_team": model_by_match_id[match_id].get("home_team"),
                    "away_team": model_by_match_id[match_id].get("away_team"),
                    "kickoff_time": timing.kickoff_time,
                    "prediction_time": prediction_time.isoformat(),
                    "actual_result": actual,
                    "bookmaker_count": len(valid_selected_odds),
                    "average_market_overround": average_overround,
                    "market_home_probability": market_probabilities[OUTCOME_HOME],
                    "market_draw_probability": market_probabilities[OUTCOME_DRAW],
                    "market_away_probability": market_probabilities[OUTCOME_AWAY],
                    "model_home_probability": model_probabilities[OUTCOME_HOME],
                    "model_draw_probability": model_probabilities[OUTCOME_DRAW],
                    "model_away_probability": model_probabilities[OUTCOME_AWAY],
                    "residual_home_probability": residual.probabilities[OUTCOME_HOME],
                    "residual_draw_probability": residual.probabilities[OUTCOME_DRAW],
                    "residual_away_probability": residual.probabilities[OUTCOME_AWAY],
                }
            )

        slice_payloads.append(
            _build_slice_payload(
                time_slice=time_slice,
                rows=rows,
                market_eval_rows=market_eval_rows,
                model_eval_rows=model_eval_rows,
                residual_eval_rows=residual_eval_rows,
                model_match_count=len(model_by_match_id),
                timing_match_count=len(timing_by_match_id),
                odds_match_count=len(odds_by_match_id),
                common_match_count=len(common_match_ids),
                selected_odds_count=selected_odds_count,
                timing_valid_match_count=timing_valid_count,
            )
        )

    return {
        "input": {
            "slice_names": [time_slice.name for time_slice in slice_definitions],
            "residual_fundamental_gap_weight": residual_config.fundamental_gap_weight,
            "residual_max_adjustment_per_outcome": residual_config.max_abs_adjustment_per_outcome,
        },
        "coverage": {
            "model_match_count": len(model_by_match_id),
            "timing_match_count": len(timing_by_match_id),
            "odds_match_count": len(odds_by_match_id),
            "common_match_count": len(common_match_ids),
        },
        "slices": slice_payloads,
        "notes": [
            "Each slice selects only odds captured at or before its prediction time.",
            "The open slice uses earliest pre-kickoff odds per bookmaker.",
            "The close slice uses latest pre-kickoff odds per bookmaker and is a market-baseline comparison.",
        ],
    }


def _build_slice_payload(
    *,
    time_slice: OddsTimeSlice,
    rows: Sequence[Mapping[str, object]],
    market_eval_rows: Sequence[Mapping[str, object]],
    model_eval_rows: Sequence[Mapping[str, object]],
    residual_eval_rows: Sequence[Mapping[str, object]],
    model_match_count: int,
    timing_match_count: int,
    odds_match_count: int,
    common_match_count: int,
    selected_odds_count: int,
    timing_valid_match_count: int,
) -> dict[str, Any]:
    summary: dict[str, object] | None = None
    if rows:
        market_summary = evaluate_1x2_probability_rows(
            market_eval_rows,
            model_name=f"{time_slice.name}_market",
        )
        model_summary = evaluate_1x2_probability_rows(
            model_eval_rows,
            model_name=f"{time_slice.name}_model",
        )
        residual_summary = evaluate_1x2_probability_rows(
            residual_eval_rows,
            model_name=f"{time_slice.name}_market_residual",
        )
        summary = {
            "market": market_summary.to_dict(),
            "model": model_summary.to_dict(),
            "market_residual": residual_summary.to_dict(),
            "model_minus_market_brier": (
                model_summary.mean_brier_score - market_summary.mean_brier_score
            ),
            "model_minus_market_log_loss": (
                model_summary.mean_log_loss - market_summary.mean_log_loss
            ),
            "residual_minus_market_brier": (
                residual_summary.mean_brier_score - market_summary.mean_brier_score
            ),
            "residual_minus_market_log_loss": (
                residual_summary.mean_log_loss - market_summary.mean_log_loss
            ),
        }

    return {
        "name": time_slice.name,
        "selection_mode": time_slice.selection_mode,
        "hours_before_kickoff": time_slice.hours_before_kickoff,
        "coverage": {
            "model_match_count": model_match_count,
            "timing_match_count": timing_match_count,
            "odds_match_count": odds_match_count,
            "common_match_count": common_match_count,
            "evaluated_match_count": len(rows),
            "selected_odds_count": selected_odds_count,
            "timing_valid_match_count": timing_valid_match_count,
            "average_bookmakers_per_match": (
                selected_odds_count / len(rows) if rows else 0.0
            ),
        },
        "quality": summary,
        "rows": list(rows),
    }


def _select_odds_for_slice(
    odds_rows: Sequence[MarketOddsSnapshot],
    *,
    time_slice: OddsTimeSlice,
    kickoff_time: datetime,
    prediction_time: datetime,
) -> list[MarketOddsSnapshot]:
    by_bookmaker: dict[str, list[MarketOddsSnapshot]] = {}
    for odds in odds_rows:
        odds_time = _parse_exact_datetime(odds.captured_at, field_name="odds_captured_at")
        if odds_time > kickoff_time:
            continue
        if time_slice.selection_mode == SELECTION_LATEST_BEFORE_PREDICTION:
            if odds_time > prediction_time:
                continue
        by_bookmaker.setdefault(odds.bookmaker, []).append(odds)

    selected = []
    for bookmaker_rows in by_bookmaker.values():
        if time_slice.selection_mode == SELECTION_EARLIEST_BEFORE_KICKOFF:
            selected.append(
                min(
                    bookmaker_rows,
                    key=lambda odds: _parse_exact_datetime(
                        odds.captured_at,
                        field_name="odds_captured_at",
                    ),
                )
            )
        else:
            selected.append(
                max(
                    bookmaker_rows,
                    key=lambda odds: _parse_exact_datetime(
                        odds.captured_at,
                        field_name="odds_captured_at",
                    ),
                )
            )
    return selected


def _prediction_time_for_slice(time_slice: OddsTimeSlice, kickoff_time: datetime) -> datetime:
    if time_slice.selection_mode == SELECTION_EARLIEST_BEFORE_KICKOFF:
        return kickoff_time
    assert time_slice.hours_before_kickoff is not None
    return kickoff_time - timedelta(hours=time_slice.hours_before_kickoff)


def _parse_exact_datetime(value: str, *, field_name: str) -> datetime:
    parsed = parse_timestamp(value, field_name=field_name)
    if parsed.date_only:
        raise ValueError(f"{field_name} must have datetime precision for time-slice backtests")
    return parsed.value


def _load_probability_rows(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                **row,
                "home_probability": float(row["home_probability"]),
                "draw_probability": float(row["draw_probability"]),
                "away_probability": float(row["away_probability"]),
            }
            for row in reader
        ]


def _group_odds_by_match(
    odds_rows: Sequence[MarketOddsSnapshot],
) -> dict[str, list[MarketOddsSnapshot]]:
    grouped: dict[str, list[MarketOddsSnapshot]] = {}
    for row in odds_rows:
        grouped.setdefault(row.match_id, []).append(row)
    return grouped


def _average_market_probabilities(
    odds_rows: Sequence[MarketOddsSnapshot],
) -> tuple[dict[str, float], float]:
    totals = {outcome: 0.0 for outcome in OUTCOMES_1X2}
    overrounds = []
    for row in odds_rows:
        devig = proportional_devig(row.to_odds_map())
        overrounds.append(devig.overround)
        for outcome in OUTCOMES_1X2:
            totals[outcome] += devig.fair_probabilities[outcome]
    count = len(odds_rows)
    return {outcome: totals[outcome] / count for outcome in OUTCOMES_1X2}, sum(overrounds) / count


def _probabilities_from_row(row: Mapping[str, object]) -> dict[str, float]:
    return {
        OUTCOME_HOME: float(row["home_probability"]),
        OUTCOME_DRAW: float(row["draw_probability"]),
        OUTCOME_AWAY: float(row["away_probability"]),
    }


def _probability_row(
    match_id: str,
    probabilities: Mapping[str, float],
    actual: str,
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "home_probability": probabilities[OUTCOME_HOME],
        "draw_probability": probabilities[OUTCOME_DRAW],
        "away_probability": probabilities[OUTCOME_AWAY],
        "actual_result": actual,
    }
