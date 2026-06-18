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

### Project-generated Elo tables

- Elo history file: `data/processed/ratings/elo_history.csv`
- Elo history metadata: `data/processed/ratings/elo_history.csv.metadata.json`
- Current ratings file: `data/processed/ratings/current_elo_ratings.csv`
- Current ratings metadata: `data/processed/ratings/current_elo_ratings.csv.metadata.json`
- Source table: `data/processed/matches/canonical_matches.csv`
- Current Elo history rows: 49,425 matches.
- Current team rating rows: 336 teams.
- Current simple-Elo top five: Argentina, Spain, France, England, Brazil.
- Intended use: model features, historical rating diagnostics, and the next Elo-to-1X2 probability model.
- Limitation: these are project-generated simple Elo ratings, not official ratings and not yet calibrated to 1X2 probabilities.
