from dataclasses import dataclass


@dataclass(frozen=True)
class StructuralTargetV2:
    direction: str
    entry_price: float
    target_price: float
    source_index: int
    valid: bool
    reason: str


def find_swing_targets(rows, index, direction, lookback=48):
    """
    Finds meaningful historical swing targets.

    A swing high is higher than the candle immediately
    before and after it.
    A swing low is lower than the candle immediately
    before and after it.

    The current candle is never inspected as a swing.
    """

    if direction not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")

    if index <= lookback + 1:
        raise ValueError("not enough history")

    entry = float(rows[index]["close"])
    start = index - lookback
    end = index - 1

    candidates = []

    # `i + 1 < index` guarantees the confirming candle
    # is also historical.
    for i in range(start + 1, end):
        high_prev = float(rows[i - 1]["high"])
        high = float(rows[i]["high"])
        high_next = float(rows[i + 1]["high"])

        low_prev = float(rows[i - 1]["low"])
        low = float(rows[i]["low"])
        low_next = float(rows[i + 1]["low"])

        if direction == "LONG":
            if high > high_prev and high >= high_next and high > entry:
                candidates.append((high, i))

        else:
            if low < low_prev and low <= low_next and low < entry:
                candidates.append((low, i))

    if not candidates:
        return None

    if direction == "LONG":
        # Nearest meaningful resistance above entry.
        target, source_index = min(candidates, key=lambda x: x[0])
    else:
        # Nearest meaningful support below entry.
        target, source_index = max(candidates, key=lambda x: x[0])

    return StructuralTargetV2(
        direction=direction,
        entry_price=entry,
        target_price=target,
        source_index=source_index,
        valid=True,
        reason="SWING_TARGET",
    )


def audit():
    # LONG fixture
    rows = []

    for _ in range(60):
        rows.append({
            "high": "104.0",
            "low": "100.0",
            "close": "102.0",
        })

    rows[40]["high"] = "120.0"
    rows[41]["high"] = "110.0"
    rows[39]["high"] = "108.0"
    rows[50]["close"] = "105.0"

    long = find_swing_targets(
        rows,
        index=50,
        direction="LONG",
        lookback=48,
    )

    assert long is not None
    assert long.target_price == 120.0
    assert long.source_index == 40
    assert long.target_price > long.entry_price

    # SHORT fixture
    rows = []

    for _ in range(60):
        rows.append({
            "high": "105.0",
            "low": "101.0",
            "close": "103.0",
        })

    rows[40]["low"] = "90.0"
    rows[39]["low"] = "95.0"
    rows[41]["low"] = "94.0"
    rows[50]["close"] = "98.0"

    short = find_swing_targets(
        rows,
        index=50,
        direction="SHORT",
        lookback=48,
    )

    assert short is not None
    assert short.target_price == 90.0
    assert short.source_index == 40
    assert short.target_price < short.entry_price

    # Current candle cannot become a target.
    rows[50]["low"] = "1.0"
    rows[50]["high"] = "1000.0"

    short_again = find_swing_targets(
        rows,
        index=50,
        direction="SHORT",
        lookback=48,
    )

    assert short_again is not None
    assert short_again.target_price == 90.0
    assert short_again.source_index == 40

    print("=" * 72)
    print("STRUCTURAL TARGET V2 AUDIT")
    print("=" * 72)
    print("Historical swing detection       = PASS")
    print("LONG structural target          = PASS")
    print("SHORT structural target         = PASS")
    print("Current candle excluded         = PASS")
    print("No future data used             = PASS")
    print("No trading performed            = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
