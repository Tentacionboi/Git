"""Command-line interface for reproducible predictions and batch backtests."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Sequence, TextIO

from worldcup_betting_edp.backtest import run_batch_backtest_path
from worldcup_betting_edp.data import load_prediction_input_path
from worldcup_betting_edp.reports import evaluate_single_match


def run_prediction(
    *,
    input_path: str | Path,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
) -> dict[str, Any]:
    """Run the single-match prediction pipeline and return a flat report."""
    prediction_input = load_prediction_input_path(input_path)
    report = evaluate_single_match(
        match=prediction_input.match,
        odds_snapshot=prediction_input.odds_snapshot,
        model_probabilities=prediction_input.model_probabilities,
        probability_edge_threshold=probability_edge_threshold,
        ev_threshold=ev_threshold,
        kelly_fraction=kelly_fraction,
        stake_cap=stake_cap,
    )
    return report.to_dict()


def run_backtest(
    *,
    manifest_path: str | Path,
    flat_stake: float = 1.0,
    starting_bankroll: float = 100.0,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
) -> dict[str, Any]:
    """Run a manifest-driven batch backtest and return a serializable payload."""
    return run_batch_backtest_path(
        manifest_path,
        flat_stake=flat_stake,
        starting_bankroll=starting_bankroll,
        probability_edge_threshold=probability_edge_threshold,
        ev_threshold=ev_threshold,
        kelly_fraction=kelly_fraction,
        stake_cap=stake_cap,
    ).to_dict()


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return a process exit code."""
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.input:
            row = run_prediction(
                input_path=args.input,
                probability_edge_threshold=args.probability_edge_threshold,
                ev_threshold=args.ev_threshold,
                kelly_fraction=args.kelly_fraction,
                stake_cap=args.stake_cap,
            )
        else:
            if args.format != "json":
                raise ValueError("--format csv is only supported with --input")
            row = run_backtest(
                manifest_path=args.manifest,
                flat_stake=args.flat_stake,
                starting_bankroll=args.starting_bankroll,
                probability_edge_threshold=args.probability_edge_threshold,
                ev_threshold=args.ev_threshold,
                kelly_fraction=args.kelly_fraction,
                stake_cap=args.stake_cap,
            )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=error_output)
        return 1

    try:
        rendered = _render_payload(row, args.format)
        if args.output:
            _write_output_file(args.output, rendered)
        else:
            print(rendered, file=output, end="" if rendered.endswith("\n") else "\n")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=error_output)
        return 1

    return 0


def _render_payload(row: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    output = _StringWriter()
    writer = csv.DictWriter(output, fieldnames=list(row.keys()))
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def _write_output_file(path: str | Path, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


class _StringWriter:
    """Tiny file-like buffer for csv without importing io in the hot path."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    def write(self, text: str) -> int:
        self._parts.append(text)
        return len(text)

    def getvalue(self) -> str:
        return "".join(self._parts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="worldcup-edp-predict",
        description="Run reproducible World Cup 1X2 predictions and batch backtests.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to a one-match prediction JSON file.")
    source.add_argument("--manifest", help="Path to a batch backtest manifest JSON file.")
    parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format. Defaults to json.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path. Parent directories are created automatically.",
    )
    parser.add_argument(
        "--probability-edge-threshold",
        type=float,
        default=0.02,
        help="Minimum model-minus-market probability edge required for a value bet.",
    )
    parser.add_argument(
        "--ev-threshold",
        type=float,
        default=0.01,
        help="Minimum expected value required for a value bet.",
    )
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=0.25,
        help="Fractional Kelly multiplier.",
    )
    parser.add_argument(
        "--stake-cap",
        type=float,
        default=0.02,
        help="Maximum bankroll fraction allowed for one recommended bet.",
    )
    parser.add_argument(
        "--flat-stake",
        type=float,
        default=1.0,
        help="Fixed stake used for flat-stake settlement in batch backtests.",
    )
    parser.add_argument(
        "--starting-bankroll",
        type=float,
        default=100.0,
        help="Starting bankroll used for Kelly bankroll curves in batch backtests.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
