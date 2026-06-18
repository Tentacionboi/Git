from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.data import (
    MARKET_ODDS_COLUMNS,
    MarketOddsSnapshot,
    load_market_odds_csv,
    select_one_odds_per_match,
    write_market_odds_csv,
)


class MarketOddsTests(unittest.TestCase):
    def test_market_odds_snapshot_to_odds_map(self) -> None:
        snapshot = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-18T12:00:00+00:00",
            home_odds=2.0,
            draw_odds=3.25,
            away_odds=4.0,
            source="unit-test",
        )

        self.assertEqual(snapshot.to_odds_map()["home"], 2.0)
        self.assertEqual(tuple(snapshot.to_dict().keys()), MARKET_ODDS_COLUMNS)

    def test_rejects_invalid_odds(self) -> None:
        with self.assertRaises(ValueError):
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18",
                home_odds=1.0,
                draw_odds=3.25,
                away_odds=4.0,
                source="unit-test",
            )

    def test_writes_and_loads_market_odds_csv(self) -> None:
        snapshots = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="demo",
                captured_at="2026-06-18",
                home_odds=2.0,
                draw_odds=3.25,
                away_odds=4.0,
                source="unit-test",
            )
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "odds.csv"
            write_market_odds_csv(snapshots, path)
            loaded = load_market_odds_csv(path)

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].match_id, "m1")
            self.assertEqual(loaded[0].bookmaker, "demo")

    def test_select_one_odds_per_match_prefers_closing(self) -> None:
        opening = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-17",
            home_odds=2.1,
            draw_odds=3.3,
            away_odds=3.8,
            odds_type="opening",
            source="unit-test",
        )
        closing = MarketOddsSnapshot(
            match_id="m1",
            bookmaker="demo",
            captured_at="2026-06-18",
            home_odds=2.0,
            draw_odds=3.25,
            away_odds=4.0,
            odds_type="closing",
            source="unit-test",
        )

        selected = select_one_odds_per_match([opening, closing])

        self.assertEqual(selected["m1"], closing)


if __name__ == "__main__":
    unittest.main()
