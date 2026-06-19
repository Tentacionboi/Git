# Tasks

## Done

- [x] Build Phase 2 Python package skeleton.
- [x] Implement market odds and devig module.
- [x] Implement expected value and Kelly module.
- [x] Add unit tests for core math.
- [x] Define match schema.
- [x] Define odds snapshot schema.
- [x] Implement market baseline model.
- [x] Add a tiny demo input file.
- [x] Implement single-match prediction report.
- [x] Add Streamlit local dashboard.
- [x] Verify Streamlit dashboard in a local browser.
- [x] Add bilingual English/Chinese labels to the dashboard.
- [x] Define a JSON input format for one-match predictions.
- [x] Add JSON parser and validation tests.
- [x] Add Streamlit JSON upload for one-match predictions.
- [x] Add a CLI for one-match prediction.
- [x] Define result schema for settled historical matches.
- [x] Implement Brier score and log loss.
- [x] Implement flat-stake ROI for settled predictions.
- [x] Implement Kelly bankroll curve for settled predictions.
- [x] Define batch backtest input format.
- [x] Implement batch backtest runner.
- [x] Add batch backtest CLI command.
- [x] Add batch backtest output files.
- [x] Add Streamlit batch backtest page.
- [x] Add project screenshots for GitHub README.
- [x] Save a local Git checkpoint when permissions allow.
- [x] Configure GitHub remote and push.
- [x] Download martj42 international results data.
- [x] Parse martj42 international results data.
- [x] Build canonical historical match table.
- [x] Implement Elo ratings.
- [x] Generate processed Elo history and current rating tables.
- [x] Generate Elo-based 1X2 probabilities for historical matches.
- [x] Generate World Cup-only match and Elo probability tables.
- [x] Evaluate World Cup Elo 1X2 probability quality with Brier score and log loss.
- [x] Calibrate World Cup Elo draw probability with a historical train/validation split.
- [x] Add World Cup Elo calibration report.
- [x] Define canonical historical 1X2 market odds schema.
- [x] Implement model-vs-market probability comparison.
- [x] Add synthetic demo market comparison report.
- [x] Implement as-of/no-leakage timing validation for odds backtests.
- [x] Define canonical match kickoff timing schema.
- [x] Add synthetic kickoff timing demo for as-of market comparison.
- [x] Define demo market odds time-series input.
- [x] Implement market movement feature engineering.
- [x] Add synthetic market movement feature report.
- [x] Implement conservative market-residual probability model.
- [x] Add market-residual probabilities to single-match reports.
- [x] Add market-residual probability mode to the Streamlit dashboard.
- [x] Add market-residual probabilities to batch backtests.
- [x] Add fundamental-vs-market-vs-residual batch comparison metrics.
- [x] Add CLI and Streamlit batch controls for market-residual mode.
- [x] Audit candidate sources for real historical World Cup 1X2 odds.
- [x] Add The Odds API historical World Cup 1X2 odds parser.
- [x] Document why Football-Data is not currently enough for World Cup odds evidence.
- [x] Add safe local API-key environment variable flow.
- [x] Add one-shot The Odds API historical snapshot fetch script.
- [x] Add `.env` auto-loading and sanitized API error diagnostics.
- [x] Run a real The Odds API historical fetch permission check with local `.env`.
- [x] Confirm the current The Odds API key is on a free plan without historical odds access.
- [x] Add API-Football odds parser, client, and source-probe script.
- [x] Add API-Football source-probe plan.
- [x] Verify paid The Odds API historical access.
- [x] Download one real 2022 World Cup historical 1X2 odds snapshot.
- [x] Map The Odds API event IDs to canonical World Cup match IDs.
- [x] Generate canonical-orientation World Cup odds rows from the paid snapshot.
- [x] Run the first real 2022 World Cup model-vs-market backtest.
- [x] Write first real market backtest report.
- [x] Add Elo base single-match diagnostics.
- [x] Add context-adjusted Elo module with bounded factors.
- [x] Add evidence status and confidence schema.
- [x] Add structured single-match report output while preserving flat compatibility.
- [x] Add market alignment classification to single-match reports.

## Doing

- [ ] Design a multi-timestamp odds backtest plan.
- [ ] Implement Poisson score matrix model as the next model layer.
- [ ] Design real-time odds ingestion plan for upcoming World Cup matches.

## Next

- [ ] Fetch additional 2022 snapshots: open-ish, 24h before, 6h before, and near-close where available.
- [ ] Restrict value-bet settlement to one bookmaker or a clearly executable bookmaker set.
- [ ] Add confidence intervals/bootstrap sensitivity for ROI and scoring.
- [ ] Add Poisson top scorelines, totals, and BTTS to structured reports.
- [ ] Add verified real kickoff timestamps for World Cup matches.
- [ ] Add World Cup era/time-split evaluation.
- [ ] Add market movement features to model-vs-market reports.
- [ ] Add market movement signals to the Streamlit dashboard.
- [ ] Evaluate market-residual probabilities on real historical odds once available.

## Later

- [ ] Implement Poisson goals model.
- [ ] Implement trainable residual/fusion model.
- [ ] Implement historical backtest.
- [ ] Add charts and report generation.

## Blocked / Needs Verification

- [ ] Confirm a reproducible source for historical World Cup odds.
- [ ] Confirm licensing constraints for any odds data used in public repo.
- [ ] Decide whether to include Shin devig in MVP or keep it as research-only.
