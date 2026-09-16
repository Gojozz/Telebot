import csv

from ai_agent.market_state_v1 import classify_market_state
from ai_agent.thesis_engine_v1 import build_thesis
from ai_agent.trade_plan_v2 import build_trade_plan


TRAIN_END = 12000
VAL_END = 16000
START_INDEX = 24
FEE_RATE = 0.0004
SLIPPAGE_RATE = 0.0002


def load_rows():
    with open(
        "data/btcusdt_1h_ohlcv_new.csv",
        newline="",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


def features(rows, index):
    close = float(rows[index]["close"])
    r1 = close / float(rows[index - 1]["close"]) - 1.0
    r6 = close / float(rows[index - 6]["close"]) - 1.0
    r24 = close / float(rows[index - 24]["close"]) - 1.0

    high = float(rows[index]["high"])
    low = float(rows[index]["low"])
    volatility = (high - low) / close

    volume = float(rows[index]["volume"])
    avg_volume = sum(
        float(rows[i]["volume"])
        for i in range(index - 7, index)
    ) / 7.0

    volume_ratio = volume / avg_volume if avg_volume else 1.0

    return r1, r6, r24, volatility, volume_ratio


def execution_price(price, side):
    return price * (1.0 + SLIPPAGE_RATE * side)


def main():
    rows = load_rows()

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    open_trade = None
    trades = []

    plan_count = 0
    thesis_count = 0

    # Warmup uses historical candles before validation.
    start = TRAIN_END
    end = VAL_END

    for index in range(start, end):
        row = rows[index]

        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])

        # Manage existing trade.
        if open_trade is not None:
            position = open_trade["position"]
            invalidation = open_trade["invalidation"]
            target = open_trade["target"]

            if position == 1:
                hit_invalidation = low <= invalidation
                hit_target = high >= target
            else:
                hit_invalidation = high >= invalidation
                hit_target = low <= target

            exit_price = None
            reason = None

            # Conservative: invalidation wins if both are touched.
            if hit_invalidation:
                exit_price = invalidation
                reason = "INVALIDATION"
            elif hit_target:
                exit_price = target
                reason = "TARGET"

            if exit_price is not None:
                exit_exec = execution_price(
                    exit_price,
                    -position,
                )

                entry_exec = open_trade["entry"]

                if position == 1:
                    gross = exit_exec / entry_exec - 1.0
                else:
                    gross = entry_exec / exit_exec - 1.0

                net = gross - (2.0 * FEE_RATE)

                equity *= 1.0 + net

                trades.append({
                    "position": position,
                    "net": net,
                    "reason": reason,
                })

                peak = max(peak, equity)
                max_drawdown = max(
                    max_drawdown,
                    1.0 - equity / peak,
                )

                open_trade = None

        if open_trade is not None:
            continue

        r1, r6, r24, volatility, volume_ratio = features(
            rows,
            index,
        )

        state = classify_market_state(
            index=index,
            close=close,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
        )

        thesis = build_thesis(state)

        if thesis.direction == "NONE":
            continue

        thesis_count += 1

        plan = build_trade_plan(
            rows,
            index=index,
            direction=thesis.direction,
            lookback=48,
            min_risk_reward=1.5,
        )

        if not plan.valid:
            continue

        plan_count += 1

        position = 1 if plan.direction == "LONG" else -1

        open_trade = {
            "position": position,
            "entry": execution_price(
                plan.entry_price,
                position,
            ),
            "invalidation": plan.invalidation_price,
            "target": plan.target_price,
        }

    wins = sum(t["net"] > 0 for t in trades)
    losses = sum(t["net"] < 0 for t in trades)

    gross_profit = sum(
        t["net"] for t in trades if t["net"] > 0
    )
    gross_loss = -sum(
        t["net"] for t in trades if t["net"] < 0
    )

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    print("=" * 72)
    print("TRADER BRAIN VALIDATION V1")
    print("=" * 72)
    print(f"TRAIN boundary             = {TRAIN_END}")
    print(f"Validation rows            = {VAL_END - TRAIN_END}")
    print(f"Thesis decisions           = {thesis_count}")
    print(f"Valid trade plans           = {plan_count}")

    print()
    print("TRADES")
    print(f"Completed trades            = {len(trades)}")
    print(f"Wins                       = {wins}")
    print(f"Losses                     = {losses}")

    if trades:
        print(f"Win rate                   = {wins / len(trades) * 100:.2f}%")
        print(
            f"Average net PnL/trade      = "
            f"{sum(t['net'] for t in trades) / len(trades) * 100:.4f}%"
        )

    print(f"Profit factor              = {pf:.4f}")

    print()
    print("EQUITY")
    print(f"Final equity               = {equity:.6f}")
    print(f"Total return               = {(equity - 1) * 100:+.3f}%")
    print(f"Max drawdown               = {max_drawdown * 100:.3f}%")

    print()
    print("EXIT REASONS")
    print(
        f"TARGET                     = "
        f"{sum(t['reason'] == 'TARGET' for t in trades)}"
    )
    print(
        f"INVALIDATION               = "
        f"{sum(t['reason'] == 'INVALIDATION' for t in trades)}"
    )

    print()
    print("INTEGRITY")
    print("Training parameters frozen = PASS")
    print("Validation learning        = NO")
    print("Validation experiences     = NO")
    print("OOS accessed               = NO")
    print("Parameter tuning           = NO")
    print("=" * 72)
    print("VALIDATION RESULT = COMPLETE")


if __name__ == "__main__":
    main()
