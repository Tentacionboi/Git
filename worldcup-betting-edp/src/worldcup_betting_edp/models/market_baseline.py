"""Market baseline model for the 1X2 MVP."""

from __future__ import annotations

from worldcup_betting_edp.domain import MarketProbabilities, OddsSnapshot
from worldcup_betting_edp.market import proportional_devig


class MarketBaselineModel:
    """Use devigged bookmaker odds as the market probability baseline."""

    def __init__(self, *, devig_method: str = "proportional") -> None:
        if devig_method != "proportional":
            raise ValueError("MVP currently supports only proportional devig")
        self.devig_method = devig_method

    def predict(self, odds_snapshot: OddsSnapshot) -> MarketProbabilities:
        """Return market-implied probabilities for an odds snapshot."""
        result = proportional_devig(odds_snapshot.to_odds_map())
        return MarketProbabilities(
            match_id=odds_snapshot.match_id,
            method=result.method,
            odds=result.odds,
            implied_probabilities=result.implied_probabilities,
            probabilities=result.fair_probabilities,
            overround=result.overround,
        )

