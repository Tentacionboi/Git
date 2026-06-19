# Roadmap

## Phase 1: Research And Project Initialization

Status: Done.

Deliverables:

- Project structure.
- Initial EDP repository audit.
- Initial research report.
- MVP direction: 90-minute 1X2 World Cup market.

## Phase 2: MVP Engineering Foundation

Status: Done. Core single-match engine, batch backtest loop, CLI, and bilingual Streamlit dashboard are working.

Deliverables:

- Python package skeleton.
- Market odds conversion and devig functions.
- Expected value and fractional Kelly functions.
- Data schemas for matches and odds snapshots.
- Tests for core probability and betting math.
- Local bilingual Streamlit dashboard.
- JSON input schema and upload flow.

Exit criteria:

- `PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest discover -s tests` passes.
- One match can be represented as odds + model probabilities + value bet decision.
- The dashboard can load one prediction input from JSON.

## Phase 3: Data Pipeline

Status: In progress. martj42 international results have been downloaded, parsed, converted into a canonical processed match table, and sliced into a World Cup-only evaluation table.

Deliverables:

- Download and parse public international match results.
- Download and parse World Cup schedules/results.
- Build canonical match table.
- Record source metadata and licenses.

Exit criteria:

- Historical matches can be loaded into a single dataframe-like table. Done for the martj42 snapshot.
- Every row has date, teams, score, tournament, neutral flag. Done for the martj42 snapshot.
- World Cup-only matches can be loaded as the primary project evaluation target. Done for the martj42 snapshot.

## Phase 4: Baseline Models

Status: In progress. Market baseline exists, and a deterministic Elo rating engine now produces historical rating tables plus first-pass and calibrated 1X2 probabilities. World Cup-only Elo evaluation, draw calibration, model-vs-market comparison code, odds timing validation, kickoff timing schema, market movement feature engineering, and a conservative market-residual probability model exist. Single-match reports and the Streamlit dashboard can use residual final probabilities for EV/Kelly decisions. Verified real historical World Cup odds and exact kickoff timestamps are still pending.

Deliverables:

- Market baseline.
- Elo model. Rating engine, first-pass 1X2 probability split, World Cup evaluation, and draw calibration done.
- Model-vs-market comparison. Code, no-leakage timing validation, kickoff timing schema, and market movement features done for supplied odds snapshots; real historical World Cup odds and exact kickoff timestamps pending.
- Market-residual probability model. Conservative bounded adjustment from market probability using fundamental and movement signals done; single-match report and UI integration done; historical batch integration pending.
- Poisson goals model.
- Simple probability fusion or trained residual model.

Exit criteria:

- Each model outputs calibrated 1X2 probabilities.
- Each model can be evaluated against the same historical fixtures.

## Phase 5: Backtesting

Deliverables:

- Brier score.
- Log loss.
- Calibration curve data.
- ROI.
- Flat-stake curve.
- Fractional Kelly curve.
- Max drawdown.

Exit criteria:

- Model vs market comparison is reproducible.
- Results can be regenerated from raw inputs.

## Phase 6: Public GitHub Packaging

Deliverables:

- Polished README.
- Reproducible demo.
- Example report.
- Clear limitations.
- CI tests.

Exit criteria:

- A new user can clone the repo, run tests, and run a demo without private data.
