from bot.backtest import Backtester
from bot.optimizer import (
    Parameters,
    default_parameter_grid,
    optimize,
    walk_forward,
    run_backtest,
)


def test_parameter_grid_is_valid():
    grid = default_parameter_grid()

    assert len(grid) > 0

    for params in grid:
        assert params.fast_ema < params.slow_ema
        assert params.stop_loss_pct > 0
        assert params.take_profit_pct > 0


def test_optimizer_runs():
    rows = Backtester.load_csv("data/sample_btc.csv")

    grid = [
        Parameters(10, 40, 0.02, 0.03),
        Parameters(20, 50, 0.02, 0.03),
    ]

    results = optimize(rows[:60], grid)

    assert len(results) == 2
    assert "score" in results[0]
    assert "parameters" in results[0]


def test_walk_forward_requires_enough_data():
    rows = Backtester.load_csv("data/sample_btc.csv")

    result = walk_forward(
        rows[:50],
        train_size=60,
        test_size=20,
    )

    assert result["status"] == "INSUFFICIENT_DATA"


def test_oos_drawdown_reflects_test_losses():
    rows = Backtester.load_csv("data/sample_btc.csv")

    params = Parameters(
        10,
        40,
        0.015,
        0.04,
    )

    result = run_backtest(
        rows[:80],
        params,
        start_index=60,
    )

    metrics = result["metrics"]

    assert metrics["total_trades"] > 0

    if metrics["total_pnl"] < 0:
        assert metrics["max_drawdown_pct"] > 0
