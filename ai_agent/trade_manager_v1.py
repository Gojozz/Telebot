from dataclasses import dataclass


@dataclass(frozen=True)
class TradeStateV1:
    position: int
    entry_price: float
    invalidation_price: float
    target_price: float


def evaluate_trade(state: TradeStateV1, current_price: float) -> str:
    """
    Returns only a management decision:
    HOLD or EXIT.

    No new BUY/SELL decision is created here.
    """

    if state.position not in (-1, 1):
        raise ValueError("position must be -1 or 1")

    if state.entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    if state.invalidation_price <= 0:
        raise ValueError("invalidation_price must be > 0")

    if state.target_price <= 0:
        raise ValueError("target_price must be > 0")

    if current_price <= 0:
        raise ValueError("current_price must be > 0")

    if state.position == 1:
        if current_price <= state.invalidation_price:
            return "EXIT"

        if current_price >= state.target_price:
            return "EXIT"

    else:
        if current_price >= state.invalidation_price:
            return "EXIT"

        if current_price <= state.target_price:
            return "EXIT"

    return "HOLD"


def audit():
    long_trade = TradeStateV1(
        position=1,
        entry_price=100_000,
        invalidation_price=99_000,
        target_price=103_000,
    )

    assert evaluate_trade(long_trade, 101_000) == "HOLD"
    assert evaluate_trade(long_trade, 98_900) == "EXIT"
    assert evaluate_trade(long_trade, 103_000) == "EXIT"

    short_trade = TradeStateV1(
        position=-1,
        entry_price=100_000,
        invalidation_price=101_000,
        target_price=97_000,
    )

    assert evaluate_trade(short_trade, 99_000) == "HOLD"
    assert evaluate_trade(short_trade, 101_100) == "EXIT"
    assert evaluate_trade(short_trade, 97_000) == "EXIT"

    # Management must never create a new directional order.
    assert evaluate_trade(long_trade, 101_000) in {"HOLD", "EXIT"}
    assert evaluate_trade(short_trade, 99_000) in {"HOLD", "EXIT"}

    print("=" * 72)
    print("TRADE MANAGER V1 AUDIT")
    print("=" * 72)
    print("LONG thesis still valid → HOLD = PASS")
    print("LONG invalidation → EXIT        = PASS")
    print("LONG target → EXIT              = PASS")
    print("SHORT thesis still valid → HOLD = PASS")
    print("SHORT invalidation → EXIT       = PASS")
    print("SHORT target → EXIT             = PASS")
    print("No BUY/SELL reversal            = PASS")
    print("No trading performed             = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
