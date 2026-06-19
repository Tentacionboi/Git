from pathlib import Path
import unittest

from worldcup_betting_edp.backtest import run_batch_backtest, run_batch_backtest_path
from worldcup_betting_edp.data import load_backtest_manifest_path
from worldcup_betting_edp.models import ResidualEdgeConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "examples" / "demo_backtest_manifest.json"


class BatchRunnerTests(unittest.TestCase):
    def test_runs_demo_manifest_from_path(self) -> None:
        result = run_batch_backtest_path(MANIFEST, flat_stake=10.0, starting_bankroll=100.0)
        payload = result.to_dict()
        summary = payload["summary"]

        self.assertEqual(summary["entry_count"], 1)
        self.assertEqual(summary["match_ids"], ["demo-2026-final"])
        self.assertEqual(summary["flat_bet_count"], 1)
        self.assertEqual(summary["flat_hit_count"], 1)
        self.assertAlmostEqual(summary["flat_total_profit"], 12.0)
        self.assertAlmostEqual(summary["flat_roi"], 1.2)
        self.assertAlmostEqual(summary["mean_model_brier_score"], 0.3906)
        self.assertLess(summary["mean_model_brier_score"], summary["mean_market_brier_score"])
        self.assertLess(summary["mean_model_log_loss"], summary["mean_market_log_loss"])
        self.assertAlmostEqual(summary["kelly_final_bankroll"], 101.95)
        self.assertEqual(len(payload["reports"]), 1)
        self.assertEqual(len(payload["scored_predictions"]), 1)
        self.assertEqual(len(payload["flat_stake_settlements"]), 1)
        self.assertEqual(len(payload["kelly_curve"]["points"]), 1)

    def test_runs_loaded_manifest(self) -> None:
        manifest = load_backtest_manifest_path(MANIFEST)
        result = run_batch_backtest(manifest, flat_stake=5.0, starting_bankroll=50.0)

        self.assertEqual(result.summary()["entry_count"], 1)
        self.assertAlmostEqual(result.summary()["flat_total_profit"], 6.0)
        self.assertAlmostEqual(result.kelly_curve.final_bankroll, 50.975)

    def test_runs_batch_backtest_with_market_residual_probabilities(self) -> None:
        manifest = load_backtest_manifest_path(MANIFEST)

        result = run_batch_backtest(
            manifest,
            flat_stake=10.0,
            starting_bankroll=100.0,
            use_market_residual_model=True,
            residual_config=ResidualEdgeConfig(
                fundamental_gap_weight=0.25,
                max_abs_adjustment_per_outcome=0.05,
            ),
        )
        payload = result.to_dict()
        summary = payload["summary"]

        self.assertEqual(summary["probability_model_mode"], "market_residual")
        self.assertEqual(payload["reports"][0]["probability_model_mode"], "market_residual")
        self.assertEqual(len(payload["fundamental_scores"]), 1)
        self.assertIsNotNone(summary["mean_fundamental_brier_score"])
        self.assertIsNotNone(summary["mean_fundamental_log_loss"])
        self.assertIn("model_beats_fundamental_brier_count", summary)
        self.assertLess(
            payload["reports"][0]["model_home_prob"],
            payload["reports"][0]["fundamental_home_prob"],
        )

    def test_rejects_non_positive_flat_stake(self) -> None:
        manifest = load_backtest_manifest_path(MANIFEST)

        with self.assertRaisesRegex(ValueError, "flat_stake must be positive"):
            run_batch_backtest(manifest, flat_stake=0.0)


if __name__ == "__main__":
    unittest.main()
