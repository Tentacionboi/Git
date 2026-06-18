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
from worldcup_betting_edp.models import MarketBaselineModel


@dataclass(frozen=True)
class PredictionReport:
    """Full single-match value-bet report."""

    match: Match
    odds_snapshot: OddsSnapshot
    market_probabilities: MarketProbabilities
    model_probabilities: ModelProbabilities
    decisions: dict[str, ValueBetDecision]

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

        for outcome in OUTCOMES_1X2:
            decision = self.decisions[outcome]
            row[f"{outcome}_ev"] = decision.expected_value
            row[f"{outcome}_kelly_fraction"] = decision.sizing.capped_fraction
            row[f"{outcome}_decision_reason"] = decision.reason

        return row

    def _no_bet_reason(self) -> str:
        """Summarize why no outcome passed the value-bet rule."""
        reasons = [self.decisions[outcome].reason for outcome in OUTCOMES_1X2]
        return " | ".join(reasons)


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
) -> PredictionReport:
    """Build a single-match report from odds and model probabilities."""
    if match.match_id != odds_snapshot.match_id:
        raise ValueError("match and odds_snapshot must have the same match_id")
    if match.match_id != model_probabilities.match_id:
        raise ValueError("match and model_probabilities must have the same match_id")

    market_model = market_model or MarketBaselineModel()
    market_probabilities = market_model.predict(odds_snapshot)
    odds = odds_snapshot.to_odds_map()

    decisions = {
        outcome: evaluate_value_bet(
            outcome=outcome,
            model_probability=model_probabilities.probabilities[outcome],
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
        model_probabilities=model_probabilities,
        decisions=decisions,
    )

