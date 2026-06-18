from pathlib import Path
import unittest

from worldcup_betting_edp.data import (
    SettledResult,
    infer_result_1x2,
    load_settled_result_mapping,
    load_settled_result_path,
    load_settled_result_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SettledResultTests(unittest.TestCase):
    def test_infers_1x2_result_from_score(self) -> None:
        self.assertEqual(infer_result_1x2(2, 1), "home")
        self.assertEqual(infer_result_1x2(1, 1), "draw")
        self.assertEqual(infer_result_1x2(0, 2), "away")

    def test_loads_demo_settled_result(self) -> None:
        result = load_settled_result_path(PROJECT_ROOT / "examples" / "demo_settled_match.json")

        self.assertEqual(result.match_id, "demo-2026-final")
        self.assertEqual(result.home_goals, 2)
        self.assertEqual(result.away_goals, 1)
        self.assertEqual(result.result_1x2, "home")
        self.assertEqual(result.goal_difference, 1)
        self.assertEqual(result.to_outcome_vector(), {"home": 1.0, "draw": 0.0, "away": 0.0})

    def test_result_rejects_score_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match score-derived result"):
            SettledResult(
                match_id="m1",
                settled_at=load_settled_result_path(
                    PROJECT_ROOT / "examples" / "demo_settled_match.json"
                ).settled_at,
                home_goals=0,
                away_goals=0,
                result_1x2="home",
            )

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            load_settled_result_text("{not-json")

    def test_rejects_negative_goals(self) -> None:
        with self.assertRaisesRegex(ValueError, "home_goals must be non-negative"):
            load_settled_result_mapping(
                {
                    "match_id": "m1",
                    "settled_at": "2026-07-19T18:00:00Z",
                    "home_goals": -1,
                    "away_goals": 0,
                    "result_1x2": "away",
                }
            )

    def test_rejects_non_integer_goals(self) -> None:
        with self.assertRaisesRegex(ValueError, "home_goals must be an integer"):
            load_settled_result_mapping(
                {
                    "match_id": "m1",
                    "settled_at": "2026-07-19T18:00:00Z",
                    "home_goals": 1.5,
                    "away_goals": 0,
                    "result_1x2": "home",
                }
            )


if __name__ == "__main__":
    unittest.main()
