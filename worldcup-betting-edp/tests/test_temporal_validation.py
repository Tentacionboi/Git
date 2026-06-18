import unittest

from worldcup_betting_edp.backtest import (
    LEAKAGE_RISK_HIGH,
    LEAKAGE_RISK_LOW,
    LEAKAGE_RISK_MEDIUM,
    TIMING_MODE_CLOSING_MARKET,
    TIMING_MODE_IN_PLAY,
    TIMING_MODE_PRE_MATCH,
    parse_timestamp,
    validate_odds_as_of_prediction,
)


class TemporalValidationTests(unittest.TestCase):
    def test_valid_pre_match_opening_odds_are_low_risk(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18T10:00:00+00:00",
            prediction_time="2026-06-18T12:00:00+00:00",
            kickoff_time="2026-06-18T15:00:00+00:00",
            odds_type="opening",
            mode=TIMING_MODE_PRE_MATCH,
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.leakage_risk, LEAKAGE_RISK_LOW)
        self.assertEqual(result.reasons, ())

    def test_pre_match_rejects_odds_after_prediction_time(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18T13:00:00+00:00",
            prediction_time="2026-06-18T12:00:00+00:00",
            kickoff_time="2026-06-18T15:00:00+00:00",
            odds_type="opening",
            mode=TIMING_MODE_PRE_MATCH,
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.leakage_risk, LEAKAGE_RISK_HIGH)
        self.assertIn("odds_captured_at is after prediction_time", result.reasons)

    def test_pre_match_rejects_closing_odds_by_default(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18T14:55:00+00:00",
            prediction_time="2026-06-18T12:00:00+00:00",
            kickoff_time="2026-06-18T15:00:00+00:00",
            odds_type="closing",
            mode=TIMING_MODE_PRE_MATCH,
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.leakage_risk, LEAKAGE_RISK_HIGH)
        self.assertIn("closing odds are not allowed for actionable pre_match validation", result.reasons)

    def test_closing_market_mode_is_valid_but_medium_risk(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18T14:55:00+00:00",
            kickoff_time="2026-06-18T15:00:00+00:00",
            odds_type="closing",
            mode=TIMING_MODE_CLOSING_MARKET,
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.leakage_risk, LEAKAGE_RISK_MEDIUM)

    def test_date_only_timestamps_are_medium_risk(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18",
            prediction_time="2026-06-18",
            kickoff_time="2026-06-18",
            odds_type="opening",
            mode=TIMING_MODE_PRE_MATCH,
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.leakage_risk, LEAKAGE_RISK_MEDIUM)
        self.assertIn("odds_captured_at has date-only precision", result.reasons)

    def test_in_play_rejects_prediction_before_kickoff(self) -> None:
        result = validate_odds_as_of_prediction(
            odds_captured_at="2026-06-18T14:00:00+00:00",
            prediction_time="2026-06-18T14:30:00+00:00",
            kickoff_time="2026-06-18T15:00:00+00:00",
            odds_type="live",
            mode=TIMING_MODE_IN_PLAY,
        )

        self.assertFalse(result.valid)
        self.assertIn("in_play prediction_time is before kickoff_time", result.reasons)

    def test_parse_timestamp_identifies_date_only(self) -> None:
        parsed = parse_timestamp("2026-06-18", field_name="example")

        self.assertTrue(parsed.date_only)


if __name__ == "__main__":
    unittest.main()
