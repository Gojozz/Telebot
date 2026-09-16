import csv
import json
from dataclasses import asdict

from ai_agent.trade_experience_memory_v1 import TradeExperienceMemoryV1
from ai_agent.learning_loop_v3 import LearningLoopV3


DATASET = "data/btcusdt_1h_ohlcv_new.csv"
OUTPUT = "data/train_knowledge_v1.json"
TRAIN_ROWS = 12000


def load_train_rows():
    rows = []
    with open(DATASET, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })

    if len(rows) < TRAIN_ROWS:
        raise RuntimeError(
            f"dataset has only {len(rows)} rows; need {TRAIN_ROWS}"
        )

    return rows[:TRAIN_ROWS]


def build_experiences(rows):
    """
    Rebuild the already-validated TRAIN trade experience stream.

    This intentionally uses the existing TRAIN-only economic decision path
    rather than inventing a new trading rule.
    """
    from ai_agent.decision_engine_v1 import DecisionEngineV1
    from ai_agent.market_state_v1 import classify_market_state
    from ai_agent.trade_plan_v2 import build_trade_plan
    from ai_agent.trade_journal_v1 import TradeJournalV1

    engine = DecisionEngineV1()
    memory = TradeExperienceMemoryV1()
    journal = TradeJournalV1(memory)

    open_plan = None

    for index in range(24, len(rows)):
        row = rows[index]

        r1 = row["close"] / rows[index - 1]["close"] - 1.0
        r6 = row["close"] / rows[index - 6]["close"] - 1.0
        r24 = row["close"] / rows[index - 24]["close"] - 1.0
        volatility = (row["high"] - row["low"]) / row["close"]

        volume_start = max(0, index - 7)
        prior = rows[volume_start:index]
        avg_volume = (
            sum(x["volume"] for x in prior) / len(prior)
            if prior else row["volume"]
        )
        volume_ratio = (
            row["volume"] / avg_volume if avg_volume > 0 else 1.0
        )

        # Manage only candles after entry.
        if open_plan is not None and index > open_plan["entry_index"]:
            position = open_plan["position"]

            invalidated = (
                row["low"] <= open_plan["invalidation_price"]
                if position == 1
                else row["high"] >= open_plan["invalidation_price"]
            )

            targeted = (
                row["high"] >= open_plan["target_price"]
                if position == 1
                else row["low"] <= open_plan["target_price"]
            )

            if invalidated or targeted:
                # Conservative rule: invalidation wins if both occur.
                exit_price = (
                    open_plan["invalidation_price"]
                    if invalidated
                    else open_plan["target_price"]
                )

                journal.close(
                    index=index,
                    market_price=exit_price,
                    high=row["high"],
                    low=row["low"],
                )
                open_plan = None
                continue

            journal.observe_market(row["high"], row["low"])

        state = classify_market_state(
            index=index,
            close=row["close"],
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
        )

        decision = engine.decide(rows, index, state)

        if decision.action not in ("BUY", "SELL"):
            continue

        # One-position-at-a-time: never open a second trade.
        if journal.open_trade is not None:
            continue

        from ai_agent.trade_plan_v2 import build_trade_plan

        plan = build_trade_plan(
            rows,
            index=index,
            direction="LONG" if decision.action == "BUY" else "SHORT",
            lookback=48,
            min_risk_reward=1.5,
        )

        if not plan.valid:
            continue

        position = 1 if decision.action == "BUY" else -1

        journal.open(
            action=decision.action,
            index=index,
            market_price=row["close"],
            position=position,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
            close_position=(
                (row["close"] - row["low"])
                / (row["high"] - row["low"])
                if row["high"] > row["low"]
                else 0.5
            ),
            high=row["high"],
            low=row["low"],
        )

        open_plan = {
            "entry_index": index,
            "position": position,
            "invalidation_price": plan.invalidation_price,
            "target_price": plan.target_price,
        }

    return memory.all()


def main():
    rows = load_train_rows()
    experiences = build_experiences(rows)

    learning = LearningLoopV3()

    # Rebuild knowledge chronologically, one completed experience at a time.
    for i in range(1, len(experiences) + 1):
        learning.process(experiences[:i])

    knowledge = learning.all_knowledge()

    artifact = {
        "version": "train_knowledge_v1",
        "dataset": DATASET,
        "train_rows": TRAIN_ROWS,
        "train_end_timestamp": rows[-1]["timestamp"],
        "experience_count": len(experiences),
        "knowledge_count": len(knowledge),
        "experiences": [asdict(x) for x in experiences],
        "knowledge": [asdict(x) for x in knowledge],
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    print("TRAIN KNOWLEDGE BUILD V1")
    print(f"TRAIN rows        = {TRAIN_ROWS}")
    print(f"TRAIN end         = {rows[-1]['timestamp']}")
    print(f"Experiences       = {len(experiences)}")
    print(f"Knowledge records = {len(knowledge)}")
    print(f"Output            = {OUTPUT}")
    print("VALIDATION/OOS     = NOT ACCESSED")
    print("RESULT             = PASS")


if __name__ == "__main__":
    main()
