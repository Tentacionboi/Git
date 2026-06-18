from pathlib import Path
import unittest

from worldcup_betting_edp.backtest import settle_flat_stake
from worldcup_betting_edp.data import SettledResult, load_prediction_input_path, load_settled_result_path
from worldcup_betting_edp.domain import ModelProbabilities
from worldcup_betting_edp.reports import evaluate_single_match


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTION_INPUT = PROJECT_ROOT / "examples" / "demo_single_match.json"
SETTLED_RESULT = PROJECT_ROOT / "examples" / "demo_settled_match.json"


class SettlementTests(unittest.TestCase):
    def _report(self):
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        return evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=prediction_input.model_probabilities,
        )

    def test_settles_winning_flat_stake_value_bet(self) -> None:
        report = self._report()
        settled_result = load_settled_result_path(SETTLED_RESULT)

        settlement = settle_flat_stake(report=report, settled_result=settled_result, stake=10.0)
        row = settlement.to_dict()

        self.assertTrue(row["bet_placed"])
        self.assertEqual(row["bet_outcome"], "home")
        self.assertEqual(row["actual_result"], "home")
        self.assertEqual(row["decimal_odds"], 2.2)
        self.assertAlmostEqual(row["profit"], 12.0)
        self.assertAlmostEqual(row["roi"], 1.2)
        self.assertTrue(row["hit"])

    def test_settles_losing_flat_stake_value_bet(self) -> None:
        report = self._report()
        settled_result = load_settled_result_path(SETTLED_RESULT)
        losing_result = SettledResult(
            match_id=settled_result.match_id,
            settled_at=settled_result.settled_at,
            home_goals=0,
            away_goals=0,
            result_1x2="draw",
        )

        settlement = settle_flat_stake(report=report, settled_result=losing_result, stake=10.0)

        self.assertTrue(settlement.bet_placed)
        self.assertFalse(settlement.hit)
        self.assertAlmostEqual(settlement.profit, -10.0)
        self.assertAlmostEqual(settlement.roi, -1.0)

    def test_no_bet_settlement_has_zero_stake_and_profit(self) -> None:
        prediction_input = load_prediction_input_path(PREDICTION_INPUT)
        no_bet_model = ModelProbabilities.from_1x2(
            match_id=prediction_input.match.match_id,
            model_name="market_like_model",
            home=0.44,
            draw=0.30,
            away=0.26,
        )
        report = evaluate_single_match(
            match=prediction_input.match,
            odds_snapshot=prediction_input.odds_snapshot,
            model_probabilities=no_bet_model,
            probability_edge_threshold=0.20,
        )
        settled_result = load_settled_result_path(SETTLED_RESULT)

        settlement = settle_flat_stake(report=report, settled_result=settled_result, stake=10.0)

        self.assertFalse(settlement.bet_placed)
        self.assertIsNone(settlement.bet_outcome)
        self.assertIsNone(settlement.decimal_odds)
        self.assertEqual(settlement.stake, 0.0)
        self.assertEqual(settlement.profit, 0.0)
        self.assertEqual(settlement.roi, 0.0)
        self.assertIsNone(settlement.hit)

    def test_rejects_mismatched_match_id(self) -> None:
        report = self._report()
        settled_result = load_settled_result_path(SETTLED_RESULT)
        other_result = SettledResult(
            match_id="other",
            settled_at=settled_result.settled_at,
            home_goals=settled_result.home_goals,
            away_goals=settled_result.away_goals,
            result_1x2=settled_result.result_1x2,
        )

        with self.assertRaisesRegex(ValueError, "same match_id"):
            settle_flat_stake(report=report, settled_result=other_result)

    def test_rejects_non_positive_stake(self) -> None:
        report = self._report()
        settled_result = load_settled_result_path(SETTLED_RESULT)

        with self.assertRaisesRegex(ValueError, "stake must be positive"):
            settle_flat_stake(report=report, settled_result=settled_result, stake=0.0)


if __name__ == "__main__":
    unittest.main()
