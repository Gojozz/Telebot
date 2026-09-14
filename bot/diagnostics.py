from collections import defaultdict
from statistics import mean, median


def _pnl(trade):
    return float(trade.get("pnl", 0.0))


def _gross_pnl(trade):
    return float(trade.get("gross_pnl", 0.0))


def _fees(trade):
    return float(trade.get("fees", 0.0))


def _summary(trades):
    trades = list(trades)

    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "pnl": 0.0,
            "gross_pnl": 0.0,
            "fees": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "payoff_ratio": 0.0,
            "longest_loss_streak": 0,
        }

    pnls = [_pnl(t) for t in trades]
    gross_pnls = [_gross_pnl(t) for t in trades]

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    avg_win = mean(wins) if wins else 0.0
    avg_loss = abs(mean(losses)) if losses else 0.0

    if avg_loss > 0:
        payoff_ratio = avg_win / avg_loss
    elif avg_win > 0:
        payoff_ratio = float("inf")
    else:
        payoff_ratio = 0.0

    longest_streak = 0
    current_streak = 0

    for pnl in pnls:
        if pnl < 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) * 100.0,
        "pnl": sum(pnls),
        "gross_pnl": sum(gross_pnls),
        "fees": sum(_fees(t) for t in trades),
        "profit_factor": profit_factor,
        "expectancy": sum(pnls) / len(trades),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": payoff_ratio,
        "longest_loss_streak": longest_streak,
    }


def group_trades(trades, field):
    groups = defaultdict(list)

    for trade in trades:
        value = trade.get(field, "UNKNOWN")

        if value is None or value == "":
            value = "UNKNOWN"

        groups[str(value)].append(trade)

    return dict(groups)


def group_by_year(trades):
    groups = defaultdict(list)

    for trade in trades:
        timestamp = str(trade.get("exit_timestamp", ""))

        if len(timestamp) >= 4:
            year = timestamp[:4]
        else:
            year = "UNKNOWN"

        groups[year].append(trade)

    return dict(groups)


def collect_window_trades(rows, candidate, train_size, test_size):
    from bot.research_runner import run_candidate

    all_trades = []
    windows = []

    start = 0

    while start + train_size + test_size <= len(rows):
        train_start = start
        test_start = start + train_size
        test_end = test_start + test_size

        context_rows = rows[train_start:test_end]

        result = run_candidate(
            context_rows,
            candidate,
            start_index=train_size,
        )

        trades = result.get("trades", [])

        all_trades.extend(trades)

        windows.append({
            "test_start": rows[test_start]["timestamp"],
            "test_end": rows[test_end - 1]["timestamp"],
            "trades": trades,
            "summary": _summary(trades),
        })

        start += test_size

    return all_trades, windows


def diagnose_candidate(rows, candidate, train_size, test_size):
    trades, windows = collect_window_trades(
        rows,
        candidate,
        train_size,
        test_size,
    )

    return {
        "candidate": candidate.name,
        "overall": _summary(trades),
        "year": {
            key: _summary(value)
            for key, value in sorted(group_by_year(trades).items())
        },
        "regime": {
            key: _summary(value)
            for key, value in sorted(
                group_trades(trades, "regime").items()
            )
        },
        "strategy": {
            key: _summary(value)
            for key, value in sorted(
                group_trades(trades, "strategy").items()
            )
        },
        "exit": {
            key: _summary(value)
            for key, value in sorted(
                group_trades(trades, "reason").items()
            )
        },
        "windows": windows,
    }


def format_number(value):
    if value == float("inf"):
        return "INF"

    if value == float("-inf"):
        return "-INF"

    return f"{value:.4f}"


def print_group(title, groups):
    print()
    print(title)
    print("-" * len(title))

    if not groups:
        print("NO DATA")
        return

    for name, data in groups.items():
        print(
            f"{name:18} "
            f"TRADES={data['trades']:3d} "
            f"WR={data['win_rate']:6.2f}% "
            f"PNL={format_number(data['pnl']):>10} "
            f"GROSS={format_number(data['gross_pnl']):>10} "
            f"FEES={format_number(data['fees']):>9} "
            f"PF={format_number(data['profit_factor']):>7} "
            f"EXP={format_number(data['expectancy']):>8}"
        )


def print_diagnosis(result):
    overall = result["overall"]

    print()
    print("=" * 72)
    print(f"V4.7 DIAGNOSTIC: {result['candidate'].upper()}")
    print("=" * 72)

    print()
    print("OVERALL")
    print("-------")
    print(f"TRADES             : {overall['trades']}")
    print(f"WINS               : {overall['wins']}")
    print(f"LOSSES             : {overall['losses']}")
    print(f"WIN RATE           : {overall['win_rate']:.2f}%")
    print(f"GROSS PNL          : {format_number(overall['gross_pnl'])}")
    print(f"NET PNL            : {format_number(overall['pnl'])}")
    print(f"FEES               : {format_number(overall['fees'])}")
    print(f"PROFIT FACTOR      : {format_number(overall['profit_factor'])}")
    print(f"EXPECTANCY         : {format_number(overall['expectancy'])}")
    print(f"AVG WIN            : {format_number(overall['avg_win'])}")
    print(f"AVG LOSS           : {format_number(overall['avg_loss'])}")
    print(f"PAYOFF RATIO       : {format_number(overall['payoff_ratio'])}")
    print(f"LONGEST LOSS STREAK: {overall['longest_loss_streak']}")

    print_group("YEAR", result["year"])
    print_group("REGIME", result["regime"])
    print_group("STRATEGY", result["strategy"])
    print_group("EXIT REASON", result["exit"])

    print()
    print("WINDOW DIAGNOSTIC")
    print("-----------------")

    positive = 0
    negative = 0
    zero = 0

    for window in result["windows"]:
        pnl = window["summary"]["pnl"]

        if pnl > 0:
            positive += 1
        elif pnl < 0:
            negative += 1
        else:
            zero += 1

    print(f"PROFITABLE WINDOWS : {positive}")
    print(f"LOSING WINDOWS     : {negative}")
    print(f"ZERO WINDOWS       : {zero}")

    print()
    print("INTERPRETATION")
    print("--------------")

    gross = overall["gross_pnl"]
    net = overall["pnl"]

    if gross > 0 and net <= 0:
        print("EDGE LOST TO COSTS: gross PNL positive, net PNL non-positive.")
    elif gross <= 0:
        print("ENTRY/EXIT EDGE WEAK: gross PNL is already non-positive.")
    else:
        print("GROSS EDGE SURVIVES BASE COSTS.")

    if overall["payoff_ratio"] < 1.0:
        print("PAYOFF WARNING: average loss exceeds average win.")
    elif overall["payoff_ratio"] > 1.0:
        print("PAYOFF: average win exceeds average loss.")

    if overall["longest_loss_streak"] >= 5:
        print("STREAK WARNING: prolonged losing streak detected.")

    if overall["fees"] != 0:
        cost_share = abs(overall["fees"]) / max(abs(gross), 1e-12) * 100.0
        print(f"COST IMPACT VS GROSS: {cost_share:.2f}%")


def load_csv(path):
    import csv

    rows = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })

    return rows
