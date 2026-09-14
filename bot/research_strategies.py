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
        prev_close = float(closes[i - 1])

        trs.append(
            max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
        )

    if len(trs) < period:
        return None

    return sum(trs[-period:]) / period


@dataclass
class TrendFollowingStrategy:
    fast_period: int = 20
    slow_period: int = 50

    def analyze(self, prices, highs=None, lows=None):
        if len(prices) < self.slow_period:
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        fast = _ema(prices, self.fast_period)
        slow = _ema(prices, self.slow_period)

        if fast is None or slow is None:
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        if fast > slow:
            return {
                "signal": "BUY",
                "reason": "fast EMA above slow EMA",
            }

        return {
            "signal": "HOLD",
            "reason": "trend filter failed",
        }


@dataclass
class DonchianBreakoutStrategy:
    """
    Donchian breakout with ATR-based risk management.

    Signal:
        BUY when current close breaks above the highest high
        of the previous `lookback` candles.

    Risk:
        stop distance = ATR(period) * atr_stop_mult

    The backtester uses the returned stop_distance and reward_r
    to construct the actual order.
    """

    lookback: int = 20
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    reward_r: float = 2.0
    min_atr_pct: float = 0.005

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        required = max(self.lookback + 1, self.atr_period + 1)

        if len(prices) < required:
            return {
                "signal": "HOLD",
                "reason": "insufficient OHLC data",
            }

        current_close = float(prices[-1])

        if current_close <= 0:
            return {
                "signal": "HOLD",
                "reason": "invalid price",
            }

        previous_highs = [
            float(value)
            for value in highs[-self.lookback - 1:-1]
        ]

        if len(previous_highs) < self.lookback:
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

        if atr is None or atr <= 0:
            return {
                "signal": "HOLD",
                "reason": "ATR unavailable",
            }

        atr_pct = atr / current_close

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
                "atr": atr,
                "atr_pct": atr_pct,
            }

        if current_close > breakout_level:
            stop_distance = atr * self.atr_stop_mult

            return {
                "signal": "BUY",
                "reason": "Donchian breakout",
                "breakout_level": breakout_level,
                "atr": atr,
                "atr_pct": atr_pct,
                "stop_distance": stop_distance,
                "reward_r": self.reward_r,
                "strategy": "DonchianATR",
            }

        return {
            "signal": "HOLD",
            "reason": "breakout not confirmed",
            "breakout_level": breakout_level,
            "atr": atr,
            "atr_pct": atr_pct,
        }

@dataclass
class MeanReversionStrategy:
    ema_period: int = 20
    deviation_pct: float = 0.015
    min_atr_pct: float = 0.003

    def analyze(self, prices, highs=None, lows=None):
        if len(prices) < max(self.ema_period, 15):
            return {
                "signal": "HOLD",
                "reason": "insufficient data",
            }

        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        current_close = float(prices[-1])
        ema = _ema(prices, self.ema_period)

        atr = _atr(
            highs,
            lows,
            prices,
            period=14,
        )

        if ema is None or atr is None or current_close <= 0:
            return {
                "signal": "HOLD",
                "reason": "indicator unavailable",
            }

        atr_pct = atr / current_close

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
            }

        distance = (current_close - ema) / ema

        if distance <= -self.deviation_pct:
            return {
                "signal": "BUY",
                "reason": "price below EMA mean",
            }

        return {
            "signal": "HOLD",
            "reason": "mean reversion condition not met",
        }


@dataclass
class BollingerMeanReversionStrategy:
    """
    Bollinger mean-reversion with an EMA regime filter.

    Entry:
      - price closes at/below lower Bollinger Band
      - price is not in a strong bearish regime
      - ATR is available

    Risk:
      - ATR-based stop
      - reward_r supplied to the backtester
    """
    bb_period: int = 20
    bb_std: float = 2.0
    regime_ema_period: int = 50
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    reward_r: float = 1.5
    min_atr_pct: float = 0.003

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {
                "signal": "HOLD",
                "reason": "OHLC data required",
            }

        required = max(
            self.bb_period,
            self.regime_ema_period,
            self.atr_period + 1,
        )

        if len(prices) < required:
            return {
                "signal": "HOLD",
                "reason": "insufficient OHLC data",
            }

        closes = [float(x) for x in prices]
        current_close = closes[-1]

        if current_close <= 0:
            return {
                "signal": "HOLD",
                "reason": "invalid price",
            }

        bb_window = closes[-self.bb_period:]
        middle = sum(bb_window) / self.bb_period

        variance = sum(
            (x - middle) ** 2 for x in bb_window
        ) / self.bb_period

        std = variance ** 0.5
        lower_band = middle - (self.bb_std * std)
        upper_band = middle + (self.bb_std * std)

        regime_ema = _ema(
            closes,
            self.regime_ema_period,
        )

        atr = _atr(
            highs,
            lows,
            closes,
            period=self.atr_period,
        )

        if regime_ema is None or atr is None or atr <= 0:
            return {
                "signal": "HOLD",
                "reason": "indicator unavailable",
            }

        atr_pct = atr / current_close

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
                "atr": atr,
                "atr_pct": atr_pct,
            }

        # Regime filter:
        # Do not fade a strong bearish regime.
        if current_close < regime_ema:
            return {
                "signal": "HOLD",
                "reason": "bearish regime filter",
                "middle_band": middle,
                "lower_band": lower_band,
                "upper_band": upper_band,
                "regime_ema": regime_ema,
                "atr": atr,
                "atr_pct": atr_pct,
            }

        if current_close <= lower_band:
            stop_distance = atr * self.atr_stop_mult

            return {
                "signal": "BUY",
                "reason": "Bollinger lower-band mean reversion",
                "middle_band": middle,
                "lower_band": lower_band,
                "upper_band": upper_band,
                "regime_ema": regime_ema,
                "atr": atr,
                "atr_pct": atr_pct,
                "stop_distance": stop_distance,
                "reward_r": self.reward_r,
                "strategy": "BollingerMR",
            }

        return {
            "signal": "HOLD",
            "reason": "mean reversion condition not met",
            "middle_band": middle,
            "lower_band": lower_band,
            "upper_band": upper_band,
            "regime_ema": regime_ema,
            "atr": atr,
            "atr_pct": atr_pct,
        }


@dataclass
class VolatilityBreakoutStrategy:
    """
    Volatility expansion breakout using a rolling price channel
    with ATR-based risk management.

    Entry:
      - close breaks above the previous upper channel
      - ATR percentage is above the minimum volatility threshold

    Risk:
      - ATR-based stop
      - fixed reward multiple
    """
    channel_period: int = 20
    channel_std: float = 2.0
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    reward_r: float = 2.0
    min_atr_pct: float = 0.005

    def analyze(self, prices, highs=None, lows=None):
        if highs is None or lows is None:
            return {"signal": "HOLD", "reason": "OHLC data required"}

        required = max(
            self.channel_period + 1,
            self.atr_period + 1,
        )

        if len(prices) < required:
            return {"signal": "HOLD", "reason": "insufficient OHLC data"}

        closes = [float(x) for x in prices]
        current_close = closes[-1]

        if current_close <= 0:
            return {"signal": "HOLD", "reason": "invalid price"}

        # IMPORTANT:
        # Use the channel from candles BEFORE the current candle.
        # This prevents the current close from defining its own breakout.
        previous_window = closes[-self.channel_period - 1:-1]

        middle = sum(previous_window) / len(previous_window)

        variance = sum(
            (x - middle) ** 2
            for x in previous_window
        ) / len(previous_window)

        std = variance ** 0.5
        upper_band = middle + (self.channel_std * std)

        atr = _atr(
            highs,
            lows,
            closes,
            period=self.atr_period,
        )

        if atr is None or atr <= 0:
            return {"signal": "HOLD", "reason": "indicator unavailable"}

        atr_pct = atr / current_close

        if atr_pct < self.min_atr_pct:
            return {
                "signal": "HOLD",
                "reason": "volatility too low",
                "atr": atr,
                "atr_pct": atr_pct,
                "upper_band": upper_band,
            }

        if current_close > upper_band:
            stop_distance = atr * self.atr_stop_mult

            return {
                "signal": "BUY",
                "reason": "volatility breakout",
                "upper_band": upper_band,
                "middle_band": middle,
                "atr": atr,
                "atr_pct": atr_pct,
                "stop_distance": stop_distance,
                "reward_r": self.reward_r,
                "strategy": "VolatilityBreakout",
            }

        return {
            "signal": "HOLD",
            "reason": "breakout condition not met",
            "upper_band": upper_band,
            "middle_band": middle,
            "atr": atr,
            "atr_pct": atr_pct,
        }
