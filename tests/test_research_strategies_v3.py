from bot.research_strategies_v3 import (
    VolatilityBreakoutStrategy,
    MomentumRegimeStrategy,
)


def make_data(count=80):
    closes = [
        100.0 + i * 0.5
        for i in range(count)
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


def test_volatility_breakout_detects_breakout():
    closes, highs, lows = make_data()

    previous_high = max(highs[-21:-1])

    closes[-1] = previous_high * 1.02
    highs[-1] = closes[-1] * 1.005
    lows[-1] = closes[-1] * 0.995

    strategy = VolatilityBreakoutStrategy(
        lookback=20,
        atr_period=14,
        breakout_buffer=0.001,
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"


def test_volatility_breakout_rejects_missing_ohlc():
    closes, _, _ = make_data()

    strategy = VolatilityBreakoutStrategy()

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"


def test_volatility_breakout_rejects_weak_breakout():
    closes, highs, lows = make_data()

    closes[-1] = max(highs[-21:-1]) * 0.99
    highs[-1] = closes[-1] * 1.005
    lows[-1] = closes[-1] * 0.995

    strategy = VolatilityBreakoutStrategy(
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"


def test_momentum_regime_detects_positive_momentum():
    closes, highs, lows = make_data()

    closes[-1] = closes[-11] * 1.03
    highs[-1] = closes[-1] * 1.005
    lows[-1] = closes[-1] * 0.995

    strategy = MomentumRegimeStrategy(
        min_momentum=0.005,
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"


def test_momentum_regime_rejects_negative_momentum():
    closes, highs, lows = make_data()

    closes[-1] = closes[-11] * 0.97
    highs[-1] = closes[-1] * 1.005
    lows[-1] = closes[-1] * 0.995

    strategy = MomentumRegimeStrategy(
        min_momentum=0.005,
        min_atr_pct=0.001,
    )

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"


def test_momentum_regime_rejects_missing_ohlc():
    closes, _, _ = make_data()

    strategy = MomentumRegimeStrategy()

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"
