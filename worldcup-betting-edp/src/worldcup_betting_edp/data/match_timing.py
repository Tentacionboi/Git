"""Kickoff-time data for as-of World Cup odds validation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


MATCH_TIMING_COLUMNS = (
    "match_id",
    "kickoff_time",
    "time_zone",
    "precision",
    "source",
)


@dataclass(frozen=True)
class MatchTiming:
    """Kickoff timestamp metadata for one match."""

    match_id: str
    kickoff_time: str
    time_zone: str = "UTC"
    precision: str = "datetime"
    source: str = "unknown"

    def __post_init__(self) -> None:
        if not self.match_id:
            raise ValueError("match_id cannot be empty")
        if not self.kickoff_time:
            raise ValueError("kickoff_time cannot be empty")
        if not self.time_zone:
            raise ValueError("time_zone cannot be empty")
        if self.precision not in {"datetime", "date"}:
            raise ValueError("precision must be datetime or date")
        if not self.source:
            raise ValueError("source cannot be empty")
        _validate_iso_datetime_or_date(self.kickoff_time)

    def to_dict(self) -> dict[str, object]:
        """Return a CSV/JSON-ready row."""
        return {
            "match_id": self.match_id,
            "kickoff_time": self.kickoff_time,
            "time_zone": self.time_zone,
            "precision": self.precision,
            "source": self.source,
        }


def load_match_timing_csv(path: str | Path) -> list[MatchTiming]:
    """Load match kickoff timestamps from a canonical CSV file."""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("match timing CSV must include a header row")
        missing = sorted(set(MATCH_TIMING_COLUMNS).difference(reader.fieldnames))
        if missing:
            raise ValueError(f"match timing CSV missing required columns: {missing}")
        return [_parse_match_timing_row(row, row_number=index + 2) for index, row in enumerate(reader)]


def write_match_timing_csv(
    timings: Iterable[MatchTiming],
    destination_path: str | Path,
) -> Path:
    """Write match kickoff timestamps to a canonical CSV file."""
    rows = list(timings)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MATCH_TIMING_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    return destination


def kickoff_time_by_match_id(timings: Iterable[MatchTiming]) -> dict[str, str]:
    """Return kickoff timestamp keyed by match id."""
    result: dict[str, str] = {}
    for timing in timings:
        if timing.match_id in result:
            raise ValueError(f"duplicate timing row for match_id: {timing.match_id}")
        result[timing.match_id] = timing.kickoff_time
    return result


def summarize_match_timing_coverage(
    *,
    match_ids: Iterable[str],
    timings: Iterable[MatchTiming],
) -> dict[str, object]:
    """Return coverage diagnostics for a set of match ids."""
    requested_ids = set(match_ids)
    timing_by_id = {timing.match_id: timing for timing in timings}
    covered_ids = requested_ids.intersection(timing_by_id)
    datetime_precision_count = sum(
        1 for match_id in covered_ids if timing_by_id[match_id].precision == "datetime"
    )
    date_precision_count = sum(
        1 for match_id in covered_ids if timing_by_id[match_id].precision == "date"
    )
    total = len(requested_ids)
    return {
        "match_count": total,
        "timing_count": len(timing_by_id),
        "covered_match_count": len(covered_ids),
        "missing_match_count": total - len(covered_ids),
        "coverage_ratio": len(covered_ids) / total if total else 0.0,
        "datetime_precision_count": datetime_precision_count,
        "date_precision_count": date_precision_count,
    }


def _parse_match_timing_row(row: dict[str, str], *, row_number: int) -> MatchTiming:
    try:
        return MatchTiming(
            match_id=_required(row, "match_id"),
            kickoff_time=_required(row, "kickoff_time"),
            time_zone=_required(row, "time_zone"),
            precision=_required(row, "precision"),
            source=_required(row, "source"),
        )
    except ValueError as exc:
        raise ValueError(f"invalid match timing row {row_number}") from exc


def _required(row: dict[str, str], field_name: str) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _validate_iso_datetime_or_date(value: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
        return
    except ValueError:
        pass
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("kickoff_time must be an ISO datetime or YYYY-MM-DD date") from exc
