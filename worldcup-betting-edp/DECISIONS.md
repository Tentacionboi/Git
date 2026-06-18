# Decisions

## 2026-06-18: Treat EDP As Inspiration, Not As A Dependency

Decision: Do not vendor or depend on `ai-nurmamat/EDP` for MVP code.

Reason:

- EDP code is a prototype with API drift between README, examples, tests, and implementation.
- It does not include football data, model training, or backtesting.
- The useful ideas are simple enough to reimplement cleanly.

## 2026-06-18: MVP Market Is 90-Minute 1X2

Decision: MVP predicts 90-minute home/draw/away probabilities only.

Reason:

- It is the simplest market with clear mutually exclusive outcomes.
- It allows direct comparison to bookmaker probabilities.
- Handicap, totals, correct score, and qualification markets require richer distributions.

## 2026-06-18: Market Odds Are The Primary Benchmark

Decision: Every model must be evaluated against devigged market probabilities.

Reason:

- Betting markets already aggregate large amounts of public information.
- A model that cannot beat the market baseline is not useful for value betting.

## 2026-06-18: Use Standard Python Package Layout

Decision: Core code lives under `src/worldcup_betting_edp/`.

Reason:

- Avoid exposing generic top-level packages like `market` or `models`.
- Make the repository easier to publish, test, and install later.

## 2026-06-18: Establish Single-Match MVP Contract Before Data Ingestion

Decision: Build `Match`, `OddsSnapshot`, `ModelProbabilities`, `MarketProbabilities`, and `PredictionReport` before downloading real datasets.

Reason:

- Data, model, and backtest work need a shared interface.
- A tiny demo can validate the full prediction/value-bet output without waiting on external data.
- This prevents later threads from inventing incompatible schemas.

## 2026-06-18: Add Streamlit As The First Local UI

Decision: Build the first interactive panel in Streamlit rather than React or a notebook.

Reason:

- The current model code is Python-first.
- Streamlit is fast enough for a research dashboard and requires little UI infrastructure.
- A local panel is more usable for manual odds/probability exploration than a CLI-only flow.

## 2026-06-18: Use Bilingual Dashboard Labels

Decision: Keep English-first labels and add Chinese translations directly after them, for example `Market Odds / 市场赔率`.

Reason:

- GitHub readers can still understand the project in English.
- The project owner can operate and present the UI comfortably in Chinese.
- A fixed bilingual interface is simpler than language toggles at this stage.
