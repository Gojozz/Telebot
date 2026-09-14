import pytest

from bot.regime_attribution import summarize_trades, group_by_field, attribute_trades


def test_summarize_trades():
    trades = [
        {"pnl": 10.0},
        {"pnl": -5.0},
        {"pnl": 5.0},
    ]

    result = summarize_trades(trades)

    assert result["trades"] == 3
    assert result["wins"] == 2
    assert result["losses"] == 1
    assert result["pnl"] == 10.0
    assert result["profit_factor"] == 3.0
    assert result["win_rate"] == pytest.approx(100.0 * 2.0 / 3.0)


def test_group_by_field():
    trades = [
        {"regime": "TRENDING", "pnl": 10},
        {"regime": "RANGING", "pnl": -5},
        {"regime": "TRENDING", "pnl": 2},
    ]

    groups = group_by_field(trades, "regime")

    assert len(groups["TRENDING"]) == 2
    assert len(groups["RANGING"]) == 1


def test_attribute_trades():
    trades = [
        {
            "regime": "TRENDING",
            "strategy": "TrendFollowingStrategy",
            "pnl": 10,
        },
        {
            "regime": "RANGING",
            "strategy": "MeanReversionStrategy",
            "pnl": -5,
        },
    ]

    result = attribute_trades(trades)

    assert result["regime"]["TRENDING"]["pnl"] == 10
    assert result["regime"]["RANGING"]["pnl"] == -5

    assert (
        result["strategy"]["TrendFollowingStrategy"]["trades"]
        == 1
    )
