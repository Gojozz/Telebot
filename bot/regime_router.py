from dataclasses import dataclass

from bot.regime import MarketRegimeDetector
from bot.research_strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    DonchianBreakoutStrategy,
)


@dataclass
class RegimeRouter:
    detector: MarketRegimeDetector = None
    trend_strategy: object = None
    mean_reversion_strategy: object = None
    breakout_strategy: object = None

    def __post_init__(self):
        if self.detector is None:
            self.detector = MarketRegimeDetector()

        if self.trend_strategy is None:
            self.trend_strategy = TrendFollowingStrategy()

        if self.mean_reversion_strategy is None:
            self.mean_reversion_strategy = MeanReversionStrategy()

        if self.breakout_strategy is None:
            self.breakout_strategy = DonchianBreakoutStrategy()

    def analyze(self, prices, highs=None, lows=None):
        regime = self.detector.analyze(
            prices,
            highs=highs,
            lows=lows,
        )

        if regime.regime == "TRENDING":
            strategy_result = self.trend_strategy.analyze(
                prices,
                highs=highs,
                lows=lows,
            )

        elif regime.regime == "RANGING":
            strategy_result = self.mean_reversion_strategy.analyze(
                prices,
                highs=highs,
                lows=lows,
            )

        elif regime.regime == "HIGH_VOLATILITY":
            strategy_result = self.breakout_strategy.analyze(
                prices,
                highs=highs,
                lows=lows,
            )

        else:
            return {
                "signal": "HOLD",
                "regime": regime.regime,
                "strategy": "none",
                "reason": regime.reason,
            }

        return {
            "signal": strategy_result.get("signal", "HOLD"),
            "regime": regime.regime,
            "strategy": type(
                self._strategy_for_regime(regime.regime)
            ).__name__,
            "reason": strategy_result.get("reason", ""),
            "regime_reason": regime.reason,
            "trend_strength": regime.trend_strength,
            "volatility_pct": regime.volatility_pct,
            "range_position": regime.range_position,
        }

    def _strategy_for_regime(self, regime):
        if regime == "TRENDING":
            return self.trend_strategy

        if regime == "RANGING":
            return self.mean_reversion_strategy

        if regime == "HIGH_VOLATILITY":
            return self.breakout_strategy

        return self.trend_strategy
