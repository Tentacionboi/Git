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

## Doing

- [ ] Configure `API_FOOTBALL_KEY` locally and run the API-Football source probe.
- [ ] Design real-time odds ingestion plan for upcoming World Cup matches.

## Next

- [ ] If The Odds API is upgraded, rerun historical fetch for 2022-11-20T12:00:00Z.
- [ ] If not upgrading The Odds API, evaluate API-Football probe results.
- [ ] Store one raw historical odds JSON snapshot under `data/raw/odds/`, excluding API keys.
- [ ] Convert the first real The Odds API snapshot into canonical `MarketOddsSnapshot` CSV.
- [ ] Align The Odds API event IDs to project `match_id` values.
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
