"""JSON contract for settled historical match results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from worldcup_betting_edp.domain import OUTCOMES_1X2, OUTCOME_AWAY, OUTCOME_DRAW, OUTCOME_HOME


@dataclass(frozen=True)
class SettledResult:
    """A settled football match result for scoring one 1X2 prediction."""

    match_id: str
    settled_at: datetime
    home_goals: int
    away_goals: int
    result_1x2: str
    source: str = "manual"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if self.home_goals < 0:
            raise ValueError("home_goals must be non-negative")
        if self.away_goals < 0:
            raise ValueError("away_goals must be non-negative")
        if self.result_1x2 not in OUTCOMES_1X2:
            raise ValueError(f"result_1x2 must be one of {OUTCOMES_1X2}")

        inferred = infer_result_1x2(self.home_goals, self.away_goals)
        if self.result_1x2 != inferred:
            raise ValueError(
                f"result_1x2 {self.result_1x2!r} does not match score-derived result {inferred!r}"
            )

    @property
    def goal_difference(self) -> int:
        """Return home goals minus away goals."""
        return self.home_goals - self.away_goals

    def to_outcome_vector(self) -> dict[str, float]:
        """Return a one-hot 1X2 outcome vector for scoring metrics."""
        return {outcome: 1.0 if outcome == self.result_1x2 else 0.0 for outcome in OUTCOMES_1X2}


def infer_result_1x2(home_goals: int, away_goals: int) -> str:
    """Infer the canonical 1X2 result from a final score."""
    if home_goals > away_goals:
        return OUTCOME_HOME
    if home_goals < away_goals:
        return OUTCOME_AWAY
    return OUTCOME_DRAW


def load_settled_result_path(path: str | Path) -> SettledResult:
    """Load a settled result from a JSON file path."""
    return load_settled_result_text(Path(path).read_text(encoding="utf-8"))


def load_settled_result_text(text: str) -> SettledResult:
    """Load a settled result from JSON text."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    return load_settled_result_mapping(raw)


def load_settled_result_mapping(raw: Mapping[str, Any]) -> SettledResult:
    """Load a settled result from a decoded JSON mapping."""
    root = _require_mapping(raw, "root")
    return SettledResult(
        match_id=_require_str(root.get("match_id"), "match_id"),
        settled_at=_parse_datetime(_require_str(root.get("settled_at"), "settled_at"), "settled_at"),
        home_goals=_require_int(root.get("home_goals"), "home_goals"),
        away_goals=_require_int(root.get("away_goals"), "away_goals"),
        result_1x2=_require_str(root.get("result_1x2"), "result_1x2"),
        source=_optional_str(root.get("source"), "source", "manual"),
        notes=_optional_str(root.get("notes"), "notes", ""),
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


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value
