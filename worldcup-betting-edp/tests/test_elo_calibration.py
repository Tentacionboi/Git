from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.backtest import (
    calibrate_elo_probability_config,
    filter_rating_history_by_date,
    write_elo_calibration_report_json,
)
from worldcup_betting_edp.data import build_canonical_matches_from_results, load_martj42_results_path
from worldcup_betting_edp.models import (
    EloProbabilityConfig,
    build_elo_probability_history,
    build_elo_rating_history,
)


SAMPLE_CSV = "tests/fixtures/martj42_results_sample.csv"


class EloCalibrationTests(unittest.TestCase):
    def test_calibrates_elo_probability_config_from_candidate_grid(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)
        candidates = [
            EloProbabilityConfig(base_draw_probability=0.20, min_draw_probability=0.08, max_draw_probability=0.40),
            EloProbabilityConfig(base_draw_probability=0.30, min_draw_probability=0.08, max_draw_probability=0.40),
        ]

        result = calibrate_elo_probability_config(
            history,
            model_name="demo_elo",
            candidate_configs=candidates,
        )

        self.assertEqual(result.model_name, "demo_elo")
        self.assertEqual(result.candidate_count, 2)
        self.assertIn(result.best_candidate.probability_config, candidates)
        self.assertGreater(result.best_candidate.summary.mean_log_loss, 0.0)

    def test_rejects_empty_calibration_history(self) -> None:
        with self.assertRaises(ValueError):
            calibrate_elo_probability_config([], model_name="empty")

    def test_filters_rating_history_by_date(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)

        filtered = filter_rating_history_by_date(
            history,
            start_date="2020-01-01",
            end_date="2023-12-31",
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].match_date, "2022-12-18")

    def test_writes_elo_calibration_report_json(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)
        result = calibrate_elo_probability_config(
            history,
            model_name="demo_elo",
            candidate_configs=[EloProbabilityConfig()],
        )
        full_sample_summary = result.best_candidate.summary

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "calibration.json"
            written = write_elo_calibration_report_json(
                result,
                path,
                full_sample_summary=full_sample_summary,
                notes=["unit test"],
            )

            self.assertEqual(written, path)
            payload = path.read_text(encoding="utf-8")
            self.assertIn('"model_name": "demo_elo"', payload)
            self.assertIn('"full_sample_summary"', payload)

    def test_calibrated_config_can_build_probability_history(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)
        result = calibrate_elo_probability_config(
            history,
            model_name="demo_elo",
            candidate_configs=[EloProbabilityConfig(base_draw_probability=0.30)],
        )

        probabilities = build_elo_probability_history(
            history,
            probability_config=result.best_candidate.probability_config,
        )

        self.assertEqual(len(probabilities), len(history))
        self.assertAlmostEqual(sum(probabilities[0].probabilities.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
