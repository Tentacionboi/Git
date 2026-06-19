#!/usr/bin/env python3
"""Fetch one The Odds API historical World Cup odds snapshot.

Usage:

    THE_ODDS_API_KEY=... PYTHONPATH=src python scripts/fetch_the_odds_api_snapshot.py \
        --date 2022-11-20T12:00:00Z \
        --raw-output data/raw/odds/the_odds_api/2022-11-20T120000Z.json \
        --canonical-output data/processed/odds/the_odds_api/2022-11-20T120000Z.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from worldcup_betting_edp.data import (
    THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    parse_the_odds_api_historical_odds_response,
    write_market_odds_csv,
)
from worldcup_betting_edp.data.the_odds_api_client import (
    THE_ODDS_API_KEY_ENV_VAR,
    fetch_the_odds_api_historical_odds_payload,
    get_the_odds_api_key_from_env,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch one time-stamped historical World Cup 1X2 odds snapshot.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Historical snapshot timestamp, for example 2022-11-20T12:00:00Z.",
    )
    parser.add_argument(
        "--raw-output",
        required=True,
        help="Path for the raw JSON response. API keys are not written.",
    )
    parser.add_argument(
        "--canonical-output",
        help="Optional path for parsed canonical market-odds CSV.",
    )
    parser.add_argument(
        "--sport-key",
        default=THE_ODDS_API_WORLD_CUP_SPORT_KEY,
        help="The Odds API sport key. Defaults to soccer_fifa_world_cup.",
    )
    parser.add_argument(
        "--regions",
        default="us,uk,eu,au",
        help="Comma-separated bookmaker regions. Defaults to us,uk,eu,au.",
    )
    parser.add_argument(
        "--markets",
        default="h2h",
        help="Requested markets. Keep h2h for World Cup 1X2 MVP.",
    )
    args = parser.parse_args(argv)

    api_key = get_the_odds_api_key_from_env()
    payload = fetch_the_odds_api_historical_odds_payload(
        api_key=api_key,
        date=args.date,
        sport_key=args.sport_key,
        regions=args.regions,
        markets=args.markets,
    )

    raw_output = Path(args.raw_output)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    snapshots = parse_the_odds_api_historical_odds_response(payload)
    if args.canonical_output:
        write_market_odds_csv(snapshots, args.canonical_output)

    print(
        json.dumps(
            {
                "raw_output": str(raw_output),
                "canonical_output": args.canonical_output,
                "snapshot_count": len(snapshots),
                "api_key_env_var": THE_ODDS_API_KEY_ENV_VAR,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
