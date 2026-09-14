from bot.backtest import Backtester


def main():
    print("=== TELEBOT v0.2 BACKTEST ===")

    rows = Backtester.load_csv("data/sample_btc.csv")

    print(f"CANDLES: {len(rows)}")
    print(f"INITIAL BALANCE: {1000:.2f}")

    result = Backtester(initial_balance=1000).run(rows)
    metrics = result["metrics"]

    print()
    print("=== RESULTS ===")
    print(f"TRADES:           {metrics['total_trades']}")
    print(f"WINS:             {metrics['wins']}")
    print(f"LOSSES:           {metrics['losses']}")
    print(f"WIN RATE:         {metrics['win_rate']:.2f}%")
    print(f"TOTAL PNL:        {metrics['total_pnl']:.4f}")
    print(f"RETURN:           {metrics['return_pct']:.2f}%")

    if metrics["profit_factor"] == float("inf"):
        print("PROFIT FACTOR:    inf")
    else:
        print(f"PROFIT FACTOR:    {metrics['profit_factor']:.3f}")

    print(f"AVG WIN:          {metrics['average_win']:.4f}")
    print(f"AVG LOSS:         {metrics['average_loss']:.4f}")
    print(f"EXPECTANCY:       {metrics['expectancy']:.4f}")
    print(f"MAX DRAWDOWN:     {metrics['max_drawdown_pct']:.2f}%")
    print(f"FINAL BALANCE:    {result['final_balance']:.4f}")

    print()

    if result["halted"]:
        print(f"RISK HALT:        YES")
        print(f"REASON:           {result['halt_reason']}")
    else:
        print("RISK HALT:        NO")

    print()
    print("=== TRADES ===")

    for i, trade in enumerate(result["trades"], 1):
        print(
            f"{i:02d} | "
            f"{trade['reason']:12s} | "
            f"entry={trade['entry_price']:.4f} | "
            f"exit={trade['exit_price']:.4f} | "
            f"pnl={trade['pnl']:.4f}"
        )


if __name__ == "__main__":
    main()
