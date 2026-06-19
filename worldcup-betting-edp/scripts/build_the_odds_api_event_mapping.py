#!/usr/bin/env python3
"""Build The Odds API event-id to canonical match-id mappings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from worldcup_betting_edp.data import load_canonical_matches_csv
from worldcup_betting_edp.data.the_odds_api import (
    build_the_odds_api_event_mapping,
    parse_the_odds_api_historical_odds_response,
    remap_the_odds_api_snapshots_to_canonical,
    write_the_odds_api_event_mapping_csv,
)
from worldcup_betting_edp.data.market_odds import write_market_odds_csv


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Map The Odds API event ids to canonical World Cup match ids.",
    )
    parser.add_argument("--raw-odds-json", required=True, help="The Odds API raw snapshot JSON.")
    parser.add_argument(
        "--canonical-matches",
        default="data/processed/matches/world_cup_matches.csv",
        help="Canonical World Cup match CSV.",
    )
    parser.add_argument("--output", required=True, help="Output mapping CSV.")
    parser.add_argument(
        "--canonical-odds-output",
        help="Optional output CSV for source odds remapped to canonical match ids and orientation.",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional summary JSON path. Defaults to OUTPUT.summary.json.",
    )
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.raw_odds_json).read_text(encoding="utf-8"))
    canonical_matches = load_canonical_matches_csv(args.canonical_matches)
    mappings = build_the_odds_api_event_mapping(payload, canonical_matches=canonical_matches)
    write_the_odds_api_event_mapping_csv(mappings, args.output)
    canonical_odds_count = None
    if args.canonical_odds_output:
        source_snapshots = parse_the_odds_api_historical_odds_response(payload)
        canonical_snapshots = remap_the_odds_api_snapshots_to_canonical(source_snapshots, mappings)
        write_market_odds_csv(canonical_snapshots, args.canonical_odds_output)
        canonical_odds_count = len(canonical_snapshots)

    event_count = len(payload.get("data", [])) if isinstance(payload, dict) else None
    summary = {
        "raw_odds_json": args.raw_odds_json,
        "canonical_matches": args.canonical_matches,
        "output": args.output,
        "source_event_count": event_count,
        "mapped_event_count": len(mappings),
        "unmapped_event_count": event_count - len(mappings) if event_count is not None else None,
        "canonical_odds_output": args.canonical_odds_output,
        "canonical_odds_count": canonical_odds_count,
    }
    summary_output = Path(args.summary_output) if args.summary_output else Path(args.output).with_suffix(
        Path(args.output).suffix + ".summary.json"
    )
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary | {"summary_output": str(summary_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
