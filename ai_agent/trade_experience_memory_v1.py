from dataclasses import dataclass, asdict
from collections import defaultdict
import json


@dataclass
class TradeExperience:
    trade_id: int
    action: str
    entry_price: float
    exit_price: float
    position: str
    pnl_pct: float
    holding_bars: int

    # Market context at decision time
    r1: float
    r6: float
    r24: float
    volatility: float
    volume_ratio: float
    close_position: float

    # Execution / outcome
    max_favorable_excursion: float
    max_adverse_excursion: float
    outcome: str


class TradeExperienceMemoryV1:
    """
    Episodic trade memory.

    Purpose:
    - store completed trading experiences
    - aggregate historical outcomes by context/action
    - provide evidence for a future learner

    This class does NOT decide BUY/SELL.
    """

    def __init__(self):
        self.experiences = []

    def add(self, experience):
        if not isinstance(experience, TradeExperience):
            raise TypeError(
                "experience must be TradeExperience"
            )

        self.experiences.append(experience)

    def all(self):
        return list(self.experiences)

    def count(self):
        return len(self.experiences)

    def action_stats(self):
        stats = defaultdict(
            lambda: {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl_sum": 0.0,
            }
        )

        for e in self.experiences:
            s = stats[e.action]

            s["trades"] += 1

            if e.pnl_pct > 0:
                s["wins"] += 1
            elif e.pnl_pct < 0:
                s["losses"] += 1

            s["pnl_sum"] += e.pnl_pct

        result = {}

        for action, s in stats.items():
            result[action] = {
                **s,
                "win_rate": (
                    s["wins"] / s["trades"]
                    if s["trades"]
                    else 0.0
                ),
                "avg_pnl": (
                    s["pnl_sum"] / s["trades"]
                    if s["trades"]
                    else 0.0
                ),
            }

        return result

    def context_action_stats(
        self,
        context_key,
    ):
        """
        Aggregate outcomes for a discrete context.

        Example context_key:
        ("HIGH_VOL", "POSITIVE_MOMENTUM")
        """

        stats = defaultdict(
            lambda: {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl_sum": 0.0,
            }
        )

        for e in self.experiences:
            key = context_key(e)

            s = stats[(key, e.action)]

            s["trades"] += 1

            if e.pnl_pct > 0:
                s["wins"] += 1
            elif e.pnl_pct < 0:
                s["losses"] += 1

            s["pnl_sum"] += e.pnl_pct

        result = {}

        for (key, action), s in stats.items():
            result[(key, action)] = {
                **s,
                "win_rate": (
                    s["wins"] / s["trades"]
                    if s["trades"]
                    else 0.0
                ),
                "avg_pnl": (
                    s["pnl_sum"] / s["trades"]
                    if s["trades"]
                    else 0.0
                ),
            }

        return result

    def save_json(self, path):
        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                [asdict(e) for e in self.experiences],
                f,
                indent=2,
            )


def make_experience(
    trade_id,
    action,
    entry,
    exit_price,
    position,
    holding,
    r1,
    r6,
    r24,
    volatility,
    volume_ratio,
    close_position,
    mfe,
    mae,
):
    pnl = (
        (exit_price / entry - 1.0)
        if position == "LONG"
        else
        (entry / exit_price - 1.0)
    )

    outcome = (
        "WIN"
        if pnl > 0
        else "LOSS"
        if pnl < 0
        else "FLAT"
    )

    return TradeExperience(
        trade_id=trade_id,
        action=action,
        entry_price=entry,
        exit_price=exit_price,
        position=position,
        pnl_pct=pnl,
        holding_bars=holding,
        r1=r1,
        r6=r6,
        r24=r24,
        volatility=volatility,
        volume_ratio=volume_ratio,
        close_position=close_position,
        max_favorable_excursion=mfe,
        max_adverse_excursion=mae,
        outcome=outcome,
    )


def audit():
    memory = TradeExperienceMemoryV1()

    # Synthetic experiences only.
    # No market dataset is accessed.
    samples = [
        make_experience(
            1, "BUY",
            100, 102, "LONG", 6,
            .002, .008, .015,
            .006, 1.4, .82,
            .025, -.004,
        ),
        make_experience(
            2, "BUY",
            100, 98, "LONG", 4,
            -.003, -.006, -.012,
            .012, 1.8, .31,
            .003, -.024,
        ),
        make_experience(
            3, "SELL",
            100, 97, "SHORT", 5,
            -.002, -.009, -.014,
            .009, 1.6, .22,
            .031, -.003,
        ),
        make_experience(
            4, "SELL",
            100, 101, "SHORT", 3,
            .004, .007, .010,
            .004, .7, .73,
            .002, -.014,
        ),
    ]

    for e in samples:
        memory.add(e)

    assert memory.count() == 4

    stats = memory.action_stats()

    assert stats["BUY"]["trades"] == 2
    assert stats["BUY"]["wins"] == 1
    assert stats["BUY"]["losses"] == 1

    assert stats["SELL"]["trades"] == 2
    assert stats["SELL"]["wins"] == 1
    assert stats["SELL"]["losses"] == 1

    def context(e):
        if e.volatility >= .008:
            vol = "HIGH_VOL"
        else:
            vol = "LOW_VOL"

        if e.r6 > 0:
            mom = "POSITIVE_MOMENTUM"
        else:
            mom = "NEGATIVE_MOMENTUM"

        return (vol, mom)

    context_stats = memory.context_action_stats(
        context
    )

    assert len(context_stats) > 0

    path = "trade_experience_memory_v1_audit.json"
    memory.save_json(path)

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        saved = json.load(f)

    assert len(saved) == 4

    print("=" * 80)
    print("TRADE EXPERIENCE MEMORY V1 AUDIT")
    print("=" * 80)
    print("Synthetic experiences only")
    print("No market data accessed")
    print()

    print(f"experiences        = {memory.count()}")

    for action, s in stats.items():
        print(
            f"{action:5s} "
            f"trades={s['trades']} "
            f"wins={s['wins']} "
            f"losses={s['losses']} "
            f"win_rate={s['win_rate']:.2%} "
            f"avg_pnl={s['avg_pnl']:+.4%}"
        )

    print()
    print(
        f"context groups     = "
        f"{len(context_stats)}"
    )

    print(
        f"json persistence   = "
        f"{len(saved)} records"
    )

    print()
    print("AUDIT RESULT: PASS")
    print()
    print(
        "Memory can store completed trades, "
        "outcomes, market context, MFE/MAE, "
        "and aggregate evidence by action/context."
    )

    print()
    print(
        "IMPORTANT: Memory does NOT make decisions "
        "and does NOT modify strategy parameters."
    )


if __name__ == "__main__":
    audit()
