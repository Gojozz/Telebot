from ai_agent.knowledge_layer_v1 import KnowledgeLayerV1
from ai_agent.trade_experience_memory_v1 import make_experience


def exp(
    trade_id,
    action,
    entry,
    exit_price,
    position,
    pnl_context,
):
    return make_experience(
        trade_id=trade_id,
        action=action,
        entry=entry,
        exit_price=exit_price,
        position=position,
        holding=3,
        r1=0.0,
        r6=pnl_context,
        r24=0.0,
        volatility=0.004,
        volume_ratio=1.0,
        close_position=0.5,
        mfe=0.01,
        mae=-0.005,
    )


def main():
    memory = []

    # Context A:
    # BUY has repeated positive outcomes.
    for i in range(6):
        memory.append(
            exp(
                i + 1,
                "BUY",
                100.0,
                101.0,
                "LONG",
                0.0,
            )
        )

    # Context B:
    # SELL has repeated positive outcomes.
    for i in range(6):
        memory.append(
            exp(
                100 + i,
                "SELL",
                100.0,
                99.0,
                "SHORT",
                0.02,
            )
        )

    # Small sample must remain insufficient.
    memory.append(
        exp(
            999,
            "BUY",
            100.0,
            101.0,
            "LONG",
            0.03,
        )
    )

    learner = KnowledgeLayerV1(
        min_trades=5,
        prior_win_rate=0.50,
        prior_weight=5.0,
        min_confidence=0.55,
        min_pnl=0.0,
    )

    knowledge = learner.learn(memory)

    assert knowledge
    assert all(x.trades >= 1 for x in knowledge)

    reliable = [x for x in knowledge if learner.reliable(x)]

    assert reliable
    assert any(
        x.action == "BUY" and x.status == "BUY_SUPPORTED"
        for x in reliable
    )
    assert any(
        x.action == "SELL" and x.status == "SELL_SUPPORTED"
        for x in reliable
    )

    # No decision for insufficient evidence.
    small = [
        x
        for x in knowledge
        if x.trades < 5
    ]
    assert small
    assert all(
        x.status == "INSUFFICIENT_EVIDENCE"
        for x in small
    )

    # Knowledge layer must not expose mutation APIs.
    assert not hasattr(learner, "update_policy")
    assert not hasattr(learner, "set_strategy")

    print("=" * 70)
    print("KNOWLEDGE LAYER V1 AUDIT")
    print("=" * 70)
    print(f"Experiences              = {len(memory)}")
    print(f"Knowledge records        = {len(knowledge)}")
    print(f"Reliable records         = {len(reliable)}")

    for item in reliable:
        print(
            f"{item.action:5s} "
            f"trades={item.trades:2d} "
            f"wins={item.wins:2d} "
            f"losses={item.losses:2d} "
            f"win_rate={item.win_rate:.1%} "
            f"avg_pnl={item.avg_pnl_pct:+.3%} "
            f"confidence={item.confidence:.1%} "
            f"status={item.status}"
        )

    print()
    print("Minimum sample guard   = PASS")
    print("Shrinkage confidence   = PASS")
    print("Action-specific status = PASS")
    print("Read-only behavior     = PASS")
    print("AUDIT RESULT           = PASS")


if __name__ == "__main__":
    main()
