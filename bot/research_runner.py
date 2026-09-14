from dataclasses import dataclass
from typing import Callable
from bot.backtest import Backtester
from bot.config import CONFIG
from bot.regime_router import RegimeRouter
from bot.ranging_only_router import RangingOnlyRouter
from bot.research_strategies_v3 import (
    VolatilityBreakoutStrategy,
    MomentumRegimeStrategy,
)


@dataclass(frozen=True)
class Candidate:
    name: str
    factory: Callable


CANDIDATES = [
    Candidate(
        "trend_following",
        lambda: __import__(
            "bot.research_strategies",
            fromlist=["TrendFollowingStrategy"],
        ).TrendFollowingStrategy(),
    ),
    Candidate(
        "donchian_breakout",
        lambda: __import__(
            "bot.research_strategies",
            fromlist=["DonchianBreakoutStrategy"],
        ).DonchianBreakoutStrategy(),
    ),
    Candidate(
        "mean_reversion",
        lambda: __import__(
            "bot.research_strategies",
            fromlist=["MeanReversionStrategy"],
        ).MeanReversionStrategy(),
    ),
    Candidate(
        "volatility_breakout",
        lambda: VolatilityBreakoutStrategy(),
    ),
    Candidate(
        "momentum_regime",
        lambda: MomentumRegimeStrategy(),
    ),
    Candidate(
        "regime_router",
        lambda: RegimeRouter(),
    ),
    Candidate(
        "ranging_only",
        lambda: RangingOnlyRouter(),
    ),
]


COST_SCENARIOS = [
    ("BASE", 0.0010, 0.0005),
    ("STRESS", 0.0015, 0.0010),
    ("HARSH", 0.0020, 0.0015),
]

# V4.6 research configuration
DATA_PATH = "data/btcusdt_1h_18000.csv"
TRAIN_SIZE = 1000
TEST_SIZE = 500



def load_csv(path):
    import csv

    rows = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )

    return rows


def run_candidate(rows, candidate, start_index=0):
    backtester = Backtester(initial_balance=1000.0)
    backtester.strategy = candidate.factory()

    return backtester.run(
        rows,
        start_index=start_index,
    )


def summarize(result):
    metrics = result.get("metrics", {})

    trades = result.get("trades", [])

    wins = []
    losses = []

    for trade in trades:
        pnl = float(trade.get("pnl", 0.0))

        if pnl > 0:
            wins.append(pnl)
        elif pnl < 0:
            losses.append(pnl)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    total_trades = len(trades)

    total_pnl = sum(
        float(trade.get("pnl", 0.0))
        for trade in trades
    )

    expectancy = (
        total_pnl / total_trades
        if total_trades
        else 0.0
    )

    return {
        "pnl": total_pnl,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "drawdown": float(
            metrics.get("max_drawdown_pct", 0.0)
        ),
        "trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "final_balance": float(
            result.get("final_balance", 1000.0)
        ),
    }


def walk_forward(
    rows,
    candidate,
    train_size=TRAIN_SIZE,
    test_size=TEST_SIZE,
):
    windows = []
    start = 0

    while start + train_size + test_size <= len(rows):
        train_start = start
        test_start = start + train_size
        test_end = test_start + test_size

        train_rows = rows[
            train_start:test_start
        ]

        train_result = run_candidate(
            train_rows,
            candidate,
            start_index=0,
        )

        context_rows = rows[
            train_start:test_end
        ]

        test_result = run_candidate(
            context_rows,
            candidate,
            start_index=train_size,
        )

        train = summarize(train_result)
        test = summarize(test_result)

        windows.append(
            {
                "train_start": rows[train_start]["timestamp"],
                "train_end": rows[test_start - 1]["timestamp"],
                "test_start": rows[test_start]["timestamp"],
                "test_end": rows[test_end - 1]["timestamp"],
                "train": train,
                "test": test,
            }
        )

        start += test_size

    return windows


def aggregate(windows):
    tests = [
        window["test"]
        for window in windows
    ]

    if not tests:
        return {
            "windows": 0,
            "profitable_windows": 0,
            "positive_expectancy_windows": 0,
            "total_pnl": 0.0,
            "total_trades": 0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
        }

    gross_profit = sum(
        item["gross_profit"]
        for item in tests
    )

    gross_loss = sum(
        item["gross_loss"]
        for item in tests
    )

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    total_pnl = sum(
        item["pnl"]
        for item in tests
    )

    total_trades = sum(
        item["trades"]
        for item in tests
    )

    expectancy = (
        total_pnl / total_trades
        if total_trades
        else 0.0
    )

    return {
        "windows": len(tests),
        "profitable_windows": sum(
            item["pnl"] > 0
            for item in tests
        ),
        "positive_expectancy_windows": sum(
            item["expectancy"] > 0
            for item in tests
        ),
        "total_pnl": total_pnl,
        "total_trades": total_trades,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_drawdown": max(
            item["drawdown"]
            for item in tests
        ),
    }


def run_scenario(
    rows,
    candidate,
    fee_rate,
    slippage_pct,
):
    old_fee = CONFIG.fee_rate
    old_slippage = CONFIG.slippage_pct

    try:
        CONFIG.fee_rate = fee_rate
        CONFIG.slippage_pct = slippage_pct

        windows = walk_forward(
            rows,
            candidate,
            train_size=TRAIN_SIZE,
            test_size=TEST_SIZE,
        )

        return windows

    finally:
        CONFIG.fee_rate = old_fee
        CONFIG.slippage_pct = old_slippage


def scenario_summary(
    rows,
    candidate,
    fee_rate,
    slippage_pct,
):
    windows = run_scenario(
        rows,
        candidate,
        fee_rate,
        slippage_pct,
    )

    return aggregate(windows)


def consistency_score(summary):
    windows = summary["windows"]

    if windows == 0:
        return 0.0

    profitable_ratio = (
        summary["profitable_windows"]
        / windows
    )

    positive_exp_ratio = (
        summary["positive_expectancy_windows"]
        / windows
    )

    return (
        profitable_ratio * 50.0
        + positive_exp_ratio * 50.0
    )


def verdict(base, stress, harsh):
    if base["total_trades"] < 30:
        return "REJECT"

    if (
        base["profit_factor"] > 1.0
        and base["expectancy"] > 0
        and stress["profit_factor"] > 1.0
        and stress["expectancy"] > 0
        and harsh["profit_factor"] > 1.0
        and harsh["expectancy"] > 0
    ):
        return "SURVIVE"

    if (
        base["profit_factor"] > 1.0
        and base["expectancy"] > 0
        and stress["expectancy"] > 0
    ):
        return "FRAGILE"

    return "REJECT"


def print_scenario(name, summary):
    pf = summary["profit_factor"]

    if pf == float("inf"):
        pf_text = "inf"
    else:
        pf_text = f"{pf:.4f}"

    print(
        f"{name:<7} "
        f"PNL={summary['total_pnl']:>9.4f} "
        f"PF={pf_text:>8} "
        f"EXP={summary['expectancy']:>8.4f} "
        f"TRADES={summary['total_trades']:>4} "
        f"PROFITABLE="
        f"{summary['profitable_windows']}/"
        f"{summary['windows']} "
        f"DD={summary['max_drawdown']:.3f}%"
    )


def evaluate_candidate(rows, candidate):
    results = {}

    for name, fee, slippage in COST_SCENARIOS:
        results[name] = scenario_summary(
            rows,
            candidate,
            fee,
            slippage,
        )

    base = results["BASE"]
    stress = results["STRESS"]
    harsh = results["HARSH"]

    return {
        "name": candidate.name,
        "base": base,
        "stress": stress,
        "harsh": harsh,
        "consistency": consistency_score(base),
        "verdict": verdict(
            base,
            stress,
            harsh,
        ),
    }


def print_evaluation(evaluation):
    print()
    print("=" * 72)
    print(evaluation["name"].upper())
    print("=" * 72)

    print_scenario(
        "BASE",
        evaluation["base"],
    )

    print_scenario(
        "STRESS",
        evaluation["stress"],
    )

    print_scenario(
        "HARSH",
        evaluation["harsh"],
    )

    print(
        f"CONSISTENCY : "
        f"{evaluation['consistency']:.2f}/100"
    )

    print(
        f"VERDICT     : "
        f"{evaluation['verdict']}"
    )


def main():
    path = DATA_PATH
    rows = load_csv(path)

    print("RESEARCH ENGINE V4")
    print("=" * 72)
    print(f"DATA       : {path}")
    print(f"CANDLES    : {len(rows)}")
    print(f"TRAIN      : {TRAIN_SIZE}")
    print(f"TEST       : {TEST_SIZE}")
    print("COST       : BASE / STRESS / HARSH")
    print("MODE       : RESEARCH / PAPER")
    print("=" * 72)

    evaluations = []

    for candidate in CANDIDATES:
        evaluation = evaluate_candidate(
            rows,
            candidate,
        )

        evaluations.append(evaluation)

        print_evaluation(evaluation)

    ranked = sorted(
        evaluations,
        key=lambda item: (
            item["verdict"] == "SURVIVE",
            item["verdict"] == "FRAGILE",
            item["consistency"],
            item["base"]["expectancy"],
            item["base"]["profit_factor"],
        ),
        reverse=True,
    )

    print()
    print("=" * 72)
    print("ROBUSTNESS RANKING")
    print("=" * 72)

    for number, item in enumerate(
        ranked,
        1,
    ):
        base = item["base"]

        print(
            f"{number}. "
            f"{item['name']:<20} "
            f"{item['verdict']:<7} "
            f"CONS={item['consistency']:>6.2f} "
            f"PNL={base['total_pnl']:>9.4f} "
            f"PF={base['profit_factor']!s:>8} "
            f"TRADES={base['total_trades']}"
        )


if __name__ == "__main__":
    main()
