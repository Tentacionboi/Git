import csv
import tempfile
import unittest
from pathlib import Path

from worldcup_betting_edp.backtest import run_real_market_backtest, strip_detail_rows
from worldcup_betting_edp.data import MarketOddsSnapshot, write_market_odds_csv
from worldcup_betting_edp.models import ResidualEdgeConfig


class RealMarketBacktestTests(unittest.TestCase):
    def test_run_real_market_backtest_returns_scoring_bets_and_curve(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            odds_path = tmp_path / "odds.csv"
            elo_path = tmp_path / "elo.csv"
            write_market_odds_csv(
                [
                    MarketOddsSnapshot(
                        match_id="m1",
                        bookmaker="book_a",
                        captured_at="2022-11-20T12:00:00Z",
                        home_odds=2.20,
                        draw_odds=3.50,
                        away_odds=4.00,
                        odds_type="historical_snapshot",
                        source="unit-test",
                    ),
                    MarketOddsSnapshot(
                        match_id="m2",
                        bookmaker="book_a",
                        captured_at="2022-11-20T12:00:00Z",
                        home_odds=1.80,
                        draw_odds=3.30,
                        away_odds=5.00,
                        odds_type="historical_snapshot",
                        source="unit-test",
                    ),
                ],
                odds_path,
            )
            with elo_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "match_id",
                        "match_date",
                        "home_team",
                        "away_team",
                        "home_probability",
                        "draw_probability",
                        "away_probability",
                        "actual_result",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "match_id": "m1",
                        "match_date": "2022-11-21",
                        "home_team": "A",
                        "away_team": "B",
                        "home_probability": 0.58,
                        "draw_probability": 0.24,
                        "away_probability": 0.18,
                        "actual_result": "home",
                    }
                )
                writer.writerow(
                    {
                        "match_id": "m2",
                        "match_date": "2022-11-22",
                        "home_team": "C",
                        "away_team": "D",
                        "home_probability": 0.50,
                        "draw_probability": 0.29,
                        "away_probability": 0.21,
                        "actual_result": "draw",
                    }
                )

            payload = run_real_market_backtest(
                canonical_odds_path=odds_path,
                elo_probabilities_path=elo_path,
                edge_threshold=0.0,
                ev_threshold=0.0,
                residual_config=ResidualEdgeConfig(
                    fundamental_gap_weight=0.50,
                    max_abs_adjustment_per_outcome=0.10,
                ),
            )

        self.assertEqual(payload["coverage"]["evaluated_match_count"], 2)
        self.assertIn("market_residual", payload["probability_quality"])
        self.assertGreaterEqual(payload["value_bet_summary"]["bet_count"], 1)
        self.assertEqual(
            len(payload["bankroll_curve"]),
            payload["value_bet_summary"]["bet_count"],
        )
        self.assertEqual(len(payload["match_rows"]), 2)

    def test_strip_detail_rows_removes_paid_market_details(self):
        payload = {
            "coverage": {},
            "value_bets": [{"bookmaker": "book_a"}],
            "match_rows": [{"match_id": "m1"}],
            "bankroll_curve": [{"bankroll": 101.0}],
        }
        aggregate = strip_detail_rows(payload)

        self.assertNotIn("value_bets", aggregate)
        self.assertNotIn("match_rows", aggregate)
        self.assertEqual(aggregate["bankroll_curve"]["final_bankroll"], 101.0)


if __name__ == "__main__":
    unittest.main()
