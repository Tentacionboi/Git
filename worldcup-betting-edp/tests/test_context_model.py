import unittest

from worldcup_betting_edp.evidence import EVIDENCE_AVAILABLE, EVIDENCE_MISSING
from worldcup_betting_edp.models import (
    ContextAdjustmentConfig,
    ContextFactor,
    build_context_adjusted_elo_prediction,
    build_elo_base_prediction,
    default_missing_context_factors,
)


class ContextModelTests(unittest.TestCase):
    def _elo_base(self):
        return build_elo_base_prediction(
            match_id="m1",
            home_team="Team A",
            away_team="Team B",
            home_rating=1600.0,
            away_rating=1500.0,
            neutral=True,
        )

    def test_elo_base_prediction_exposes_diagnostics(self) -> None:
        elo = self._elo_base()

        self.assertEqual(elo.match_id, "m1")
        self.assertEqual(elo.rating_gap, 100.0)
        self.assertAlmostEqual(sum(elo.probabilities.values()), 1.0)

    def test_missing_context_does_not_change_probability(self) -> None:
        elo = self._elo_base()

        adjusted = build_context_adjusted_elo_prediction(
            elo_base=elo,
            factors=default_missing_context_factors(),
        )

        self.assertEqual(adjusted.probabilities, elo.probabilities)
        self.assertEqual(adjusted.total_home_away_adjustment, 0.0)

    def test_available_context_makes_bounded_home_away_adjustment(self) -> None:
        elo = self._elo_base()
        adjusted = build_context_adjusted_elo_prediction(
            elo_base=elo,
            factors=[
                ContextFactor(
                    name="rest",
                    value=2.0,
                    status=EVIDENCE_AVAILABLE,
                    source="unit-test",
                ),
                ContextFactor(
                    name="travel",
                    value=None,
                    status=EVIDENCE_MISSING,
                    source="unit-test",
                ),
            ],
            config=ContextAdjustmentConfig(rest_weight=0.01, max_factor_adjustment=0.015),
        )

        self.assertGreater(adjusted.probabilities["home"], elo.probabilities["home"])
        self.assertLess(adjusted.probabilities["away"], elo.probabilities["away"])
        self.assertAlmostEqual(adjusted.total_home_away_adjustment, 0.015)


if __name__ == "__main__":
    unittest.main()
