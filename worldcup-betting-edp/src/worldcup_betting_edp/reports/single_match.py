"""Single-match prediction report for the 1X2 MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worldcup_betting_edp.betting import ValueBetDecision, evaluate_value_bet
from worldcup_betting_edp.domain import (
    OUTCOME_AWAY,
    OUTCOME_DRAW,
    OUTCOME_HOME,
    OUTCOMES_1X2,
    MarketProbabilities,
    Match,
    ModelProbabilities,
    OddsSnapshot,
)
from worldcup_betting_edp.evidence import (
    EVIDENCE_AVAILABLE,
    EVIDENCE_MISSING,
    EVIDENCE_SYNTHETIC,
    ConfidenceReport,
    EvidenceItem,
    build_confidence_report,
)
from worldcup_betting_edp.market import MarketMovementFeatures
from worldcup_betting_edp.models import (
    ContextAdjustedEloPrediction,
    EloBasePrediction,
    MarketBaselineModel,
    MarketResidualPrediction,
    ResidualEdgeConfig,
    build_market_residual_prediction,
)


@dataclass(frozen=True)
class PredictionReport:
    """Full single-match value-bet report."""

    match: Match
    odds_snapshot: OddsSnapshot
    market_probabilities: MarketProbabilities
    model_probabilities: ModelProbabilities
    decisions: dict[str, ValueBetDecision]
    fundamental_probabilities: ModelProbabilities | None = None
    residual_prediction: MarketResidualPrediction | None = None
    elo_base_prediction: EloBasePrediction | None = None
    context_prediction: ContextAdjustedEloPrediction | None = None
    evidence_items: tuple[EvidenceItem, ...] = ()
    confidence_report: ConfidenceReport | None = None

    @property
    def value_bets(self) -> list[ValueBetDecision]:
        """Return all positive value-bet decisions sorted by EV descending."""
        return sorted(
            [decision for decision in self.decisions.values() if decision.is_value_bet],
            key=lambda decision: decision.expected_value,
            reverse=True,
        )

    @property
    def best_value_bet(self) -> ValueBetDecision | None:
        """Return the best single value bet, if any."""
        value_bets = self.value_bets
        return value_bets[0] if value_bets else None

    def to_dict(self) -> dict[str, Any]:
        """Return a flat dictionary matching the MVP output contract."""
        best = self.best_value_bet
        market = self.market_probabilities.probabilities
        model = self.model_probabilities.probabilities
        odds = self.odds_snapshot.to_odds_map()

        row: dict[str, Any] = {
            "match_id": self.match.match_id,
            "match_time": self.match.match_time.isoformat(),
            "home_team": self.match.home_team,
            "away_team": self.match.away_team,
            "competition": self.match.competition,
            "stage": self.match.stage,
            "neutral": self.match.neutral,
            "bookmaker": self.odds_snapshot.bookmaker,
            "odds_captured_at": self.odds_snapshot.captured_at.isoformat(),
            "model_name": self.model_probabilities.model_name,
            "probability_model_mode": (
                "market_residual" if self.residual_prediction is not None else "direct_model"
            ),
            "market_home_odds": odds[OUTCOME_HOME],
            "market_draw_odds": odds[OUTCOME_DRAW],
            "market_away_odds": odds[OUTCOME_AWAY],
            "market_overround": self.market_probabilities.overround,
            "market_home_prob_devig": market[OUTCOME_HOME],
            "market_draw_prob_devig": market[OUTCOME_DRAW],
            "market_away_prob_devig": market[OUTCOME_AWAY],
            "model_home_prob": model[OUTCOME_HOME],
            "model_draw_prob": model[OUTCOME_DRAW],
            "model_away_prob": model[OUTCOME_AWAY],
            "delta_home": model[OUTCOME_HOME] - market[OUTCOME_HOME],
            "delta_draw": model[OUTCOME_DRAW] - market[OUTCOME_DRAW],
            "delta_away": model[OUTCOME_AWAY] - market[OUTCOME_AWAY],
            "value_bet_flag": best is not None,
            "value_bet_direction": best.outcome if best else None,
            "expected_value": best.expected_value if best else None,
            "fractional_kelly_fraction": best.sizing.capped_fraction if best else 0.0,
            "risk_level": best.risk_level.value if best else "no_bet",
            "reason": best.reason if best else self._no_bet_reason(),
        }

        if self.fundamental_probabilities is not None:
            fundamental = self.fundamental_probabilities.probabilities
            row.update(
                {
                    "fundamental_model_name": self.fundamental_probabilities.model_name,
                    "fundamental_home_prob": fundamental[OUTCOME_HOME],
                    "fundamental_draw_prob": fundamental[OUTCOME_DRAW],
                    "fundamental_away_prob": fundamental[OUTCOME_AWAY],
                }
            )

        if self.residual_prediction is not None:
            residual = self.residual_prediction
            row.update(
                {
                    "residual_home_adjustment": residual.residual_adjustments[OUTCOME_HOME],
                    "residual_draw_adjustment": residual.residual_adjustments[OUTCOME_DRAW],
                    "residual_away_adjustment": residual.residual_adjustments[OUTCOME_AWAY],
                    "movement_home_probability_delta": residual.movement_probability_deltas[
                        OUTCOME_HOME
                    ],
                    "movement_draw_probability_delta": residual.movement_probability_deltas[
                        OUTCOME_DRAW
                    ],
                    "movement_away_probability_delta": residual.movement_probability_deltas[
                        OUTCOME_AWAY
                    ],
                    "largest_residual_adjustment_outcome": residual.largest_adjustment_outcome,
                    "largest_residual_adjustment": residual.largest_adjustment,
                    "residual_fundamental_gap_weight": residual.config.fundamental_gap_weight,
                    "residual_market_movement_weight": residual.config.market_movement_weight,
                    "residual_max_abs_adjustment_per_outcome": (
                        residual.config.max_abs_adjustment_per_outcome
                    ),
                }
            )

        for outcome in OUTCOMES_1X2:
            decision = self.decisions[outcome]
            row[f"{outcome}_ev"] = decision.expected_value
            row[f"{outcome}_kelly_fraction"] = decision.sizing.capped_fraction
            row[f"{outcome}_decision_reason"] = decision.reason

        return row

    def to_structured_dict(self) -> dict[str, Any]:
        """Return a structured report while preserving flat `to_dict` compatibility."""
        market = self.market_probabilities.probabilities
        model = self.model_probabilities.probabilities
        odds = self.odds_snapshot.to_odds_map()
        alignment = market_alignment(model, market)
        confidence = self.confidence_report or build_confidence_report(
            self._default_evidence_items(alignment=alignment["level"])
        )
        return {
            "match": {
                "match_id": self.match.match_id,
                "match_time": self.match.match_time.isoformat(),
                "home_team": self.match.home_team,
                "away_team": self.match.away_team,
                "competition": self.match.competition,
                "stage": self.match.stage,
                "neutral": self.match.neutral,
            },
            "data_status": {
                item.name: item.to_dict() for item in confidence.evidence
            },
            "elo_base": (
                self.elo_base_prediction.to_dict()
                if self.elo_base_prediction is not None
                else {
                    "status": EVIDENCE_MISSING,
                    "detail": "elo base prediction not supplied to report",
                }
            ),
            "context_adjustments": (
                self.context_prediction.to_dict()
                if self.context_prediction is not None
                else {
                    "status": EVIDENCE_MISSING,
                    "detail": "context adjustment not supplied to report",
                }
            ),
            "fundamental_probabilities": (
                {
                    "model_name": self.fundamental_probabilities.model_name,
                    "probabilities": dict(self.fundamental_probabilities.probabilities),
                }
                if self.fundamental_probabilities is not None
                else {
                    "model_name": self.model_probabilities.model_name,
                    "probabilities": dict(self.model_probabilities.probabilities),
                }
            ),
            "goal_model": {
                "status": EVIDENCE_MISSING,
                "detail": "Poisson score matrix not implemented in phase 1",
            },
            "market": {
                "odds": dict(odds),
                "bookmaker": self.odds_snapshot.bookmaker,
                "captured_at": self.odds_snapshot.captured_at.isoformat(),
                "overround": self.market_probabilities.overround,
                "devig_probabilities": dict(market),
                "alignment": alignment,
                "movement": {
                    "status": EVIDENCE_MISSING,
                    "detail": "market movement features not supplied to report",
                },
            },
            "residual_final": (
                self.residual_prediction.to_dict()
                if self.residual_prediction is not None
                else {
                    "status": EVIDENCE_MISSING,
                    "detail": "market residual model not used",
                    "probabilities": dict(model),
                }
            ),
            "confidence": confidence.to_dict(),
            "value_bet_decision": {
                "has_value_bet": self.best_value_bet is not None,
                "best": self.best_value_bet.to_dict() if self.best_value_bet is not None else None,
                "by_outcome": {
                    outcome: self.decisions[outcome].to_dict() for outcome in OUTCOMES_1X2
                },
            },
            "flat_compat": self.to_dict(),
        }

    def _no_bet_reason(self) -> str:
        """Summarize why no outcome passed the value-bet rule."""
        reasons = [self.decisions[outcome].reason for outcome in OUTCOMES_1X2]
        return " | ".join(reasons)

    def _default_evidence_items(self, *, alignment: str) -> tuple[EvidenceItem, ...]:
        items = list(self.evidence_items)
        if not any(item.name == "odds" for item in items):
            items.append(
                EvidenceItem(
                    name="odds",
                    status=EVIDENCE_AVAILABLE,
                    source=self.odds_snapshot.bookmaker,
                    detail="timestamped 1X2 odds snapshot",
                )
            )
        if not any(item.name == "model_probabilities" for item in items):
            items.append(
                EvidenceItem(
                    name="model_probabilities",
                    status=EVIDENCE_AVAILABLE,
                    source=self.model_probabilities.model_name,
                    detail="single-match probability vector supplied",
                )
            )
        if self.elo_base_prediction is None and not any(item.name == "elo" for item in items):
            items.append(
                EvidenceItem(
                    name="elo",
                    status=EVIDENCE_MISSING,
                    source="report",
                    detail="elo diagnostics not supplied",
                )
            )
        if self.context_prediction is None and not any(item.name == "context" for item in items):
            items.append(
                EvidenceItem(
                    name="context",
                    status=EVIDENCE_MISSING,
                    source="report",
                    detail="context adjustment not supplied",
                )
            )
        if self.odds_snapshot.bookmaker.startswith("demo"):
            items.append(
                EvidenceItem(
                    name="odds_realism",
                    status=EVIDENCE_SYNTHETIC,
                    source=self.odds_snapshot.bookmaker,
                    detail="demo bookmaker suggests synthetic odds",
                )
            )
        if alignment == MARKET_ALIGNMENT_STRONG_DIVERGENCE:
            items.append(
                EvidenceItem(
                    name="market_divergence",
                    status="partial",
                    source="model_vs_market_delta",
                    detail="model strongly diverges from market",
                )
            )
        return tuple(items)


def evaluate_single_match(
    *,
    match: Match,
    odds_snapshot: OddsSnapshot,
    model_probabilities: ModelProbabilities,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
    market_model: MarketBaselineModel | None = None,
    use_market_residual_model: bool = False,
    residual_config: ResidualEdgeConfig | None = None,
    movement_features: MarketMovementFeatures | None = None,
    elo_base_prediction: EloBasePrediction | None = None,
    context_prediction: ContextAdjustedEloPrediction | None = None,
    evidence_items: tuple[EvidenceItem, ...] = (),
    confidence_report: ConfidenceReport | None = None,
) -> PredictionReport:
    """Build a single-match report from odds and model probabilities."""
    if match.match_id != odds_snapshot.match_id:
        raise ValueError("match and odds_snapshot must have the same match_id")
    if match.match_id != model_probabilities.match_id:
        raise ValueError("match and model_probabilities must have the same match_id")

    market_model = market_model or MarketBaselineModel()
    market_probabilities = market_model.predict(odds_snapshot)
    odds = odds_snapshot.to_odds_map()
    fundamental_probabilities: ModelProbabilities | None = None
    residual_prediction: MarketResidualPrediction | None = None
    effective_model_probabilities = model_probabilities

    if use_market_residual_model:
        fundamental_probabilities = model_probabilities
        residual_prediction = build_market_residual_prediction(
            match_id=match.match_id,
            market_probabilities=market_probabilities.probabilities,
            fundamental_probabilities=fundamental_probabilities.probabilities,
            movement_features=movement_features,
            config=residual_config,
        )
        effective_model_probabilities = residual_prediction.to_model_probabilities()

    decisions = {
        outcome: evaluate_value_bet(
            outcome=outcome,
            model_probability=effective_model_probabilities.probabilities[outcome],
            market_probability=market_probabilities.probabilities[outcome],
            decimal_odds=odds[outcome],
            probability_edge_threshold=probability_edge_threshold,
            ev_threshold=ev_threshold,
            kelly_fraction=kelly_fraction,
            stake_cap=stake_cap,
        )
        for outcome in OUTCOMES_1X2
    }

    return PredictionReport(
        match=match,
        odds_snapshot=odds_snapshot,
        market_probabilities=market_probabilities,
        model_probabilities=effective_model_probabilities,
        decisions=decisions,
        fundamental_probabilities=fundamental_probabilities,
        residual_prediction=residual_prediction,
        elo_base_prediction=elo_base_prediction,
        context_prediction=context_prediction,
        evidence_items=evidence_items,
        confidence_report=confidence_report,
    )


MARKET_ALIGNMENT_ALIGNED = "market_aligned"
MARKET_ALIGNMENT_MILD_DIVERGENCE = "mild_divergence"
MARKET_ALIGNMENT_STRONG_DIVERGENCE = "strong_divergence"


def market_alignment(
    model_probabilities: dict[str, float],
    market_probabilities: dict[str, float],
    *,
    mild_threshold: float = 0.03,
    strong_threshold: float = 0.08,
) -> dict[str, object]:
    """Classify model-vs-market probability divergence."""
    deltas = {
        outcome: model_probabilities[outcome] - market_probabilities[outcome]
        for outcome in OUTCOMES_1X2
    }
    largest_outcome = max(OUTCOMES_1X2, key=lambda outcome: abs(deltas[outcome]))
    largest_abs_delta = abs(deltas[largest_outcome])
    if largest_abs_delta >= strong_threshold:
        level = MARKET_ALIGNMENT_STRONG_DIVERGENCE
    elif largest_abs_delta >= mild_threshold:
        level = MARKET_ALIGNMENT_MILD_DIVERGENCE
    else:
        level = MARKET_ALIGNMENT_ALIGNED
    return {
        "level": level,
        "largest_delta_outcome": largest_outcome,
        "largest_abs_delta": largest_abs_delta,
        "deltas": deltas,
        "market_favorite": max(OUTCOMES_1X2, key=lambda outcome: market_probabilities[outcome]),
        "model_favorite": max(OUTCOMES_1X2, key=lambda outcome: model_probabilities[outcome]),
    }
