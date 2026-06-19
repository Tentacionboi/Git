import unittest

from worldcup_betting_edp.evidence import (
    EVIDENCE_AVAILABLE,
    EVIDENCE_MISSING,
    EVIDENCE_SYNTHETIC,
    EvidenceItem,
    build_confidence_report,
)


class EvidenceTests(unittest.TestCase):
    def test_confidence_penalizes_missing_and_synthetic_inputs(self) -> None:
        report = build_confidence_report(
            [
                EvidenceItem(name="elo", status=EVIDENCE_AVAILABLE, source="model"),
                EvidenceItem(name="lineup", status=EVIDENCE_MISSING, source="not_configured"),
                EvidenceItem(name="odds", status=EVIDENCE_SYNTHETIC, source="demo"),
            ],
            base_score=0.90,
        )

        self.assertEqual(report.level, "medium")
        self.assertAlmostEqual(report.score, 0.58)
        self.assertEqual(len(report.penalties), 2)

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceItem(name="bad", status="made_up")


if __name__ == "__main__":
    unittest.main()
