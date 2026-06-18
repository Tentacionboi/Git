from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.backtest import (
    evaluate_1x2_probability_rows,
    load_1x2_probability_rows_csv,
    write_probability_evaluation_json,
)


class ProbabilityEvaluationTests(unittest.TestCase):
    def test_evaluates_probability_rows(self) -> None:
        rows = [
            {
                "match_id": "m1",
                "home_probability": 0.60,
                "draw_probability": 0.25,
                "away_probability": 0.15,
                "actual_result": "home",
            },
            {
                "match_id": "m2",
                "home_probability": 0.30,
                "draw_probability": 0.30,
                "away_probability": 0.40,
                "actual_result": "draw",
            },
        ]

        summary = evaluate_1x2_probability_rows(rows, model_name="demo")

        self.assertEqual(summary.model_name, "demo")
        self.assertEqual(summary.match_count, 2)
        self.assertAlmostEqual(summary.accuracy, 0.5)
        self.assertGreater(summary.mean_brier_score, 0.0)
        self.assertGreater(summary.mean_log_loss, 0.0)
        self.assertEqual(summary.outcome_counts["home"], 1)
        self.assertEqual(summary.outcome_counts["draw"], 1)
        self.assertEqual(summary.predicted_outcome_counts["home"], 1)
        self.assertEqual(summary.predicted_outcome_counts["away"], 1)

    def test_rejects_empty_probability_rows(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_1x2_probability_rows([], model_name="empty")

    def test_loads_probability_rows_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "probabilities.csv"
            path.write_text(
                "match_id,home_probability,draw_probability,away_probability,actual_result\n"
                "m1,0.60,0.25,0.15,home\n",
                encoding="utf-8",
            )

            rows = load_1x2_probability_rows_csv(path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["home_probability"], 0.60)
            self.assertEqual(rows[0]["actual_result"], "home")

    def test_writes_probability_evaluation_json(self) -> None:
        rows = [
            {
                "match_id": "m1",
                "home_probability": 0.60,
                "draw_probability": 0.25,
                "away_probability": 0.15,
                "actual_result": "home",
            }
        ]
        summary = evaluate_1x2_probability_rows(rows, model_name="demo")

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "evaluation.json"
            written = write_probability_evaluation_json(summary, path)

            self.assertEqual(written, path)
            self.assertIn('"model_name": "demo"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
