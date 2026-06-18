import unittest

from worldcup_betting_edp.backtest import (
    build_market_comparison_rows,
    evaluate_market_comparison,
    write_market_comparison_report_json,
)
from worldcup_betting_edp.data import MarketOddsSnapshot
from pathlib import Path
import tempfile


class MarketComparisonTests(unittest.TestCase):
    def test_builds_market_comparison_rows(self) -> None:
        model_rows = [
            {
                "match_id": "m1",
                "home_probability": 0.50,
                "draw_probability": 0.25,
                "away_probability": 0.25,
                "actual_result": "home",
            },
            {
                "match_id": "m2",
                "home_probability": 0.30,
                "draw_probability": 0.30,
                "away_probability": 0.40,
                "actual_result": "away",
            },
        ]
        odds = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18",
                home_odds=2.00,
                draw_odds=3.20,
                away_odds=4.20,
                source="unit-test",
            )
        ]

        rows, unmatched_model_count, unmatched_market_count = build_market_comparison_rows(
            model_rows,
            odds,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(unmatched_model_count, 1)
        self.assertEqual(unmatched_market_count, 0)
        self.assertAlmostEqual(
            rows[0].market_home_probability
            + rows[0].market_draw_probability
            + rows[0].market_away_probability,
            1.0,
        )

    def test_evaluates_market_comparison(self) -> None:
        model_rows = [
            {
                "match_id": "m1",
                "home_probability": 0.50,
                "draw_probability": 0.25,
                "away_probability": 0.25,
                "actual_result": "home",
            }
        ]
        odds = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18",
                home_odds=2.00,
                draw_odds=3.20,
                away_odds=4.20,
                source="unit-test",
            )
        ]
        comparison_rows, unmatched_model_count, unmatched_market_count = build_market_comparison_rows(
            model_rows,
            odds,
        )

        summary = evaluate_market_comparison(
            comparison_rows,
            model_name="demo_model",
            market_name="demo_market",
            unmatched_model_match_count=unmatched_model_count,
            unmatched_market_match_count=unmatched_market_count,
        )

        self.assertEqual(summary.matched_match_count, 1)
        self.assertEqual(summary.unmatched_model_match_count, 0)
        self.assertEqual(summary.market_summary.model_name, "demo_market")
        self.assertIn("model_minus_market_log_loss", summary.to_dict())

    def test_rejects_market_comparison_without_matches(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_market_comparison(
                [],
                model_name="demo_model",
                market_name="demo_market",
            )

    def test_writes_market_comparison_report_json(self) -> None:
        model_rows = [
            {
                "match_id": "m1",
                "home_probability": 0.50,
                "draw_probability": 0.25,
                "away_probability": 0.25,
                "actual_result": "home",
            }
        ]
        odds = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18",
                home_odds=2.00,
                draw_odds=3.20,
                away_odds=4.20,
                source="unit-test",
            )
        ]
        comparison_rows, unmatched_model_count, unmatched_market_count = build_market_comparison_rows(
            model_rows,
            odds,
        )
        summary = evaluate_market_comparison(
            comparison_rows,
            model_name="demo_model",
            market_name="demo_market",
            unmatched_model_match_count=unmatched_model_count,
            unmatched_market_match_count=unmatched_market_count,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "market_comparison.json"
            written = write_market_comparison_report_json(summary, path)

            self.assertEqual(written, path)
            self.assertIn('"model_name": "demo_model"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
