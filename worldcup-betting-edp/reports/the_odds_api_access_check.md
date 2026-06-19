# The Odds API Access Check

Date: 2026-06-19

## Check

The local `.env` file was configured with `THE_ODDS_API_KEY`, and the project ran the historical World Cup 1X2 fetch script:

```text
scripts/fetch_the_odds_api_snapshot.py
```

Requested snapshot:

```text
sport_key: soccer_fifa_world_cup
market: h2h
date: 2022-11-20T12:00:00Z
```

## Result

The API request reached The Odds API, but the provider rejected the historical endpoint with:

```text
status_code: 401
error_code: HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN
message: Historical odds are only available on paid usage plans.
```

No raw odds JSON file or canonical odds CSV was written.

## Interpretation

The current key works as a syntactically valid The Odds API key, but it does not have historical odds access.

This is a vendor-plan limitation, not a modeling issue and not a project parser issue.

## Project Decision

The next branch in the roadmap is binary:

1. Upgrade The Odds API to a plan with historical odds, then rerun the same fetch command.
2. If not upgrading, validate an alternate source such as API-Football for World Cup odds and historical timestamp coverage.

Until one of those is done, the project cannot run a real World Cup model-vs-market historical backtest.
