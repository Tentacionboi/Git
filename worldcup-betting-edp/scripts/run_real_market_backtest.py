#!/usr/bin/env python3
"""Run a first real model-vs-market backtest from a paid odds snapshot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from worldcup_betting_edp.backtest.probability_evaluation import evaluate_1x2_probability_rows
from worldcup_betting_edp.data import load_market_odds_csv
from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME
from worldcup_betting_edp.market import proportional_devig
from worldcup_betting_edp.models import ResidualEdgeConfig, build_market_residual_prediction


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate market, Elo, and market-residual probabilities on real odds.",
    )
    parser.add_argument("--canonical-odds", required=True, help="Canonical paid odds CSV.")
    parser.add_argument(
        "--elo-probabilities",
        default="data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv",
        help="World Cup Elo probability CSV.",
    )
    parser.add_argument("--output", required=True, help="Output aggregate JSON report.")
    parser.add_argument("--edge-threshold", type=float, default=0.02)
    parser.add_argument("--ev-threshold", type=float, default=0.01)
    args = parser.parse_args(argv)

    odds_rows = load_market_odds_csv(args.canonical_odds)
    elo_rows = _load_probability_rows(args.elo_probabilities)
    elo_by_match_id = {str(row["match_id"]): row for row in elo_rows}
    odds_by_match_id = _group_odds_by_match(odds_rows)

    common_match_ids = sorted(set(odds_by_match_id).intersection(elo_by_match_id))
    market_rows = []
    elo_eval_rows = []
    residual_rows = []
    value_bets = []
    overrounds = []

    for match_id in common_match_ids:
        actual = str(elo_by_match_id[match_id]["actual_result"])
        market_probabilities, average_overround = _average_market_probabilities(odds_by_match_id[match_id])
        overrounds.append(average_overround)
        elo_probabilities = _probabilities_from_row(elo_by_match_id[match_id])
        residual = build_market_residual_prediction(
            match_id=match_id,
            market_probabilities=market_probabilities,
            fundamental_probabilities=elo_probabilities,
            config=ResidualEdgeConfig(),
        )

        market_rows.append(_probability_row(match_id, market_probabilities, actual))
        elo_eval_rows.append(_probability_row(match_id, elo_probabilities, actual))
        residual_rows.append(_probability_row(match_id, residual.probabilities, actual))
        value_bet = _best_value_bet(
            match_id=match_id,
            actual=actual,
            odds_rows=odds_by_match_id[match_id],
            model_probabilities=residual.probabilities,
            edge_threshold=args.edge_threshold,
            ev_threshold=args.ev_threshold,
        )
        if value_bet is not None:
            value_bets.append(value_bet)

    market_summary = evaluate_1x2_probability_rows(market_rows, model_name="market_average_devig")
    elo_summary = evaluate_1x2_probability_rows(elo_eval_rows, model_name="elo_calibrated")
    residual_summary = evaluate_1x2_probability_rows(
        residual_rows,
        model_name="market_residual_mvp",
    )
    value_summary = _summarize_value_bets(value_bets)
    payload = {
        "input": {
            "canonical_odds": args.canonical_odds,
            "elo_probabilities": args.elo_probabilities,
            "edge_threshold": args.edge_threshold,
            "ev_threshold": args.ev_threshold,
        },
        "coverage": {
            "odds_row_count": len(odds_rows),
            "odds_match_count": len(odds_by_match_id),
            "elo_match_count": len(elo_by_match_id),
            "evaluated_match_count": len(common_match_ids),
            "average_bookmakers_per_match": len(odds_rows) / len(odds_by_match_id),
            "average_market_overround": sum(overrounds) / len(overrounds),
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
        "notes": [
            "Market probabilities are averaged across bookmaker-level proportional-devig probabilities.",
            "Value-bet settlement line-shops across bookmakers available in the snapshot.",
            "This is a first 48-match group-stage snapshot test, not proof of durable market edge.",
            "The underlying paid odds rows are ignored by Git and are not included in this report.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["coverage"] | value_summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


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


def _group_odds_by_match(odds_rows):
    grouped = {}
    for row in odds_rows:
        grouped.setdefault(row.match_id, []).append(row)
    return grouped


def _average_market_probabilities(odds_rows) -> tuple[dict[str, float], float]:
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


def _probability_row(match_id: str, probabilities: Mapping[str, float], actual: str) -> dict[str, object]:
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
    actual: str,
    odds_rows,
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
                        "bookmaker": row.bookmaker,
                        "outcome": outcome,
                        "actual": actual,
                        "odds": odds_map[outcome],
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
    }


if __name__ == "__main__":
    raise SystemExit(main())
