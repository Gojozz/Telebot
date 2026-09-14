class RegimeTrendStrategy:
    """
    V2-R: Regime-aware trend strategy.

    Entry requires:
    1. Fast EMA above slow EMA.
    2. ADX above minimum trend-strength threshold.
    3. ATR percentage above minimum volatility threshold.

    ADX measures directional strength, while ATR% prevents very small
    but extremely consistent price movements from being treated as
    tradable trends.
    """

    def __init__(
        self,
        fast_period=20,
        slow_period=50,
        adx_period=14,
        min_adx=20.0,
        min_atr_pct=0.005,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.min_adx = min_adx
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
    def _atr(highs, lows, closes, period):
        if len(closes) <= period:
            return None

        tr_values = []

        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            previous_close = closes[i - 1]

            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

            tr_values.append(true_range)

        if len(tr_values) < period:
            return None

        atr = sum(tr_values[:period]) / period

        for value in tr_values[period:]:
            atr = ((atr * (period - 1)) + value) / period

        return atr

    @staticmethod
    def _adx(highs, lows, closes, period):
        if len(closes) <= period * 2:
            return None

        tr_values = []
        plus_dm = []
        minus_dm = []

        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            previous_high = highs[i - 1]
            previous_low = lows[i - 1]
            previous_close = closes[i - 1]

            up_move = high - previous_high
            down_move = previous_low - low

            plus = up_move if up_move > down_move and up_move > 0 else 0.0
            minus = (
                down_move
                if down_move > up_move and down_move > 0
                else 0.0
            )

            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

            tr_values.append(true_range)
            plus_dm.append(plus)
            minus_dm.append(minus)

        if len(tr_values) < period * 2:
            return None

        atr = sum(tr_values[:period]) / period
        plus_smoothed = sum(plus_dm[:period]) / period
        minus_smoothed = sum(minus_dm[:period]) / period

        dx_values = []

        def calculate_dx(atr_value, plus_value, minus_value):
            if atr_value == 0:
                return 0.0

            plus_di = 100.0 * plus_value / atr_value
            minus_di = 100.0 * minus_value / atr_value

            denominator = plus_di + minus_di

            if denominator == 0:
                return 0.0

            return 100.0 * abs(plus_di - minus_di) / denominator

        dx_values.append(
            calculate_dx(
                atr,
                plus_smoothed,
                minus_smoothed,
            )
        )

        for i in range(period, len(tr_values)):
            atr = ((atr * (period - 1)) + tr_values[i]) / period

            plus_smoothed = (
                ((plus_smoothed * (period - 1)) + plus_dm[i])
                / period
            )

            minus_smoothed = (
                ((minus_smoothed * (period - 1)) + minus_dm[i])
                / period
            )

            dx_values.append(
                calculate_dx(
                    atr,
                    plus_smoothed,
                    minus_smoothed,
                )
            )

        if len(dx_values) < period:
            return None

        adx = sum(dx_values[:period]) / period

        for dx in dx_values[period:]:
            adx = ((adx * (period - 1)) + dx) / period

        return adx

    def analyze(self, prices, highs=None, lows=None):
        required = max(
            self.slow_period,
            self.adx_period * 2 + 1,
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

        fast = self._ema(
            prices,
            self.fast_period,
        )

        slow = self._ema(
            prices,
            self.slow_period,
        )

        adx = self._adx(
            highs,
            lows,
            prices,
            self.adx_period,
        )

        atr = self._atr(
            highs,
            lows,
            prices,
            self.adx_period,
        )

        if (
            fast is None
            or slow is None
            or adx is None
            or atr is None
        ):
            return {
                "signal": "HOLD",
                "reason": "indicators unavailable",
            }

        atr_pct = atr / prices[-1] if prices[-1] else 0.0

        if fast <= slow:
            return {
                "signal": "HOLD",
                "reason": "uptrend filter failed",
                "ema_fast": fast,
                "ema_slow": slow,
                "adx": adx,
                "atr_pct": atr_pct,
            }

        if adx < self.min_adx:
            return {
                "signal": "HOLD",
                "reason": "trend strength too weak",
                "ema_fast": fast,
                "ema_slow": slow,
                "adx": adx,
                "atr_pct": atr_pct,
            }

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
                "ema_fast": fast,
                "ema_slow": slow,
                "adx": adx,
                "atr_pct": atr_pct,
            }

        return {
            "signal": "BUY",
            "reason": "uptrend + strong regime + sufficient volatility",
            "ema_fast": fast,
            "ema_slow": slow,
            "adx": adx,
            "atr_pct": atr_pct,
        }
