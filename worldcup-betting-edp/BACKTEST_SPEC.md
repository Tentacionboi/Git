# Backtest Specification

## Core Principle

A backtest is valid only if every input was available at the simulated decision time.

## Prediction Metrics

Use at least:

- Accuracy.
- Brier score.
- Log loss.
- Calibration by probability bucket.

Accuracy is secondary. A model can have acceptable accuracy and still be badly calibrated.

## Betting Metrics

Use at least:

- Number of bets.
- Hit rate.
- Average odds.
- ROI.
- Profit/loss distribution.
- Maximum drawdown.
- Longest losing streak.
- Flat-stake bankroll curve.
- Fractional Kelly bankroll curve.
- Closing line value when closing odds are available.

## Baselines

Compare against:

- Devigged market probability.
- Random betting.
- Always betting favorite.
- No-bet baseline.

## Leakage Checks

Reject any experiment that uses:

- Closing odds when the simulated bet is placed earlier.
- Actual lineups before official release time.
- Post-match xG or match stats as pre-match features.
- Final tournament standings before the match.
- Manually selected successful odds snapshots.

## Sample Size Warning

World Cup-only samples are small. Any ROI result from one tournament is weak evidence. Prefer training and validation on broader international matches, then evaluate World Cup separately.

