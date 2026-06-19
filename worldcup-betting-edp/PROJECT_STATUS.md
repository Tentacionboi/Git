# Project Status

Last updated: 2026-06-19

## One-Line Summary

This project is currently a bilingual, local World Cup 1X2 value-bet research dashboard plus a reproducible World Cup-focused historical-results, Elo baseline, and market-odds research pipeline. It is not yet a real-time odds monitor or an automatic prediction system.

## Current Capability

The project can:

- represent one football match with `Match`;
- represent one 1X2 decimal-odds snapshot with `OddsSnapshot`;
- convert bookmaker odds into implied probabilities and proportional devigged market probabilities;
- accept manually supplied model probabilities;
- compare model probabilities against market probabilities;
- calculate EV, full Kelly, fractional Kelly, capped stake fraction, risk level, and decision reasons;
- generate a flat single-match prediction report;
- load one-match prediction inputs from JSON;
- load settled match results from JSON;
- run a one-match CLI that emits JSON or CSV reports;
- score one prediction against one settled result with Brier score and log loss;
- compare model probability quality against the devigged market baseline;
- settle the best value bet with flat-stake profit, ROI, and hit/miss flags;
- build a sequential Kelly bankroll curve with peak and drawdown tracking;
- load batch backtest manifests that pair ordered prediction JSON files with settled-result JSON files;
- run a batch backtest manifest through reports, scoring, flat-stake settlement, and Kelly bankroll summary;
- run single-match prediction and batch backtest flows from the CLI;
- save CLI JSON/CSV outputs to files with `--output`;
- run a local Streamlit dashboard with single-match and batch-backtest modes, English-first bilingual labels, JSON upload, summary metrics, tables, and Kelly bankroll chart.
- download and parse martj42 international results CSV into typed historical result rows;
- build, write, load, and summarize a canonical historical match table for modeling;
- replay historical matches through a deterministic Elo rating engine;
- write full Elo history and current team Elo rating tables to processed CSV files;
- convert Elo expected score into first-pass home/draw/away probabilities with a transparent draw heuristic;
- write historical Elo 1X2 probabilities to processed CSV files;
- generate World Cup-only match and Elo probability tables;
- evaluate World Cup Elo 1X2 probability quality with Brier score, log loss, accuracy, and outcome-count diagnostics;
- calibrate World Cup Elo draw-probability parameters with a train/validation split;
- load canonical historical 1X2 odds snapshots from CSV;
- load canonical match kickoff timing rows from CSV;
- compare model probabilities against devigged market probabilities when odds snapshots are supplied;
- validate odds timing with as-of/no-leakage rules for pre-match, closing-market, and in-play modes.
- load time-series 1X2 market odds snapshots when a file contains multiple captures per match and bookmaker;
- engineer market movement features between configurable start and end odds types, such as opening to current;
- write market movement feature tables with overround deltas, devigged probability deltas, favorite changes, and largest probability moves.
- build a conservative market-residual probability vector where market probability is the anchor and fundamental/movement signals can only make bounded adjustments.
- evaluate single-match decisions with either direct model probabilities or market-residual final probabilities;
- show market, fundamental, and final probabilities in the Streamlit single-match dashboard when residual mode is selected.
- run batch backtests with either direct model probabilities or market-residual final probabilities;
- report raw fundamental, market baseline, and residual-final probability quality side by side in residual batch mode.
- parse stored The Odds API historical World Cup 1X2 odds JSON snapshots into the canonical market-odds schema.
- build The Odds API historical odds URLs for `soccer_fifa_world_cup` with decimal odds format.
- fetch one The Odds API historical odds snapshot from a local `THE_ODDS_API_KEY` environment variable without committing the key.
- load a local `.env` file for the one-shot The Odds API fetch script.
- write no-key fetch metadata next to raw odds JSON.
- diagnose The Odds API historical endpoint permission failures without leaking the API key.

## What It Does Not Do Yet

The project does not yet:

- scrape or monitor live odds;
- call The Odds API directly or store API keys;
- ingest real fixture feeds;
- auto-detect the next match;
- merge multiple raw sources into one deduplicated canonical table;
- compare World Cup predictions against verified real historical market odds;
- fetch historical odds using the current free The Odds API key, because historical odds require a paid usage plan;
- attach verified exact kickoff timestamps to all historical World Cup matches;
- generate model probabilities from Poisson or Dixon-Coles;
- use injury, lineup, weather, sentiment, or tactical signals;
- run historical backtests;
- prove that any model beats the market;
- send alerts or notifications.

## Current Architecture

```text
worldcup-betting-edp/
├── apps/
│   └── streamlit_app.py
├── examples/
│   ├── single_match_demo.py
│   ├── demo_single_match.json
│   └── demo_settled_match.json
├── scripts/
│   └── fetch_the_odds_api_snapshot.py
├── src/worldcup_betting_edp/
│   ├── data/prediction_input.py
│   ├── data/settled_result.py
│   ├── data/backtest_manifest.py
│   ├── data/historical_results.py
│   ├── data/canonical_matches.py
│   ├── data/the_odds_api.py
│   ├── cli.py
│   ├── domain.py
│   ├── market/devig.py
│   ├── market/movement.py
│   ├── betting/kelly.py
│   ├── backtest/scoring.py
│   ├── backtest/settlement.py
│   ├── backtest/runner.py
│   ├── models/market_baseline.py
│   ├── models/elo.py
│   ├── models/residual.py
│   └── reports/single_match.py
├── tests/
├── reports/initial_research_report.md
├── AGENTS.md
├── ROADMAP.md
├── TASKS.md
├── DECISIONS.md
├── DATA_SOURCES.md
├── MODEL_SPEC.md
└── BACKTEST_SPEC.md
```

## Important Files

- `AGENTS.md`: project collaboration rules.
- `ROADMAP.md`: phase plan.
- `TASKS.md`: current task list.
- `DECISIONS.md`: architectural decisions.
- `MODEL_SPEC.md`: MVP model contract.
- `BACKTEST_SPEC.md`: future backtest rules.
- `DATA_SOURCES.md`: candidate public data sources.
- `reports/initial_research_report.md`: first research report and EDP audit.
- `apps/streamlit_app.py`: local dashboard.
- `examples/demo_single_match.json`: canonical one-match prediction input example.
- `examples/demo_settled_match.json`: canonical settled result example.
- `examples/demo_backtest_manifest.json`: canonical batch manifest example.
- `reports/demo_backtest_result.json`: demo batch backtest output generated by the CLI.
- `docs/assets/single_match_preview.svg`: GitHub README preview for single-match pricing.
- `docs/assets/batch_backtest_preview.svg`: GitHub README preview for batch backtesting.
- `src/worldcup_betting_edp/data/prediction_input.py`: JSON input parser and validator.
- `src/worldcup_betting_edp/data/settled_result.py`: settled result parser and validator.
- `src/worldcup_betting_edp/data/backtest_manifest.py`: batch backtest manifest parser and validator.
- `src/worldcup_betting_edp/data/historical_results.py`: martj42 CSV downloader/parser and dataset summaries.
- `src/worldcup_betting_edp/data/canonical_matches.py`: canonical historical match table builder/loader.
- `src/worldcup_betting_edp/data/match_timing.py`: kickoff timestamp schema, loader, writer, and coverage diagnostics.
- `src/worldcup_betting_edp/data/the_odds_api.py`: parser and URL builder for stored The Odds API historical World Cup 1X2 odds snapshots.
- `src/worldcup_betting_edp/data/the_odds_api_client.py`: environment-key reader and minimal HTTP client helpers for The Odds API.
- `scripts/fetch_the_odds_api_snapshot.py`: one-shot historical odds fetch script that writes raw JSON and optional canonical CSV.
- `src/worldcup_betting_edp/backtest/scoring.py`: Brier score and log loss.
- `src/worldcup_betting_edp/backtest/market_comparison.py`: model-vs-market probability comparison for matched odds rows.
- `src/worldcup_betting_edp/backtest/temporal_validation.py`: as-of timing validation to detect odds leakage.
- `src/worldcup_betting_edp/market/movement.py`: market movement features between two odds snapshots for the same match and bookmaker.
- `src/worldcup_betting_edp/backtest/settlement.py`: flat-stake settlement and Kelly bankroll curves.
- `src/worldcup_betting_edp/backtest/runner.py`: manifest-driven batch backtest runner.
- `src/worldcup_betting_edp/models/elo.py`: simple Elo rating engine, historical replay, and rating table writers.
- `src/worldcup_betting_edp/models/residual.py`: conservative market-residual model that treats market probability as the anchor and applies bounded residual adjustments.
- `src/worldcup_betting_edp/cli.py`: command-line report generator.
- `data/raw/martj42/results.csv`: downloaded public historical international results snapshot.
- `data/raw/martj42/results.csv.metadata.json`: source URL, download time, and license notes.
- `data/processed/matches/canonical_matches.csv`: processed canonical match table for model training.
- `data/processed/matches/canonical_matches.csv.metadata.json`: processed table creation time, source, row count, and columns.
- `data/processed/matches/world_cup_matches.csv`: World Cup-only match table and primary evaluation target.
- `data/processed/ratings/elo_history.csv`: match-by-match simple Elo replay output.
- `data/processed/ratings/current_elo_ratings.csv`: latest simple Elo team ratings.
- `data/processed/ratings/elo_1x2_probabilities.csv`: match-by-match first-pass Elo 1X2 probabilities.
- `data/processed/ratings/world_cup_elo_1x2_probabilities.csv`: World Cup-only Elo 1X2 probabilities.
- `data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv`: World Cup-only calibrated Elo 1X2 probabilities.
- `reports/world_cup_elo_1x2_evaluation.json`: first World Cup-only Elo probability evaluation report.
- `reports/world_cup_elo_1x2_evaluation_calibrated.json`: calibrated World Cup-only Elo probability evaluation report.
- `reports/world_cup_elo_draw_calibration.json`: train/validation draw calibration report.
- `examples/demo_world_cup_market_odds.csv`: synthetic odds file that demonstrates the historical odds schema.
- `examples/demo_world_cup_match_timing.csv`: synthetic kickoff timing file that demonstrates as-of validation.
- `examples/demo_world_cup_market_odds_timeseries.csv`: synthetic opening/current odds time-series file for market movement features.
- `examples/demo_the_odds_api_historical_snapshot.json`: synthetic The Odds API-shaped JSON snapshot for parser verification only.
- `reports/demo_market_comparison.json`: synthetic demo model-vs-market comparison report.
- `reports/demo_market_movement_features.csv`: synthetic demo market movement feature table.
- `reports/odds_source_validation.md`: audit of candidate real World Cup odds sources and current recommendation.
- `reports/the_odds_api_access_check.md`: local API-key permission check showing the current key lacks historical odds access.

## Current UI

Dashboard:

```text
http://localhost:8503
```

Run locally:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[ui]"
streamlit run apps/streamlit_app.py
```

The currently running development server was started from a temporary virtual environment under `/private/tmp/worldcup-edp-ui-venv312`.

The dashboard has two sidebar modes:

- `Single Match / 单场预测`: manual or JSON-loaded single-match pricing.
- `Batch Backtest / 批量回测`: manifest-driven summary metrics, model-vs-market chart, scoring table, flat-stake settlement table, and Kelly bankroll curve.

The single-match page has two probability modes:

- `Direct Model / 直接模型概率`: user-supplied model probabilities are used directly for EV/Kelly decisions.
- `Market Residual / 市场残差模型`: user-supplied probabilities are treated as fundamental probabilities, then converted into market-anchored final probabilities before EV/Kelly decisions.

The batch-backtest page can also run in market-residual mode. In that mode:

- `Model / 模型` means residual-final probability.
- `Fundamental / 基本面` means the raw user-supplied model probability before market anchoring.
- `Market / 市场` means devigged bookmaker probability.

## Verification

Latest test command:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest discover -s tests
```

Latest result:

```text
Ran 144 tests
OK
```

The Streamlit dashboard was also browser-verified with local Chrome automation. The latest screenshot path was:

```text
/private/tmp/worldcup_streamlit_dashboard_bilingual.png
```

## Current Git Situation

- Branch: `main`
- Remote: `https://github.com/Tentacionboi/Git.git`
- The repository is being checkpointed directly on `main` for now.

## Current Historical Results Data

The project can download and parse `martj42/international_results`:

```text
data/raw/martj42/results.csv
```

Current parsed snapshot:

```text
match_count: 49425
first_date: 1872-11-30
last_date: 2026-06-16
team_count: 336
tournament_count: 200
FIFA World Cup match_count: 984
```

The loader skips rows with `NA` scores by default because those rows are not settled historical results.

The project can also build and load a processed canonical match table:

```text
data/processed/matches/canonical_matches.csv
```

Current processed snapshot:

```text
match_count: 49425
first_date: 1872-11-30
last_date: 2026-06-16
team_count: 336
tournament_count: 200
neutral_match_count: 13075
```

This is the immediate input table for Elo ratings and the later Poisson model.

The project now also has a World Cup-only match table:

```text
data/processed/matches/world_cup_matches.csv
```

Current World Cup-only snapshot:

```text
match_count: 984
first_date: 1930-07-13
last_date: 2026-06-16
```

## Current Elo Data

The project can replay the canonical match table through a simple Elo engine:

```text
data/processed/ratings/elo_history.csv
data/processed/ratings/current_elo_ratings.csv
data/processed/ratings/elo_1x2_probabilities.csv
data/processed/ratings/world_cup_elo_1x2_probabilities.csv
data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv
```

Current generated snapshot:

```text
elo_history_rows: 49425
current_team_rows: 336
elo_1x2_probability_rows: 49425
world_cup_elo_1x2_probability_rows: 984
elo_1x2_average_probabilities: home 39.18%, draw 23.87%, away 36.94%
top_5_simple_elo: Argentina, Spain, France, England, Brazil
```

Important: these are project-generated simple Elo ratings and heuristic 1X2 probabilities. They are useful model features, but they are not yet draw-calibrated, not compared against market odds, and they do not prove betting edge.

## Current World Cup Elo Evaluation

First World Cup-only Elo 1X2 evaluation:

```text
report: reports/world_cup_elo_1x2_evaluation.json
match_count: 984
accuracy: 54.17%
mean_brier_score: 0.5867
mean_log_loss: 0.9880
average_probability_actual: 0.4036
actual_results: home 449, draw 222, away 313
predicted_results: home 600, draw 0, away 384
```

The zero predicted draws are not acceptable for a mature 1X2 model. This is the strongest current evidence that the next modeling task should be draw calibration, not UI polish.

World Cup Elo draw calibration:

```text
report: reports/world_cup_elo_draw_calibration.json
calibration_set: World Cup matches through 2014-12-31, 836 matches
validation_set: World Cup matches from 2018-01-01, 148 matches
objective: mean_log_loss
candidate_count: 99
best_base_draw_probability: 0.28
best_draw_gap_penalty_per_100_elo: 0.05
full_sample_calibrated_accuracy: 54.17%
full_sample_calibrated_mean_brier_score: 0.5859
full_sample_calibrated_mean_log_loss: 0.9861
validation_calibrated_mean_brier_score: 0.5966
validation_calibrated_mean_log_loss: 1.0037
```

This is a small improvement over the uncalibrated heuristic, not a breakthrough. The next serious research blocker is historical World Cup odds: without odds, the project can score probability quality but cannot test market edge.

## Current Market Comparison Status

The project now has a canonical 1X2 historical odds schema:

```text
match_id, bookmaker, captured_at, home_odds, draw_odds, away_odds, odds_type, source
```

Implemented comparison flow:

```text
model probabilities + historical odds -> proportional devig -> model vs market Brier/log-loss comparison
```

Demo report:

```text
report: reports/demo_market_comparison.json
odds_file: examples/demo_world_cup_market_odds.csv
timing_file: examples/demo_world_cup_match_timing.csv
matched_match_count: 3
unmatched_model_match_count: 981
average_market_overround: 6.44%
leakage_risk_counts: low 3
```

The demo odds and kickoff times are synthetic and are not historical market evidence. The project can now compare against market odds once real, reproducible, legally usable World Cup odds and kickoff timestamp files are added.

Market movement feature engineering now exists:

```text
module: src/worldcup_betting_edp/market/movement.py
input demo: examples/demo_world_cup_market_odds_timeseries.csv
output demo: reports/demo_market_movement_features.csv
feature_count: 3
```

The feature table compares two snapshots for the same match and bookmaker, such as opening odds and current odds. It emits start/end overround, overround delta, start/end devigged probabilities, home/draw/away probability deltas, start/end favorite, favorite-changed flag, favorite probability delta, and largest probability move.

Interpretation boundary: this describes how the market price moved. It does not prove the move is exploitable, and it does not by itself identify a value bet. For that, the project still needs real timestamped odds, model probabilities generated strictly as of the prediction time, and out-of-sample market comparison.

Timing leakage policy now exists in code:

```text
actionable pre-match backtest:
  odds_captured_at <= prediction_time <= kickoff_time
  closing odds rejected by default

closing-market comparison:
  odds_captured_at <= kickoff_time
  valid only as market-baseline research, not as an early betting strategy

in-play comparison:
  prediction_time >= kickoff_time
  must not be mixed with pre-match model evaluation
```

Date-only timestamps are treated as medium leakage risk because they do not prove the odds were available at the claimed prediction moment.

Kickoff timing contract:

```text
match_id, kickoff_time, time_zone, precision, source
```

Coverage diagnostics can report how many World Cup matches have exact datetime precision versus date-only precision. Exact kickoff times are still a data-source task, not a solved historical data problem.

## Current JSON Input Contract

The canonical single-match input format is:

```text
examples/demo_single_match.json
```

It contains three required top-level objects:

- `match`: match identity, teams, kickoff time, competition, stage, and neutral flag.
- `odds`: 1X2 decimal odds and odds capture timestamp.
- `model`: model name and home/draw/away probabilities that must sum to 1.0.

The Streamlit sidebar can load this format through `Upload JSON / 上传JSON`.

## Current Settled Result Contract

The canonical settled-result format is:

```text
examples/demo_settled_match.json
```

It contains:

- `match_id`: must match the prediction report being scored.
- `settled_at`: settlement timestamp.
- `home_goals` and `away_goals`: non-negative integer final score.
- `result_1x2`: canonical result label: `home`, `draw`, or `away`.
- `source` and `notes`: optional provenance and comments.

The loader verifies that `result_1x2` agrees with the final score, so a 2-1 score cannot be mislabeled as `draw` or `away`.

## CLI Usage

Run single-match prediction from source:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m worldcup_betting_edp.cli --input examples/demo_single_match.json
```

The command emits the same flat report dictionary as the Streamlit dashboard. Use `--format csv` for a one-row CSV output.

Run batch backtest from source:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m worldcup_betting_edp.cli --manifest examples/demo_backtest_manifest.json --flat-stake 10 --starting-bankroll 100
```

The batch command emits a JSON payload with `summary`, `manifest`, `reports`, `scored_predictions`, `flat_stake_settlements`, and `kelly_curve`.

Save CLI output to a file:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m worldcup_betting_edp.cli --manifest examples/demo_backtest_manifest.json --flat-stake 10 --starting-bankroll 100 --output reports/demo_backtest_result.json
```

## Current Scoring Metrics

The scoring layer supports:

- multiclass Brier score across `home`, `draw`, and `away`;
- clipped multiclass log loss;
- one-report scoring against one settled result;
- model-vs-market comparison for both metrics.

Example demo result:

```text
model_brier_score: 0.3906
market_brier_score: 0.4757719049739413
model_log_loss: 0.7133498878774648
market_log_loss: 0.8276930157285507
```

This demo result only validates the scoring pipeline. It does not prove real market edge.

## Current Flat-Stake Settlement

The settlement layer supports:

- selecting the report's best value bet;
- returning no-bet rows with zero stake and zero profit;
- settling fixed-stake win/loss payoff from decimal odds;
- reporting stake, profit, ROI, selected odds, and hit/miss flag.

Example demo result with a 10-unit stake:

```text
bet_outcome: home
actual_result: home
decimal_odds: 2.2
profit: 12.0
roi: 1.2
hit: True
```

This demo result only validates settlement math. It does not prove real profitability.

## Current Kelly Bankroll Curve

The bankroll layer supports:

- ordered prediction/result pairs;
- per-match stake from the report's capped fractional Kelly recommendation;
- bankroll updates after each settled bet;
- explicit no-bet rows with unchanged bankroll;
- peak bankroll, point drawdown, maximum drawdown, final bankroll, total ROI, and hit rate.

Example two-step demo path:

```text
starting_bankroll: 100.0
final_bankroll: 100.2933125
peak_bankroll: 101.95
max_drawdown: 0.01625
bet_count: 2
hit_rate: 0.5
```

This demo result only validates bankroll math. It does not prove real profitability.

## Current Batch Manifest

The batch manifest format is:

```text
examples/demo_backtest_manifest.json
```

It contains an ordered `entries` array. Each entry contains:

- `label`: optional human-readable row label.
- `prediction_path`: path to a one-match prediction JSON file.
- `settled_result_path`: path to a settled-result JSON file.

The loader resolves relative paths from the manifest file's directory, loads both JSON files, validates that their match IDs agree, rejects duplicate match IDs, and preserves entry order.

## Current Batch Runner

The batch runner loads a manifest and emits:

- one prediction report per entry;
- one Brier/log-loss scoring row per entry;
- one flat-stake settlement row per entry;
- one Kelly bankroll curve;
- one summary containing mean model/market scores, flat-stake ROI, Kelly final bankroll, and max drawdown.

Example demo summary:

```text
entry_count: 1
flat_total_profit: 12.0
flat_roi: 1.2
mean_model_brier_score: 0.3906
mean_market_brier_score: 0.4757719049739413
kelly_final_bankroll: 101.95
kelly_total_roi: 0.0195
```

This demo result only validates batch plumbing. It does not prove real market edge.

## Next Recommended Task

Evaluate market-residual probabilities on real or verified historical market odds:

1. Add a reproducible historical World Cup 1X2 odds source with timestamps and license notes.
2. Generate residual-final probabilities from market probability plus Elo/fundamental probabilities.
3. Compare market baseline, raw fundamental, and residual-final probabilities on identical settled matches.
4. Add market movement signals once real timestamped odds exist.
5. Do not claim market edge until out-of-sample backtests beat market baselines.

## Target End-State

The intended final system is:

```text
fixtures + odds snapshots + team/model data
        -> market probability baseline
        -> Elo / Poisson / fundamental probabilities
        -> bounded market-residual probability adjustment
        -> EDP-style situation signals
        -> model-vs-market comparison
        -> EV / Kelly / risk controls
        -> dashboard + backtest + optional monitoring
```

## Handoff Prompt For A New Conversation

Use this prompt when starting a fresh thread:

```text
Please continue the World Cup Betting EDP project. First read:

- worldcup-betting-edp/AGENTS.md
- worldcup-betting-edp/PROJECT_STATUS.md
- worldcup-betting-edp/TASKS.md
- worldcup-betting-edp/ROADMAP.md
- worldcup-betting-edp/DECISIONS.md

Current priority: find or build a reproducible historical World Cup odds dataset, then evaluate market baseline, raw fundamental, and market-residual probabilities on identical settled matches. Do not claim market edge before real timestamped odds and out-of-sample model-vs-market backtests exist.
```
