from bot.strategy_v2r import RegimeTrendStrategy


def make_trending_data(n=150):
    closes = []
    highs = []
    lows = []

    price = 100.0

    for _ in range(n):
        price += 0.5
        closes.append(price)
        highs.append(price + 1.0)
        lows.append(price - 1.0)

    return closes, highs, lows


def test_v2r_requires_enough_data():
    strategy = RegimeTrendStrategy()

    closes = [100.0] * 20
    highs = [101.0] * 20
    lows = [99.0] * 20

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"
    assert result["reason"] == "not enough data"


def test_v2r_requires_ohlc():
    strategy = RegimeTrendStrategy()

    closes = [100.0 + i * 0.5 for i in range(100)]

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"
    assert result["reason"] == "OHLC data required"


def test_v2r_rejects_weak_regime():
    strategy = RegimeTrendStrategy(
        fast_period=10,
        slow_period=30,
        adx_period=14,
        min_adx=20.0,
    )

    closes = []
    highs = []
    lows = []

    for i in range(150):
        price = 100.0 + (0.01 * i)
        closes.append(price)
        highs.append(price + 0.01)
        lows.append(price - 0.01)

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"
    assert result["reason"] in {
        "trend strength too weak",
        "volatility too low",
    }


def test_v2r_can_confirm_strong_uptrend():
    strategy = RegimeTrendStrategy(
        fast_period=10,
        slow_period=30,
        adx_period=14,
        min_adx=20.0,
    )

    closes, highs, lows = make_trending_data()

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"
    assert result["ema_fast"] > result["ema_slow"]
    assert result["adx"] >= 20.0
