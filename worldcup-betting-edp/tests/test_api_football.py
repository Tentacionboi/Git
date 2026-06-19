import unittest

from worldcup_betting_edp.data import (
    parse_api_football_odds_response,
    summarize_api_football_probe_payloads,
)


class ApiFootballOddsTests(unittest.TestCase):
    def test_parses_match_winner_odds(self) -> None:
        payload = {
            "response": [
                {
                    "league": {"id": 1, "season": 2022},
                    "fixture": {
                        "id": 855734,
                        "date": "2022-11-20T16:00:00+00:00",
                    },
                    "update": "2022-11-20T12:00:00+00:00",
                    "bookmakers": [
                        {
                            "id": 8,
                            "name": "Bet365",
                            "bets": [
                                {
                                    "id": 1,
                                    "name": "Match Winner",
                                    "values": [
                                        {"value": "Home", "odd": "3.60"},
                                        {"value": "Draw", "odd": "3.20"},
                                        {"value": "Away", "odd": "2.10"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        snapshots = parse_api_football_odds_response(payload)

        self.assertEqual(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertEqual(snapshot.match_id, "api-football:855734")
        self.assertEqual(snapshot.bookmaker, "Bet365")
        self.assertEqual(snapshot.captured_at, "2022-11-20T12:00:00+00:00")
        self.assertEqual(snapshot.home_odds, 3.6)
        self.assertEqual(snapshot.draw_odds, 3.2)
        self.assertEqual(snapshot.away_odds, 2.1)
        self.assertEqual(snapshot.source, "api-football:league:1:season:2022")

    def test_skips_incomplete_match_winner_odds(self) -> None:
        payload = {
            "response": [
                {
                    "fixture": {"id": 1, "date": "2022-11-20T16:00:00+00:00"},
                    "bookmakers": [
                        {
                            "name": "Demo",
                            "bets": [
                                {
                                    "name": "Match Winner",
                                    "values": [
                                        {"value": "Home", "odd": "3.60"},
                                        {"value": "Away", "odd": "2.10"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        self.assertEqual(parse_api_football_odds_response(payload), [])

    def test_summarizes_probe_payloads(self) -> None:
        summary = summarize_api_football_probe_payloads(
            {
                "fixtures": {
                    "results": 64,
                    "errors": [],
                    "paging": {"current": 1, "total": 1},
                    "response": [{}, {}],
                }
            }
        )

        self.assertEqual(summary["fixtures"]["results"], 64)
        self.assertEqual(summary["fixtures"]["response_count"], 2)


if __name__ == "__main__":
    unittest.main()
