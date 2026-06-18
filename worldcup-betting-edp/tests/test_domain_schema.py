from datetime import datetime, timezone
import unittest

from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot


class DomainSchemaTests(unittest.TestCase):
    def test_match_rejects_same_teams(self) -> None:
        with self.assertRaises(ValueError):
            Match(
                match_id="m1",
                match_time=datetime(2026, 6, 11, tzinfo=timezone.utc),
                home_team="A",
                away_team="A",
            )

    def test_odds_snapshot_to_odds_map(self) -> None:
        snapshot = OddsSnapshot(
            match_id="m1",
            captured_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
            bookmaker="demo",
            home=2.0,
            draw=3.5,
            away=4.0,
        )

        self.assertEqual(snapshot.to_odds_map(), {"home": 2.0, "draw": 3.5, "away": 4.0})

    def test_model_probabilities_must_sum_to_one(self) -> None:
        with self.assertRaises(ValueError):
            ModelProbabilities.from_1x2(
                match_id="m1",
                model_name="bad_model",
                home=0.50,
                draw=0.30,
                away=0.30,
            )


if __name__ == "__main__":
    unittest.main()

