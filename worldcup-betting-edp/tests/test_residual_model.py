import unittest

from worldcup_betting_edp.data import MarketOddsSnapshot
from worldcup_betting_edp.market import build_market_movement_feature
from worldcup_betting_edp.models import (
    ResidualEdgeConfig,
    build_market_residual_prediction,
)


class ResidualModelTests(unittest.TestCase):
    def test_builds_market_residual_prediction_from_market_and_fundamental(self) -> None:
        prediction = build_market_residual_prediction(
            match_id="m1",
            market_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            fundamental_probabilities={"home": 0.58, "draw": 0.24, "away": 0.18},
            config=ResidualEdgeConfig(fundamental_gap_weight=0.25),
        )

        self.assertEqual(prediction.match_id, "m1")
        self.assertEqual(prediction.model_name, "market_residual_mvp")
        self.assertGreater(prediction.probabilities["home"], 0.50)
        self.assertLess(prediction.probabilities["away"], 0.25)
        self.assertAlmostEqual(sum(prediction.probabilities.values()), 1.0)
        self.assertEqual(prediction.to_model_probabilities().probabilities, prediction.probabilities)

    def test_keeps_market_probabilities_when_fundamental_matches_market(self) -> None:
        prediction = build_market_residual_prediction(
            match_id="m1",
            market_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            fundamental_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
        )

        self.assertEqual(prediction.probabilities, {"home": 0.50, "draw": 0.25, "away": 0.25})
        self.assertEqual(prediction.residual_adjustments, {"home": 0.0, "draw": 0.0, "away": 0.0})

    def test_caps_large_fundamental_adjustments(self) -> None:
        prediction = build_market_residual_prediction(
            match_id="m1",
            market_probabilities={"home": 0.34, "draw": 0.33, "away": 0.33},
            fundamental_probabilities={"home": 0.95, "draw": 0.03, "away": 0.02},
            config=ResidualEdgeConfig(
                fundamental_gap_weight=1.0,
                max_abs_adjustment_per_outcome=0.04,
            ),
        )

        self.assertLessEqual(abs(prediction.residual_adjustments["home"]), 0.04)
        self.assertAlmostEqual(sum(prediction.probabilities.values()), 1.0)

    def test_can_use_market_movement_as_a_small_incremental_signal(self) -> None:
        opening = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-18T10:00:00+00:00",
            home_odds=2.20,
            draw_odds=3.30,
            away_odds=3.40,
            odds_type="opening",
        )
        current = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-18T12:00:00+00:00",
            home_odds=2.00,
            draw_odds=3.40,
            away_odds=3.80,
            odds_type="current",
        )
        movement = build_market_movement_feature(opening, current)
        without_movement = build_market_residual_prediction(
            match_id="m1",
            market_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            fundamental_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            config=ResidualEdgeConfig(market_movement_weight=0.0),
        )
        with_movement = build_market_residual_prediction(
            match_id="m1",
            market_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            fundamental_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
            movement_features=movement,
            config=ResidualEdgeConfig(market_movement_weight=0.10),
        )

        self.assertGreater(
            with_movement.probabilities["home"],
            without_movement.probabilities["home"],
        )
        self.assertAlmostEqual(sum(with_movement.probabilities.values()), 1.0)

    def test_rejects_movement_features_for_a_different_match(self) -> None:
        opening = MarketOddsSnapshot(
            match_id="other",
            bookmaker="demo",
            captured_at="2026-06-18T10:00:00+00:00",
            home_odds=2.20,
            draw_odds=3.30,
            away_odds=3.40,
            odds_type="opening",
        )
        current = MarketOddsSnapshot(
            match_id="other",
            bookmaker="demo",
            captured_at="2026-06-18T12:00:00+00:00",
            home_odds=2.00,
            draw_odds=3.40,
            away_odds=3.80,
            odds_type="current",
        )
        movement = build_market_movement_feature(opening, current)

        with self.assertRaises(ValueError):
            build_market_residual_prediction(
                match_id="m1",
                market_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
                fundamental_probabilities={"home": 0.50, "draw": 0.25, "away": 0.25},
                movement_features=movement,
            )


if __name__ == "__main__":
    unittest.main()
