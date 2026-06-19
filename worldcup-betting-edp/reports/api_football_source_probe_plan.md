# API-Football Source Probe Plan

Date: 2026-06-19

## Objective

Validate whether API-Football can be used as an alternate source for World Cup odds.

The probe is not trying to prove a model edge. It is only checking source feasibility:

- Can the API key access fixtures?
- Does API-Football identify the World Cup league and season cleanly?
- Does the odds endpoint return 1X2 pre-match odds for World Cup 2022?
- Do odds rows include useful update timestamps?
- Can returned odds be mapped to the project's canonical `MarketOddsSnapshot` schema?

## Implemented

- Parser: `src/worldcup_betting_edp/data/api_football.py`
- Client: `src/worldcup_betting_edp/data/api_football_client.py`
- Probe script: `scripts/probe_api_football_source.py`
- Environment variable: `API_FOOTBALL_KEY`

## Probe Command

After adding `API_FOOTBALL_KEY` to `.env`:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 scripts/probe_api_football_source.py \
  --league 1 \
  --season 2022 \
  --raw-output data/raw/source_probes/api_football/world_cup_2022_probe.json \
  --summary-output data/raw/source_probes/api_football/world_cup_2022_probe.summary.json \
  --canonical-output data/processed/source_probes/api_football/world_cup_2022_odds.csv
```

## Expected Decision Rules

API-Football is a serious candidate only if:

1. The key can access `/fixtures` for World Cup 2022.
2. The `/odds` endpoint returns bookmaker odds for `league=1&season=2022`.
3. Returned odds include complete Home/Draw/Away prices.
4. Returned odds include an `update` timestamp or other time semantics that can be used in no-leakage backtests.

If it returns only current/final odds without historical snapshot timestamps, it may still help future live monitoring, but it cannot replace The Odds API historical endpoint for rigorous 2022 backtests.
