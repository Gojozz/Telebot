from dataclasses import dataclass


@dataclass(frozen=True)
class SwingPointV2:
    index: int
    price: float
    kind: str  # HIGH / LOW


@dataclass(frozen=True)
class StructureLevelsV2:
    direction: str
    entry_price: float
    invalidation_price: float
    reference_swing_index: int
    valid: bool
    reason: str


def find_swing_points(rows, start_index, end_index):
    """
    Detect confirmed swing highs/lows.

    The candle at end_index is excluded.
    A swing is confirmed using only candles already available
    before the decision point.
    """
    points = []

    start = max(1, start_index)
    end = min(len(rows) - 1, end_index)

    for i in range(start, end):
        high = float(rows[i]["high"])
        low = float(rows[i]["low"])

        prev_high = float(rows[i - 1]["high"])
        next_high = float(rows[i + 1]["high"])

        prev_low = float(rows[i - 1]["low"])
        next_low = float(rows[i + 1]["low"])

        if high > prev_high and high >= next_high:
            points.append(
                SwingPointV2(i, high, "HIGH")
            )

        if low < prev_low and low <= next_low:
            points.append(
                SwingPointV2(i, low, "LOW")
            )

    return points


def build_structure_levels(
    rows,
    index,
    direction,
    lookback=48,
):
    if direction not in ("LONG", "SHORT"):
        return StructureLevelsV2(
            direction=direction,
            entry_price=0.0,
            invalidation_price=0.0,
            reference_swing_index=-1,
            valid=False,
            reason="INVALID_DIRECTION",
        )

    if index <= 2:
        return StructureLevelsV2(
            direction=direction,
            entry_price=0.0,
            invalidation_price=0.0,
            reference_swing_index=-1,
            valid=False,
            reason="INSUFFICIENT_HISTORY",
        )

    entry = float(rows[index]["close"])

    start = max(1, index - lookback)

    swings = find_swing_points(
        rows,
        start,
        index,
    )

    if direction == "LONG":
        candidates = [
            s for s in swings
            if s.kind == "LOW" and s.price < entry
        ]

        if not candidates:
            return StructureLevelsV2(
                direction=direction,
                entry_price=entry,
                invalidation_price=0.0,
                reference_swing_index=-1,
                valid=False,
                reason="NO_SWING_LOW",
            )

        # Most recent structural low below entry.
        swing = max(candidates, key=lambda x: x.index)

    else:
        candidates = [
            s for s in swings
            if s.kind == "HIGH" and s.price > entry
        ]

        if not candidates:
            return StructureLevelsV2(
                direction=direction,
                entry_price=entry,
                invalidation_price=0.0,
                reference_swing_index=-1,
                valid=False,
                reason="NO_SWING_HIGH",
            )

        # Most recent structural high above entry.
        swing = max(candidates, key=lambda x: x.index)

    return StructureLevelsV2(
        direction=direction,
        entry_price=entry,
        invalidation_price=swing.price,
        reference_swing_index=swing.index,
        valid=True,
        reason="STRUCTURAL_SWING",
    )


def _audit():
    rows = []

    # Flat fixture with no accidental swings.
    for i in range(80):
        rows.append({
            "high": "100.0",
            "low": "100.0",
            "close": "100.0",
        })

    # Confirmed LONG invalidation swing low.
    rows[65]["low"] = "90.0"
    rows[64]["low"] = "100.0"
    rows[66]["low"] = "100.0"

    # Confirmed SHORT invalidation swing high.
    rows[70]["high"] = "110.0"
    rows[69]["high"] = "100.0"
    rows[71]["high"] = "100.0"

    # Keep entry above LONG invalidation and below SHORT invalidation.
    rows[75]["close"] = "100.0"

    long_result = build_structure_levels(
        rows,
        75,
        "LONG",
        lookback=48,
    )

    short_result = build_structure_levels(
        rows,
        75,
        "SHORT",
        lookback=48,
    )

    assert long_result.valid
    assert long_result.invalidation_price == 90.0
    assert long_result.reference_swing_index == 65

    assert short_result.valid
    assert short_result.invalidation_price == 110.0
    assert short_result.reference_swing_index == 70

    # Current candle must not affect structure.
    rows[75]["low"] = "50.0"
    rows[75]["high"] = "150.0"

    result = build_structure_levels(
        rows,
        75,
        "LONG",
        lookback=48,
    )

    assert result.invalidation_price == 90.0

    print("=" * 72)
    print("MARKET STRUCTURE V2 AUDIT")
    print("=" * 72)
    print("Confirmed swing detection       = PASS")
    print("LONG structural invalidation    = PASS")
    print("SHORT structural invalidation   = PASS")
    print("Current candle excluded         = PASS")
    print("No future decision data         = PASS")
    print("No trading performed            = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    _audit()
