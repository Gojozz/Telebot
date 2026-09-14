from bot.strategy_v2 import MomentumVolatilityStrategy


def make_uptrend_data(n=100):
    closes = []
    highs = []
    lows = []

    price = 100.0

    for i in range(n):
        price += 0.5
        closes.append(price)
        highs.append(price + 1.0)
        lows.append(price - 1.0)

    return closes, highs, lows


def test_v2_returns_hold_without_enough_data():
    strategy = MomentumVolatilityStrategy()

    result = strategy.analyze(
        [100.0] * 20,
        highs=[101.0] * 20,
        lows=[99.0] * 20,
    )

    assert result["signal"] == "HOLD"
    assert result["reason"] == "not enough data"


def test_v2_requires_ohlc_data():
    strategy = MomentumVolatilityStrategy()

    closes, _, _ = make_uptrend_data()

    result = strategy.analyze(closes)

    assert result["signal"] == "HOLD"
    assert result["reason"] == "OHLC data required"


def test_v2_can_confirm_uptrend():
    strategy = MomentumVolatilityStrategy(
        fast_period=10,
        slow_period=30,
        rsi_period=14,
        rsi_min=52.0,
        rsi_max=70.0,
        atr_period=14,
        min_atr_pct=0.005,
    )

    closes, highs, lows = make_uptrend_data()

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"
    assert result["reason"] == "momentum overbought"


def test_v2_can_generate_buy_with_balanced_momentum():
    strategy = MomentumVolatilityStrategy(
        fast_period=10,
        slow_period=30,
        rsi_period=14,
        rsi_min=50.0,
        rsi_max=100.0,
        atr_period=14,
        min_atr_pct=0.005,
    )

    closes = []
    highs = []
    lows = []

    price = 100.0

    for i in range(120):
        if i < 80:
            price += 0.20
        elif i % 3 == 0:
            price += 0.30
        else:
            price -= 0.05

        closes.append(price)
        highs.append(price + 1.0)
        lows.append(price - 1.0)

    result = strategy.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"
    assert result["ema_fast"] > result["ema_slow"]
    assert result["rsi"] >= 50.0
    assert result["atr_pct"] >= 0.005
