from dataclasses import dataclass

from bot.backtest import Backtester
from bot.config import CONFIG


@dataclass(frozen=True)
class Parameters:
    fast_ema: int
    slow_ema: int
    stop_loss_pct: float
    take_profit_pct: float


def run_backtest(rows, params, initial_balance=1000.0, start_index=0):
    original = {
        "fast_ema": CONFIG.fast_ema,
        "slow_ema": CONFIG.slow_ema,
        "stop_loss_pct": CONFIG.stop_loss_pct,
        "take_profit_pct": CONFIG.take_profit_pct,
    }

    try:
        CONFIG.fast_ema = params.fast_ema
        CONFIG.slow_ema = params.slow_ema
        CONFIG.stop_loss_pct = params.stop_loss_pct
        CONFIG.take_profit_pct = params.take_profit_pct

        return Backtester(
            initial_balance=initial_balance
        ).run(
            rows,
            start_index=start_index,
        )

    finally:
        for key, value in original.items():
            setattr(CONFIG, key, value)


def score_result(result):
    metrics = result["metrics"]

    trades = metrics["total_trades"]
    profit_factor = metrics["profit_factor"]
    expectancy = metrics["expectancy"]
    drawdown = metrics["max_drawdown_pct"]

    if trades < 2:
        return float("-inf")

    if profit_factor == float("inf"):
        profit_factor_score = 5.0
    else:
        profit_factor_score = min(profit_factor, 5.0)

    return (
        expectancy * 10
        + profit_factor_score * 2
        - drawdown * 0.5
    )


def optimize(rows, parameter_grid):
    results = []

    for params in parameter_grid:
        result = run_backtest(rows, params)
        metrics = result["metrics"]

        results.append({
            "parameters": params,
            "score": score_result(result),
            "total_pnl": metrics["total_pnl"],
            "profit_factor": metrics["profit_factor"],
            "expectancy": metrics["expectancy"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
            "trades": metrics["total_trades"],
            "win_rate": metrics["win_rate"],
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results


def default_parameter_grid():
    grid = []

    for fast in [10, 20, 30]:
        for slow in [40, 50, 70]:
            if fast >= slow:
                continue

            for sl in [0.015, 0.02, 0.025]:
                for tp in [0.03, 0.04, 0.05]:
                    grid.append(
                        Parameters(
                            fast_ema=fast,
                            slow_ema=slow,
                            stop_loss_pct=sl,
                            take_profit_pct=tp,
                        )
                    )

    return grid


def walk_forward(rows, train_size=60, test_size=20):
    if len(rows) < train_size + test_size:
        return {
            "status": "INSUFFICIENT_DATA",
            "windows": [],
        }

    windows = []
    start = 0

    while start + train_size + test_size <= len(rows):
        train = rows[
            start:start + train_size
        ]

        test_start = start + train_size

        test = rows[
            test_start:test_start + test_size
        ]

        # Optimize ONLY on training data.
        optimization = optimize(
            train,
            default_parameter_grid(),
        )

        if not optimization:
            break

        best = optimization[0]
        params = best["parameters"]

        # TRAIN is indicator context only.
        # Trading begins exactly at test_start.
        context = train + test

        test_result = run_backtest(
            context,
            params,
            start_index=len(train),
        )

        test_metrics = test_result["metrics"]

        windows.append({
            "train_start": train[0]["timestamp"],
            "train_end": train[-1]["timestamp"],
            "test_start": test[0]["timestamp"],
            "test_end": test[-1]["timestamp"],
            "parameters": params,
            "train_score": best["score"],
            "train_pnl": best["total_pnl"],
            "test_pnl": test_metrics["total_pnl"],
            "test_profit_factor": test_metrics["profit_factor"],
            "test_expectancy": test_metrics["expectancy"],
            "test_drawdown_pct": test_metrics["max_drawdown_pct"],
            "test_trades": test_metrics["total_trades"],
        })

        start += test_size

    if not windows:
        return {
            "status": "INSUFFICIENT_DATA",
            "windows": [],
        }

    profitable_tests = sum(
        1
        for window in windows
        if window["test_pnl"] > 0
    )

    positive_expectancy = sum(
        1
        for window in windows
        if window["test_expectancy"] > 0
    )

    status = "ACCEPT"

    if profitable_tests < len(windows):
        status = "REJECT"

    if positive_expectancy < len(windows):
        status = "REJECT"

    return {
        "status": status,
        "windows": windows,
        "profitable_test_windows": profitable_tests,
        "positive_expectancy_windows": positive_expectancy,
    }
