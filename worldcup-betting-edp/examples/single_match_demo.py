#!/usr/bin/env python3
"""Run a tiny single-match MVP demo."""

from __future__ import annotations

from datetime import datetime, timezone
from pprint import pprint

from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot
from worldcup_betting_edp.reports import evaluate_single_match


def main() -> None:
    match = Match(
        match_id="demo-2026-final",
        match_time=datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        stage="Final",
        neutral=True,
    )

    odds = OddsSnapshot(
        match_id=match.match_id,
        captured_at=datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc),
        bookmaker="demo_book",
        home=2.20,
        draw=3.25,
        away=3.60,
    )

    model = ModelProbabilities.from_1x2(
        match_id=match.match_id,
        model_name="demo_subjective_model",
        home=0.49,
        draw=0.27,
        away=0.24,
    )

    report = evaluate_single_match(
        match=match,
        odds_snapshot=odds,
        model_probabilities=model,
    )

    pprint(report.to_dict(), sort_dicts=False)


if __name__ == "__main__":
    main()

