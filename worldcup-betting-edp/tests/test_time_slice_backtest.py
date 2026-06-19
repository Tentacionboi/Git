import unittest

from worldcup_betting_edp.backtest import (
    OddsTimeSlice,
    run_market_time_slice_backtest,
)
from worldcup_betting_edp.data import MarketOddsSnapshot, MatchTiming


class TimeSliceBacktestTests(unittest.TestCase):
    def test_time_slice_backtest_selects_only_as_of_odds(self):
        market_odds = [
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="book_a",
                captured_at="2022-11-20T12:00:00+00:00",
                home_odds=2.40,
                draw_odds=3.20,
                away_odds=3.10,
                odds_type="open",
                source="unit-test",
            ),
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="book_a",
                captured_at="2022-11-21T18:00:00+00:00",
                home_odds=2.00,
                draw_odds=3.30,
                away_odds=4.10,
                odds_type="six_hours_before",
                source="unit-test",
            ),
            MarketOddsSnapshot(
                match_id="m1",
                bookmaker="book_a",
                captured_at="2022-11-21T23:00:00+00:00",
                home_odds=1.90,
                draw_odds=3.40,
                away_odds=4.40,
                odds_type="close",
                source="unit-test",
            ),
        ]
        model_rows = [
            {
                "match_id": "m1",
                "match_date": "2022-11-22",
                "home_team": "A",
                "away_team": "B",
                "home_probability": 0.50,
                "draw_probability": 0.28,
                "away_probability": 0.22,
                "actual_result": "home",
            }
        ]
        timings = [
            MatchTiming(
                match_id="m1",
                kickoff_time="2022-11-22T00:00:00+00:00",
                precision="datetime",
                source="unit-test",
            )
        ]

        payload = run_market_time_slice_backtest(
            market_odds=market_odds,
            model_probability_rows=model_rows,
            match_timings=timings,
            slices=(
                OddsTimeSlice("24h_before", hours_before_kickoff=24.0),
                OddsTimeSlice("6h_before", hours_before_kickoff=6.0),
                OddsTimeSlice("close", hours_before_kickoff=0.0),
            ),
        )

        by_name = {slice_payload["name"]: slice_payload for slice_payload in payload["slices"]}
        self.assertEqual(by_name["24h_before"]["coverage"]["evaluated_match_count"], 1)
        self.assertEqual(by_name["6h_before"]["coverage"]["evaluated_match_count"], 1)
        self.assertEqual(by_name["close"]["coverage"]["evaluated_match_count"], 1)

        row_24h = by_name["24h_before"]["rows"][0]
        row_6h = by_name["6h_before"]["rows"][0]
        row_close = by_name["close"]["rows"][0]
        self.assertEqual(row_24h["prediction_time"], "2022-11-21T00:00:00+00:00")
        self.assertEqual(row_6h["prediction_time"], "2022-11-21T18:00:00+00:00")
        self.assertEqual(row_close["prediction_time"], "2022-11-22T00:00:00+00:00")
        self.assertLess(
            row_24h["market_home_probability"],
            row_6h["market_home_probability"],
        )
        self.assertLess(
            row_6h["market_home_probability"],
            row_close["market_home_probability"],
        )

    def test_time_slice_backtest_requires_datetime_kickoff(self):
        with self.assertRaises(ValueError):
            run_market_time_slice_backtest(
                market_odds=[
                    MarketOddsSnapshot(
                        match_id="m1",
                        bookmaker="book_a",
                        captured_at="2022-11-20T12:00:00+00:00",
                        home_odds=2.40,
                        draw_odds=3.20,
                        away_odds=3.10,
                        source="unit-test",
                    )
                ],
                model_probability_rows=[
                    {
                        "match_id": "m1",
                        "home_probability": 0.50,
                        "draw_probability": 0.28,
                        "away_probability": 0.22,
                        "actual_result": "home",
                    }
                ],
                match_timings=[
                    MatchTiming(
                        match_id="m1",
                        kickoff_time="2022-11-22",
                        precision="date",
                        source="unit-test",
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
