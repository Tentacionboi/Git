"""Batch backtest runner for manifest-driven prediction evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from worldcup_betting_edp.backtest.scoring import ScoredPrediction, score_prediction_report
from worldcup_betting_edp.backtest.settlement import (
    BankrollCurve,
    FlatStakeSettlement,
    settle_flat_stake,
    settle_kelly_bankroll,
)
from worldcup_betting_edp.data import BacktestManifest, load_backtest_manifest_path
from worldcup_betting_edp.reports import PredictionReport, evaluate_single_match


@dataclass(frozen=True)
class BatchBacktestResult:
    """All outputs from running one manifest-driven backtest."""

    manifest: BacktestManifest
    reports: list[PredictionReport]
    scored_predictions: list[ScoredPrediction]
    flat_stake_settlements: list[FlatStakeSettlement]
    kelly_curve: BankrollCurve
    flat_stake: float

    def summary(self) -> dict[str, Any]:
        """Return batch-level metrics."""
        entry_count = len(self.reports)
        flat_bet_count = sum(1 for settlement in self.flat_stake_settlements if settlement.bet_placed)
        flat_hit_count = sum(1 for settlement in self.flat_stake_settlements if settlement.hit)
        flat_total_staked = sum(settlement.stake for settlement in self.flat_stake_settlements)
        flat_total_profit = sum(settlement.profit for settlement in self.flat_stake_settlements)

        model_brier_values = [score.model_brier_score for score in self.scored_predictions]
        market_brier_values = [score.market_brier_score for score in self.scored_predictions]
        model_log_loss_values = [score.model_log_loss for score in self.scored_predictions]
        market_log_loss_values = [score.market_log_loss for score in self.scored_predictions]

        return {
            "entry_count": entry_count,
            "match_ids": self.manifest.match_ids,
            "flat_stake": self.flat_stake,
            "flat_bet_count": flat_bet_count,
            "flat_hit_count": flat_hit_count,
            "flat_hit_rate": flat_hit_count / flat_bet_count if flat_bet_count else None,
            "flat_total_staked": flat_total_staked,
            "flat_total_profit": flat_total_profit,
            "flat_roi": flat_total_profit / flat_total_staked if flat_total_staked else None,
            "mean_model_brier_score": _mean(model_brier_values),
            "mean_market_brier_score": _mean(market_brier_values),
            "mean_model_log_loss": _mean(model_log_loss_values),
            "mean_market_log_loss": _mean(market_log_loss_values),
            "model_beats_market_brier_count": sum(
                score.model_brier_score < score.market_brier_score
                for score in self.scored_predictions
            ),
            "model_beats_market_log_loss_count": sum(
                score.model_log_loss < score.market_log_loss
                for score in self.scored_predictions
            ),
            "kelly_final_bankroll": self.kelly_curve.final_bankroll,
            "kelly_total_profit": self.kelly_curve.total_profit,
            "kelly_total_roi": self.kelly_curve.total_roi,
            "kelly_max_drawdown": self.kelly_curve.max_drawdown,
            "kelly_bet_count": self.kelly_curve.bet_count,
            "kelly_hit_count": self.kelly_curve.hit_count,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable batch backtest payload."""
        return {
            "summary": self.summary(),
            "manifest": self.manifest.to_dict(),
            "reports": [report.to_dict() for report in self.reports],
            "scored_predictions": [score.to_dict() for score in self.scored_predictions],
            "flat_stake_settlements": [
                settlement.to_dict() for settlement in self.flat_stake_settlements
            ],
            "kelly_curve": self.kelly_curve.to_dict(),
        }


def run_batch_backtest_path(
    manifest_path: str | Path,
    *,
    flat_stake: float = 1.0,
    starting_bankroll: float = 100.0,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
) -> BatchBacktestResult:
    """Load a manifest path and run the batch backtest."""
    return run_batch_backtest(
        load_backtest_manifest_path(manifest_path),
        flat_stake=flat_stake,
        starting_bankroll=starting_bankroll,
        probability_edge_threshold=probability_edge_threshold,
        ev_threshold=ev_threshold,
        kelly_fraction=kelly_fraction,
        stake_cap=stake_cap,
    )


def run_batch_backtest(
    manifest: BacktestManifest,
    *,
    flat_stake: float = 1.0,
    starting_bankroll: float = 100.0,
    probability_edge_threshold: float = 0.02,
    ev_threshold: float = 0.01,
    kelly_fraction: float = 0.25,
    stake_cap: float = 0.02,
) -> BatchBacktestResult:
    """Run all manifest entries through prediction, scoring, and settlement."""
    if flat_stake <= 0.0:
        raise ValueError("flat_stake must be positive")

    reports: list[PredictionReport] = []
    scored_predictions: list[ScoredPrediction] = []
    flat_stake_settlements: list[FlatStakeSettlement] = []

    for entry in manifest.entries:
        report = evaluate_single_match(
            match=entry.prediction_input.match,
            odds_snapshot=entry.prediction_input.odds_snapshot,
            model_probabilities=entry.prediction_input.model_probabilities,
            probability_edge_threshold=probability_edge_threshold,
            ev_threshold=ev_threshold,
            kelly_fraction=kelly_fraction,
            stake_cap=stake_cap,
        )
        reports.append(report)
        scored_predictions.append(
            score_prediction_report(report=report, settled_result=entry.settled_result)
        )
        flat_stake_settlements.append(
            settle_flat_stake(report=report, settled_result=entry.settled_result, stake=flat_stake)
        )

    kelly_curve = settle_kelly_bankroll(
        [(report, entry.settled_result) for report, entry in zip(reports, manifest.entries)],
        starting_bankroll=starting_bankroll,
    )

    return BatchBacktestResult(
        manifest=manifest,
        reports=reports,
        scored_predictions=scored_predictions,
        flat_stake_settlements=flat_stake_settlements,
        kelly_curve=kelly_curve,
        flat_stake=flat_stake,
    )


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
