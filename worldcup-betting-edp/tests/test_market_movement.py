from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.data import MarketOddsSnapshot
from worldcup_betting_edp.market import (
    MARKET_MOVEMENT_COLUMNS,
    build_market_movement_feature,
    build_market_movement_features,
    write_market_movement_features_csv,
)


class MarketMovementTests(unittest.TestCase):
    def test_builds_market_movement_feature(self) -> None:
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

        feature = build_market_movement_feature(opening, current)

        self.assertEqual(feature.match_id, "m1")
        self.assertEqual(feature.start_odds_type, "opening")
        self.assertEqual(feature.end_odds_type, "current")
        self.assertGreater(feature.probability_deltas["home"], 0.0)
        self.assertEqual(tuple(feature.to_dict().keys()), MARKET_MOVEMENT_COLUMNS)

    def test_rejects_mismatched_snapshots(self) -> None:
        first = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-18T10:00:00+00:00",
            home_odds=2.20,
            draw_odds=3.30,
            away_odds=3.40,
            odds_type="opening",
        )
        second = MarketOddsSnapshot(
            match_id="m2",
            bookmaker="demo",
            captured_at="2026-06-18T12:00:00+00:00",
            home_odds=2.00,
            draw_odds=3.40,
            away_odds=3.80,
            odds_type="current",
        )

        with self.assertRaises(ValueError):
            build_market_movement_feature(first, second)

    def test_builds_features_by_match_and_bookmaker(self) -> None:
        snapshots = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18T10:00:00+00:00",
                home_odds=2.20,
                draw_odds=3.30,
                away_odds=3.40,
                odds_type="opening",
            ),
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18T12:00:00+00:00",
                home_odds=2.00,
                draw_odds=3.40,
                away_odds=3.80,
                odds_type="current",
            ),
            MarketOddsSnapshot(
                match_id="m2",
                bookmaker="demo",
                captured_at="2026-06-18T12:00:00+00:00",
                home_odds=1.90,
                draw_odds=3.50,
                away_odds=4.50,
                odds_type="current",
            ),
        ]

        features = build_market_movement_features(snapshots)

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].match_id, "m1")

    def test_writes_market_movement_features_csv(self) -> None:
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
        feature = build_market_movement_feature(opening, current)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "movement.csv"
            written = write_market_movement_features_csv([feature], path)

            self.assertEqual(written, path)
            self.assertIn("home_probability_delta", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
