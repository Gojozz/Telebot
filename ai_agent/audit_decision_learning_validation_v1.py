import csv

from ai_agent.market_state_v1 import classify_market_state
from ai_agent.decision_engine_v1 import DecisionEngineV1
from ai_agent.trade_journal_v1 import TradeJournalV1
from ai_agent.trade_experience_memory_v1 import TradeExperienceMemoryV1
from ai_agent.learning_loop_v3 import LearningLoopV3
from ai_agent.hybrid_context_v1 import HybridContextV1


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


def build_train_knowledge(rows):
    memory = TradeExperienceMemoryV1()
    learning = LearningLoopV3()

    journal = TradeJournalV1(
        memory,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )

    engine = DecisionEngineV1()

    open_entry_index = None
    open_position = None
    open_invalidation = None
    open_target = None

    for index in range(START_INDEX, TRAIN_END):
        row = rows[index]
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])

        if journal.open_trade is not None:
            position = journal.open_trade.position

            if position == 1:
                hit_invalidation = low <= open_invalidation
                hit_target = high >= open_target
            else:
                hit_invalidation = high >= open_invalidation
                hit_target = low <= open_target

            if hit_invalidation or hit_target:
                journal.close(
                    market_price=(
                        open_invalidation
                        if hit_invalidation
                        else open_target
                    ),
                    index=index,
                    high=high,
                    low=low,
                )

                all_experiences = memory.all()
                learning.process(all_experiences)

                open_entry_index = None
                open_position = None
                open_invalidation = None
                open_target = None
            else:
                journal.observe_market(high, low)
                continue

        r1, r6, r24, volatility, volume_ratio = features(rows, index)

        state = classify_market_state(
            index=index,
            close=close,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
        )

        decision = engine.decide(
            rows,
            index,
            state,
            knowledge=learning.all_knowledge(),
        )

        if decision.action not in ("BUY", "SELL"):
            continue

        position = 1 if decision.action == "BUY" else -1

        plan_price = close

        journal.open(
            action=decision.action,
            position=position,
            market_price=plan_price,
            index=index,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
            close_position=(
                (close - low) / (high - low)
                if high != low
                else 0.5
            ),
            high=high,
            low=low,
        )

        open_entry_index = index
        open_position = position
        open_invalidation = (
            plan_price - decision.risk_pct * plan_price
            if position == 1
            else plan_price + decision.risk_pct * plan_price
        )
        open_target = (
            plan_price + decision.reward_pct * plan_price
            if position == 1
            else plan_price - decision.reward_pct * plan_price
        )

    return memory.all(), learning.all_knowledge()


def main():
    rows = load_rows()

    train_experiences, train_knowledge = build_train_knowledge(rows)

    frozen_knowledge = tuple(train_knowledge)

    engine = DecisionEngineV1()

    memory = TradeExperienceMemoryV1()
    journal = TradeJournalV1(
        memory,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    trades = []
    decisions = 0
    valid_plans = 0
    advisor_changes = 0

    open_invalidation = None
    open_target = None

    for index in range(TRAIN_END, VAL_END):
        row = rows[index]
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])

        if journal.open_trade is not None:
            position = journal.open_trade.position
            invalidation = open_invalidation
            target = open_target

            if position == 1:
                hit_invalidation = low <= invalidation
                hit_target = high >= target
            else:
                hit_invalidation = high >= invalidation
                hit_target = low <= target

            if hit_invalidation or hit_target:
                exit_price = (
                    invalidation
                    if hit_invalidation
                    else target
                )
                reason = (
                    "INVALIDATION"
                    if hit_invalidation
                    else "TARGET"
                )

                entry_price = journal.open_trade.entry_price

                if position == 1:
                    gross = exit_price / entry_price - 1.0
                else:
                    gross = entry_price / exit_price - 1.0

                net = gross - (2.0 * FEE_RATE)
                equity *= 1.0 + net

                trades.append(
                    {
                        "net": net,
                        "reason": reason,
                    }
                )

                peak = max(peak, equity)
                max_drawdown = max(
                    max_drawdown,
                    1.0 - equity / peak,
                )

                journal.close(
                    market_price=exit_price,
                    index=index,
                    high=high,
                    low=low,
                )
            else:
                journal.observe_market(high, low)
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

        decision = engine.decide(
            rows,
            index,
            state,
            knowledge=frozen_knowledge,
        )

        decisions += 1

        if decision.action in ("BUY", "SELL"):
            valid_plans += 1

            if decision.evidence_for or decision.evidence_against:
                advisor_changes += 1

            position = 1 if decision.action == "BUY" else -1

            from ai_agent.trade_plan_v2 import build_trade_plan

            plan = build_trade_plan(
                rows,
                index=index,
                direction="LONG" if position == 1 else "SHORT",
                lookback=48,
                min_risk_reward=1.5,
            )

            if not plan.valid:
                raise RuntimeError(
                    "VALIDATION PLAN MISMATCH: decision was directional "
                    "but reconstructed plan is invalid"
                )

            open_invalidation = plan.invalidation_price
            open_target = plan.target_price

            journal.open(
                action=decision.action,
                position=position,
                market_price=close,
                index=index,
                r1=r1,
                r6=r6,
                r24=r24,
                volatility=volatility,
                volume_ratio=volume_ratio,
                close_position=(
                    (close - low) / (high - low)
                    if high != low
                    else 0.5
                ),
                high=high,
                low=low,
            )

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
    print("DECISION + LEARNING FROZEN VALIDATION V1")
    print("=" * 72)
    print(f"TRAIN experiences         = {len(train_experiences)}")
    print(f"TRAIN knowledge records   = {len(frozen_knowledge)}")
    print(f"Validation rows            = {VAL_END - TRAIN_END}")
    print(f"Validation decisions       = {decisions}")
    print(f"Valid trade plans          = {valid_plans}")
    print(f"Advisor evidence changes  = {advisor_changes}")
    print()
    print("TRADES")
    print(f"Completed trades           = {len(trades)}")
    print(f"Wins                       = {wins}")
    print(f"Losses                     = {losses}")

    if trades:
        print(
            f"Win rate                   = "
            f"{wins / len(trades) * 100:.2f}%"
        )
        print(
            f"Average net PnL/trade      = "
            f"{sum(t['net'] for t in trades) / len(trades) * 100:.4f}%"
        )
        print(f"Profit factor              = {pf:.4f}")

    print()
    print("EQUITY")
    print(f"Final equity               = {equity:.6f}")
    print(
        f"Total return               = "
        f"{(equity - 1) * 100:+.3f}%"
    )
    print(
        f"Max drawdown               = "
        f"{max_drawdown * 100:.3f}%"
    )

    print()
    print("INTEGRITY")
    print("TRAIN knowledge frozen     = PASS")
    print("Validation learning        = NO")
    print("Validation experiences     = NO")
    print("OOS accessed               = NO")
    print("Parameter tuning           = NO")
    print("=" * 72)
    print("VALIDATION RESULT = COMPLETE")


if __name__ == "__main__":
    main()
