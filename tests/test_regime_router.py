from bot.regime_router import RegimeRouter


class FakeDetector:
    def __init__(self, regime):
        self.regime = regime

    def analyze(self, prices, highs=None, lows=None):
        from bot.regime import RegimeResult

        return RegimeResult(
            regime=self.regime,
            trend_strength=0.02,
            volatility_pct=0.01,
            range_position=0.5,
            reason="test regime",
        )


class FakeStrategy:
    def __init__(self, signal):
        self.signal = signal

    def analyze(self, prices, highs=None, lows=None):
        return {
            "signal": self.signal,
            "reason": "test strategy",
        }


def make_router(regime, signal):
    return RegimeRouter(
        detector=FakeDetector(regime),
        trend_strategy=FakeStrategy(signal),
        mean_reversion_strategy=FakeStrategy(signal),
        breakout_strategy=FakeStrategy(signal),
    )


def test_trending_routes_to_trend_strategy():
    router = make_router("TRENDING", "BUY")

    result = router.analyze(
        [100] * 60,
        highs=[101] * 60,
        lows=[99] * 60,
    )

    assert result["regime"] == "TRENDING"
    assert result["signal"] == "BUY"
    assert result["strategy"] == "FakeStrategy"


def test_ranging_routes_to_mean_reversion():
    router = make_router("RANGING", "BUY")

    result = router.analyze(
        [100] * 60,
        highs=[101] * 60,
        lows=[99] * 60,
    )

    assert result["regime"] == "RANGING"
    assert result["signal"] == "BUY"


def test_high_volatility_routes_to_breakout():
    router = make_router("HIGH_VOLATILITY", "BUY")

    result = router.analyze(
        [100] * 60,
        highs=[101] * 60,
        lows=[99] * 60,
    )

    assert result["regime"] == "HIGH_VOLATILITY"
    assert result["signal"] == "BUY"


def test_uncertain_never_trades():
    router = make_router("UNCERTAIN", "BUY")

    result = router.analyze(
        [100] * 60,
        highs=[101] * 60,
        lows=[99] * 60,
    )

    assert result["regime"] == "UNCERTAIN"
    assert result["signal"] == "HOLD"
    assert result["strategy"] == "none"


def test_router_preserves_regime_diagnostics():
    router = make_router("TRENDING", "HOLD")

    result = router.analyze(
        [100] * 60,
        highs=[101] * 60,
        lows=[99] * 60,
    )

    assert result["trend_strength"] >= 0
    assert result["volatility_pct"] >= 0
    assert 0 <= result["range_position"] <= 1
    assert result["regime_reason"] == "test regime"
