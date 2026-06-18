"""Batch backtest manifest contract."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from worldcup_betting_edp.data.prediction_input import PredictionInput, load_prediction_input_path
from worldcup_betting_edp.data.settled_result import SettledResult, load_settled_result_path


@dataclass(frozen=True)
class BacktestManifestEntry:
    """One ordered prediction/result pair in a batch backtest manifest."""

    label: str
    prediction_path: Path
    settled_result_path: Path
    prediction_input: PredictionInput
    settled_result: SettledResult

    @property
    def match_id(self) -> str:
        """Return the paired match id."""
        return self.prediction_input.match.match_id

    def to_dict(self) -> dict[str, Any]:
        """Return a manifest row for inspection."""
        return {
            "label": self.label,
            "match_id": self.match_id,
            "prediction_path": str(self.prediction_path),
            "settled_result_path": str(self.settled_result_path),
            "match_time": self.prediction_input.match.match_time.isoformat(),
            "settled_at": self.settled_result.settled_at.isoformat(),
        }


@dataclass(frozen=True)
class BacktestManifest:
    """Loaded ordered manifest for batch scoring and settlement."""

    entries: list[BacktestManifestEntry]
    source_path: Path | None = None

    @property
    def match_ids(self) -> list[str]:
        """Return match ids in manifest order."""
        return [entry.match_id for entry in self.entries]

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable manifest summary."""
        return {
            "source_path": str(self.source_path) if self.source_path else None,
            "entry_count": len(self.entries),
            "match_ids": self.match_ids,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def load_backtest_manifest_path(path: str | Path) -> BacktestManifest:
    """Load a backtest manifest from a JSON file path."""
    manifest_path = Path(path)
    return load_backtest_manifest_text(
        manifest_path.read_text(encoding="utf-8"),
        base_dir=manifest_path.parent,
        source_path=manifest_path,
    )


def load_backtest_manifest_text(
    text: str,
    *,
    base_dir: str | Path = ".",
    source_path: str | Path | None = None,
) -> BacktestManifest:
    """Load a backtest manifest from JSON text."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    return load_backtest_manifest_mapping(raw, base_dir=base_dir, source_path=source_path)


def load_backtest_manifest_mapping(
    raw: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
    source_path: str | Path | None = None,
) -> BacktestManifest:
    """Load a backtest manifest from a decoded JSON mapping."""
    root = _require_mapping(raw, "root")
    entries_raw = _require_sequence(root.get("entries"), "entries")
    if not entries_raw:
        raise ValueError("entries cannot be empty")

    base_path = Path(base_dir)
    entries: list[BacktestManifestEntry] = []
    seen_match_ids: set[str] = set()

    for index, entry_raw in enumerate(entries_raw):
        entry = _load_manifest_entry(entry_raw, base_path=base_path, index=index)
        if entry.match_id in seen_match_ids:
            raise ValueError(f"duplicate match_id in manifest: {entry.match_id}")
        seen_match_ids.add(entry.match_id)
        entries.append(entry)

    return BacktestManifest(
        entries=entries,
        source_path=Path(source_path) if source_path is not None else None,
    )


def _load_manifest_entry(
    raw: object,
    *,
    base_path: Path,
    index: int,
) -> BacktestManifestEntry:
    entry_raw = _require_mapping(raw, f"entries[{index}]")
    label = _optional_str(entry_raw.get("label"), f"entries[{index}].label", f"entry-{index + 1}")
    prediction_path = _resolve_path(
        _require_str(entry_raw.get("prediction_path"), f"entries[{index}].prediction_path"),
        base_path=base_path,
    )
    settled_result_path = _resolve_path(
        _require_str(entry_raw.get("settled_result_path"), f"entries[{index}].settled_result_path"),
        base_path=base_path,
    )

    prediction_input = load_prediction_input_path(prediction_path)
    settled_result = load_settled_result_path(settled_result_path)
    if prediction_input.match.match_id != settled_result.match_id:
        raise ValueError(
            "prediction and settled result match_id must match for "
            f"entries[{index}] ({prediction_input.match.match_id!r} != {settled_result.match_id!r})"
        )

    return BacktestManifestEntry(
        label=label,
        prediction_path=prediction_path,
        settled_result_path=settled_result_path,
        prediction_input=prediction_input,
        settled_result=settled_result,
    )


def _resolve_path(path_text: str, *, base_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return base_path / path


def _require_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be an array")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_str(value: object, field_name: str, default: str) -> str:
    if value is None:
        return default
    return _require_str(value, field_name)
