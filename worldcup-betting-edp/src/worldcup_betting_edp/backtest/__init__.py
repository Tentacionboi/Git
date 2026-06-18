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
from worldcup_betting_edp.backtest.elo_calibration import (
    EloCalibrationCandidate,
    EloCalibrationResult,
    calibrate_elo_probability_config,
    default_elo_probability_config_grid,
    filter_rating_history_by_date,
    write_elo_calibration_report_json,
)
from worldcup_betting_edp.backtest.market_comparison import (
    MarketComparisonRow,
    MarketComparisonSummary,
    build_market_comparison_rows,
    evaluate_market_comparison,
    write_market_comparison_report_json,
)
from worldcup_betting_edp.backtest.temporal_validation import (
    LEAKAGE_RISK_HIGH,
    LEAKAGE_RISK_LOW,
    LEAKAGE_RISK_MEDIUM,
    TIMING_MODE_CLOSING_MARKET,
    TIMING_MODE_IN_PLAY,
    TIMING_MODE_PRE_MATCH,
    ParsedTimestamp,
    TemporalValidationResult,
    parse_timestamp,
    validate_odds_as_of_prediction,
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
    "EloCalibrationCandidate",
    "EloCalibrationResult",
    "FlatStakeSettlement",
    "LEAKAGE_RISK_HIGH",
    "LEAKAGE_RISK_LOW",
    "LEAKAGE_RISK_MEDIUM",
    "MarketComparisonRow",
    "MarketComparisonSummary",
    "ParsedTimestamp",
    "ProbabilityEvaluationSummary",
    "ScoredPrediction",
    "TIMING_MODE_CLOSING_MARKET",
    "TIMING_MODE_IN_PLAY",
    "TIMING_MODE_PRE_MATCH",
    "TemporalValidationResult",
    "brier_score",
    "calibrate_elo_probability_config",
    "build_market_comparison_rows",
    "default_elo_probability_config_grid",
    "evaluate_1x2_probability_rows",
    "evaluate_market_comparison",
    "filter_rating_history_by_date",
    "load_1x2_probability_rows_csv",
    "log_loss",
    "parse_timestamp",
    "run_batch_backtest",
    "run_batch_backtest_path",
    "score_prediction_report",
    "settle_flat_stake",
    "settle_kelly_bankroll",
    "validate_odds_as_of_prediction",
    "write_elo_calibration_report_json",
    "write_market_comparison_report_json",
    "write_probability_evaluation_json",
]
