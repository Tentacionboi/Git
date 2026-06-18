"""Backtesting and scoring utilities."""

from worldcup_betting_edp.backtest.runner import (
    BatchBacktestResult,
    run_batch_backtest,
    run_batch_backtest_path,
)
from worldcup_betting_edp.backtest.scoring import (
    ScoredPrediction,
    brier_score,
    log_loss,
    score_prediction_report,
)
from worldcup_betting_edp.backtest.probability_evaluation import (
    ProbabilityEvaluationSummary,
    evaluate_1x2_probability_rows,
    load_1x2_probability_rows_csv,
    write_probability_evaluation_json,
)
from worldcup_betting_edp.backtest.settlement import (
    BankrollCurve,
    BankrollPoint,
    FlatStakeSettlement,
    settle_flat_stake,
    settle_kelly_bankroll,
)

__all__ = [
    "BatchBacktestResult",
    "BankrollCurve",
    "BankrollPoint",
    "FlatStakeSettlement",
    "ProbabilityEvaluationSummary",
    "ScoredPrediction",
    "brier_score",
    "evaluate_1x2_probability_rows",
    "load_1x2_probability_rows_csv",
    "log_loss",
    "run_batch_backtest",
    "run_batch_backtest_path",
    "score_prediction_report",
    "settle_flat_stake",
    "settle_kelly_bankroll",
    "write_probability_evaluation_json",
]
