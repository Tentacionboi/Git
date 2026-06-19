#!/usr/bin/env python3
"""Probe API-Football World Cup fixtures and odds coverage.

This script is a source-validation tool, not a production ingestion job.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from worldcup_betting_edp.data import write_market_odds_csv
from worldcup_betting_edp.data.api_football import (
    API_FOOTBALL_WORLD_CUP_LEAGUE_ID,
    parse_api_football_odds_response,
    summarize_api_football_probe_payloads,
)
from worldcup_betting_edp.data.api_football_client import (
    API_FOOTBALL_KEY_ENV_VAR,
    ApiFootballRequestError,
    fetch_api_football_payload,
    get_api_football_key_from_env,
)
from worldcup_betting_edp.data.the_odds_api_client import load_dotenv_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe whether API-Football can support World Cup odds ingestion.",
    )
    parser.add_argument(
        "--league",
        type=int,
        default=API_FOOTBALL_WORLD_CUP_LEAGUE_ID,
        help="API-Football league id. Defaults to 1, commonly used for World Cup.",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2022,
        help="Season to probe. Defaults to 2022.",
    )
    parser.add_argument(
        "--raw-output",
        required=True,
        help="Path for combined raw probe JSON. API keys are not written.",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional summary JSON path. Defaults to RAW_OUTPUT.summary.json.",
    )
    parser.add_argument(
        "--canonical-output",
        help="Optional canonical market-odds CSV output parsed from the odds probe.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional local env file to load before reading API_FOOTBALL_KEY.",
    )
    args = parser.parse_args(argv)

    try:
        load_dotenv_file(args.env_file)
        api_key = get_api_football_key_from_env()
        payloads = _run_probe(api_key=api_key, league=args.league, season=args.season)
    except (OSError, ValueError, ApiFootballRequestError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    raw_output = Path(args.raw_output)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text(
        json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = summarize_api_football_probe_payloads(payloads)
    summary.update(
        {
            "source": "api-football",
            "league": args.league,
            "season": args.season,
            "api_key_env_var": API_FOOTBALL_KEY_ENV_VAR,
            "api_key_stored": False,
            "raw_output": str(raw_output),
        }
    )
    summary_output = Path(args.summary_output) if args.summary_output else raw_output.with_suffix(
        raw_output.suffix + ".summary.json"
    )
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    snapshots = parse_api_football_odds_response(payloads.get("odds", {}))
    if args.canonical_output:
        write_market_odds_csv(snapshots, args.canonical_output)

    print(
        json.dumps(
            {
                "raw_output": str(raw_output),
                "summary_output": str(summary_output),
                "canonical_output": args.canonical_output,
                "canonical_snapshot_count": len(snapshots),
                "api_key_env_var": API_FOOTBALL_KEY_ENV_VAR,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_probe(*, api_key: str, league: int, season: int) -> dict[str, dict[str, Any]]:
    return {
        "status": fetch_api_football_payload(api_key=api_key, endpoint="/status"),
        "leagues_world_cup_search": fetch_api_football_payload(
            api_key=api_key,
            endpoint="/leagues",
            params={"search": "World Cup"},
        ),
        "fixtures": fetch_api_football_payload(
            api_key=api_key,
            endpoint="/fixtures",
            params={"league": league, "season": season},
        ),
        "odds_bets": fetch_api_football_payload(api_key=api_key, endpoint="/odds/bets"),
        "odds_bookmakers": fetch_api_football_payload(
            api_key=api_key,
            endpoint="/odds/bookmakers",
        ),
        "odds": fetch_api_football_payload(
            api_key=api_key,
            endpoint="/odds",
            params={"league": league, "season": season},
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
