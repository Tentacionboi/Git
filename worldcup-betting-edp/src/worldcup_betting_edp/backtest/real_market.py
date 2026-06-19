"""Real market odds backtest helpers for the World Cup research app."""

from __future__ import annotations

import csv
from itertools import product
from pathlib import Path
from typing import Any, Mapping, Sequence

from worldcup_betting_edp.backtest.probability_evaluation import evaluate_1x2_probability_rows
from worldcup_betting_edp.data import MarketOddsSnapshot, load_market_odds_csv
from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME
from worldcup_betting_edp.market import proportional_devig
from worldcup_betting_edp.models import ResidualEdgeConfig, build_market_residual_prediction


def run_real_market_backtest(
    *,
    canonical_odds_path: str | Path,
    elo_probabilities_path: str | Path,
    edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    residual_config: ResidualEdgeConfig | None = None,
) -> dict[str, Any]:
    """Evaluate market, Elo, and residual probabilities against real odds rows.

    The odds file is interpreted as one historical snapshot. The function does
    not combine later odds into earlier predictions, which keeps the first
    dashboard view aligned with temporal validation discipline.
    """
    if edge_threshold < 0.0:
        raise ValueError("edge_threshold must be non-negative")
    if ev_threshold < 0.0:
        raise ValueError("ev_threshold must be non-negative")

    residual_config = residual_config or ResidualEdgeConfig()
    odds_rows = load_market_odds_csv(canonical_odds_path)
    elo_rows = _load_probability_rows(elo_probabilities_path)
    elo_by_match_id = {str(row["match_id"]): row for row in elo_rows}
    odds_by_match_id = _group_odds_by_match(odds_rows)
    common_match_ids = sorted(
        set(odds_by_match_id).intersection(elo_by_match_id),
        key=lambda match_id: (
            str(elo_by_match_id[match_id].get("match_date", "")),
            match_id,
        ),
    )

    market_rows = []
    elo_eval_rows = []
    residual_rows = []
    match_rows = []
    value_bets = []
    overrounds = []

    for match_id in common_match_ids:
        elo_row = elo_by_match_id[match_id]
        actual = str(elo_row["actual_result"])
        market_probabilities, average_overround = _average_market_probabilities(
            odds_by_match_id[match_id]
        )
        overrounds.append(average_overround)
        elo_probabilities = _probabilities_from_row(elo_row)
        residual = build_market_residual_prediction(
            match_id=match_id,
            market_probabilities=market_probabilities,
            fundamental_probabilities=elo_probabilities,
            config=residual_config,
        )

        market_rows.append(_probability_row(match_id, market_probabilities, actual))
        elo_eval_rows.append(_probability_row(match_id, elo_probabilities, actual))
        residual_rows.append(_probability_row(match_id, residual.probabilities, actual))
        match_rows.append(
            {
                "match_id": match_id,
                "match_date": elo_row.get("match_date"),
                "home_team": elo_row.get("home_team"),
                "away_team": elo_row.get("away_team"),
                "actual_result": actual,
                "bookmaker_count": len(odds_by_match_id[match_id]),
                "average_market_overround": average_overround,
                "market_home_probability": market_probabilities[OUTCOME_HOME],
                "market_draw_probability": market_probabilities[OUTCOME_DRAW],
                "market_away_probability": market_probabilities[OUTCOME_AWAY],
                "elo_home_probability": elo_probabilities[OUTCOME_HOME],
                "elo_draw_probability": elo_probabilities[OUTCOME_DRAW],
                "elo_away_probability": elo_probabilities[OUTCOME_AWAY],
                "residual_home_probability": residual.probabilities[OUTCOME_HOME],
                "residual_draw_probability": residual.probabilities[OUTCOME_DRAW],
                "residual_away_probability": residual.probabilities[OUTCOME_AWAY],
                "largest_residual_adjustment_outcome": residual.largest_adjustment_outcome,
                "largest_residual_adjustment": residual.largest_adjustment,
            }
        )
        value_bet = _best_value_bet(
            match_id=match_id,
            match_date=str(elo_row.get("match_date", "")),
            home_team=str(elo_row.get("home_team", "")),
            away_team=str(elo_row.get("away_team", "")),
            actual=actual,
            odds_rows=odds_by_match_id[match_id],
            model_probabilities=residual.probabilities,
            edge_threshold=edge_threshold,
            ev_threshold=ev_threshold,
        )
        if value_bet is not None:
            value_bets.append(value_bet)

    market_summary = evaluate_1x2_probability_rows(market_rows, model_name="market_average_devig")
    elo_summary = evaluate_1x2_probability_rows(elo_eval_rows, model_name="elo_calibrated")
    residual_summary = evaluate_1x2_probability_rows(
        residual_rows,
        model_name=residual_config.model_name,
    )
    value_summary = _summarize_value_bets(value_bets)
    bankroll_curve = _build_flat_bankroll_curve(value_bets)
    average_bookmakers = len(odds_rows) / len(odds_by_match_id) if odds_by_match_id else 0.0
    average_overround = sum(overrounds) / len(overrounds) if overrounds else 0.0

    return {
        "input": {
            "canonical_odds": str(canonical_odds_path),
            "elo_probabilities": str(elo_probabilities_path),
            "edge_threshold": edge_threshold,
            "ev_threshold": ev_threshold,
            "residual_fundamental_gap_weight": residual_config.fundamental_gap_weight,
            "residual_max_adjustment_per_outcome": residual_config.max_abs_adjustment_per_outcome,
            "residual_min_probability": residual_config.min_probability,
        },
        "coverage": {
            "odds_row_count": len(odds_rows),
            "odds_match_count": len(odds_by_match_id),
            "elo_match_count": len(elo_by_match_id),
            "evaluated_match_count": len(common_match_ids),
            "average_bookmakers_per_match": average_bookmakers,
            "average_market_overround": average_overround,
        },
        "probability_quality": {
            "market_average": market_summary.to_dict(),
            "elo_calibrated": elo_summary.to_dict(),
            "market_residual": residual_summary.to_dict(),
            "elo_minus_market_brier": (
                elo_summary.mean_brier_score - market_summary.mean_brier_score
            ),
            "elo_minus_market_log_loss": (
                elo_summary.mean_log_loss - market_summary.mean_log_loss
            ),
            "residual_minus_market_brier": (
                residual_summary.mean_brier_score - market_summary.mean_brier_score
            ),
            "residual_minus_market_log_loss": (
                residual_summary.mean_log_loss - market_summary.mean_log_loss
            ),
        },
        "value_bet_summary": value_summary,
        "match_rows": match_rows,
        "value_bets": value_bets,
        "bankroll_curve": bankroll_curve,
        "notes": [
            "Market probabilities are averaged across bookmaker-level proportional-devig probabilities.",
            "Value-bet settlement line-shops across bookmakers available in the snapshot.",
            "This is one historical snapshot test, not proof of durable market edge.",
            "The function does not use odds captured after the snapshot timestamp for earlier predictions.",
        ],
    }


def run_real_market_parameter_sweep(
    *,
    canonical_odds_path: str | Path,
    elo_probabilities_path: str | Path,
    edge_thresholds: Sequence[float],
    ev_thresholds: Sequence[float],
    residual_gap_weights: Sequence[float],
    residual_max_adjustments: Sequence[float],
    max_parameter_runs: int = 200,
) -> dict[str, Any]:
    """Run a bounded grid search over real-market backtest parameters."""
    edge_values = _validated_sweep_values(edge_thresholds, name="edge_thresholds")
    ev_values = _validated_sweep_values(ev_thresholds, name="ev_thresholds")
    gap_values = _validated_sweep_values(residual_gap_weights, name="residual_gap_weights")
    adjustment_values = _validated_sweep_values(
        residual_max_adjustments,
        name="residual_max_adjustments",
    )
    parameter_count = len(edge_values) * len(ev_values) * len(gap_values) * len(adjustment_values)
    if parameter_count > max_parameter_runs:
        raise ValueError(
            f"parameter grid has {parameter_count} runs, above max_parameter_runs={max_parameter_runs}"
        )

    rows = []
    for edge_threshold, ev_threshold, gap_weight, max_adjustment in product(
        edge_values,
        ev_values,
        gap_values,
        adjustment_values,
    ):
        payload = run_real_market_backtest(
            canonical_odds_path=canonical_odds_path,
            elo_probabilities_path=elo_probabilities_path,
            edge_threshold=edge_threshold,
            ev_threshold=ev_threshold,
            residual_config=ResidualEdgeConfig(
                fundamental_gap_weight=gap_weight,
                max_abs_adjustment_per_outcome=max_adjustment,
            ),
        )
        quality = payload["probability_quality"]
        residual = quality["market_residual"]
        value_summary = payload["value_bet_summary"]
        rows.append(
            {
                "edge_threshold": edge_threshold,
                "ev_threshold": ev_threshold,
                "residual_gap_weight": gap_weight,
                "residual_max_adjustment": max_adjustment,
                "accuracy": residual["accuracy"],
                "brier_score": residual["mean_brier_score"],
                "log_loss": residual["mean_log_loss"],
                "residual_minus_market_brier": quality["residual_minus_market_brier"],
                "residual_minus_market_log_loss": quality["residual_minus_market_log_loss"],
                "bet_count": value_summary["bet_count"],
                "hit_rate": value_summary["hit_rate"],
                "flat_roi": value_summary["flat_roi"],
                "flat_profit": value_summary["flat_profit"],
                "average_ev": value_summary["average_ev"],
                "average_odds": value_summary["average_odds"],
                "max_drawdown": value_summary["max_drawdown"],
            }
        )

    return {
        "input": {
            "canonical_odds": str(canonical_odds_path),
            "elo_probabilities": str(elo_probabilities_path),
            "edge_thresholds": list(edge_values),
            "ev_thresholds": list(ev_values),
            "residual_gap_weights": list(gap_values),
            "residual_max_adjustments": list(adjustment_values),
            "max_parameter_runs": max_parameter_runs,
        },
        "run_count": parameter_count,
        "rows": sorted(
            rows,
            key=lambda row: (
                -float(row["flat_roi"]),
                float(row["brier_score"]),
                -int(row["bet_count"]),
            ),
        ),
        "notes": [
            "Sweep results are descriptive. They are not an out-of-sample parameter selection proof.",
            "Ranking by ROI alone can overfit this single historical odds snapshot.",
            "Prefer parameter regions that also preserve probability quality and enough bet count.",
        ],
    }


def strip_detail_rows(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return an aggregate-only report payload safe for committed reports."""
    aggregate = dict(payload)
    aggregate.pop("value_bets", None)
    aggregate.pop("match_rows", None)
    aggregate["bankroll_curve"] = {
        "point_count": len(payload.get("bankroll_curve", [])),
        "final_bankroll": (
            payload["bankroll_curve"][-1]["bankroll"]
            if payload.get("bankroll_curve")
            else 100.0
        ),
    }
    return aggregate


def _validated_sweep_values(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    unique_values = tuple(sorted({round(float(value), 10) for value in values}))
    if not unique_values:
        raise ValueError(f"{name} cannot be empty")
    for value in unique_values:
        if value < 0.0:
            raise ValueError(f"{name} cannot include negative values")
    return unique_values


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


def _best_value_bet(
    *,
    match_id: str,
    match_date: str,
    home_team: str,
    away_team: str,
    actual: str,
    odds_rows: Sequence[MarketOddsSnapshot],
    model_probabilities: Mapping[str, float],
    edge_threshold: float,
    ev_threshold: float,
) -> dict[str, object] | None:
    candidates = []
    for row in odds_rows:
        market_probabilities = proportional_devig(row.to_odds_map()).fair_probabilities
        odds_map = row.to_odds_map()
        for outcome in OUTCOMES_1X2:
            probability = model_probabilities[outcome]
            edge = probability - market_probabilities[outcome]
            ev = probability * odds_map[outcome] - 1.0
            if edge >= edge_threshold and ev >= ev_threshold:
                candidates.append(
                    {
                        "match_id": match_id,
                        "match_date": match_date,
                        "home_team": home_team,
                        "away_team": away_team,
                        "bookmaker": row.bookmaker,
                        "outcome": outcome,
                        "actual": actual,
                        "odds": odds_map[outcome],
                        "market_probability": market_probabilities[outcome],
                        "model_probability": probability,
                        "edge": edge,
                        "ev": ev,
                        "hit": outcome == actual,
                    }
                )
    if not candidates:
        return None
    best = max(candidates, key=lambda item: item["ev"])
    best["profit_flat_1"] = best["odds"] - 1.0 if best["hit"] else -1.0
    return best


def _summarize_value_bets(value_bets: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not value_bets:
        return {
            "bet_count": 0,
            "hit_count": 0,
            "hit_rate": None,
            "flat_profit": 0.0,
            "flat_roi": 0.0,
            "average_ev": None,
            "average_odds": None,
            "max_drawdown": 0.0,
        }
    bet_count = len(value_bets)
    hit_count = sum(1 for bet in value_bets if bet["hit"])
    flat_profit = sum(float(bet["profit_flat_1"]) for bet in value_bets)
    return {
        "bet_count": bet_count,
        "hit_count": hit_count,
        "hit_rate": hit_count / bet_count,
        "flat_profit": flat_profit,
        "flat_roi": flat_profit / bet_count,
        "average_ev": sum(float(bet["ev"]) for bet in value_bets) / bet_count,
        "average_odds": sum(float(bet["odds"]) for bet in value_bets) / bet_count,
        "max_drawdown": _max_drawdown(_build_flat_bankroll_curve(value_bets)),
    }


def _build_flat_bankroll_curve(
    value_bets: Sequence[Mapping[str, object]],
    *,
    starting_bankroll: float = 100.0,
) -> list[dict[str, object]]:
    bankroll = starting_bankroll
    high_water = starting_bankroll
    points = []
    ordered_bets = sorted(
        value_bets,
        key=lambda bet: (str(bet.get("match_date", "")), str(bet.get("match_id", ""))),
    )
    for index, bet in enumerate(ordered_bets, start=1):
        profit = float(bet["profit_flat_1"])
        bankroll += profit
        high_water = max(high_water, bankroll)
        drawdown = 0.0 if high_water <= 0.0 else (high_water - bankroll) / high_water
        points.append(
            {
                "step": index,
                "match_id": bet["match_id"],
                "match_date": bet.get("match_date"),
                "home_team": bet.get("home_team"),
                "away_team": bet.get("away_team"),
                "outcome": bet["outcome"],
                "actual": bet["actual"],
                "odds": bet["odds"],
                "profit": profit,
                "bankroll": bankroll,
                "drawdown": drawdown,
            }
        )
    return points


def _max_drawdown(curve: Sequence[Mapping[str, object]]) -> float:
    if not curve:
        return 0.0
    return max(float(point["drawdown"]) for point in curve)
