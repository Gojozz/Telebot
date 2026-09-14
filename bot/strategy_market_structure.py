class MarketStructureBOSRetestStrategy:
    """
    Market Structure v1:
    - Confirmed swing highs/lows using 2 bars left + 2 bars right.
    - Bullish break of structure (BOS) by candle close above latest swing high.
    - Entry only after a retest of the broken level.
    - Stop below the latest confirmed swing low before BOS.
    - Fixed 2R target.

    No EMA/RSI/Bollinger/ATR filters.
    """

    def __init__(
        self,
        swing_left=2,
        swing_right=2,
        retest_bars=10,
        reward_r=2.0,
    ):
        self.swing_left = swing_left
        self.swing_right = swing_right
        self.retest_bars = retest_bars
        self.reward_r = reward_r

    def _swing_high(self, highs, i):
        left = self.swing_left
        right = self.swing_right

        if i - left < 0 or i + right >= len(highs):
            return False

        value = float(highs[i])

        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if float(highs[j]) >= value:
                return False

        return True

    def _swing_low(self, lows, i):
        left = self.swing_left
        right = self.swing_right

        if i - left < 0 or i + right >= len(lows):
            return False

        value = float(lows[i])

        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if float(lows[j]) <= value:
                return False

        return True

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        n = len(prices)
        minimum = (
            self.swing_left
            + self.swing_right
            + 5
        )

        if n < minimum:
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        current_close = float(prices[-1])

        # Only pivots that are already fully confirmed may be used.
        last_confirmed = n - 1 - self.swing_right

        swing_highs = []
        swing_lows = []

        for i in range(
            self.swing_left,
            last_confirmed + 1,
        ):
            if self._swing_high(highs, i):
                swing_highs.append(i)

            if self._swing_low(lows, i):
                swing_lows.append(i)

        if not swing_highs or not swing_lows:
            return {
                "signal": "HOLD",
                "reason": "no confirmed market structure",
            }

        # Search chronologically for the most recent valid BOS.
        #
        # Important:
        # A BOS must break a swing high that existed BEFORE
        # the breakout candle. We must not use a newer swing
        # high created at or after the breakout itself.
        bos_idx = None
        breakout_level = None
        breakout_high_idx = None

        for high_idx in swing_highs:
            level = float(highs[high_idx])

            for i in range(high_idx + 1, n):
                if float(prices[i]) > level:
                    bos_idx = i
                    breakout_level = level
                    breakout_high_idx = high_idx
                    break

            if bos_idx is not None:
                break

        if bos_idx is None:
            return {
                "signal": "HOLD",
                "reason": "BOS not confirmed",
                "strategy": "MarketStructureBOSRetest",
            }

        # BOS must be recent enough for a retest.
        bars_since_bos = (n - 1) - bos_idx

        if bars_since_bos < 1:
            return {
                "signal": "HOLD",
                "reason": "waiting for retest",
                "strategy": "MarketStructureBOSRetest",
            }

        if bars_since_bos > self.retest_bars:
            return {
                "signal": "HOLD",
                "reason": "retest window expired",
                "strategy": "MarketStructureBOSRetest",
            }

        # Find the latest confirmed structural low before the BOS.
        structural_lows = [
            j for j in swing_lows
            if j < bos_idx
        ]

        if not structural_lows:
            return {
                "signal": "HOLD",
                "reason": "no structural stop",
                "strategy": "MarketStructureBOSRetest",
            }

        stop_idx = structural_lows[-1]
        stop = float(lows[stop_idx])

        # Retest must occur AFTER the BOS candle.
        for i in range(bos_idx + 1, n):
            candle_low = float(lows[i])
            candle_close = float(prices[i])

            if (
                candle_low <= breakout_level
                and candle_close > breakout_level
            ):
                risk_distance = candle_close - stop

                if risk_distance <= 0:
                    return {
                        "signal": "HOLD",
                        "reason": "invalid structural risk",
                        "strategy": "MarketStructureBOSRetest",
                    }

                return {
                    "signal": "BUY",
                    "reason": "bullish BOS retest",
                    "strategy": "MarketStructureBOSRetest",
                    "breakout_level": breakout_level,
                    "stop_distance": risk_distance,
                    "stop_price": stop,
                    "reward_r": self.reward_r,
                    "swing_high": breakout_level,
                    "swing_low": stop,
                    "bos_index": bos_idx,
                }

        return {
            "signal": "HOLD",
            "reason": "waiting for valid retest",
            "strategy": "MarketStructureBOSRetest",
        }
