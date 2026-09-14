def calculate_metrics(trades, initial_balance, equity_curve):
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "return_pct": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "expectancy": 0.0,
            "max_drawdown_pct": 0.0,
        }

    pnls = [float(t["pnl"]) for t in trades]

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss == 0:
        profit_factor = float("inf") if gross_profit > 0 else 0.0
    else:
        profit_factor = gross_profit / gross_loss

    peak = initial_balance
    max_drawdown = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity

        if peak > 0:
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)

    total_pnl = sum(pnls)

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(trades)) * 100,
        "total_pnl": total_pnl,
        "return_pct": (total_pnl / initial_balance) * 100,
        "profit_factor": profit_factor,
        "average_win": sum(wins) / len(wins) if wins else 0.0,
        "average_loss": sum(losses) / len(losses) if losses else 0.0,
        "expectancy": total_pnl / len(trades),
        "max_drawdown_pct": max_drawdown * 100,
    }
