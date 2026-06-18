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

Constraints:

- Must use only ratings available before the match.
- Draw probability must be explicitly modeled, not ignored.

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

The single-match MVP report returns a flat dictionary with:

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
