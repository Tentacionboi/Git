#!/usr/bin/env python3
"""Run a real model-vs-market backtest from a historical odds snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from worldcup_betting_edp.backtest import run_real_market_backtest, strip_detail_rows
from worldcup_betting_edp.models import ResidualEdgeConfig


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
    parser.add_argument("--residual-gap-weight", type=float, default=0.25)
    parser.add_argument("--residual-max-adjustment", type=float, default=0.05)
    args = parser.parse_args(argv)

    payload = run_real_market_backtest(
        canonical_odds_path=args.canonical_odds,
        elo_probabilities_path=args.elo_probabilities,
        edge_threshold=args.edge_threshold,
        ev_threshold=args.ev_threshold,
        residual_config=ResidualEdgeConfig(
            fundamental_gap_weight=args.residual_gap_weight,
            max_abs_adjustment_per_outcome=args.residual_max_adjustment,
        ),
    )
    aggregate_payload = strip_detail_rows(payload)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(aggregate_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            payload["coverage"] | payload["value_bet_summary"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
