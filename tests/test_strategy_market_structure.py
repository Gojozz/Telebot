from bot.strategy_market_structure import MarketStructureBOSRetestStrategy


def test_market_structure_requires_ohlc():
    strategy = MarketStructureBOSRetestStrategy()

    result = strategy.analyze([100, 101, 102])

    assert result["signal"] == "HOLD"
    assert result["reason"] == "OHLC data required"


def test_market_structure_waits_for_confirmed_structure():
    strategy = MarketStructureBOSRetestStrategy()

    prices = [100, 101, 102, 101, 100, 101]
    highs =   [101, 102, 103, 102, 101, 102]
    lows =    [ 99, 100, 101, 100,  99, 100]

    result = strategy.analyze(
        prices,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "HOLD"


def test_market_structure_can_detect_bos_retest():
    strategy = MarketStructureBOSRetestStrategy(
        swing_left=2,
        swing_right=2,
        retest_bars=10,
        reward_r=2.0,
    )

    # Struktur:
    # index 2  -> confirmed swing high = 105
    # index 9  -> close 108 breaks swing high => BOS
    # index 11 -> low 104 retests 105, close 106.5 back above => RETEST
    # index 12+ do not create a newer confirmed swing high before evaluation.
    prices = [
        100, 102, 104, 102, 100,
        103, 105, 103, 101, 108,
        108, 106.5, 109, 110, 111,
    ]

    highs = [
        101, 103, 105, 103, 101,
        104, 106, 104, 102, 109,
        108, 108, 110, 111, 112,
    ]

    lows = [
         99, 101, 103, 101,  99,
        102, 104, 102, 100, 107,
        106, 104, 108, 109, 110,
    ]

    result = strategy.analyze(
        prices,
        highs=highs,
        lows=lows,
    )

    assert result["signal"] == "BUY"
    assert result["strategy"] == "MarketStructureBOSRetest"
    assert result["reward_r"] == 2.0
    assert result["stop_price"] < prices[-1]
    assert result["breakout_level"] == 105
