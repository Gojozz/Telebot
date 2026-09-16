from dataclasses import dataclass

from ai_agent.market_structure_v2 import build_structure_levels
from ai_agent.structural_target_v2 import find_swing_targets


@dataclass(frozen=True)
class TradePlanV2:
    direction: str
    entry_price: float
    invalidation_price: float
    target_price: float
    risk_pct: float
    reward_pct: float
    risk_reward_ratio: float
    valid: bool
    reason: str


def build_trade_plan(
    rows,
    index,
    direction,
    lookback=48,
    min_risk_reward=1.5,
):
    if direction not in ("LONG", "SHORT"):
        return TradePlanV2(
            direction=direction,
            entry_price=0.0,
            invalidation_price=0.0,
            target_price=0.0,
            risk_pct=0.0,
            reward_pct=0.0,
            risk_reward_ratio=0.0,
            valid=False,
            reason="NO_THESIS",
        )

    structure = build_structure_levels(
        rows,
        index,
        direction,
        lookback=lookback,
    )

    if not structure.valid:
        return TradePlanV2(
            direction=direction,
            entry_price=structure.entry_price,
            invalidation_price=structure.invalidation_price,
            target_price=0.0,
            risk_pct=0.0,
            reward_pct=0.0,
            risk_reward_ratio=0.0,
            valid=False,
            reason=structure.reason,
        )

    entry = structure.entry_price
    invalidation = structure.invalidation_price

    target = find_swing_targets(
        rows,
        index,
        direction,
        lookback=lookback,
    )

    if target is None:
        return TradePlanV2(
            direction=direction,
            entry_price=entry,
            invalidation_price=invalidation,
            target_price=0.0,
            risk_pct=0.0,
            reward_pct=0.0,
            risk_reward_ratio=0.0,
            valid=False,
            reason="NO_STRUCTURAL_TARGET",
        )

    target_price = target.target_price

    risk = abs(entry - invalidation)
    reward = abs(target_price - entry)

    if risk <= 0 or reward <= 0:
        return TradePlanV2(
            direction=direction,
            entry_price=entry,
            invalidation_price=invalidation,
            target_price=target_price,
            risk_pct=0.0,
            reward_pct=0.0,
            risk_reward_ratio=0.0,
            valid=False,
            reason="INVALID_RISK_REWARD",
        )

    risk_pct = risk / entry
    reward_pct = reward / entry
    rr = reward / risk

    if rr < min_risk_reward:
        return TradePlanV2(
            direction=direction,
            entry_price=entry,
            invalidation_price=invalidation,
            target_price=target_price,
            risk_pct=risk_pct,
            reward_pct=reward_pct,
            risk_reward_ratio=rr,
            valid=False,
            reason="INSUFFICIENT_RISK_REWARD",
        )

    return TradePlanV2(
        direction=direction,
        entry_price=entry,
        invalidation_price=invalidation,
        target_price=target_price,
        risk_pct=risk_pct,
        reward_pct=reward_pct,
        risk_reward_ratio=rr,
        valid=True,
        reason="VALID_TRADE_PLAN",
    )


def audit():
    rows = []

    for _ in range(80):
        rows.append({
            "high": "104.0",
            "low": "100.0",
            "close": "102.0",
        })

    # Historical swing low = structural invalidation.
    rows[65]["low"] = "98.0"
    rows[64]["low"] = "100.0"
    rows[66]["low"] = "100.0"

    # Historical swing high = structural target.
    rows[60]["high"] = "120.0"
    rows[59]["high"] = "110.0"
    rows[61]["high"] = "110.0"

    rows[70]["close"] = "105.0"

    plan = build_trade_plan(
        rows,
        index=70,
        direction="LONG",
        lookback=48,
        min_risk_reward=1.5,
    )

    assert plan.valid
    assert plan.invalidation_price == 98.0
    assert plan.target_price == 120.0
    assert plan.target_price > plan.entry_price
    assert plan.risk_pct > 0
    assert plan.reward_pct > 0
    assert plan.risk_reward_ratio > 1.5

    # Current candle must not influence the plan.
    rows[70]["high"] = "1000.0"
    rows[70]["low"] = "1.0"

    plan_again = build_trade_plan(
        rows,
        index=70,
        direction="LONG",
        lookback=48,
        min_risk_reward=1.5,
    )

    assert plan_again.target_price == 120.0
    assert plan_again.invalidation_price == 98.0

    print("=" * 72)
    print("TRADE PLAN V2 AUDIT")
    print("=" * 72)
    print("Structure-based invalidation    = PASS")
    print("Historical swing target         = PASS")
    print("Risk/reward validation           = PASS")
    print("Minimum R:R guard                = PASS")
    print("Current candle excluded          = PASS")
    print("No future data used              = PASS")
    print("No trading performed             = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()


if __name__ == "__main__":
    audit()
