from pathlib import Path
import math
import unittest

from worldcup_betting_edp.backtest import brier_score, log_loss, score_prediction_report
from worldcup_betting_edp.data import load_prediction_input_path, load_settled_result_path
from worldcup_betting_edp.reports import evaluate_single_match


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTION_INPUT = PROJECT_ROOT / "examples" / "demo_single_match.json"
SETTLED_RESULT = PROJECT_ROOT / "examples" / "demo_settled_match.json"


class ScoringTests(unittest.TestCase):
    def test_brier_score_for_three_way_forecast(self) -> None:
        score = brier_score({"home": 0.49, "draw": 0.27, "away": 0.24}, "home")

        self.assertAlmostEqual(score, 0.3906)

    def test_log_loss_for_actual_outcome(self) -> None:
        score = log_loss({"home": 0.49, "draw": 0.27, "away": 0.24}, "home")

        self.assertAlmostEqual(score, -math.log(0.49))

    def test_log_loss_clips_zero_probability(self) -> None:
        score = log_loss({"home": 0.0, "draw": 0.5, "away": 0.5}, "home", epsilon=1e-6)

        self.assertAlmostEqual(score, -math.log(1e-6))

    def test_score_prediction_report_compares_model_to_market(self) -> None:
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        settled_result = load_settled_result_path(SETTLED_RESULT)
        report = evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=prediction_input.model_probabilities,
        )

        scored = score_prediction_report(report=report, settled_result=settled_result)
        row = scored.to_dict()

        self.assertEqual(row["match_id"], "demo-2026-final")
        self.assertEqual(row["actual_result"], "home")
        self.assertEqual(row["model_predicted_outcome"], "home")
        self.assertEqual(row["market_predicted_outcome"], "home")
        self.assertAlmostEqual(row["model_brier_score"], 0.3906)
        self.assertLess(row["model_brier_score"], row["market_brier_score"])
        self.assertLess(row["model_log_loss"], row["market_log_loss"])
        self.assertTrue(row["model_beats_market_brier"])
        self.assertTrue(row["model_beats_market_log_loss"])

    def test_score_prediction_report_rejects_mismatched_match_id(self) -> None:
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        settled_result = load_settled_result_path(SETTLED_RESULT)
        other_result = type(settled_result)(
            match_id="other",
            settled_at=settled_result.settled_at,
            home_goals=settled_result.home_goals,
            away_goals=settled_result.away_goals,
            result_1x2=settled_result.result_1x2,
        )
        report = evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=prediction_input.model_probabilities,
        )

        with self.assertRaisesRegex(ValueError, "same match_id"):
            score_prediction_report(report=report, settled_result=other_result)

    def test_rejects_invalid_actual_outcome(self) -> None:
        with self.assertRaisesRegex(ValueError, "actual_outcome must be one of"):
            brier_score({"home": 0.49, "draw": 0.27, "away": 0.24}, "win")


if __name__ == "__main__":
    unittest.main()
