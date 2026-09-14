from bot.research_strategies import (
    TrendFollowingStrategy,
    DonchianBreakoutStrategy,
    MeanReversionStrategy,
)


def make_uptrend(length=80):
    closes = [
        100.0 + i * 1.0
        for i in range(length)
    ]

    highs = [
        close + 1.0
        for close in closes
    ]

    lows = [
        close - 1.0
        for close in closes
    ]

    return closes, highs, lows


def test_trend_following_confirms_uptrend():
    closes, highs, lows = make_uptrend()

    strategy = TrendFollowingStrategy(
        fast_period=10,
        slow_period=30,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"


def test_donchian_requires_ohlc():
    closes = [100.0 + i for i in range(50)]

    strategy = DonchianBreakoutStrategy()

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"


def test_donchian_detects_breakout():
    closes, highs, lows = make_uptrend()

    # Make the latest candle a genuine breakout
    closes[-1] = max(highs[:-1]) + 5.0
    highs[-1] = closes[-1] + 1.0
    lows[-1] = closes[-1] - 1.0

    strategy = DonchianBreakoutStrategy(
        lookback=20,
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"


def test_mean_reversion_detects_oversold_deviation():
    closes, highs, lows = make_uptrend()

    # Force the final candle well below the EMA20.
    closes[-1] = closes[-2] * 0.90
    highs[-1] = closes[-2] * 0.91
    lows[-1] = closes[-1] * 0.99

    strategy = MeanReversionStrategy(
        ema_period=20,
        deviation_pct=0.01,
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"


def test_mean_reversion_requires_ohlc():
    closes = [100.0 + i for i in range(30)]

    strategy = MeanReversionStrategy()

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"
