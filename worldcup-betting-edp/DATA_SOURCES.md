# Data Sources

This file records candidate data sources, their expected use, and their risks.

## MVP-Ready Candidates

| Source | Use | Access | Reliability | Risk |
|---|---|---|---|---|
| openfootball/worldcup | World Cup schedule/results | GitHub | Medium-high | Text format parsing |
| martj42/international_results | Historical national-team results | GitHub CSV | Medium-high | Community maintained; includes `NA` score rows that must be skipped |
| FIFA Men's Ranking | Ranking feature | FIFA site | High | Historical scraping/download friction |
| World Football Elo Ratings | Rating feature | Website snapshot | Medium-high | Not official; API stability unclear |
| football-data.co.uk | Historical results and odds | CSV/XLSX | Medium-high | World Cup coverage/fields must be verified |

## Enhancement Candidates

| Source | Use | Access | Reliability | Risk |
|---|---|---|---|---|
| The Odds API | Live and historical odds | API | High | Historical odds may require paid plan |
| StatsBomb Open Data | xG/events/lineups | GitHub JSON | High | Limited competition coverage |
| Open-Meteo | Historical and forecast weather | API | High | Needs stadium coordinates |
| FIFA Match Centre | Fixtures/lineups | FIFA website | High | Automation and terms need verification |

## Source Rules

1. Core backtests must use reproducible sources.
2. Every raw file should retain source URL, download date, and license notes.
3. If a source cannot be redistributed, store only scripts and metadata, not copied proprietary data.
4. Odds data must include timestamp or be clearly labeled as open/close/closing.

## Downloaded Snapshots

### martj42/international_results

- Raw file: `data/raw/martj42/results.csv`
- Metadata: `data/raw/martj42/results.csv.metadata.json`
- Source URL: `https://raw.githubusercontent.com/martj42/international_results/master/results.csv`
- License note: CC0-1.0 according to the upstream repository.
- Current parsed rows: 49,425 settled matches.
- Current parsed FIFA World Cup rows: 984.
- Date coverage in parsed settled rows: 1872-11-30 to 2026-06-16.
- Loader behavior: skips unplayed/unsettled rows where score is `NA` by default.

### Canonical historical match table

- Processed file: `data/processed/matches/canonical_matches.csv`
- Metadata: `data/processed/matches/canonical_matches.csv.metadata.json`
- Source raw file: `data/raw/martj42/results.csv`
- Current processed rows: 49,425 settled matches.
- Date coverage: 1872-11-30 to 2026-06-16.
- Columns: `match_id`, `match_date`, `home_team`, `away_team`, `home_score`, `away_score`, `result_1x2`, `total_goals`, `tournament`, `city`, `country`, `neutral`, `source`, `source_match_id`.
- Intended use: baseline modeling, Elo updates, Poisson training, tournament filters, and reproducible historical backtests.
- Limitation: this table currently has match results only. It does not include odds, xG, lineups, injuries, market movement, or live situation signals.

### World Cup-only match table

- Processed file: `data/processed/matches/world_cup_matches.csv`
- Metadata: `data/processed/matches/world_cup_matches.csv.metadata.json`
- Source table: `data/processed/matches/canonical_matches.csv`
- Current processed rows: 984 FIFA World Cup matches.
- Date coverage: 1930-07-13 to 2026-06-16.
- Intended use: primary evaluation target for this project.
- Limitation: this is still result-only data. It does not include market odds or pre-match lineup/injury context.

### Project-generated Elo tables

- Elo history file: `data/processed/ratings/elo_history.csv`
- Elo history metadata: `data/processed/ratings/elo_history.csv.metadata.json`
- Current ratings file: `data/processed/ratings/current_elo_ratings.csv`
- Current ratings metadata: `data/processed/ratings/current_elo_ratings.csv.metadata.json`
- Elo 1X2 probability file: `data/processed/ratings/elo_1x2_probabilities.csv`
- Elo 1X2 probability metadata: `data/processed/ratings/elo_1x2_probabilities.csv.metadata.json`
- World Cup Elo 1X2 probability file: `data/processed/ratings/world_cup_elo_1x2_probabilities.csv`
- World Cup Elo 1X2 probability metadata: `data/processed/ratings/world_cup_elo_1x2_probabilities.csv.metadata.json`
- Calibrated World Cup Elo 1X2 probability file: `data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv`
- Calibrated World Cup Elo evaluation report: `reports/world_cup_elo_1x2_evaluation_calibrated.json`
- World Cup Elo draw calibration report: `reports/world_cup_elo_draw_calibration.json`
- Source table: `data/processed/matches/canonical_matches.csv`
- Current Elo history rows: 49,425 matches.
- Current team rating rows: 336 teams.
- Current Elo 1X2 probability rows: 49,425 matches.
- Current World Cup Elo 1X2 probability rows: 984 matches.
- Current Elo 1X2 average probabilities: home 39.18%, draw 23.87%, away 36.94%.
- Current simple-Elo top five: Argentina, Spain, France, England, Brazil.
- Intended use: model features, historical rating diagnostics, first-pass Elo 1X2 model scoring, and later calibration.
- Limitation: these are project-generated simple Elo ratings and heuristic Elo 1X2 probabilities, not official ratings, not market-validated, and not yet draw-calibrated.

### World Cup Elo evaluation report

- Report file: `reports/world_cup_elo_1x2_evaluation.json`
- Model name: `elo_heuristic_1x2_world_cup`
- Match count: 984 FIFA World Cup matches.
- Accuracy: 54.17%.
- Mean Brier score: 0.5867.
- Mean log loss: 0.9880.
- Actual result mix: home 449, draw 222, away 313.
- Predicted outcome mix: home 600, draw 0, away 384.
- Interpretation: useful as a first baseline, but the zero predicted draws are a clear sign that draw probability needs calibration before this can be treated as a serious World Cup 1X2 model.

### World Cup Elo draw calibration report

- Report file: `reports/world_cup_elo_draw_calibration.json`
- Calibrated probability file: `data/processed/ratings/world_cup_elo_1x2_probabilities_calibrated.csv`
- Calibration set: FIFA World Cup matches through 2014-12-31, 836 matches.
- Validation set: FIFA World Cup matches from 2018-01-01 through current snapshot, 148 matches.
- Objective: minimize calibration-set mean log loss.
- Grid size: 99 draw-probability candidates.
- Best draw config: base draw probability 0.28, draw gap penalty per 100 Elo 0.05, min draw 0.08, max draw 0.40.
- Full-sample calibrated accuracy: 54.17%.
- Full-sample calibrated mean Brier score: 0.5859.
- Full-sample calibrated mean log loss: 0.9861.
- Validation calibrated mean Brier score: 0.5966.
- Validation calibrated mean log loss: 1.0037.
- Interpretation: calibration slightly improves probability quality versus the uncalibrated heuristic, but not enough to claim a strong model. The project still needs market-odds comparison and richer World Cup-specific features.

### Market odds schema and demo comparison

- Canonical odds schema columns: `match_id`, `bookmaker`, `captured_at`, `home_odds`, `draw_odds`, `away_odds`, `odds_type`, `source`.
- Canonical kickoff timing schema columns: `match_id`, `kickoff_time`, `time_zone`, `precision`, `source`.
- Demo odds file: `examples/demo_world_cup_market_odds.csv`
- Demo odds time-series file: `examples/demo_world_cup_market_odds_timeseries.csv`
- Demo timing file: `examples/demo_world_cup_match_timing.csv`
- Demo comparison report: `reports/demo_market_comparison.json`
- Demo market movement feature report: `reports/demo_market_movement_features.csv`
- Demo match count: 3 matched rows, 981 unmatched model rows.
- Demo source note: the demo odds and kickoff times are synthetic and must not be used as historical market evidence.
- Implemented use: once real World Cup odds are available with `match_id` alignment, the project can devig market odds, score model and market probabilities on the same matches, and report Brier/log-loss deltas.
- Timing validation: odds comparisons can enforce `odds_captured_at <= prediction_time <= kickoff_time` for actionable pre-match backtests.
- Leakage labels: `low`, `medium`, and `high` leakage risk are reported in model-vs-market summaries.
- Closing odds rule: closing odds are rejected by default for actionable pre-match validation unless explicitly allowed; closing-market comparison is treated as market baseline research, not an early betting simulation.
- Market movement features: the project can compare two odds snapshots for the same match/bookmaker, such as opening and current odds, then emit overround deltas, devigged probability deltas, favorite changes, and largest probability moves.
- Intended market-signal use: market movement features are candidate inputs for the later World Cup prediction model and dashboard, especially for detecting price movement, steam, favorite flips, and market reaction to team news.
- Current blocker: no verified redistributable historical World Cup 1X2 odds dataset or full real kickoff timestamp dataset has been committed to the repository.
