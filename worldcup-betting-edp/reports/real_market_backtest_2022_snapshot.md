# Real Market Backtest: 2022 World Cup Snapshot

Date: 2026-06-19

## Input

Paid The Odds API historical snapshot:

```text
requested_date: 2022-11-20T12:00:00Z
provider_snapshot_timestamp: 2022-11-20T11:55:38Z
sport_key: soccer_fifa_world_cup
market: h2h
```

Local data files used but not committed:

```text
data/processed/odds/the_odds_api/2022-11-20T120000Z_canonical_odds.csv
data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv
```

Aggregate JSON report:

```text
reports/real_market_backtest_2022_snapshot.json
```

## Coverage

```text
evaluated matches: 48
odds rows: 1737
bookmakers: 42
average bookmakers per match: 36.19
average market overround: 5.85%
```

The snapshot covers the 48 group-stage fixtures known before the 2022 World Cup started. Knockout fixtures were not known at this timestamp, so their absence is expected.

## Probability Quality

Lower Brier score and log loss are better.

| Model | Accuracy | Mean Brier | Mean Log Loss | Avg Prob Actual |
|---|---:|---:|---:|---:|
| Market average devig | 54.17% | 0.6182 | 1.0599 | 0.4114 |
| Calibrated Elo | 54.17% | 0.6090 | 1.0332 | 0.4062 |
| Market residual | 52.08% | 0.6117 | 1.0444 | 0.4105 |

Against market average:

```text
Elo minus market Brier: -0.0091
Elo minus market log loss: -0.0267
Residual minus market Brier: -0.0064
Residual minus market log loss: -0.0155
```

In this small snapshot, calibrated Elo and market-residual probabilities score slightly better than average market-implied probabilities. This is a useful signal, not a durable conclusion.

## Value-Bet Settlement

Rules:

```text
model probability: market-residual
edge threshold: 2 percentage points
EV threshold: 1%
settlement: flat stake = 1 per selected bet
bookmaker selection: best available bookmaker price in the snapshot
```

Summary:

```text
bet count: 34
hit count: 13
hit rate: 38.24%
average odds: 7.45
average model EV: 22.31%
flat profit: +59.55
flat ROI per bet: +175.15%
```

This value-bet result is intentionally treated as unstable. It may be inflated by:

- small sample size;
- line-shopping across many bookmakers;
- loose thresholds;
- longshot wins in the 2022 group stage;
- missing real account availability, limits, and execution constraints.

Do not interpret this as proof of a profitable system.

## Interpretation

The key milestone is not the ROI number. The key milestone is that the project now has an end-to-end real-market test path:

1. paid historical odds snapshot;
2. canonical match mapping;
3. orientation-correct home/draw/away odds;
4. market devig;
5. Elo and residual probability comparison;
6. settled value-bet simulation.

## Next Checks

Before making any claim of edge:

1. Run the same test on multiple timestamps before each match.
2. Compare open, 24h-before, 6h-before, and close snapshots.
3. Restrict value-bet settlement to one chosen bookmaker or an average executable market.
4. Add confidence intervals or bootstrap sensitivity.
5. Separate group stage and knockout stage.
6. Add strict bankroll/Kelly drawdown reporting.
