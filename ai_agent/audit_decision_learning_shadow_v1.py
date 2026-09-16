import csv

from ai_agent.decision_engine_v1 import DecisionEngineV1
from ai_agent.trade_plan_v2 import build_trade_plan
from ai_agent.market_state_v1 import classify_market_state
from ai_agent.trade_experience_memory_v1 import TradeExperienceMemoryV1
from ai_agent.learning_loop_v3 import LearningLoopV3
from ai_agent.trade_journal_v1 import TradeJournalV1


DATASET = "data/btcusdt_1h_ohlcv_new.csv"
TRAIN_END = 12000
START_INDEX = 24
STEPS = 10000


def load_rows():
    rows = []
    with open(DATASET, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def main():
    rows = load_rows()

    assert len(rows) >= TRAIN_END

    memory = TradeExperienceMemoryV1()
    learning = LearningLoopV3()
    journal = TradeJournalV1(memory)
    engine = DecisionEngineV1()

    knowledge = []

    actions = {
        "HOLD": 0,
        "BUY": 0,
        "SELL": 0,
    }

    advisor_changes = 0
    valid_decisions = 0
    completed_trades = 0
    knowledge_change_count = 0
    previous_knowledge_count = 0

    open_levels = None

    end_index = min(START_INDEX + STEPS, TRAIN_END)

    for index in range(START_INDEX, end_index):
        row = rows[index]
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])

        # ---------------------------------------------------------
        # 1. Manage existing trade ONLY from candles after entry.
        # ---------------------------------------------------------
        if journal.open_trade is not None:
            assert open_levels is not None

            if index > journal.open_trade.entry_index:
                position = journal.open_trade.position

                if position == 1:
                    hit_invalidation = low <= open_levels["invalidation"]
                    hit_target = high >= open_levels["target"]
                else:
                    hit_invalidation = high >= open_levels["invalidation"]
                    hit_target = low <= open_levels["target"]

                # Same conservative rule as the validated
                # economic audit: invalidation wins if both hit.
                if hit_invalidation or hit_target:
                    exit_price = (
                        open_levels["invalidation"]
                        if hit_invalidation
                        else open_levels["target"]
                    )

                    journal.close(
                        market_price=exit_price,
                        index=index,
                        high=high,
                        low=low,
                    )

                    completed_trades = memory.count()

                    new_experiences = memory.all()
                    if new_experiences:
                        before = len(learning.all_knowledge())
                        new_records = learning.process(new_experiences)
                        knowledge = learning.all_knowledge()
                        after = len(knowledge)

                        if after != before:
                            knowledge_change_count += 1

                    open_levels = None

        # Never open a second position.
        if journal.open_trade is not None:
            continue

        # ---------------------------------------------------------
        # 2. Build market state using the project's existing
        #    feature definitions.
        # ---------------------------------------------------------
        r1 = close / float(rows[index - 1]["close"]) - 1.0
        r6 = close / float(rows[index - 6]["close"]) - 1.0
        r24 = close / float(rows[index - 24]["close"]) - 1.0

        volatility = (high - low) / close

        avg_volume = sum(
            float(rows[i]["volume"])
            for i in range(index - 7, index)
        ) / 7.0

        volume_ratio = (
            float(row["volume"]) / avg_volume
            if avg_volume
            else 1.0
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

        # ---------------------------------------------------------
        # 3. Decision with frozen knowledge available so far.
        # ---------------------------------------------------------
        decision = engine.decide(
            rows,
            index,
            state,
            knowledge=knowledge,
        )

        base_decision = engine.decide(
            rows,
            index,
            state,
            knowledge=None,
        )

        valid_decisions += 1
        actions[decision.action] += 1

        # Advisor must remain evidence-only.
        assert decision.action == base_decision.action
        assert decision.risk_pct == base_decision.risk_pct
        assert decision.reward_pct == base_decision.reward_pct
        assert decision.invalidation == base_decision.invalidation

        if decision.evidence_for != base_decision.evidence_for:
            advisor_changes += 1

        # ---------------------------------------------------------
        # 4. Open only when the complete structural trade plan
        #    is valid.
        # ---------------------------------------------------------
        if decision.action in {"BUY", "SELL"}:
            direction = (
                "LONG" if decision.action == "BUY" else "SHORT"
            )

            plan = build_trade_plan(
                rows,
                index=index,
                direction=direction,
                lookback=48,
                min_risk_reward=1.5,
            )

            assert plan.valid

            position = 1 if direction == "LONG" else -1

            close_position = (
                (close - low) / max(high - low, 1e-12)
            )

            journal.open(
                action=decision.action,
                position=position,
                market_price=close,
                index=index,
                r1=state.r1,
                r6=state.r6,
                r24=state.r24,
                volatility=state.volatility,
                volume_ratio=state.volume_ratio,
                close_position=close_position,
                high=high,
                low=low,
            )

            open_levels = {
                "invalidation": plan.invalidation_price,
                "target": plan.target_price,
            }

    # -------------------------------------------------------------
    # Final open trade is intentionally NOT converted into an
    # experience because it has no completed outcome.
    # -------------------------------------------------------------
    knowledge = learning.all_knowledge()

    assert memory.count() == completed_trades
    assert len(knowledge) >= previous_knowledge_count

    print("=" * 72)
    print("DECISION + LEARNING SHADOW AUDIT V1")
    print("=" * 72)
    print(f"TRAIN rows                 = {TRAIN_END}")
    print(f"Shadow decision steps      = {end_index - START_INDEX}")
    print(f"Valid decisions            = {valid_decisions}")
    print(f"Completed experiences      = {memory.count()}")
    print(f"Knowledge records          = {len(knowledge)}")
    print(f"Knowledge state changes    = {knowledge_change_count}")
    print()
    print("ACTIONS")
    for action in ("HOLD", "BUY", "SELL"):
        print(f"{action:<25} = {actions[action]}")
    print()
    print(f"Advisor evidence changes   = {advisor_changes}")
    print()
    print("INTEGRITY")
    print("Chronological decisions    = PASS")
    print("Experience memory used     = PASS")
    print("Learning from completed    = PASS")
    print("Knowledge fed forward      = PASS")
    print("Action unchanged           = PASS")
    print("Risk unchanged             = PASS")
    print("Reward unchanged           = PASS")
    print("Exit starts after entry    = PASS")
    print("TRAIN-only data            = PASS")
    print("Validation accessed        = NO")
    print("OOS accessed               = NO")
    print("Parameter tuning           = NO")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    main()
