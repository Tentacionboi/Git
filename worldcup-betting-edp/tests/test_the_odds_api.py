from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from worldcup_betting_edp.data import (
    CanonicalMatch,
    MarketOddsSnapshot,
    THE_ODDS_API_WORLD_CUP_SPORT_KEY,
    build_the_odds_api_event_mapping,
    build_the_odds_api_historical_odds_url,
    parse_the_odds_api_historical_odds_response,
    remap_the_odds_api_snapshots_to_canonical,
    write_the_odds_api_event_mapping_csv,
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

    def test_builds_event_mapping_to_canonical_match(self) -> None:
        payload = {
            "timestamp": "2022-11-20T12:00:00Z",
            "data": [
                {
                    "id": "evt1",
                    "sport_key": "soccer_fifa_world_cup",
                    "commence_time": "2022-11-20T16:00:00Z",
                    "home_team": "Qatar",
                    "away_team": "Ecuador",
                    "bookmakers": [],
                }
            ],
        }
        canonical_match = CanonicalMatch(
            match_id="match_qatar_ecuador",
            match_date="2022-11-20",
            home_team="Qatar",
            away_team="Ecuador",
            home_score=0,
            away_score=2,
            result_1x2="away",
            total_goals=2,
            tournament="FIFA World Cup",
            city="Al Khor",
            country="Qatar",
            neutral=False,
            source="unit-test",
            source_match_id="unit-test:1",
        )

        mappings = build_the_odds_api_event_mapping(
            payload,
            canonical_matches=[canonical_match],
        )

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].source_match_id, "the-odds-api:evt1")
        self.assertEqual(mappings[0].canonical_match_id, "match_qatar_ecuador")
        self.assertEqual(mappings[0].orientation, "same")

    def test_builds_swapped_event_mapping_to_canonical_match(self) -> None:
        payload = {
            "timestamp": "2022-11-29T12:00:00Z",
            "data": [
                {
                    "id": "evt1",
                    "commence_time": "2022-11-29T15:00:00Z",
                    "home_team": "Netherlands",
                    "away_team": "Qatar",
                }
            ],
        }
        canonical_match = CanonicalMatch(
            match_id="match_qatar_netherlands",
            match_date="2022-11-29",
            home_team="Qatar",
            away_team="Netherlands",
            home_score=0,
            away_score=2,
            result_1x2="away",
            total_goals=2,
            tournament="FIFA World Cup",
            city="Al Khor",
            country="Qatar",
            neutral=False,
            source="unit-test",
            source_match_id="unit-test:1",
        )

        mappings = build_the_odds_api_event_mapping(payload, canonical_matches=[canonical_match])

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].canonical_match_id, "match_qatar_netherlands")
        self.assertEqual(mappings[0].orientation, "swapped")

    def test_writes_event_mapping_csv(self) -> None:
        payload = {
            "timestamp": "2022-11-20T12:00:00Z",
            "data": [
                {
                    "id": "evt1",
                    "commence_time": "2022-11-20T16:00:00Z",
                    "home_team": "Qatar",
                    "away_team": "Ecuador",
                }
            ],
        }
        canonical_match = CanonicalMatch(
            match_id="match_qatar_ecuador",
            match_date="2022-11-20",
            home_team="Qatar",
            away_team="Ecuador",
            home_score=0,
            away_score=2,
            result_1x2="away",
            total_goals=2,
            tournament="FIFA World Cup",
            city="Al Khor",
            country="Qatar",
            neutral=False,
            source="unit-test",
            source_match_id="unit-test:1",
        )
        mappings = build_the_odds_api_event_mapping(
            payload,
            canonical_matches=[canonical_match],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "mapping.csv"
            write_the_odds_api_event_mapping_csv(mappings, output)

            self.assertIn("source_event_id", output.read_text(encoding="utf-8"))
            self.assertIn("match_qatar_ecuador", output.read_text(encoding="utf-8"))

    def test_remaps_swapped_source_odds_to_canonical_orientation(self) -> None:
        payload = {
            "data": [
                {
                    "id": "evt1",
                    "commence_time": "2022-11-29T15:00:00Z",
                    "home_team": "Netherlands",
                    "away_team": "Qatar",
                }
            ],
        }
        canonical_match = CanonicalMatch(
            match_id="match_qatar_netherlands",
            match_date="2022-11-29",
            home_team="Qatar",
            away_team="Netherlands",
            home_score=0,
            away_score=2,
            result_1x2="away",
            total_goals=2,
            tournament="FIFA World Cup",
            city="Al Khor",
            country="Qatar",
            neutral=False,
            source="unit-test",
            source_match_id="unit-test:1",
        )
        mappings = build_the_odds_api_event_mapping(payload, canonical_matches=[canonical_match])
        source_snapshot = MarketOddsSnapshot(
            match_id="the-odds-api:evt1",
            bookmaker="demo",
            captured_at="2022-11-29T12:00:00Z",
            home_odds=1.4,
            draw_odds=4.5,
            away_odds=8.0,
            source="unit-test",
        )

        remapped = remap_the_odds_api_snapshots_to_canonical([source_snapshot], mappings)

        self.assertEqual(len(remapped), 1)
        self.assertEqual(remapped[0].match_id, "match_qatar_netherlands")
        self.assertEqual(remapped[0].home_odds, 8.0)
        self.assertEqual(remapped[0].draw_odds, 4.5)
        self.assertEqual(remapped[0].away_odds, 1.4)


if __name__ == "__main__":
    unittest.main()
