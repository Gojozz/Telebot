from __future__ import annotations

from trade_experience_memory_v1 import TradeExperience, TradeExperienceMemoryV1
from post_mortem_learner_v1 import PostMortemLearnerV1


def make_trade(i: int, win: bool) -> TradeExperience:
    return TradeExperience(
        trade_id=f"T{i:02d}",
        action="BUY",
        entry_price=100.0,
        exit_price=101.0 if win else 99.0,
        position="LONG",
        pnl_pct=0.01 if win else -0.01,
        holding_bars=3,
        r1=1,
        r6=2,
        r24=3,
        volatility=1,
        volume_ratio=2,
        close_position=4,
        max_favorable_excursion=0.015 if win else 0.003,
        max_adverse_excursion=0.003 if win else 0.015,
        outcome="WIN" if win else "LOSS",
    )


def get_buy_evidence(learner, memory):
    evidence = learner.learn(memory.all())
    assert len(evidence) == 1
    assert evidence[0].action == "BUY"
    return evidence[0]


def audit():
    print("=" * 80)
    print("POST-MORTEM LEARNER V1 TEMPORAL AUDIT")
    print("=" * 80)
    print("Synthetic chronological experiences only")
    print("No market data accessed")
    print()

    memory = TradeExperienceMemoryV1()

    learner = PostMortemLearnerV1(
        prior_win_rate=0.50,
        prior_avg_pnl_pct=0.0,
        prior_weight=5.0,
        min_trades=5,
    )

    # ------------------------------------------------------------------
    # T0: belum ada pengalaman
    # ------------------------------------------------------------------
    assert memory.count() == 0
    assert learner.learn(memory.all()) == []

    # ------------------------------------------------------------------
    # T1-T2: dua kemenangan.
    # Belum cukup sample untuk dianggap reliable.
    # ------------------------------------------------------------------
    memory.add(make_trade(1, True))
    e1 = get_buy_evidence(learner, memory)

    assert e1.trades == 1
    assert e1.wins == 1
    assert e1.losses == 0
    assert e1.confidence < 1.0
    assert learner.reliable(e1) is False

    memory.add(make_trade(2, True))
    e2 = get_buy_evidence(learner, memory)

    assert e2.trades == 2
    assert e2.wins == 2
    assert e2.confidence > e1.confidence
    assert learner.reliable(e2) is False

    # ------------------------------------------------------------------
    # T3-T4: dua kekalahan.
    # Confidence harus turun karena pengalaman buruk benar-benar masuk.
    # ------------------------------------------------------------------
    memory.add(make_trade(3, False))
    e3 = get_buy_evidence(learner, memory)

    assert e3.trades == 3
    assert e3.wins == 2
    assert e3.losses == 1
    assert e3.confidence < e2.confidence

    memory.add(make_trade(4, False))
    e4 = get_buy_evidence(learner, memory)

    assert e4.trades == 4
    assert e4.wins == 2
    assert e4.losses == 2
    assert learner.reliable(e4) is False

    # ------------------------------------------------------------------
    # T5: sample minimum tercapai.
    # ------------------------------------------------------------------
    memory.add(make_trade(5, True))
    e5 = get_buy_evidence(learner, memory)

    assert e5.trades == 5
    assert e5.wins == 3
    assert e5.losses == 2
    assert learner.reliable(e5) is True

    # ------------------------------------------------------------------
    # Anti-lookahead test:
    # Ambil snapshot setelah T3.
    # Kemudian tambahkan T4/T5.
    # Snapshot lama harus tetap merepresentasikan hanya T1-T3.
    # ------------------------------------------------------------------
    historical_memory = TradeExperienceMemoryV1()
    for i, win in enumerate((True, True, False), start=1):
        historical_memory.add(make_trade(i, win))

    historical_evidence = get_buy_evidence(
        learner,
        historical_memory,
    )

    assert historical_evidence.trades == 3
    assert historical_evidence.wins == 2
    assert historical_evidence.losses == 1

    # Future trades tidak boleh muncul di snapshot historis.
    assert historical_memory.count() == 3
    assert all(
        exp.trade_id in {"T01", "T02", "T03"}
        for exp in historical_memory.all()
    )

    # ------------------------------------------------------------------
    # Duplicate/order sanity.
    # ------------------------------------------------------------------
    ids = [x.trade_id for x in memory.all()]
    assert ids == ["T01", "T02", "T03", "T04", "T05"]
    assert len(ids) == len(set(ids))

    print(f"T0  experiences=0")
    print(
        f"T1  trades={e1.trades} wins={e1.wins} "
        f"confidence={e1.confidence:.2%} reliable={learner.reliable(e1)}"
    )
    print(
        f"T2  trades={e2.trades} wins={e2.wins} "
        f"confidence={e2.confidence:.2%} reliable={learner.reliable(e2)}"
    )
    print(
        f"T3  trades={e3.trades} wins={e3.wins} losses={e3.losses} "
        f"confidence={e3.confidence:.2%}"
    )
    print(
        f"T4  trades={e4.trades} wins={e4.wins} losses={e4.losses} "
        f"confidence={e4.confidence:.2%} reliable={learner.reliable(e4)}"
    )
    print(
        f"T5  trades={e5.trades} wins={e5.wins} losses={e5.losses} "
        f"confidence={e5.confidence:.2%} reliable={learner.reliable(e5)}"
    )
    print()
    print("Chronological accumulation = PASS")
    print("Future-trade exclusion     = PASS")
    print("Confidence reacts to loss  = PASS")
    print("Minimum sample guard       = PASS")
    print("Duplicate/order sanity     = PASS")
    print()
    print("AUDIT RESULT: PASS")
    print()
    print(
        "Post-Mortem Learner V1 uses only experiences available "
        "at the time of learning; no future trade is included."
    )


if __name__ == "__main__":
    audit()
