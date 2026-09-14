from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeResult:
    regime: str
    trend_strength: float
    volatility_pct: float
    range_position: float
    reason: str


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
class MarketRegimeDetector:
    fast_period: int = 20
    slow_period: int = 50
    atr_period: int = 14
    range_period: int = 50

    trend_threshold: float = 0.01
    high_volatility_threshold: float = 0.03

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return RegimeResult(
                regime="UNCERTAIN",
                trend_strength=0.0,
                volatility_pct=0.0,
                range_position=0.0,
                reason="OHLC data required",
            )

        minimum = max(
            self.slow_period,
            self.atr_period + 1,
            self.range_period,
        )

        if len(prices) < minimum:
            return RegimeResult(
                regime="UNCERTAIN",
                trend_strength=0.0,
                volatility_pct=0.0,
                range_position=0.0,
                reason="insufficient data",
            )

        closes = [float(value) for value in prices]
        current_close = closes[-1]

        if current_close <= 0:
            return RegimeResult(
                regime="UNCERTAIN",
                trend_strength=0.0,
                volatility_pct=0.0,
                range_position=0.0,
                reason="invalid price",
            )

        fast = _ema(closes, self.fast_period)
        slow = _ema(closes, self.slow_period)
        atr = _atr(highs, lows, closes, self.atr_period)

        if fast is None or slow is None or atr is None:
            return RegimeResult(
                regime="UNCERTAIN",
                trend_strength=0.0,
                volatility_pct=0.0,
                range_position=0.0,
                reason="indicator unavailable",
            )

        trend_strength = abs(fast - slow) / current_close
        volatility_pct = atr / current_close

        recent_highs = [
            float(value)
            for value in highs[-self.range_period:]
        ]
        recent_lows = [
            float(value)
            for value in lows[-self.range_period:]
        ]

        range_high = max(recent_highs)
        range_low = min(recent_lows)

        range_size = range_high - range_low

        if range_size <= 0:
            range_position = 0.5
        else:
            range_position = (
                (current_close - range_low) / range_size
            )

        if volatility_pct >= self.high_volatility_threshold:
            return RegimeResult(
                regime="HIGH_VOLATILITY",
                trend_strength=trend_strength,
                volatility_pct=volatility_pct,
                range_position=range_position,
                reason="ATR volatility above high-volatility threshold",
            )

        if trend_strength >= self.trend_threshold:
            return RegimeResult(
                regime="TRENDING",
                trend_strength=trend_strength,
                volatility_pct=volatility_pct,
                range_position=range_position,
                reason="EMA separation indicates directional market",
            )

        return RegimeResult(
            regime="RANGING",
            trend_strength=trend_strength,
            volatility_pct=volatility_pct,
            range_position=range_position,
            reason="low trend strength and normal volatility",
        )
