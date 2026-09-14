from dataclasses import dataclass


def _ema(values, period):
    if len(values) < period:
        return None

    alpha = 2.0 / (period + 1.0)
    value = float(values[0])

    for price in values[1:]:
        value = alpha * float(price) + (1.0 - alpha) * value

    return value


def _atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None

    trs = []

    for i in range(1, len(closes)):
        high = float(highs[i])
        low = float(lows[i])
        previous_close = float(closes[i - 1])

        trs.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )

    if len(trs) < period:
        return None

    return sum(trs[-period:]) / period


@dataclass
class VolatilityBreakoutStrategy:
    lookback: int = 20
    atr_period: int = 14
    breakout_buffer: float = 0.001
    min_atr_pct: float = 0.005

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        minimum = max(
            self.lookback + 1,
            self.atr_period + 1,
        )

        if len(prices) < minimum:
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        current_close = float(prices[-1])

        previous_highs = [
            float(value)
            for value in highs[-self.lookback - 1:-1]
        ]

        if not previous_highs:
            return {
                "signal": "HOLD",
                "reason": "insufficient breakout window",
            }

        breakout_level = max(previous_highs)

        atr = _atr(
            highs,
            lows,
            prices,
            period=self.atr_period,
        )

        if atr is None or current_close <= 0:
            return {
                "signal": "HOLD",
                "reason": "ATR unavailable",
            }

        atr_pct = atr / current_close

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility expansion too weak",
            }

        required_price = (
            breakout_level
            * (1.0 + self.breakout_buffer)
        )

        if current_close > required_price:
            return {
                "signal": "BUY",
                "reason": "volatility breakout confirmed",
            }

        return {
            "signal": "HOLD",
            "reason": "breakout not confirmed",
        }


@dataclass
class MomentumRegimeStrategy:
    fast_period: int = 10
    slow_period: int = 50
    momentum_period: int = 10
    atr_period: int = 14
    min_momentum: float = 0.005
    min_atr_pct: float = 0.004

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        minimum = max(
            self.slow_period,
            self.momentum_period + 1,
            self.atr_period + 1,
        )

        if len(prices) < minimum:
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        current_close = float(prices[-1])

        fast = _ema(
            prices,
            self.fast_period,
        )

        slow = _ema(
            prices,
            self.slow_period,
        )

        atr = _atr(
            highs,
            lows,
            prices,
            period=self.atr_period,
        )

        reference_price = float(
            prices[-self.momentum_period - 1]
        )

        if (
            fast is None
            or slow is None
            or atr is None
            or reference_price <= 0
            or current_close <= 0
        ):
            return {
                "signal": "HOLD",
                "reason": "indicator unavailable",
            }

        momentum = (
            current_close - reference_price
        ) / reference_price

        atr_pct = atr / current_close

        if fast <= slow:
            return {
                "signal": "HOLD",
                "reason": "trend regime failed",
            }

        if momentum < self.min_momentum:
            return {
                "signal": "HOLD",
                "reason": "momentum too weak",
            }

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
            }

        return {
            "signal": "BUY",
            "reason": "positive momentum regime",
        }
