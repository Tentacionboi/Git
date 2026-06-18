# Data Sources

This file records candidate data sources, their expected use, and their risks.

## MVP-Ready Candidates

| Source | Use | Access | Reliability | Risk |
|---|---|---|---|---|
| openfootball/worldcup | World Cup schedule/results | GitHub | Medium-high | Text format parsing |
| martj42/international_results | Historical national-team results | GitHub CSV | Medium-high | Community maintained |
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

