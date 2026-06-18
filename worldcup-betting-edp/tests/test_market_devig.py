import unittest

from worldcup_betting_edp.market import fair_odds, implied_probabilities, overround, proportional_devig


class MarketDevigTests(unittest.TestCase):
    def test_implied_probabilities(self) -> None:
        odds = {"home": 2.0, "draw": 4.0, "away": 4.0}

        result = implied_probabilities(odds)

        self.assertAlmostEqual(result["home"], 0.5)
        self.assertAlmostEqual(result["draw"], 0.25)
        self.assertAlmostEqual(result["away"], 0.25)

    def test_proportional_devig_sums_to_one(self) -> None:
        odds = {"home": 1.80, "draw": 3.60, "away": 5.00}

        result = proportional_devig(odds)

        self.assertEqual(result.method, "proportional")
        self.assertGreater(result.overround, 0.0)
        self.assertAlmostEqual(sum(result.fair_probabilities.values()), 1.0)

    def test_overround(self) -> None:
        odds = {"home": 2.0, "draw": 3.0, "away": 4.0}

        self.assertAlmostEqual(overround(odds), (0.5 + 1 / 3 + 0.25) - 1.0)

    def test_fair_odds(self) -> None:
        self.assertAlmostEqual(fair_odds(0.25), 4.0)

    def test_invalid_odds_raise(self) -> None:
        with self.assertRaises(ValueError):
            implied_probabilities({"home": 1.0})


if __name__ == "__main__":
    unittest.main()

