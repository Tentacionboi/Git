"""Bet settlement utilities for one settled 1X2 prediction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from worldcup_betting_edp.data import SettledResult
from worldcup_betting_edp.reports import PredictionReport


@dataclass(frozen=True)
class FlatStakeSettlement:
    """Flat-stake payoff for one prediction report and one settled result."""

    match_id: str
    actual_result: str
    bet_placed: bool
    bet_outcome: str | None
    decimal_odds: float | None
    stake: float
    profit: float
    roi: float
    hit: bool | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a flat row for reporting and future backtests."""
        return {
            "match_id": self.match_id,
            "actual_result": self.actual_result,
            "bet_placed": self.bet_placed,
            "bet_outcome": self.bet_outcome,
            "decimal_odds": self.decimal_odds,
            "stake": self.stake,
            "profit": self.profit,
            "roi": self.roi,
            "hit": self.hit,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BankrollPoint:
    """One step in a sequential Kelly bankroll curve."""

    match_id: str
    actual_result: str
    bet_placed: bool
    bet_outcome: str | None
    decimal_odds: float | None
    stake_fraction: float
    stake: float
    profit: float
    bankroll_start: float
    bankroll_end: float
    peak_bankroll: float
    drawdown: float
    hit: bool | None

    def to_dict(self) -> dict[str, Any]:
        """Return a flat row for curve tables and dashboard charts."""
        return {
            "match_id": self.match_id,
            "actual_result": self.actual_result,
            "bet_placed": self.bet_placed,
            "bet_outcome": self.bet_outcome,
            "decimal_odds": self.decimal_odds,
            "stake_fraction": self.stake_fraction,
            "stake": self.stake,
            "profit": self.profit,
            "bankroll_start": self.bankroll_start,
            "bankroll_end": self.bankroll_end,
            "peak_bankroll": self.peak_bankroll,
            "drawdown": self.drawdown,
            "hit": self.hit,
        }


@dataclass(frozen=True)
class BankrollCurve:
    """Sequential bankroll curve summary."""

    starting_bankroll: float
    final_bankroll: float
    total_profit: float
    total_roi: float
    peak_bankroll: float
    max_drawdown: float
    bet_count: int
    hit_count: int
    points: list[BankrollPoint]

    def to_dict(self) -> dict[str, Any]:
        """Return a summary row plus point rows."""
        return {
            "starting_bankroll": self.starting_bankroll,
            "final_bankroll": self.final_bankroll,
            "total_profit": self.total_profit,
            "total_roi": self.total_roi,
            "peak_bankroll": self.peak_bankroll,
            "max_drawdown": self.max_drawdown,
            "bet_count": self.bet_count,
            "hit_count": self.hit_count,
            "hit_rate": self.hit_count / self.bet_count if self.bet_count else None,
            "points": [point.to_dict() for point in self.points],
        }


def settle_flat_stake(
    *,
    report: PredictionReport,
    settled_result: SettledResult,
    stake: float = 1.0,
) -> FlatStakeSettlement:
    """Settle the report's best value bet with a fixed stake.

    A no-bet report returns zero stake, zero profit, zero ROI, and ``hit=None``.
    """
    if report.match.match_id != settled_result.match_id:
        raise ValueError("report and settled_result must have the same match_id")
    if stake <= 0.0:
        raise ValueError("stake must be positive")

    best = report.best_value_bet
    if best is None:
        return FlatStakeSettlement(
            match_id=report.match.match_id,
            actual_result=settled_result.result_1x2,
            bet_placed=False,
            bet_outcome=None,
            decimal_odds=None,
            stake=0.0,
            profit=0.0,
            roi=0.0,
            hit=None,
            reason=report.to_dict()["reason"],
        )

    hit = best.outcome == settled_result.result_1x2
    profit = stake * (best.decimal_odds - 1.0) if hit else -stake
    return FlatStakeSettlement(
        match_id=report.match.match_id,
        actual_result=settled_result.result_1x2,
        bet_placed=True,
        bet_outcome=best.outcome,
        decimal_odds=best.decimal_odds,
        stake=stake,
        profit=profit,
        roi=profit / stake,
        hit=hit,
        reason=best.reason,
    )


def settle_kelly_bankroll(
    ordered_predictions: Sequence[tuple[PredictionReport, SettledResult]],
    *,
    starting_bankroll: float = 100.0,
) -> BankrollCurve:
    """Settle ordered predictions using each report's capped fractional Kelly stake."""
    if starting_bankroll <= 0.0:
        raise ValueError("starting_bankroll must be positive")

    bankroll = starting_bankroll
    peak = starting_bankroll
    max_drawdown = 0.0
    points: list[BankrollPoint] = []
    bet_count = 0
    hit_count = 0

    for report, settled_result in ordered_predictions:
        if report.match.match_id != settled_result.match_id:
            raise ValueError("report and settled_result must have the same match_id")

        bankroll_start = bankroll
        best = report.best_value_bet
        if best is None:
            stake_fraction = 0.0
            stake = 0.0
            profit = 0.0
            bet_placed = False
            bet_outcome = None
            decimal_odds = None
            hit = None
        else:
            stake_fraction = best.sizing.capped_fraction
            stake = bankroll_start * stake_fraction
            hit = best.outcome == settled_result.result_1x2
            profit = stake * (best.decimal_odds - 1.0) if hit else -stake
            bet_placed = stake > 0.0
            bet_outcome = best.outcome
            decimal_odds = best.decimal_odds
            if bet_placed:
                bet_count += 1
                if hit:
                    hit_count += 1

        bankroll = bankroll_start + profit
        peak = max(peak, bankroll)
        drawdown = (peak - bankroll) / peak if peak > 0.0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

        points.append(
            BankrollPoint(
                match_id=report.match.match_id,
                actual_result=settled_result.result_1x2,
                bet_placed=bet_placed,
                bet_outcome=bet_outcome,
                decimal_odds=decimal_odds,
                stake_fraction=stake_fraction,
                stake=stake,
                profit=profit,
                bankroll_start=bankroll_start,
                bankroll_end=bankroll,
                peak_bankroll=peak,
                drawdown=drawdown,
                hit=hit,
            )
        )

    return BankrollCurve(
        starting_bankroll=starting_bankroll,
        final_bankroll=bankroll,
        total_profit=bankroll - starting_bankroll,
        total_roi=(bankroll - starting_bankroll) / starting_bankroll,
        peak_bankroll=peak,
        max_drawdown=max_drawdown,
        bet_count=bet_count,
        hit_count=hit_count,
        points=points,
    )
