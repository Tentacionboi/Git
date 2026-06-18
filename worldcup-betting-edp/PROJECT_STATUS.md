# Project Status

Last updated: 2026-06-18

## One-Line Summary

This project is currently a bilingual, local, single-match World Cup 1X2 value-bet research dashboard. It is not yet a real-time odds monitor or an automatic prediction system.

## Current Capability

The project can:

- represent one football match with `Match`;
- represent one 1X2 decimal-odds snapshot with `OddsSnapshot`;
- convert bookmaker odds into implied probabilities and proportional devigged market probabilities;
- accept manually supplied model probabilities;
- compare model probabilities against market probabilities;
- calculate EV, full Kelly, fractional Kelly, capped stake fraction, risk level, and decision reasons;
- generate a flat single-match prediction report;
- run a local Streamlit dashboard with English-first bilingual labels.

## What It Does Not Do Yet

The project does not yet:

- scrape or monitor live odds;
- ingest real fixture feeds;
- auto-detect the next match;
- generate model probabilities from Elo;
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
│   └── single_match_demo.py
├── src/worldcup_betting_edp/
│   ├── domain.py
│   ├── market/devig.py
│   ├── betting/kelly.py
│   ├── models/market_baseline.py
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

## Current UI

Dashboard:

```text
http://localhost:8501
```

Run locally:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[ui]"
streamlit run apps/streamlit_app.py
```

The currently running development server was started from a temporary virtual environment under `/private/tmp/worldcup-edp-ui-venv312`.

## Verification

Latest test command:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest discover -s tests
```

Latest result:

```text
Ran 17 tests
OK
```

The Streamlit dashboard was also browser-verified with local Chrome automation. The latest screenshot path was:

```text
/private/tmp/worldcup_streamlit_dashboard_bilingual.png
```

## Current Git Situation

- Branch: `main`
- Remote: none configured
- This repository had no commits before the first checkpoint.
- The intended first commit is a local checkpoint containing the current project structure, research report, code, tests, and bilingual dashboard.

## Next Recommended Task

Implement JSON input schema and UI upload:

1. Add `examples/demo_single_match.json`.
2. Add `src/worldcup_betting_edp/data/prediction_input.py`.
3. Parse JSON into `Match`, `OddsSnapshot`, and `ModelProbabilities`.
4. Add tests for valid and invalid JSON.
5. Add `Upload JSON / 上传JSON` to the Streamlit sidebar.

This should happen before Elo, Poisson, live odds, or backtesting.

## Target End-State

The intended final system is:

```text
fixtures + odds snapshots + team/model data
        -> market probability baseline
        -> Elo / Poisson / fusion probabilities
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

Current priority: implement JSON input schema and Streamlit upload for single-match predictions. Do not start live odds monitoring, Elo, Poisson, or backtesting before the JSON input contract is complete.
```

