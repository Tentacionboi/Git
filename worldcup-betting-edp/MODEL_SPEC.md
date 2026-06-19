# Model Specification

## MVP Target

Predict 90-minute 1X2 probabilities:

```text
P(home_win), P(draw), P(away_win)
```

The three probabilities must sum to 1.

## MVP Models

### 1. Market Baseline

Input:

- Decimal odds for home, draw, away.

Output:

- Raw implied probabilities.
- Overround.
- Devigged market probabilities.

Method:

```text
implied_i = 1 / odds_i
market_prob_i = implied_i / sum(implied)
```

### 2. Elo Baseline

Input:

- Team ratings before match.
- Neutral/home flag.
- Optional home advantage.

Output:

- 1X2 probability vector.
- Rating gap.
- Expected home score.
- Explicit `EloBasePrediction` diagnostics for structured reports.

Constraints:

- Must use only ratings available before the match.
- Draw probability must be explicitly modeled, not ignored.
- Elo is the base-strength layer. It is not the final probability when context
  and market calibration layers are available.

### 2B. Context-Adjusted Elo

Input:

- Elo base probabilities.
- Signed home-team context factors:
  - rest;
  - travel;
  - host / near-host;
  - recent form;
  - lineup availability.

Method:

```text
context_adjustment =
    w_rest   * rest_delta
  + w_travel * travel_delta
  + w_host   * host_delta
  + w_form   * recent_form_delta
  + w_lineup * lineup_delta

p_context = normalize_and_bound(p_elo + bounded_context_adjustment)
```

Constraints:

- Context adjusts Elo; it does not replace Elo.
- Missing, synthetic, blocked, or unverified context inputs do not change team
  probabilities.
- Evidence status affects confidence, not team strength.
- Weights must stay centralized in `ContextAdjustmentConfig` and be tuned only
  through backtests.

### 3. Poisson Goals Model

Input:

- Historical goals for/against.
- Team attack/defense strengths.
- Neutral/home flag.

Output:

- Score matrix.
- 1X2 probabilities.
- Optional totals/handicap probabilities later.

### 4. Market-Residual Model

Input:

- Market probabilities.
- Fundamental probabilities from Elo, Poisson, or a later ensemble.
- Optional market movement features.

Output:

- Final model probabilities.
- Residual adjustments versus market probability.

Initial rule:

```text
raw_adjustment_i =
    w_fundamental * (p_fundamental_i - p_market_i)
  + w_movement * market_movement_delta_i

p_final_i = normalize_and_bound(p_market_i + raw_adjustment_i)
```

The market is the anchor, not an ordinary weak feature. Fundamental and movement signals must only apply bounded residual adjustments until out-of-sample evidence proves they add value.

Market reports also classify model-vs-market alignment:

```text
market_aligned
mild_divergence
strong_divergence
```

The classification is explanatory and risk-control metadata. It does not prove
an edge by itself.

### 5. Simple Fusion

Simple weighted averaging remains a research baseline, not the preferred decision model:

```text
p_final = w_market*p_market + w_elo*p_elo + w_poisson*p_poisson
```

The market weight should start high. Do not pretend the market does not exist.

## Value Bet Rule

For outcome `i`:

```text
edge_prob_i = model_prob_i - market_prob_i
ev_i = model_prob_i * decimal_odds_i - 1
```

Candidate value bet if:

```text
edge_prob_i >= probability_edge_threshold
ev_i >= ev_threshold
kelly_fraction_i > 0
```

Default thresholds are intentionally conservative and may be tuned only through backtesting.

## Current Single-Match Output Contract

The single-match report preserves the flat dictionary contract with:

- match metadata;
- bookmaker and odds timestamp;
- 1X2 decimal odds;
- market overround;
- devigged market probabilities;
- model probabilities;
- model-minus-market deltas;
- value-bet flag;
- best value-bet direction;
- expected value;
- capped fractional Kelly fraction;
- risk level;
- decision reason;
- per-outcome EV, Kelly fraction, and reason.

It also exposes `to_structured_dict()` with:

- match metadata;
- data status;
- Elo base diagnostics;
- context adjustments;
- fundamental probabilities;
- goal-model placeholder until Poisson is implemented;
- market odds, devig probabilities, and alignment;
- residual final probabilities;
- confidence report;
- value-bet decision.
