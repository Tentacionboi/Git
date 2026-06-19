from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.cli import main, run_backtest, run_prediction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_INPUT = PROJECT_ROOT / "examples" / "demo_single_match.json"
DEMO_MANIFEST = PROJECT_ROOT / "examples" / "demo_backtest_manifest.json"


class CliTests(unittest.TestCase):
    def test_run_prediction_returns_flat_report(self) -> None:
        row = run_prediction(input_path=DEMO_INPUT)

        self.assertEqual(row["match_id"], "demo-2026-final")
        self.assertEqual(row["value_bet_direction"], "home")
        self.assertAlmostEqual(row["expected_value"], 0.078)

    def test_run_prediction_can_use_market_residual_mode(self) -> None:
        row = run_prediction(input_path=DEMO_INPUT, use_market_residual_model=True)

        self.assertEqual(row["probability_model_mode"], "market_residual")
        self.assertEqual(row["model_name"], "market_residual_mvp")
        self.assertEqual(row["fundamental_model_name"], "manual_research_model")

    def test_main_outputs_json(self) -> None:
        output = StringIO()
        exit_code = main(["--input", str(DEMO_INPUT)], stdout=output)

        self.assertEqual(exit_code, 0)
        row = json.loads(output.getvalue())
        self.assertEqual(row["match_id"], "demo-2026-final")
        self.assertEqual(row["bookmaker"], "demo_book")

    def test_main_outputs_csv(self) -> None:
        output = StringIO()
        exit_code = main(["--input", str(DEMO_INPUT), "--format", "csv"], stdout=output)

        self.assertEqual(exit_code, 0)
        csv_text = output.getvalue()
        self.assertIn("match_id", csv_text)
        self.assertIn("demo-2026-final", csv_text)

    def test_main_writes_single_match_json_output_file(self) -> None:
        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nested" / "single_match.json"
            exit_code = main(
                ["--input", str(DEMO_INPUT), "--output", str(output_path)],
                stdout=output,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue(), "")
            row = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(row["match_id"], "demo-2026-final")

    def test_main_returns_error_for_invalid_input(self) -> None:
        output = StringIO()
        error_output = StringIO()
        exit_code = main(
            ["--input", str(PROJECT_ROOT / "missing.json")],
            stdout=output,
            stderr=error_output,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("missing.json", error_output.getvalue())

    def test_run_backtest_returns_batch_payload(self) -> None:
        payload = run_backtest(manifest_path=DEMO_MANIFEST, flat_stake=10.0)

        self.assertEqual(payload["summary"]["entry_count"], 1)
        self.assertEqual(payload["summary"]["match_ids"], ["demo-2026-final"])
        self.assertAlmostEqual(payload["summary"]["flat_total_profit"], 12.0)
        self.assertIn("kelly_curve", payload)

    def test_main_outputs_batch_backtest_json(self) -> None:
        output = StringIO()
        exit_code = main(
            ["--manifest", str(DEMO_MANIFEST), "--flat-stake", "10"],
            stdout=output,
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["summary"]["entry_count"], 1)
        self.assertAlmostEqual(payload["summary"]["flat_total_profit"], 12.0)
        self.assertEqual(payload["manifest"]["match_ids"], ["demo-2026-final"])

    def test_main_outputs_batch_backtest_json_with_market_residual(self) -> None:
        output = StringIO()
        exit_code = main(
            ["--manifest", str(DEMO_MANIFEST), "--market-residual"],
            stdout=output,
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["summary"]["probability_model_mode"], "market_residual")
        self.assertEqual(len(payload["fundamental_scores"]), 1)

    def test_main_writes_batch_backtest_json_output_file(self) -> None:
        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "reports" / "demo_backtest_result.json"
            exit_code = main(
                [
                    "--manifest",
                    str(DEMO_MANIFEST),
                    "--flat-stake",
                    "10",
                    "--output",
                    str(output_path),
                ],
                stdout=output,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue(), "")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["entry_count"], 1)
            self.assertAlmostEqual(payload["summary"]["flat_total_profit"], 12.0)

    def test_main_rejects_csv_for_batch_backtest(self) -> None:
        output = StringIO()
        error_output = StringIO()
        exit_code = main(
            ["--manifest", str(DEMO_MANIFEST), "--format", "csv"],
            stdout=output,
            stderr=error_output,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("only supported with --input", error_output.getvalue())

    def test_main_returns_error_for_invalid_manifest(self) -> None:
        output = StringIO()
        error_output = StringIO()
        exit_code = main(
            ["--manifest", str(PROJECT_ROOT / "missing_manifest.json")],
            stdout=output,
            stderr=error_output,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("missing_manifest.json", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
