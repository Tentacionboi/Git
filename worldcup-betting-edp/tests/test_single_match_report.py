from datetime import datetime, timezone
import unittest

from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot
from worldcup_betting_edp.models import (
    ContextFactor,
    MarketBaselineModel,
    ResidualEdgeConfig,
    build_context_adjusted_elo_prediction,
    build_elo_base_prediction,
)
from worldcup_betting_edp.reports import evaluate_single_match


class SingleMatchReportTests(unittest.TestCase):
    def _match(self) -> Match:
        return Match(
            match_id="m1",
            match_time=datetime(2026, 6, 11, tzinfo=timezone.utc),
            home_team="Team A",
            away_team="Team B",
            stage="Group A",
            neutral=True,
        )

    def _odds(self) -> OddsSnapshot:
        return OddsSnapshot(
            match_id="m1",
            captured_at=datetime(2026, 6, 10, 12, tzinfo=timezone.utc),
            bookmaker="demo",
            home=2.20,
            draw=3.25,
            away=3.60,
        )

    def test_market_baseline_model_outputs_probabilities(self) -> None:
        market = MarketBaselineModel().predict(self._odds())

        self.assertEqual(market.match_id, "m1")
        self.assertAlmostEqual(sum(market.probabilities.values()), 1.0)
        self.assertGreater(market.overround, 0.0)

    def test_single_match_report_flags_best_value_bet(self) -> None:
        model = ModelProbabilities.from_1x2(
            match_id="m1",
            model_name="test_model",
            home=0.49,
            draw=0.27,
            away=0.24,
        )

        report = evaluate_single_match(
            match=self._match(),
            odds_snapshot=self._odds(),
            model_probabilities=model,
        )
        row = report.to_dict()

        self.assertTrue(row["value_bet_flag"])
        self.assertEqual(row["value_bet_direction"], "home")
        self.assertGreater(row["expected_value"], 0.0)
        self.assertLessEqual(row["fractional_kelly_fraction"], 0.02)
        self.assertIn("delta_home", row)

    def test_single_match_report_can_return_no_bet(self) -> None:
        model = ModelProbabilities.from_1x2(
            match_id="m1",
            model_name="market_like_model",
            home=0.44,
            draw=0.30,
            away=0.26,
        )

        report = evaluate_single_match(
            match=self._match(),
            odds_snapshot=self._odds(),
            model_probabilities=model,
            probability_edge_threshold=0.20,
        )
        row = report.to_dict()

        self.assertFalse(row["value_bet_flag"])
        self.assertEqual(row["fractional_kelly_fraction"], 0.0)
        self.assertEqual(row["risk_level"], "no_bet")

    def test_single_match_report_can_use_market_residual_final_probabilities(self) -> None:
        fundamental = ModelProbabilities.from_1x2(
            match_id="m1",
            model_name="fundamental_test_model",
            home=0.60,
            draw=0.22,
            away=0.18,
        )

        report = evaluate_single_match(
            match=self._match(),
            odds_snapshot=self._odds(),
            model_probabilities=fundamental,
            use_market_residual_model=True,
            residual_config=ResidualEdgeConfig(
                fundamental_gap_weight=0.25,
                max_abs_adjustment_per_outcome=0.03,
            ),
        )
        row = report.to_dict()

        self.assertEqual(row["probability_model_mode"], "market_residual")
        self.assertEqual(row["fundamental_model_name"], "fundamental_test_model")
        self.assertEqual(row["model_name"], "market_residual_mvp")
        self.assertGreater(row["fundamental_home_prob"], row["model_home_prob"])
        self.assertGreater(row["model_home_prob"], row["market_home_prob_devig"])
        self.assertAlmostEqual(
            row["delta_home"],
            row["model_home_prob"] - row["market_home_prob_devig"],
        )
        self.assertIn("residual_home_adjustment", row)

    def test_single_match_report_has_structured_output(self) -> None:
        elo_base = build_elo_base_prediction(
            match_id="m1",
            home_team="Team A",
            away_team="Team B",
            home_rating=1580.0,
            away_rating=1500.0,
            neutral=True,
        )
        context = build_context_adjusted_elo_prediction(
            elo_base=elo_base,
            factors=[
                ContextFactor(
                    name="rest",
                    value=1.0,
                    status="available",
                    source="unit-test",
                )
            ],
        )
        model = ModelProbabilities(
            match_id="m1",
            model_name=context.model_name,
            probabilities=dict(context.probabilities),
        )

        report = evaluate_single_match(
            match=self._match(),
            odds_snapshot=self._odds(),
            model_probabilities=model,
            elo_base_prediction=elo_base,
            context_prediction=context,
        )
        structured = report.to_structured_dict()
        flat = report.to_dict()

        self.assertEqual(structured["match"]["match_id"], "m1")
        self.assertIn("elo_base", structured)
        self.assertIn("context_adjustments", structured)
        self.assertIn("confidence", structured)
        self.assertIn("market", structured)
        self.assertIn(structured["market"]["alignment"]["level"], {
            "market_aligned",
            "mild_divergence",
            "strong_divergence",
        })
        self.assertEqual(structured["flat_compat"]["match_id"], flat["match_id"])


if __name__ == "__main__":
    unittest.main()
