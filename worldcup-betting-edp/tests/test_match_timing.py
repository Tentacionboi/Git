from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.data import (
    MATCH_TIMING_COLUMNS,
    MatchTiming,
    kickoff_time_by_match_id,
    load_match_timing_csv,
    summarize_match_timing_coverage,
    write_match_timing_csv,
)


class MatchTimingTests(unittest.TestCase):
    def test_match_timing_to_dict_has_expected_columns(self) -> None:
        timing = MatchTiming(
            match_id="m1",
            kickoff_time="2026-06-18T15:00:00+00:00",
            source="unit-test",
        )

        self.assertEqual(tuple(timing.to_dict().keys()), MATCH_TIMING_COLUMNS)

    def test_rejects_invalid_precision(self) -> None:
        with self.assertRaises(ValueError):
            MatchTiming(
                match_id="m1",
                kickoff_time="2026-06-18T15:00:00+00:00",
                precision="minute",
                source="unit-test",
            )

    def test_writes_and_loads_match_timing_csv(self) -> None:
        timings = [
            MatchTiming(
                match_id="m1",
                kickoff_time="2026-06-18T15:00:00+00:00",
                source="unit-test",
            )
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "timing.csv"
            written = write_match_timing_csv(timings, path)
            loaded = load_match_timing_csv(written)

            self.assertEqual(written, path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].match_id, "m1")

    def test_kickoff_time_by_match_id_rejects_duplicates(self) -> None:
        timings = [
            MatchTiming(match_id="m1", kickoff_time="2026-06-18", precision="date"),
            MatchTiming(match_id="m1", kickoff_time="2026-06-19", precision="date"),
        ]

        with self.assertRaises(ValueError):
            kickoff_time_by_match_id(timings)

    def test_summarizes_match_timing_coverage(self) -> None:
        timings = [
            MatchTiming(
                match_id="m1",
                kickoff_time="2026-06-18T15:00:00+00:00",
                precision="datetime",
            ),
            MatchTiming(
                match_id="m2",
                kickoff_time="2026-06-19",
                precision="date",
            ),
        ]

        summary = summarize_match_timing_coverage(
            match_ids=["m1", "m2", "m3"],
            timings=timings,
        )

        self.assertEqual(summary["match_count"], 3)
        self.assertEqual(summary["covered_match_count"], 2)
        self.assertEqual(summary["missing_match_count"], 1)
        self.assertAlmostEqual(summary["coverage_ratio"], 2 / 3)
        self.assertEqual(summary["datetime_precision_count"], 1)
        self.assertEqual(summary["date_precision_count"], 1)


if __name__ == "__main__":
    unittest.main()
