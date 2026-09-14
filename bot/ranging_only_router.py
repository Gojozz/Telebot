from dataclasses import dataclass

from bot.regime import MarketRegimeDetector
from bot.research_strategies import (
    MeanReversionStrategy,
    DonchianBreakoutStrategy,
)


@dataclass
class RangingOnlyRouter:
    detector: MarketRegimeDetector = None
    mean_reversion_strategy: object = None
    breakout_strategy: object = None

    def __post_init__(self):
        if self.detector is None:
            self.detector = MarketRegimeDetector()

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

        if regime.regime == "RANGING":
            strategy = self.mean_reversion_strategy

        elif regime.regime == "HIGH_VOLATILITY":
            strategy = self.breakout_strategy

        else:
            return {
                "signal": "HOLD",
                "regime": regime.regime,
                "strategy": "none",
                "reason": (
                    "Ranging-only router blocks "
                    f"{regime.regime} regime"
                ),
                "regime_reason": regime.reason,
                "trend_strength": regime.trend_strength,
                "volatility_pct": regime.volatility_pct,
                "range_position": regime.range_position,
            }

        result = strategy.analyze(
            prices,
            highs=highs,
            lows=lows,
        )

        return {
            "signal": result.get("signal", "HOLD"),
            "regime": regime.regime,
            "strategy": type(strategy).__name__,
            "reason": result.get("reason", ""),
            "regime_reason": regime.reason,
            "trend_strength": regime.trend_strength,
            "volatility_pct": regime.volatility_pct,
            "range_position": regime.range_position,
        }
