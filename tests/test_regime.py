from bot.regime import MarketRegimeDetector


def make_series(length=100, start=100.0, step=1.0):
    closes = [start + i * step for i in range(length)]
    highs = [price * 1.002 for price in closes]
    lows = [price * 0.998 for price in closes]
    return closes, highs, lows


def test_trending_market():
    closes, highs, lows = make_series(step=2.0)

    detector = MarketRegimeDetector(
        trend_threshold=0.005,
        high_volatility_threshold=0.10,
    )

    result = detector.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result.regime == "TRENDING"


def test_ranging_market():
    closes = [
        100, 101, 100, 99, 100,
        101, 100, 99, 100, 101,
    ] * 10

    highs = [price * 1.002 for price in closes]
    lows = [price * 0.998 for price in closes]

    detector = MarketRegimeDetector(
        trend_threshold=0.05,
        high_volatility_threshold=0.10,
    )

    result = detector.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result.regime == "RANGING"


def test_high_volatility_market():
    closes = [
        100,
        110,
        90,
        115,
        85,
        120,
        80,
        125,
        75,
        130,
    ] * 10

    highs = [price * 1.01 for price in closes]
    lows = [price * 0.99 for price in closes]

    detector = MarketRegimeDetector(
        trend_threshold=0.50,
        high_volatility_threshold=0.03,
    )

    result = detector.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result.regime == "HIGH_VOLATILITY"


def test_missing_ohlc_returns_uncertain():
    closes, _, _ = make_series()

    detector = MarketRegimeDetector()

    result = detector.analyze(closes)

    assert result.regime == "UNCERTAIN"


def test_insufficient_data_returns_uncertain():
    closes, highs, lows = make_series(length=20)

    detector = MarketRegimeDetector()

    result = detector.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result.regime == "UNCERTAIN"


def test_result_contains_diagnostics():
    closes, highs, lows = make_series(step=1.5)

    detector = MarketRegimeDetector(
        trend_threshold=0.005,
        high_volatility_threshold=0.10,
    )

    result = detector.analyze(
        closes,
        highs=highs,
        lows=lows,
    )

    assert result.trend_strength >= 0
    assert result.volatility_pct >= 0
    assert 0 <= result.range_position <= 1
    assert result.reason
