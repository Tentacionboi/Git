"""Evidence status and confidence scoring for prediction reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


EVIDENCE_AVAILABLE = "available"
EVIDENCE_MISSING = "missing"
EVIDENCE_PARTIAL = "partial"
EVIDENCE_STALE = "stale"
EVIDENCE_BLOCKED = "blocked"
EVIDENCE_SYNTHETIC = "synthetic"
EVIDENCE_UNVERIFIED = "unverified"
EVIDENCE_STATUSES = (
    EVIDENCE_AVAILABLE,
    EVIDENCE_MISSING,
    EVIDENCE_PARTIAL,
    EVIDENCE_STALE,
    EVIDENCE_BLOCKED,
    EVIDENCE_SYNTHETIC,
    EVIDENCE_UNVERIFIED,
)

CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

DEFAULT_CONFIDENCE_PENALTIES = {
    EVIDENCE_AVAILABLE: 0.0,
    EVIDENCE_PARTIAL: 0.08,
    EVIDENCE_STALE: 0.10,
    EVIDENCE_MISSING: 0.12,
    EVIDENCE_UNVERIFIED: 0.15,
    EVIDENCE_SYNTHETIC: 0.20,
    EVIDENCE_BLOCKED: 0.25,
}


@dataclass(frozen=True)
class EvidenceItem:
    """Status for one model input or data module."""

    name: str
    status: str
    source: str = "unknown"
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("evidence item name cannot be empty")
        if self.status not in EVIDENCE_STATUSES:
            raise ValueError(f"unsupported evidence status: {self.status!r}")
        if not self.source:
            raise ValueError("evidence item source cannot be empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "source": self.source,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ConfidenceReport:
    """Confidence score for one prediction, separate from probability."""

    score: float
    level: str
    penalties: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        if self.score < 0.0 or self.score > 1.0:
            raise ValueError("confidence score must be in [0, 1]")
        if self.level not in {CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH}:
            raise ValueError("unsupported confidence level")

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "level": self.level,
            "penalties": list(self.penalties),
            "evidence": [item.to_dict() for item in self.evidence],
        }


def build_confidence_report(
    evidence: Sequence[EvidenceItem],
    *,
    base_score: float = 0.90,
    extra_penalties: Sequence[str] = (),
    penalty_weights: Mapping[str, float] | None = None,
) -> ConfidenceReport:
    """Build a confidence report from evidence statuses.

    Evidence status changes confidence only. It does not modify team strength or
    predicted probabilities.
    """
    if base_score < 0.0 or base_score > 1.0:
        raise ValueError("base_score must be in [0, 1]")
    weights = dict(DEFAULT_CONFIDENCE_PENALTIES)
    if penalty_weights is not None:
        weights.update(penalty_weights)

    penalty_messages: list[str] = list(extra_penalties)
    score = base_score
    for item in evidence:
        penalty = weights[item.status]
        if penalty <= 0.0:
            continue
        score -= penalty
        message = f"{item.name} {item.status}"
        if item.detail:
            message = f"{message}: {item.detail}"
        penalty_messages.append(message)
    score = max(0.0, min(1.0, score))
    return ConfidenceReport(
        score=score,
        level=confidence_level(score),
        penalties=tuple(penalty_messages),
        evidence=tuple(evidence),
    )


def confidence_level(score: float) -> str:
    """Return low/medium/high confidence label for a score."""
    if score >= 0.75:
        return CONFIDENCE_HIGH
    if score >= 0.50:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW
