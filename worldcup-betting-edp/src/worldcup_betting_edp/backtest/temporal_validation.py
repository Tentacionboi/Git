"""As-of timing validation for odds and prediction backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


TIMING_MODE_PRE_MATCH = "pre_match"
TIMING_MODE_CLOSING_MARKET = "closing_market"
TIMING_MODE_IN_PLAY = "in_play"
LEAKAGE_RISK_LOW = "low"
LEAKAGE_RISK_MEDIUM = "medium"
LEAKAGE_RISK_HIGH = "high"


@dataclass(frozen=True)
class ParsedTimestamp:
    """Parsed timestamp plus whether the source only had date precision."""

    value: datetime
    date_only: bool


@dataclass(frozen=True)
class TemporalValidationResult:
    """Result of as-of/no-leakage timing validation."""

    valid: bool
    leakage_risk: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready validation payload."""
        return {
            "valid": self.valid,
            "leakage_risk": self.leakage_risk,
            "reasons": list(self.reasons),
        }


def validate_odds_as_of_prediction(
    *,
    odds_captured_at: str,
    kickoff_time: str | None,
    prediction_time: str | None = None,
    odds_type: str = "unknown",
    mode: str = TIMING_MODE_PRE_MATCH,
    allow_closing: bool = False,
) -> TemporalValidationResult:
    """Validate that odds were available at the claimed prediction time."""
    if mode not in {TIMING_MODE_PRE_MATCH, TIMING_MODE_CLOSING_MARKET, TIMING_MODE_IN_PLAY}:
        raise ValueError("mode must be pre_match, closing_market, or in_play")

    reasons: list[str] = []
    invalid_reasons: list[str] = []
    odds_time = parse_timestamp(odds_captured_at, field_name="odds_captured_at")
    kickoff = parse_timestamp(kickoff_time, field_name="kickoff_time") if kickoff_time else None
    prediction = (
        parse_timestamp(prediction_time, field_name="prediction_time")
        if prediction_time
        else None
    )

    if odds_time.date_only:
        reasons.append("odds_captured_at has date-only precision")
    if kickoff is not None and kickoff.date_only:
        reasons.append("kickoff_time has date-only precision")
    if prediction is not None and prediction.date_only:
        reasons.append("prediction_time has date-only precision")

    normalized_odds_type = odds_type.strip().lower()
    if mode == TIMING_MODE_PRE_MATCH:
        if kickoff is None:
            invalid_reasons.append("pre_match validation requires kickoff_time")
        if prediction is None:
            invalid_reasons.append("pre_match validation requires prediction_time")
        if normalized_odds_type == "closing" and not allow_closing:
            invalid_reasons.append("closing odds are not allowed for actionable pre_match validation")
        if prediction is not None and _is_after(odds_time, prediction):
            invalid_reasons.append("odds_captured_at is after prediction_time")
        if kickoff is not None and prediction is not None and _is_after(prediction, kickoff):
            invalid_reasons.append("prediction_time is after kickoff_time")
        if kickoff is not None and _is_after(odds_time, kickoff):
            invalid_reasons.append("odds_captured_at is after kickoff_time")

    if mode == TIMING_MODE_CLOSING_MARKET:
        reasons.append("closing_market mode is a market-baseline comparison, not an early betting simulation")
        if kickoff is None:
            invalid_reasons.append("closing_market validation requires kickoff_time")
        elif _is_after(odds_time, kickoff):
            invalid_reasons.append("odds_captured_at is after kickoff_time")
        if prediction is not None and kickoff is not None and _is_after(prediction, kickoff):
            invalid_reasons.append("prediction_time is after kickoff_time")

    if mode == TIMING_MODE_IN_PLAY:
        reasons.append("in_play mode must not be mixed with pre_match model evaluation")
        if kickoff is None:
            invalid_reasons.append("in_play validation requires kickoff_time")
        if prediction is None:
            invalid_reasons.append("in_play validation requires prediction_time")
        if kickoff is not None and prediction is not None and _is_before(prediction, kickoff):
            invalid_reasons.append("in_play prediction_time is before kickoff_time")
        if prediction is not None and _is_after(odds_time, prediction):
            invalid_reasons.append("odds_captured_at is after prediction_time")

    if invalid_reasons:
        return TemporalValidationResult(
            valid=False,
            leakage_risk=LEAKAGE_RISK_HIGH,
            reasons=tuple(invalid_reasons + reasons),
        )

    return TemporalValidationResult(
        valid=True,
        leakage_risk=LEAKAGE_RISK_MEDIUM if reasons else LEAKAGE_RISK_LOW,
        reasons=tuple(reasons),
    )


def parse_timestamp(value: str | None, *, field_name: str) -> ParsedTimestamp:
    """Parse an ISO timestamp or YYYY-MM-DD date."""
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    text = value.strip()
    if len(text) == 10:
        try:
            return ParsedTimestamp(datetime.strptime(text, "%Y-%m-%d"), True)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO datetime or YYYY-MM-DD date") from exc
    try:
        return ParsedTimestamp(datetime.fromisoformat(text.replace("Z", "+00:00")), False)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO datetime or YYYY-MM-DD date") from exc


def _is_after(left: ParsedTimestamp, right: ParsedTimestamp) -> bool:
    if left.date_only or right.date_only:
        return left.value.date() > right.value.date()
    return left.value > right.value


def _is_before(left: ParsedTimestamp, right: ParsedTimestamp) -> bool:
    if left.date_only or right.date_only:
        return left.value.date() < right.value.date()
    return left.value < right.value
