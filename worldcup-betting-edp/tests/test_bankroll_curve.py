from pathlib import Path
import unittest

from worldcup_betting_edp.backtest import settle_kelly_bankroll
from worldcup_betting_edp.data import SettledResult, load_prediction_input_path, load_settled_result_path
from worldcup_betting_edp.domain import ModelProbabilities
from worldcup_betting_edp.reports import evaluate_single_match


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTION_INPUT = PROJECT_ROOT / "examples" / "demo_single_match.json"
SETTLED_RESULT = PROJECT_ROOT / "examples" / "demo_settled_match.json"


class BankrollCurveTests(unittest.TestCase):
    def _value_report(self):
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        return evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=prediction_input.model_probabilities,
        )

    def _no_bet_report(self):
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        no_bet_model = ModelProbabilities.from_1x2(
            match_id=prediction_input.match.match_id,
            model_name="market_like_model",
            home=0.44,
            draw=0.30,
            away=0.26,
        )
        return evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=no_bet_model,
            probability_edge_threshold=0.20,
        )

    def test_kelly_bankroll_curve_settles_winning_value_bet(self) -> None:
        report = self._value_report()
        settled_result = load_settled_result_path(SETTLED_RESULT)

        curve = settle_kelly_bankroll([(report, settled_result)], starting_bankroll=100.0)
        row = curve.to_dict()

        self.assertAlmostEqual(row["final_bankroll"], 101.95)
        self.assertAlmostEqual(row["total_profit"], 1.95)
        self.assertAlmostEqual(row["total_roi"], 0.0195)
        self.assertAlmostEqual(row["max_drawdown"], 0.0)
        self.assertEqual(row["bet_count"], 1)
        self.assertEqual(row["hit_count"], 1)
        self.assertEqual(row["hit_rate"], 1.0)
        self.assertEqual(len(row["points"]), 1)
        self.assertAlmostEqual(row["points"][0]["stake_fraction"], 0.01625)
        self.assertAlmostEqual(row["points"][0]["stake"], 1.625)

    def test_kelly_bankroll_curve_tracks_drawdown_after_loss(self) -> None:
        report = self._value_report()
        settled_result = load_settled_result_path(SETTLED_RESULT)
        losing_result = SettledResult(
            match_id=settled_result.match_id,
            settled_at=settled_result.settled_at,
            home_goals=0,
            away_goals=0,
            result_1x2="draw",
        )

        curve = settle_kelly_bankroll(
            [(report, settled_result), (report, losing_result)],
            starting_bankroll=100.0,
        )

        self.assertEqual(curve.bet_count, 2)
        self.assertEqual(curve.hit_count, 1)
        self.assertAlmostEqual(curve.final_bankroll, 100.2933125)
        self.assertGreater(curve.max_drawdown, 0.0)
        self.assertAlmostEqual(curve.points[1].drawdown, curve.max_drawdown)

    def test_no_bet_keeps_bankroll_unchanged(self) -> None:
        report = self._no_bet_report()
        settled_result = load_settled_result_path(SETTLED_RESULT)

        curve = settle_kelly_bankroll([(report, settled_result)], starting_bankroll=100.0)

        self.assertEqual(curve.final_bankroll, 100.0)
        self.assertEqual(curve.bet_count, 0)
        self.assertEqual(curve.hit_count, 0)
        self.assertFalse(curve.points[0].bet_placed)
        self.assertIsNone(curve.points[0].hit)
        self.assertEqual(curve.points[0].stake, 0.0)

    def test_rejects_bad_starting_bankroll(self) -> None:
        with self.assertRaisesRegex(ValueError, "starting_bankroll must be positive"):
            settle_kelly_bankroll([], starting_bankroll=0.0)

    def test_rejects_mismatched_match_id(self) -> None:
        report = self._value_report()
        settled_result = load_settled_result_path(SETTLED_RESULT)
        other_result = SettledResult(
            match_id="other",
            settled_at=settled_result.settled_at,
            home_goals=settled_result.home_goals,
            away_goals=settled_result.away_goals,
            result_1x2=settled_result.result_1x2,
        )

        with self.assertRaisesRegex(ValueError, "same match_id"):
            settle_kelly_bankroll([(report, other_result)])


if __name__ == "__main__":
    unittest.main()
