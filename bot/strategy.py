class TrendStrategy:
    def __init__(
        self,
        fast_period=None,
        slow_period=None,
        fast_ema=None,
        slow_ema=None,
    ):
        self.fast_period = (
            fast_period
            if fast_period is not None
            else (fast_ema if fast_ema is not None else 20)
        )

        self.slow_period = (
            slow_period
            if slow_period is not None
            else (slow_ema if slow_ema is not None else 50)
        )

    @staticmethod
    def _ema(values, period):
        if len(values) < period:
            return None

        multiplier = 2 / (period + 1)

        ema = sum(values[:period]) / period

        for price in values[period:]:
            ema = (
                (price - ema) * multiplier
            ) + ema

        return ema

    def analyze(self, prices):
        if len(prices) < self.slow_period:
            return {
                "signal": "HOLD",
                "reason": "not enough data",
            }

        fast = self._ema(prices, self.fast_period)
        slow = self._ema(prices, self.slow_period)

        if fast > slow:
            return {
                "signal": "BUY",
                "reason": "fast EMA above slow EMA",
            }

        if fast < slow:
            return {
                "signal": "SELL",
                "reason": "fast EMA below slow EMA",
            }

        return {
            "signal": "HOLD",
            "reason": "EMA values equal",
        }
