"""Historical international football result loading utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from http.client import IncompleteRead
import json
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


MARTJ42_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)


@dataclass(frozen=True)
class InternationalResult:
    """One historical men's international football result."""

    match_date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    tournament: str
    city: str
    country: str
    neutral: bool

    @property
    def result_1x2(self) -> str:
        """Return the canonical home/draw/away result."""
        if self.home_score > self.away_score:
            return "home"
        if self.home_score < self.away_score:
            return "away"
        return "draw"

    @property
    def total_goals(self) -> int:
        """Return total goals in the match."""
        return self.home_score + self.away_score

    def to_dict(self) -> dict[str, object]:
        """Return a flat row for downstream feature/model pipelines."""
        return {
            "date": self.match_date.isoformat(),
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
        }


def download_martj42_results(
    destination_path: str | Path,
    *,
    source_url: str = MARTJ42_RESULTS_URL,
    retries: int = 3,
) -> Path:
    """Download martj42 international results CSV and write source metadata."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    content = _download_bytes(source_url, retries=retries)

    destination.write_bytes(content)
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "source_url": source_url,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "license": "CC0-1.0 according to martj42/international_results repository",
                "notes": "Men's full international results. Scores include extra time, not penalty shootouts.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def _download_bytes(source_url: str, *, retries: int) -> bytes:
    if retries < 1:
        raise ValueError("retries must be at least 1")

    last_error: Exception | None = None
    for _attempt in range(retries):
        request = Request(source_url, headers={"User-Agent": "worldcup-betting-edp/0.1"})
        try:
            chunks: list[bytes] = []
            with urlopen(request, timeout=30) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return b"".join(chunks)
        except (OSError, IncompleteRead) as exc:
            last_error = exc

    assert last_error is not None
    raise last_error


def load_martj42_results_path(
    path: str | Path,
    *,
    skip_unplayed: bool = True,
) -> list[InternationalResult]:
    """Load martj42 results from a local CSV path."""
    return load_martj42_results_text(Path(path).read_text(encoding="utf-8"), skip_unplayed=skip_unplayed)


def load_martj42_results_text(
    text: str,
    *,
    skip_unplayed: bool = True,
) -> list[InternationalResult]:
    """Load martj42 results from CSV text."""
    reader = csv.DictReader(text.splitlines())
    required = {
        "date",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "tournament",
        "city",
        "country",
        "neutral",
    }
    if reader.fieldnames is None:
        raise ValueError("results CSV must include a header row")
    missing = sorted(required.difference(reader.fieldnames))
    if missing:
        raise ValueError(f"results CSV missing required columns: {missing}")

    results: list[InternationalResult] = []
    for index, row in enumerate(reader):
        row_number = index + 2
        if skip_unplayed and _has_missing_score(row):
            continue
        results.append(_parse_result_row(row, row_number=row_number))
    return results


def filter_tournament(
    results: Iterable[InternationalResult],
    tournament: str,
) -> list[InternationalResult]:
    """Return results from one tournament name."""
    return [result for result in results if result.tournament == tournament]


def filter_world_cup_results(results: Iterable[InternationalResult]) -> list[InternationalResult]:
    """Return FIFA World Cup final-tournament results."""
    return filter_tournament(results, "FIFA World Cup")


def summarize_results(results: Iterable[InternationalResult]) -> dict[str, object]:
    """Return lightweight dataset diagnostics."""
    rows = list(results)
    if not rows:
        return {
            "match_count": 0,
            "first_date": None,
            "last_date": None,
            "team_count": 0,
            "tournament_count": 0,
        }

    teams = {row.home_team for row in rows} | {row.away_team for row in rows}
    tournaments = {row.tournament for row in rows}
    dates = [row.match_date for row in rows]
    return {
        "match_count": len(rows),
        "first_date": min(dates).isoformat(),
        "last_date": max(dates).isoformat(),
        "team_count": len(teams),
        "tournament_count": len(tournaments),
    }


def _parse_result_row(row: dict[str, str], *, row_number: int) -> InternationalResult:
    try:
        match_date = date.fromisoformat(_required_text(row, "date"))
        home_score = int(_required_text(row, "home_score"))
        away_score = int(_required_text(row, "away_score"))
    except ValueError as exc:
        raise ValueError(f"invalid date or score at CSV row {row_number}") from exc

    if home_score < 0 or away_score < 0:
        raise ValueError(f"scores must be non-negative at CSV row {row_number}")

    return InternationalResult(
        match_date=match_date,
        home_team=_required_text(row, "home_team"),
        away_team=_required_text(row, "away_team"),
        home_score=home_score,
        away_score=away_score,
        tournament=_required_text(row, "tournament"),
        city=_required_text(row, "city"),
        country=_required_text(row, "country"),
        neutral=_parse_bool(_required_text(row, "neutral"), row_number=row_number),
    )


def _has_missing_score(row: dict[str, str]) -> bool:
    return _is_missing_score_value(row.get("home_score")) or _is_missing_score_value(row.get("away_score"))


def _is_missing_score_value(value: str | None) -> bool:
    return value is None or value.strip().upper() in {"", "NA", "N/A", "NULL"}


def _required_text(row: dict[str, str], field_name: str) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _parse_bool(value: str, *, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"neutral must be TRUE or FALSE at CSV row {row_number}")
