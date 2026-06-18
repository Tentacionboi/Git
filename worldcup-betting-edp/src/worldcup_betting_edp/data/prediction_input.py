"""JSON input contract for single-match predictions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot


@dataclass(frozen=True)
class PredictionInput:
    """Parsed single-match prediction input."""

    match: Match
    odds_snapshot: OddsSnapshot
    model_probabilities: ModelProbabilities


def load_prediction_input_path(path: str | Path) -> PredictionInput:
    """Load a single-match prediction input from a JSON file path."""
    return load_prediction_input_text(Path(path).read_text(encoding="utf-8"))


def load_prediction_input_text(text: str) -> PredictionInput:
    """Load a single-match prediction input from JSON text."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    return load_prediction_input_mapping(raw)


def load_prediction_input_mapping(raw: Mapping[str, Any]) -> PredictionInput:
    """Load a single-match prediction input from a decoded JSON mapping."""
    root = _require_mapping(raw, "root")
    match_raw = _require_mapping(root.get("match"), "match")
    odds_raw = _require_mapping(root.get("odds"), "odds")
    model_raw = _require_mapping(root.get("model"), "model")

    match_id = _require_str(match_raw.get("match_id"), "match.match_id")
    match = Match(
        match_id=match_id,
        match_time=_parse_datetime(
            _require_str(match_raw.get("match_time"), "match.match_time"),
            "match.match_time",
        ),
        home_team=_require_str(match_raw.get("home_team"), "match.home_team"),
        away_team=_require_str(match_raw.get("away_team"), "match.away_team"),
        competition=_optional_str(match_raw.get("competition"), "match.competition", "FIFA World Cup"),
        stage=_optional_str(match_raw.get("stage"), "match.stage", "unknown"),
        neutral=_optional_bool(match_raw.get("neutral"), "match.neutral", True),
    )

    odds_match_id = _optional_str(odds_raw.get("match_id"), "odds.match_id", match_id)
    if odds_match_id != match_id:
        raise ValueError("odds.match_id must match match.match_id")
    odds_snapshot = OddsSnapshot(
        match_id=match_id,
        captured_at=_parse_datetime(
            _require_str(odds_raw.get("captured_at"), "odds.captured_at"),
            "odds.captured_at",
        ),
        bookmaker=_require_str(odds_raw.get("bookmaker"), "odds.bookmaker"),
        home=_require_float(odds_raw.get("home"), "odds.home"),
        draw=_require_float(odds_raw.get("draw"), "odds.draw"),
        away=_require_float(odds_raw.get("away"), "odds.away"),
    )

    model_match_id = _optional_str(model_raw.get("match_id"), "model.match_id", match_id)
    if model_match_id != match_id:
        raise ValueError("model.match_id must match match.match_id")
    model_probabilities = ModelProbabilities.from_1x2(
        match_id=match_id,
        model_name=_require_str(model_raw.get("model_name"), "model.model_name"),
        home=_require_float(model_raw.get("home"), "model.home"),
        draw=_require_float(model_raw.get("draw"), "model.draw"),
        away=_require_float(model_raw.get("away"), "model.away"),
    )

    return PredictionInput(
        match=match,
        odds_snapshot=odds_snapshot,
        model_probabilities=model_probabilities,
    )


def _parse_datetime(value: str, field_name: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_str(value: object, field_name: str, default: str) -> str:
    if value is None:
        return default
    return _require_str(value, field_name)


def _optional_bool(value: object, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _require_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a number")
    return float(value)
