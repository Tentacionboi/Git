from pathlib import Path
import unittest

from worldcup_betting_edp.data import (
    load_prediction_input_mapping,
    load_prediction_input_path,
    load_prediction_input_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PredictionInputTests(unittest.TestCase):
    def test_loads_demo_json_file(self) -> None:
        prediction_input = load_prediction_input_path(PROJECT_ROOT / "examples" / "demo_single_match.json")

        self.assertEqual(prediction_input.match.match_id, "demo-2026-final")
        self.assertEqual(prediction_input.match.home_team, "Team A")
        self.assertEqual(prediction_input.odds_snapshot.bookmaker, "demo_book")
        self.assertEqual(prediction_input.model_probabilities.model_name, "manual_research_model")
        self.assertAlmostEqual(prediction_input.model_probabilities.probabilities["home"], 0.49)

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            load_prediction_input_text("{not-json")

    def test_rejects_missing_required_block(self) -> None:
        with self.assertRaisesRegex(ValueError, "odds must be an object"):
            load_prediction_input_mapping(
                {
                    "match": {
                        "match_id": "m1",
                        "match_time": "2026-07-19T15:00:00Z",
                        "home_team": "A",
                        "away_team": "B",
                    },
                    "model": {
                        "model_name": "manual",
                        "home": 0.4,
                        "draw": 0.3,
                        "away": 0.3,
                    },
                }
            )

    def test_rejects_probability_sum_not_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "probabilities must sum to 1.0"):
            load_prediction_input_mapping(
                {
                    "match": {
                        "match_id": "m1",
                        "match_time": "2026-07-19T15:00:00Z",
                        "home_team": "A",
                        "away_team": "B",
                    },
                    "odds": {
                        "captured_at": "2026-06-18T07:32:42Z",
                        "bookmaker": "demo",
                        "home": 2.0,
                        "draw": 3.4,
                        "away": 4.0,
                    },
                    "model": {
                        "model_name": "bad",
                        "home": 0.5,
                        "draw": 0.3,
                        "away": 0.3,
                    },
                }
            )

    def test_rejects_mismatched_model_match_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "model.match_id must match"):
            load_prediction_input_mapping(
                {
                    "match": {
                        "match_id": "m1",
                        "match_time": "2026-07-19T15:00:00Z",
                        "home_team": "A",
                        "away_team": "B",
                    },
                    "odds": {
                        "captured_at": "2026-06-18T07:32:42Z",
                        "bookmaker": "demo",
                        "home": 2.0,
                        "draw": 3.4,
                        "away": 4.0,
                    },
                    "model": {
                        "match_id": "other",
                        "model_name": "manual",
                        "home": 0.4,
                        "draw": 0.3,
                        "away": 0.3,
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
