from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPlanV1:
    entry_price: float
    invalidation_price: float
    target_price: float
    risk_pct: float
    reward_pct: float
    risk_reward_ratio: float
    valid: bool
    reason: str


def build_risk_plan(
    direction: str,
    entry_price: float,
    invalidation_price: float,
    target_price: float,
) -> RiskPlanV1:

    if direction not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")

    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    if invalidation_price <= 0 or target_price <= 0:
        raise ValueError("prices must be > 0")

    if direction == "LONG":
        risk_pct = (entry_price - invalidation_price) / entry_price
        reward_pct = (target_price - entry_price) / entry_price

    else:
        risk_pct = (invalidation_price - entry_price) / entry_price
        reward_pct = (entry_price - target_price) / entry_price

    if risk_pct <= 0:
        return RiskPlanV1(
            entry_price,
            invalidation_price,
            target_price,
            risk_pct,
            reward_pct,
            0.0,
            False,
            "INVALIDATION_ON_WRONG_SIDE",
        )

    if reward_pct <= 0:
        return RiskPlanV1(
            entry_price,
            invalidation_price,
            target_price,
            risk_pct,
            reward_pct,
            0.0,
            False,
            "TARGET_ON_WRONG_SIDE",
        )

    ratio = reward_pct / risk_pct

    return RiskPlanV1(
        entry_price,
        invalidation_price,
        target_price,
        risk_pct,
        reward_pct,
        ratio,
        True,
        "VALID",
    )


def audit():
    # LONG: risk 1%, reward 3%.
    long_plan = build_risk_plan(
        direction="LONG",
        entry_price=100_000,
        invalidation_price=99_000,
        target_price=103_000,
    )

    assert long_plan.valid
    assert abs(long_plan.risk_pct - 0.01) < 1e-9
    assert abs(long_plan.reward_pct - 0.03) < 1e-9
    assert abs(long_plan.risk_reward_ratio - 3.0) < 1e-9

    # SHORT: risk 1%, reward 3%.
    short_plan = build_risk_plan(
        direction="SHORT",
        entry_price=100_000,
        invalidation_price=101_000,
        target_price=97_000,
    )

    assert short_plan.valid
    assert abs(short_plan.risk_pct - 0.01) < 1e-9
    assert abs(short_plan.reward_pct - 0.03) < 1e-9
    assert abs(short_plan.risk_reward_ratio - 3.0) < 1e-9

    # Wrong-side invalidation must be rejected.
    bad_invalidation = build_risk_plan(
        direction="LONG",
        entry_price=100_000,
        invalidation_price=101_000,
        target_price=103_000,
    )

    assert not bad_invalidation.valid
    assert bad_invalidation.reason == "INVALIDATION_ON_WRONG_SIDE"

    # Wrong-side target must be rejected.
    bad_target = build_risk_plan(
        direction="SHORT",
        entry_price=100_000,
        invalidation_price=101_000,
        target_price=103_000,
    )

    assert not bad_target.valid
    assert bad_target.reason == "TARGET_ON_WRONG_SIDE"

    print("=" * 72)
    print("RISK ENGINE V1 AUDIT")
    print("=" * 72)
    print("LONG risk/reward calculation       = PASS")
    print("SHORT risk/reward calculation      = PASS")
    print("Invalidation validation            = PASS")
    print("Target validation                  = PASS")
    print("No trading performed               = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
