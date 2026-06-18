from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.data import (
    CANONICAL_MATCH_COLUMNS,
    build_canonical_matches_from_results,
    load_canonical_matches_csv,
    load_martj42_results_path,
    summarize_canonical_matches,
    write_canonical_matches_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = PROJECT_ROOT / "tests" / "fixtures" / "martj42_results_sample.csv"


class CanonicalMatchesTests(unittest.TestCase):
    def test_builds_stable_canonical_matches(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        first_build = build_canonical_matches_from_results(results)
        second_build = build_canonical_matches_from_results(results)

        self.assertEqual(len(first_build), 4)
        self.assertEqual(first_build[0].match_id, second_build[0].match_id)
        self.assertTrue(first_build[0].match_id.startswith("match_"))
        self.assertEqual(first_build[0].match_date, "1930-07-13")
        self.assertEqual(first_build[0].result_1x2, "home")
        self.assertEqual(first_build[0].total_goals, 5)
        self.assertEqual(first_build[0].source, "martj42/international_results")
        self.assertIn("martj42/international_results:0", first_build[0].source_match_id)

    def test_canonical_match_to_dict_has_expected_columns(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        canonical = build_canonical_matches_from_results(results)[0]

        self.assertEqual(tuple(canonical.to_dict().keys()), CANONICAL_MATCH_COLUMNS)

    def test_writes_and_loads_canonical_csv(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        canonical = build_canonical_matches_from_results(results)

        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "matches.csv"
            written = write_canonical_matches_csv(canonical, destination, source_raw_path=SAMPLE_CSV)
            loaded = load_canonical_matches_csv(written)

            self.assertEqual(written, destination)
            self.assertTrue(destination.with_suffix(".csv.metadata.json").exists())
            self.assertEqual(len(loaded), 4)
            self.assertEqual(loaded[2].result_1x2, "draw")

    def test_summarizes_canonical_matches(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        canonical = build_canonical_matches_from_results(results)
        summary = summarize_canonical_matches(canonical)

        self.assertEqual(summary["match_count"], 4)
        self.assertEqual(summary["first_date"], "1930-07-13")
        self.assertEqual(summary["last_date"], "2024-06-01")
        self.assertEqual(summary["team_count"], 7)
        self.assertEqual(summary["tournament_count"], 2)
        self.assertEqual(summary["neutral_match_count"], 3)

    def test_rejects_canonical_csv_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "bad.csv"
            destination.write_text("match_id,match_date\nm1,2024-01-01\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required columns"):
                load_canonical_matches_csv(destination)


if __name__ == "__main__":
    unittest.main()
