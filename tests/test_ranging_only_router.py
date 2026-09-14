from bot.ranging_only_router import RangingOnlyRouter


def test_ranging_only_router_exists():
    router = RangingOnlyRouter()
    assert router is not None


def test_unknown_without_ohlc_returns_hold():
    router = RangingOnlyRouter()

    result = router.analyze([100.0] * 60)

    assert result["signal"] == "HOLD"
    assert result["regime"] == "UNCERTAIN"
    assert result["strategy"] == "none"


def test_blocked_trending_returns_hold():
    router = RangingOnlyRouter()

    prices = [100.0 + i * 2.0 for i in range(60)]
    highs = [p + 1.0 for p in prices]
    lows = [p - 1.0 for p in prices]

    result = router.analyze(
        prices,
        highs=highs,
        lows=lows,
    )

    assert result["regime"] in {
        "TRENDING",
        "RANGING",
        "HIGH_VOLATILITY",
    }

    if result["regime"] == "TRENDING":
        assert result["signal"] == "HOLD"
        assert result["strategy"] == "none"
