from collections import defaultdict


def summarize_trades(trades):
    total = len(trades)

    if total == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "pnl": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    wins = [
        float(trade.get("pnl", 0.0))
        for trade in trades
        if float(trade.get("pnl", 0.0)) > 0
    ]

    losses = [
        float(trade.get("pnl", 0.0))
        for trade in trades
        if float(trade.get("pnl", 0.0)) < 0
    ]

    pnl = sum(
        float(trade.get("pnl", 0.0))
        for trade in trades
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    return {
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / total) * 100.0,
        "pnl": pnl,
        "profit_factor": profit_factor,
        "expectancy": pnl / total,
    }


def group_by_field(trades, field):
    groups = defaultdict(list)

    for trade in trades:
        value = trade.get(field, "UNKNOWN")

        if value is None:
            value = "UNKNOWN"

        groups[str(value)].append(trade)

    return dict(groups)


def attribute_trades(trades):
    by_regime = group_by_field(trades, "regime")
    by_strategy = group_by_field(trades, "strategy")

    return {
        "regime": {
            name: summarize_trades(group)
            for name, group in sorted(by_regime.items())
        },
        "strategy": {
            name: summarize_trades(group)
            for name, group in sorted(by_strategy.items())
        },
    }
