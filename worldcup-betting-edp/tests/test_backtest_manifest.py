from pathlib import Path
import unittest

from worldcup_betting_edp.data import (
    load_backtest_manifest_mapping,
    load_backtest_manifest_path,
    load_backtest_manifest_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
MANIFEST = EXAMPLES / "demo_backtest_manifest.json"


class BacktestManifestTests(unittest.TestCase):
    def test_loads_demo_manifest(self) -> None:
        manifest = load_backtest_manifest_path(MANIFEST)
        row = manifest.to_dict()

        self.assertEqual(row["entry_count"], 1)
        self.assertEqual(row["match_ids"], ["demo-2026-final"])
        self.assertEqual(row["entries"][0]["label"], "demo-final")
        self.assertEqual(manifest.entries[0].prediction_input.match.match_id, "demo-2026-final")
        self.assertEqual(manifest.entries[0].settled_result.result_1x2, "home")

    def test_loads_manifest_text_with_base_dir(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        manifest = load_backtest_manifest_text(text, base_dir=EXAMPLES)

        self.assertEqual(manifest.match_ids, ["demo-2026-final"])

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            load_backtest_manifest_text("{not-json", base_dir=EXAMPLES)

    def test_rejects_empty_entries(self) -> None:
        with self.assertRaisesRegex(ValueError, "entries cannot be empty"):
            load_backtest_manifest_mapping({"entries": []}, base_dir=EXAMPLES)

    def test_rejects_missing_entries_array(self) -> None:
        with self.assertRaisesRegex(ValueError, "entries must be an array"):
            load_backtest_manifest_mapping({}, base_dir=EXAMPLES)

    def test_rejects_duplicate_match_ids(self) -> None:
        entry = {
            "prediction_path": "demo_single_match.json",
            "settled_result_path": "demo_settled_match.json",
        }

        with self.assertRaisesRegex(ValueError, "duplicate match_id"):
            load_backtest_manifest_mapping({"entries": [entry, entry]}, base_dir=EXAMPLES)

    def test_rejects_mismatched_pair_match_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "match_id must match"):
            load_backtest_manifest_mapping(
                {
                    "entries": [
                        {
                            "prediction_path": "demo_single_match.json",
                            "settled_result_path": str(
                                PROJECT_ROOT / "tests" / "fixtures" / "settled_other_match.json"
                            ),
                        }
                    ]
                },
                base_dir=EXAMPLES,
            )


if __name__ == "__main__":
    unittest.main()
