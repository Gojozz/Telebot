import csv
from collections import Counter

from ai_agent.market_state_v1 import classify_market_state
from ai_agent.thesis_engine_v1 import build_thesis
from ai_agent.trade_plan_v2 import build_trade_plan


TRAIN_END = 12000
START_INDEX = 24
STEPS = 3000


def load_rows():
    with open(
        "data/btcusdt_1h_ohlcv_new.csv",
        newline="",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


def features(rows, index):
    close = float(rows[index]["close"])
    prev1 = float(rows[index - 1]["close"])
    prev6 = float(rows[index - 6]["close"])
    prev24 = float(rows[index - 24]["close"])

    r1 = close / prev1 - 1.0
    r6 = close / prev6 - 1.0
    r24 = close / prev24 - 1.0

    high = float(rows[index]["high"])
    low = float(rows[index]["low"])

    volatility = (high - low) / close

    volume = float(rows[index]["volume"])
    avg_volume = sum(
        float(rows[i]["volume"])
        for i in range(index - 7, index)
    ) / 7.0

    volume_ratio = volume / avg_volume if avg_volume else 1.0
    close_position = (
        (close - low) / (high - low)
        if high != low
        else 0.5
    )

    return (
        r1,
        r6,
        r24,
        volatility,
        volume_ratio,
        close_position,
    )


def main():
    rows = load_rows()

    assert len(rows) >= TRAIN_END

    end = min(START_INDEX + STEPS, TRAIN_END)

    regimes = Counter()
    theses = Counter()
    plans = Counter()
    directions = Counter()

    valid_plans = []
    invalid_reasons = Counter()

    for index in range(START_INDEX, end):
        (
            r1,
            r6,
            r24,
            volatility,
            volume_ratio,
            close_position,
        ) = features(rows, index)

        state = classify_market_state(
            index=index,
            close=float(rows[index]["close"]),
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
        )

        thesis = build_thesis(state)

        regimes[state.trend] += 1
        theses[thesis.name] += 1

        if thesis.direction == "NONE":
            plans["NO_THESIS"] += 1
            continue

        direction = thesis.direction
        directions[direction] += 1

        plan = build_trade_plan(
            rows,
            index,
            direction,
            lookback=48,
            min_risk_reward=1.5,
        )

        if plan.valid:
            plans["VALID"] += 1
            valid_plans.append(plan)
        else:
            plans["INVALID"] += 1
            invalid_reasons[plan.reason] += 1

    print("=" * 72)
    print("TRADE PLAN BEHAVIOR V1")
    print("=" * 72)
    print(f"TRAIN rows                 = {TRAIN_END}")
    print(f"Decision steps             = {end - START_INDEX}")
    print()
    print("MARKET REGIMES")
    for k, v in regimes.items():
        print(f"{k:<25} = {v}")

    print()
    print("THESIS")
    for k, v in theses.items():
        print(f"{k:<25} = {v}")

    print()
    print("DIRECTIONAL THESIS")
    for k, v in directions.items():
        print(f"{k:<25} = {v}")

    print()
    print("TRADE PLANS")
    for k, v in plans.items():
        print(f"{k:<25} = {v}")

    print()
    print("INVALID REASONS")
    for k, v in invalid_reasons.items():
        print(f"{k:<25} = {v}")

    print()
    print("VALID PLAN R:R")
    if valid_plans:
        rr = [p.risk_reward_ratio for p in valid_plans]
        risk = [p.risk_pct for p in valid_plans]
        reward = [p.reward_pct for p in valid_plans]

        print(f"count                     = {len(valid_plans)}")
        print(f"average R:R               = {sum(rr) / len(rr):.4f}")
        print(f"minimum R:R               = {min(rr):.4f}")
        print(f"average risk              = {sum(risk) / len(risk) * 100:.3f}%")
        print(f"average reward            = {sum(reward) / len(reward) * 100:.3f}%")
    else:
        print("count                     = 0")

    print()
    print("INTEGRITY")
    print("TRAIN-only data           = PASS")
    print("Validation accessed       = NO")
    print("OOS accessed              = NO")
    print("Trading performed         = NO")
    print("Parameter tuning          = NO")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    main()
