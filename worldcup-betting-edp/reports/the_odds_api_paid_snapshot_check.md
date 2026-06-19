# The Odds API Paid Snapshot Check

Date: 2026-06-19

## Result

The paid The Odds API subscription successfully returned a historical FIFA World Cup 1X2 odds snapshot.

Requested snapshot:

```text
sport_key: soccer_fifa_world_cup
market: h2h
regions: us,uk,eu,au
requested_date: 2022-11-20T12:00:00Z
provider_snapshot_timestamp: 2022-11-20T11:55:38Z
```

Files generated locally but intentionally ignored by Git:

```text
data/raw/odds/the_odds_api/2022-11-20T120000Z.json
data/raw/odds/the_odds_api/2022-11-20T120000Z.json.metadata.json
data/processed/odds/the_odds_api/2022-11-20T120000Z.csv
data/processed/odds/the_odds_api/2022-11-20T120000Z_event_mapping.csv
data/processed/odds/the_odds_api/2022-11-20T120000Z_event_mapping.csv.summary.json
data/processed/odds/the_odds_api/2022-11-20T120000Z_canonical_odds.csv
```

## Snapshot Diagnostics

```text
source events: 48
mapped events: 48
unmapped events: 0
canonical 1X2 odds rows: 1737
matches with odds: 48
bookmakers: 42
```

The downloaded snapshot covers 48 2022 World Cup matches visible from the selected timestamp, not the full tournament. Later knockout-stage games were not yet known at 2022-11-20T11:55:38Z, so they are not expected to appear in this snapshot.

## Mapping Diagnostics

The event mapping linked every The Odds API event in the snapshot to the project's canonical World Cup match table.

Orientation check:

```text
same home/away orientation: 47
swapped home/away orientation: 1
```

The swapped match was:

```text
The Odds API: Netherlands vs Qatar
Canonical table: Qatar vs Netherlands
```

The remapping pipeline swaps home and away odds for this case before writing canonical odds.

## Project Interpretation

The project has now crossed the key data milestone: it can ingest a real paid historical World Cup odds snapshot, parse bookmaker 1X2 prices, map vendor event IDs to canonical match IDs, and preserve no-leakage snapshot timestamps.

This still does not prove model edge. It only means the project now has the data path needed to run real model-vs-market tests.

## Next Step

Build a small real historical backtest using this snapshot:

1. Select matches whose kickoff time is after `2022-11-20T11:55:38Z`.
2. Join canonical odds to settled World Cup results.
3. Use the existing Elo probabilities as the first fundamental model.
4. Compare:
   - market devigged probability,
   - Elo probability,
   - market-residual probability,
   - realized outcomes.
5. Report Brier score, log loss, and value-bet settlement.
