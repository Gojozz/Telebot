from bot.diagnostics import (
    _summary,
    group_by_year,
    group_trades,
)


def test_summary_basic():
    trades = [
        {
            "pnl": 10.0,
            "gross_pnl": 12.0,
            "fees": 2.0,
        },
        {
            "pnl": -5.0,
            "gross_pnl": -4.0,
            "fees": 1.0,
        },
    ]

    result = _summary(trades)

    assert result["trades"] == 2
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["pnl"] == 5.0
    assert result["gross_pnl"] == 8.0
    assert result["fees"] == 3.0
    assert result["win_rate"] == 50.0
    assert result["avg_win"] == 10.0
    assert result["avg_loss"] == 5.0
    assert result["payoff_ratio"] == 2.0


def test_longest_loss_streak():
    trades = [
        {"pnl": 1},
        {"pnl": -1},
        {"pnl": -2},
        {"pnl": -3},
        {"pnl": 4},
        {"pnl": -1},
    ]

    result = _summary(trades)

    assert result["longest_loss_streak"] == 3


def test_group_by_year():
    trades = [
        {"exit_timestamp": "2024-01-01T00:00:00+00:00"},
        {"exit_timestamp": "2024-05-01T00:00:00+00:00"},
        {"exit_timestamp": "2025-01-01T00:00:00+00:00"},
    ]

    groups = group_by_year(trades)

    assert len(groups["2024"]) == 2
    assert len(groups["2025"]) == 1


def test_group_trades():
    trades = [
        {"regime": "RANGING"},
        {"regime": "TRENDING"},
        {"regime": "RANGING"},
    ]

    groups = group_trades(trades, "regime")

    assert len(groups["RANGING"]) == 2
    assert len(groups["TRENDING"]) == 1
