import unittest

from worldcup_betting_edp.betting import (
    RiskLevel,
    evaluate_value_bet,
    expected_value,
    fractional_kelly_fraction,
    full_kelly_fraction,
)


class BettingKellyTests(unittest.TestCase):
    def test_expected_value(self) -> None:
        self.assertAlmostEqual(expected_value(0.55, 2.0), 0.10)

    def test_full_kelly_fraction_positive_ev(self) -> None:
        self.assertAlmostEqual(full_kelly_fraction(0.55, 2.0), 0.10)

    def test_full_kelly_fraction_negative_ev_is_zero(self) -> None:
        self.assertEqual(full_kelly_fraction(0.45, 2.0), 0.0)

    def test_fractional_kelly_is_capped(self) -> None:
        sizing = fractional_kelly_fraction(0.60, 2.5, fraction=0.5, cap=0.05)

        self.assertGreater(sizing.full_kelly, 0.0)
        self.assertEqual(sizing.capped_fraction, 0.05)

    def test_value_bet_decision_positive(self) -> None:
        decision = evaluate_value_bet(
            outcome="home",
            model_probability=0.55,
            market_probability=0.50,
            decimal_odds=2.0,
        )

        self.assertTrue(decision.is_value_bet)
        self.assertEqual(decision.risk_level, RiskLevel.LOW)
        self.assertGreater(decision.sizing.capped_fraction, 0.0)

    def test_value_bet_rejected_when_edge_too_small(self) -> None:
        decision = evaluate_value_bet(
            outcome="home",
            model_probability=0.515,
            market_probability=0.50,
            decimal_odds=2.0,
        )

        self.assertFalse(decision.is_value_bet)
        self.assertEqual(decision.risk_level, RiskLevel.NO_BET)


if __name__ == "__main__":
    unittest.main()

