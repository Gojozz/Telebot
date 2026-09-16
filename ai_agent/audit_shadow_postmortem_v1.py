from ai_agent.shadow_learning_v1 import (
    load_rows,
    TRAIN_END,
    START_INDEX,
    STEPS,
    FEE_RATE,
    SLIPPAGE_RATE,
)
from ai_agent.environment_v3 import TradingEnvironmentV3
from ai_agent.state_encoder import StateEncoder
from ai_agent.online_q_policy_v2 import OnlineQPolicyV2
from ai_agent.trade_experience_memory_v1 import TradeExperienceMemoryV1
from ai_agent.trade_journal_v1 import TradeJournalV1
from ai_agent.post_mortem_learner_v1 import PostMortemLearnerV1


def context_values(rows, index):
    closes = [float(r["close"]) for r in rows[: index + 1]]
    highs = [float(r["high"]) for r in rows[: index + 1]]
    lows = [float(r["low"]) for r in rows[: index + 1]]
    volumes = [float(r["volume"]) for r in rows[: index + 1]]

    c = closes[-1]
    r1 = closes[-1] / closes[-2] - 1.0
    r6 = closes[-1] / closes[-7] - 1.0
    r24 = closes[-1] / closes[-25] - 1.0
    volatility = (highs[-1] - lows[-1]) / c

    avg_volume = sum(volumes[-7:]) / 7.0
    volume_ratio = volumes[-1] / avg_volume

    candle_range = highs[-1] - lows[-1]
    close_position = (
        (c - lows[-1]) / candle_range
        if candle_range > 0
        else 0.5
    )

    return {
        "r1": r1,
        "r6": r6,
        "r24": r24,
        "volatility": volatility,
        "volume_ratio": volume_ratio,
        "close_position": close_position,
    }


def run_shadow():
    all_rows = load_rows("data/btcusdt_1h_ohlcv_new.csv")
    assert len(all_rows) >= TRAIN_END

    rows = all_rows[:TRAIN_END]

    env = TradingEnvironmentV3(
        rows,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )
    encoder = StateEncoder()
    policy = OnlineQPolicyV2(
        learning_rate=0.05,
        discount=0.95,
        exploration=0.10,
        seed=42,
    )
    memory = TradeExperienceMemoryV1()
    journal = TradeJournalV1(
        memory,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )

    env.reset(start_index=START_INDEX)

    for _ in range(STEPS):
        index = env.index
        position_before = env.position

        closes = [float(r["close"]) for r in rows[: index + 1]]
        highs = [float(r["high"]) for r in rows[: index + 1]]
        lows = [float(r["low"]) for r in rows[: index + 1]]
        volumes = [float(r["volume"]) for r in rows[: index + 1]]

        state = encoder.encode(
            closes,
            highs,
            lows,
            volumes,
            position_before,
        )

        action = policy.choose_action(state)

        ctx = context_values(rows, index)
        journal.observe_market(float(rows[index]["high"]), float(rows[index]["low"]))

        _, _, done, _ = env.step(action)

        position_after = env.position

        if position_before == 0 and position_after != 0:
            journal.open(
                action="BUY" if position_after == 1 else "SELL",
                position=position_after,
                market_price=float(rows[index]["close"]),
                high=float(rows[index]["high"]),
                low=float(rows[index]["low"]),
                index=index,
                **ctx,
            )

        elif position_before != 0 and position_after == 0:
            journal.close(
                market_price=float(rows[index]["close"]),
                index=index,
                high=float(rows[index]["high"]),
                low=float(rows[index]["low"]),
            )

        elif position_before != 0 and position_after != 0:
            if position_before != position_after:
                journal.close(
                    market_price=float(rows[index]["close"]),
                    index=index,
                    high=float(rows[index]["high"]),
                    low=float(rows[index]["low"]),
                )
                journal.open(
                    action="BUY" if position_after == 1 else "SELL",
                    position=position_after,
                    market_price=float(rows[index]["close"]),
                    index=index,
                    r1=ctx["r1"],
                    r6=ctx["r6"],
                    r24=ctx["r24"],
                    volatility=ctx["volatility"],
                    volume_ratio=ctx["volume_ratio"],
                    close_position=ctx["close_position"],
                    high=float(rows[index]["high"]),
                    low=float(rows[index]["low"]),
                )

        if not done:
            journal.observe_market(float(rows[env.index]["high"]), float(rows[env.index]["low"]))

        if done:
            break

    if journal.open_trade is not None:
        last_index = min(env.index, len(rows) - 1)
        journal.close(
            market_price=float(rows[last_index]["close"]),
            index=last_index,
            high=float(rows[last_index]["high"]),
            low=float(rows[last_index]["low"]),
        )

    return rows, memory, policy, env


def main():
    print("=" * 80)
    print("SHADOW -> POST-MORTEM INTEGRATION V1")
    print("=" * 80)
    print("TRAIN data only")
    print("No validation/OOS access")
    print()

    rows, memory, policy, env = run_shadow()

    before_states = len(policy.values)
    before_equity = env.equity

    learner = PostMortemLearnerV1(
        prior_win_rate=0.50,
        prior_avg_pnl_pct=0.0,
        prior_weight=5.0,
        min_trades=5,
    )

    evidence = learner.learn(memory.all())

    assert len(rows) == TRAIN_END
    assert memory.count() == 100
    assert len(policy.values) == before_states
    assert env.equity == before_equity
    assert all(e.trades >= 1 for e in evidence)

    reliable = [e for e in evidence if learner.reliable(e)]

    print(f"TRAIN rows              = {len(rows)}")
    print(f"Completed experiences   = {memory.count()}")
    print(f"Evidence groups         = {len(evidence)}")
    print(f"Reliable evidence       = {len(reliable)}")
    print(f"Policy states unchanged = {len(policy.values)}")
    print(f"Final equity unchanged  = {env.equity:.6f}")
    print()

    if reliable:
        print("Reliable evidence:")
        for e in sorted(
            reliable,
            key=lambda x: x.evidence_score,
            reverse=True,
        )[:10]:
            print(
                f"{e.action:5s} "
                f"trades={e.trades:3d} "
                f"wins={e.wins:3d} "
                f"losses={e.losses:3d} "
                f"win_rate={e.raw_win_rate:.2%} "
                f"confidence={e.confidence:.2%} "
                f"score={e.evidence_score:+.6f}"
            )
    else:
        print("No reliable context/action evidence yet.")

    print()
    print("Memory → evidence       = PASS")
    print("No policy mutation      = PASS")
    print("TRAIN boundary          = PASS")
    print("No validation/OOS       = PASS")
    print("INTEGRATION RESULT      = PASS")


if __name__ == "__main__":
    main()
