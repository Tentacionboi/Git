import unittest
from urllib.parse import parse_qs, urlparse

from worldcup_betting_edp.data import (
    THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    build_the_odds_api_historical_odds_url,
    parse_the_odds_api_historical_odds_response,
)


class TheOddsApiTests(unittest.TestCase):
    def test_parses_historical_soccer_1x2_snapshot(self) -> None:
        payload = {
            "timestamp": "2022-11-20T12:00:00Z",
            "data": [
                {
                    "id": "evt1",
                    "sport_key": "soccer_fifa_world_cup",
                    "commence_time": "2022-11-20T16:00:00Z",
                    "home_team": "Qatar",
                    "away_team": "Ecuador",
                    "bookmakers": [
                        {
                            "key": "pinnacle",
                            "title": "Pinnacle",
                            "last_update": "2022-11-20T11:58:00Z",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Ecuador", "price": 2.1},
                                        {"name": "Draw", "price": 3.2},
                                        {"name": "Qatar", "price": 3.6},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        snapshots = parse_the_odds_api_historical_odds_response(payload)

        self.assertEqual(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertEqual(snapshot.match_id, "the-odds-api:evt1")
        self.assertEqual(snapshot.bookmaker, "pinnacle")
        self.assertEqual(snapshot.captured_at, "2022-11-20T12:00:00Z")
        self.assertEqual(snapshot.home_odds, 3.6)
        self.assertEqual(snapshot.draw_odds, 3.2)
        self.assertEqual(snapshot.away_odds, 2.1)
        self.assertEqual(snapshot.odds_type, "historical_snapshot")
        self.assertEqual(snapshot.source, "the-odds-api:soccer_fifa_world_cup")

    def test_skips_incomplete_1x2_market(self) -> None:
        payload = [
            {
                "id": "evt1",
                "sport_key": "soccer_fifa_world_cup",
                "commence_time": "2022-11-20T16:00:00Z",
                "home_team": "Qatar",
                "away_team": "Ecuador",
                "bookmakers": [
                    {
                        "key": "demo",
                        "last_update": "2022-11-20T11:58:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Qatar", "price": 3.6},
                                    {"name": "Ecuador", "price": 2.1},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        snapshots = parse_the_odds_api_historical_odds_response(payload)

        self.assertEqual(snapshots, [])

    def test_rejects_american_odds_payload(self) -> None:
        payload = [
            {
                "id": "evt1",
                "sport_key": "soccer_fifa_world_cup",
                "commence_time": "2022-11-20T16:00:00Z",
                "home_team": "Qatar",
                "away_team": "Ecuador",
                "bookmakers": [
                    {
                        "key": "demo",
                        "last_update": "2022-11-20T11:58:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Qatar", "price": 260},
                                    {"name": "Draw", "price": 220},
                                    {"name": "Ecuador", "price": -110},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        with self.assertRaises(ValueError):
            parse_the_odds_api_historical_odds_response(payload)

    def test_builds_historical_odds_url(self) -> None:
        url = build_the_odds_api_historical_odds_url(
            api_key="test_key",
            date="2022-11-20T12:00:00Z",
            regions="uk,eu",
        )

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, f"/v4/historical/sports/{THE_ODDS_API_WORLD_CUP_SPORT_KEY}/odds")
        self.assertEqual(query["apiKey"], ["test_key"])
        self.assertEqual(query["date"], ["2022-11-20T12:00:00Z"])
        self.assertEqual(query["markets"], ["h2h"])
        self.assertEqual(query["oddsFormat"], ["decimal"])
        self.assertEqual(query["regions"], ["uk,eu"])

    def test_url_builder_requires_decimal_odds_format(self) -> None:
        with self.assertRaises(ValueError):
            build_the_odds_api_historical_odds_url(
                api_key="test_key",
                date="2022-11-20T12:00:00Z",
                odds_format="american",
            )


if __name__ == "__main__":
    unittest.main()
