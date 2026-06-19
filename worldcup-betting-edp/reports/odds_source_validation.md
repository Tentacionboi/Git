# Odds Source Validation

Date: 2026-06-19

## Executive Verdict

The project still does not have a committed, verified, redistributable historical World Cup odds dataset.

The best identified route for real World Cup 1X2 odds is The Odds API historical endpoint because it provides time-stamped snapshots and a World Cup sport key. The practical blocker is access: historical odds require paid API access.

Football-Data is useful for league-level football betting research, but it is not enough to support this project's World Cup market-edge claims. Treat it as a league modeling sandbox, not as verified historical World Cup odds evidence.

## Source Checks

### Football-Data

Source: `https://www.football-data.co.uk/data.php`

What it provides:

- long-running football results and betting odds files;
- public CSV/XLSX-style downloads;
- strong usefulness for league model experiments and general betting-system infrastructure.

Current World Cup finding:

- the site resource list exposes a `WorldCup2026.xlsx` link;
- the audited file returned an effectively empty XLSX body during this check;
- no verified historical World Cup 1X2 odds table was identified from this source.

Project decision:

- do not use Football-Data as the core World Cup historical odds source yet;
- do not claim a World Cup odds backtest from Football-Data unless the specific World Cup odds file and fields are later verified.

### The Odds API

Sources:

- `https://the-odds-api.com/`
- `https://the-odds-api.com/historical-odds-data/`

What it provides:

- structured JSON odds snapshots;
- historical endpoint with a `date` parameter;
- decimal odds support when requested with `oddsFormat=decimal`;
- World Cup sport key: `soccer_fifa_world_cup`;
- historical coverage for this sport key starting from 2022-04-03 according to its public historical coverage table.

Why it is a good fit:

- it directly addresses odds-time leakage because every request is tied to a timestamp;
- raw JSON snapshots can be stored under `data/raw/odds/` with metadata;
- parsed odds can be converted into the existing canonical schema:
  - `match_id`
  - `bookmaker`
  - `captured_at`
  - `home_odds`
  - `draw_odds`
  - `away_odds`
  - `odds_type`
  - `source`

Limitations:

- historical access is paid;
- API keys must not be committed;
- vendor terms may restrict redistribution of raw odds payloads;
- The Odds API event IDs must still be aligned to the project's canonical World Cup `match_id`.

Implemented in this repository:

- `src/worldcup_betting_edp/data/the_odds_api.py`
- `parse_the_odds_api_historical_odds_response(...)`
- `build_the_odds_api_historical_odds_url(...)`
- unit tests covering complete 1X2 parsing, incomplete-market skipping, decimal-odds enforcement, and URL generation.

### OddsPortal / BetExplorer / Similar Odds Websites

These sites may expose useful historical odds visually, but they are not ideal as the core public repo data source unless the data can be obtained through permitted export or licensing.

Main issues:

- scraping terms and anti-bot rules are uncertain;
- timestamps are often less clean than API snapshots;
- reproducibility for a public GitHub project is weaker;
- manually scraped data would be hard for another researcher to regenerate.

Project decision:

- keep these as manual cross-check candidates;
- do not make them the primary source for a GitHub-facing MVP.

## No-Leakage Rule

For any real market backtest:

1. A prediction must have a `prediction_time`.
2. A match must have a `kickoff_time`.
3. An odds row must have `captured_at`.
4. The valid pre-match condition is:

```text
captured_at <= prediction_time <= kickoff_time
```

Closing odds can be used for market-strength comparison, but they should not be treated as actionable early betting signals unless the strategy explicitly bets at or near close.

## Recommended Next Step

Use The Odds API as the first real odds ingestion route if the project owner is willing to obtain historical access.

Minimum next engineering step after access:

1. Fetch one World Cup historical snapshot for a known 2022 match day.
2. Store the raw JSON plus metadata under `data/raw/odds/the_odds_api/`.
3. Parse it with `parse_the_odds_api_historical_odds_response`.
4. Write canonical CSV under `data/processed/odds/`.
5. Build an event-ID-to-canonical-match-ID mapping.
6. Run a tiny model-vs-market backtest on a few verified matches.

Until this is done, the system remains a research dashboard and modeling framework, not evidence of a market-beating World Cup betting model.
