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

Status: In progress. martj42 international results have been downloaded and parsed.

Deliverables:

- Download and parse public international match results.
- Download and parse World Cup schedules/results.
- Build canonical match table.
- Record source metadata and licenses.

Exit criteria:

- Historical matches can be loaded into a single dataframe-like table.
- Every row has date, teams, score, tournament, neutral flag.

## Phase 4: Baseline Models

Deliverables:

- Market baseline.
- Elo model.
- Poisson goals model.
- Simple probability fusion.

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
