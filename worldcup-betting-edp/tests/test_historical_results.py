from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from worldcup_betting_edp.data import (
    MARTJ42_RESULTS_URL,
    download_martj42_results,
    filter_world_cup_results,
    load_martj42_results_path,
    load_martj42_results_text,
    summarize_results,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = PROJECT_ROOT / "tests" / "fixtures" / "martj42_results_sample.csv"


class HistoricalResultsTests(unittest.TestCase):
    def test_loads_martj42_results_sample(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].match_date.isoformat(), "1930-07-13")
        self.assertEqual(results[0].home_team, "France")
        self.assertEqual(results[0].away_team, "Mexico")
        self.assertEqual(results[0].result_1x2, "home")
        self.assertEqual(results[2].result_1x2, "draw")
        self.assertEqual(results[3].result_1x2, "away")
        self.assertEqual(results[0].total_goals, 5)
        self.assertTrue(results[0].neutral)
        self.assertFalse(results[3].neutral)

    def test_filters_world_cup_results(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        world_cup_results = filter_world_cup_results(results)

        self.assertEqual(len(world_cup_results), 3)
        self.assertTrue(all(row.tournament == "FIFA World Cup" for row in world_cup_results))

    def test_summarizes_results(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        summary = summarize_results(results)

        self.assertEqual(summary["match_count"], 4)
        self.assertEqual(summary["first_date"], "1930-07-13")
        self.assertEqual(summary["last_date"], "2024-06-01")
        self.assertEqual(summary["team_count"], 7)
        self.assertEqual(summary["tournament_count"], 2)

    def test_rejects_missing_required_column(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            load_martj42_results_text("date,home_team\n2024-01-01,A\n")

    def test_rejects_invalid_neutral_value(self) -> None:
        bad_csv = SAMPLE_CSV.read_text(encoding="utf-8").replace("TRUE", "MAYBE", 1)

        with self.assertRaisesRegex(ValueError, "neutral must be TRUE or FALSE"):
            load_martj42_results_text(bad_csv)

    def test_skips_unplayed_rows_by_default(self) -> None:
        csv_text = (
            SAMPLE_CSV.read_text(encoding="utf-8")
            + "2026-06-11,Team A,Team B,NA,NA,FIFA World Cup,City,Country,TRUE\n"
        )

        results = load_martj42_results_text(csv_text)

        self.assertEqual(len(results), 4)

    def test_can_reject_unplayed_rows_in_strict_mode(self) -> None:
        csv_text = (
            SAMPLE_CSV.read_text(encoding="utf-8")
            + "2026-06-11,Team A,Team B,NA,NA,FIFA World Cup,City,Country,TRUE\n"
        )

        with self.assertRaisesRegex(ValueError, "invalid date or score"):
            load_martj42_results_text(csv_text, skip_unplayed=False)

    def test_download_writes_csv_and_metadata(self) -> None:
        class FakeResponse:
            def __init__(self):
                self._content = SAMPLE_CSV.read_bytes()
                self._offset = 0

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, size=-1):
                if size is None or size < 0:
                    size = len(self._content) - self._offset
                chunk = self._content[self._offset : self._offset + size]
                self._offset += len(chunk)
                return chunk

        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "results.csv"
            with patch("worldcup_betting_edp.data.historical_results.urlopen", return_value=FakeResponse()):
                written = download_martj42_results(destination)

            self.assertEqual(written, destination)
            self.assertTrue(destination.exists())
            self.assertTrue(destination.with_suffix(".csv.metadata.json").exists())
            self.assertIn("France,Mexico", destination.read_text(encoding="utf-8"))

    def test_source_url_is_raw_github_csv(self) -> None:
        self.assertIn("raw.githubusercontent.com", MARTJ42_RESULTS_URL)
        self.assertTrue(MARTJ42_RESULTS_URL.endswith("/results.csv"))


if __name__ == "__main__":
    unittest.main()
