class MomentumVolatilityStrategy:
    """
    Strategy v2:
    - Trend: fast EMA above slow EMA
    - Momentum: RSI above threshold but below overbought
    - Volatility: ATR as percentage of price above minimum
    """

    def __init__(
        self,
        fast_period=20,
        slow_period=50,
        rsi_period=14,
        rsi_min=52.0,
        rsi_max=70.0,
        atr_period=14,
        min_atr_pct=0.005,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.atr_period = atr_period
        self.min_atr_pct = min_atr_pct

    @staticmethod
    def _ema(values, period):
        if len(values) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period

        for price in values[period:]:
            ema = ((price - ema) * multiplier) + ema

        return ema

    @staticmethod
    def _rsi(values, period):
        if len(values) <= period:
            return None

        gains = []
        losses = []

        for i in range(1, len(values)):
            change = values[i] - values[i - 1]

            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _atr(highs, lows, closes, period):
        if len(closes) <= period:
            return None

        true_ranges = []

        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            previous_close = closes[i - 1]

            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

            true_ranges.append(true_range)

        if len(true_ranges) < period:
            return None

        atr = sum(true_ranges[:period]) / period

        for tr in true_ranges[period:]:
            atr = ((atr * (period - 1)) + tr) / period

        return atr

    def analyze(self, prices, highs=None, lows=None):
        required = max(
            self.slow_period,
            self.rsi_period + 1,
            self.atr_period + 1,
        )

        if len(prices) < required:
            return {
                "signal": "HOLD",
                "reason": "not enough data",
            }

        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        fast = self._ema(prices, self.fast_period)
        slow = self._ema(prices, self.slow_period)
        rsi = self._rsi(prices, self.rsi_period)
        atr = self._atr(highs, lows, prices, self.atr_period)

        if fast is None or slow is None or rsi is None or atr is None:
            return {
                "signal": "HOLD",
                "reason": "indicators unavailable",
            }

        atr_pct = atr / prices[-1]

        if fast <= slow:
            return {
                "signal": "HOLD",
                "reason": "trend filter failed",
                "ema_fast": fast,
                "ema_slow": slow,
                "rsi": rsi,
                "atr_pct": atr_pct,
            }

        if rsi < self.rsi_min:
            return {
                "signal": "HOLD",
                "reason": "momentum too weak",
                "ema_fast": fast,
                "ema_slow": slow,
                "rsi": rsi,
                "atr_pct": atr_pct,
            }

        if rsi >= self.rsi_max:
            return {
                "signal": "HOLD",
                "reason": "momentum overbought",
                "ema_fast": fast,
                "ema_slow": slow,
                "rsi": rsi,
                "atr_pct": atr_pct,
            }

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
                "ema_fast": fast,
                "ema_slow": slow,
                "rsi": rsi,
                "atr_pct": atr_pct,
            }

        return {
            "signal": "BUY",
            "reason": "trend + momentum + volatility confirmed",
            "ema_fast": fast,
            "ema_slow": slow,
            "rsi": rsi,
            "atr_pct": atr_pct,
        }
