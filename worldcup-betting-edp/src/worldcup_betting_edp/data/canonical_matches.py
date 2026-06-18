"""Canonical historical match table construction."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from worldcup_betting_edp.data.historical_results import InternationalResult


CANONICAL_MATCH_COLUMNS = (
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "result_1x2",
    "total_goals",
    "tournament",
    "city",
    "country",
    "neutral",
    "source",
    "source_match_id",
)

WORLD_CUP_TOURNAMENT = "FIFA World Cup"


@dataclass(frozen=True)
class CanonicalMatch:
    """Canonical match row used by modeling and backtesting code."""

    match_id: str
    match_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    result_1x2: str
    total_goals: int
    tournament: str
    city: str
    country: str
    neutral: bool
    source: str
    source_match_id: str

    def to_dict(self) -> dict[str, object]:
        """Return a CSV/JSON-ready row."""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "result_1x2": self.result_1x2,
            "total_goals": self.total_goals,
            "tournament": self.tournament,
            "city": self.city,
            "country": self.country,
            "neutral": self.neutral,
            "source": self.source,
            "source_match_id": self.source_match_id,
        }


def build_canonical_matches_from_results(
    results: Iterable[InternationalResult],
    *,
    source: str = "martj42/international_results",
) -> list[CanonicalMatch]:
    """Build stable canonical rows from parsed international results."""
    rows = [
        _canonicalize_result(result, source=source, source_index=index)
        for index, result in enumerate(results)
    ]
    _validate_unique_match_ids(rows)
    return rows


def write_canonical_matches_csv(
    matches: Iterable[CanonicalMatch],
    destination_path: str | Path,
    *,
    source_raw_path: str | Path | None = None,
) -> Path:
    """Write canonical matches to CSV with metadata next to it."""
    rows = list(matches)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CANONICAL_MATCH_COLUMNS))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    dates = [row.match_date for row in rows]
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
        "source_raw_path": str(source_raw_path) if source_raw_path is not None else None,
        "columns": list(CANONICAL_MATCH_COLUMNS),
    }
    destination.with_suffix(destination.suffix + ".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def load_canonical_matches_csv(path: str | Path) -> list[CanonicalMatch]:
    """Load canonical matches from a processed CSV path."""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("canonical matches CSV must include a header row")
        missing = sorted(set(CANONICAL_MATCH_COLUMNS).difference(reader.fieldnames))
        if missing:
            raise ValueError(f"canonical matches CSV missing required columns: {missing}")
        return [_parse_canonical_row(row, row_number=index + 2) for index, row in enumerate(reader)]


def filter_world_cup_canonical_matches(
    matches: Iterable[CanonicalMatch],
) -> list[CanonicalMatch]:
    """Return only FIFA World Cup matches from canonical rows."""
    return [match for match in matches if match.tournament == WORLD_CUP_TOURNAMENT]


def summarize_canonical_matches(matches: Iterable[CanonicalMatch]) -> dict[str, object]:
    """Return lightweight diagnostics for canonical matches."""
    rows = list(matches)
    if not rows:
        return {
            "match_count": 0,
            "first_date": None,
            "last_date": None,
            "team_count": 0,
            "tournament_count": 0,
            "neutral_match_count": 0,
        }
    teams = {row.home_team for row in rows} | {row.away_team for row in rows}
    tournaments = {row.tournament for row in rows}
    dates = [row.match_date for row in rows]
    return {
        "match_count": len(rows),
        "first_date": min(dates),
        "last_date": max(dates),
        "team_count": len(teams),
        "tournament_count": len(tournaments),
        "neutral_match_count": sum(1 for row in rows if row.neutral),
    }


def _canonicalize_result(
    result: InternationalResult,
    *,
    source: str,
    source_index: int,
) -> CanonicalMatch:
    source_match_id = f"{source}:{source_index}"
    stable_key = "|".join(
        [
            result.match_date.isoformat(),
            result.home_team,
            result.away_team,
            str(result.home_score),
            str(result.away_score),
            result.tournament,
            result.city,
            result.country,
            str(result.neutral),
            source,
            str(source_index),
        ]
    )
    match_id = "match_" + hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:16]
    return CanonicalMatch(
        match_id=match_id,
        match_date=result.match_date.isoformat(),
        home_team=result.home_team,
        away_team=result.away_team,
        home_score=result.home_score,
        away_score=result.away_score,
        result_1x2=result.result_1x2,
        total_goals=result.total_goals,
        tournament=result.tournament,
        city=result.city,
        country=result.country,
        neutral=result.neutral,
        source=source,
        source_match_id=source_match_id,
    )


def _validate_unique_match_ids(rows: list[CanonicalMatch]) -> None:
    seen: set[str] = set()
    for row in rows:
        if row.match_id in seen:
            raise ValueError(f"duplicate canonical match_id: {row.match_id}")
        seen.add(row.match_id)


def _parse_canonical_row(row: dict[str, str], *, row_number: int) -> CanonicalMatch:
    try:
        home_score = int(_required(row, "home_score"))
        away_score = int(_required(row, "away_score"))
        total_goals = int(_required(row, "total_goals"))
    except ValueError as exc:
        raise ValueError(f"invalid score fields at canonical CSV row {row_number}") from exc

    neutral_raw = _required(row, "neutral").strip().lower()
    if neutral_raw not in {"true", "false"}:
        raise ValueError(f"neutral must be true or false at canonical CSV row {row_number}")

    return CanonicalMatch(
        match_id=_required(row, "match_id"),
        match_date=_required(row, "match_date"),
        home_team=_required(row, "home_team"),
        away_team=_required(row, "away_team"),
        home_score=home_score,
        away_score=away_score,
        result_1x2=_required(row, "result_1x2"),
        total_goals=total_goals,
        tournament=_required(row, "tournament"),
        city=_required(row, "city"),
        country=_required(row, "country"),
        neutral=neutral_raw == "true",
        source=_required(row, "source"),
        source_match_id=_required(row, "source_match_id"),
    )


def _required(row: dict[str, str], field_name: str) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()
