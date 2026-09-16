from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MarketStateV1:
    index: int
    close: float

    r1: float
    r6: float
    r24: float

    volatility: float
    volume_ratio: float

    trend: str
    momentum: str
    volatility_state: str
    structure: str

    def __post_init__(self):
        if self.index < 0:
            raise ValueError("index must be >= 0")

        if self.close <= 0:
            raise ValueError("close must be > 0")

        if self.volatility < 0:
            raise ValueError("volatility must be >= 0")

        if self.volume_ratio < 0:
            raise ValueError("volume_ratio must be >= 0")

        valid_trend = {"BULLISH", "BEARISH", "NEUTRAL"}
        valid_momentum = {"POSITIVE", "NEGATIVE", "MIXED"}
        valid_volatility = {"LOW", "NORMAL", "HIGH"}
        valid_structure = {"UP", "DOWN", "RANGE", "UNCLEAR"}

        if self.trend not in valid_trend:
            raise ValueError("invalid trend")

        if self.momentum not in valid_momentum:
            raise ValueError("invalid momentum")

        if self.volatility_state not in valid_volatility:
            raise ValueError("invalid volatility_state")

        if self.structure not in valid_structure:
            raise ValueError("invalid structure")

    def to_dict(self):
        return asdict(self)


def classify_market_state(
    index,
    close,
    r1,
    r6,
    r24,
    volatility,
    volume_ratio,
):
    """
    Describes the market.

    IMPORTANT:
    This function does NOT produce BUY/SELL.
    """

    # Trend uses multiple horizons rather than one candle.
    if r6 > 0 and r24 > 0:
        trend = "BULLISH"
    elif r6 < 0 and r24 < 0:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    # Momentum compares short-term movement with direction.
    if r1 > 0 and r6 > 0:
        momentum = "POSITIVE"
    elif r1 < 0 and r6 < 0:
        momentum = "NEGATIVE"
    else:
        momentum = "MIXED"

    # Descriptive volatility classification.
    if volatility < 0.004:
        volatility_state = "LOW"
    elif volatility > 0.012:
        volatility_state = "HIGH"
    else:
        volatility_state = "NORMAL"

    # Structure is deliberately coarse.
    if r24 > 0.03 and r6 > 0:
        structure = "UP"
    elif r24 < -0.03 and r6 < 0:
        structure = "DOWN"
    elif abs(r24) < 0.03:
        structure = "RANGE"
    else:
        structure = "UNCLEAR"

    return MarketStateV1(
        index=index,
        close=close,
        r1=r1,
        r6=r6,
        r24=r24,
        volatility=volatility,
        volume_ratio=volume_ratio,
        trend=trend,
        momentum=momentum,
        volatility_state=volatility_state,
        structure=structure,
    )


def audit():
    bullish = classify_market_state(
        index=100,
        close=100000.0,
        r1=0.004,
        r6=0.018,
        r24=0.055,
        volatility=0.008,
        volume_ratio=1.2,
    )

    assert bullish.trend == "BULLISH"
    assert bullish.momentum == "POSITIVE"
    assert bullish.structure == "UP"

    bearish = classify_market_state(
        index=200,
        close=90000.0,
        r1=-0.004,
        r6=-0.018,
        r24=-0.055,
        volatility=0.014,
        volume_ratio=1.3,
    )

    assert bearish.trend == "BEARISH"
    assert bearish.momentum == "NEGATIVE"
    assert bearish.volatility_state == "HIGH"
    assert bearish.structure == "DOWN"

    unclear = classify_market_state(
        index=300,
        close=95000.0,
        r1=0.002,
        r6=-0.004,
        r24=0.005,
        volatility=0.003,
        volume_ratio=0.8,
    )

    assert unclear.trend == "NEUTRAL"
    assert unclear.momentum == "MIXED"
    assert unclear.volatility_state == "LOW"
    assert unclear.structure == "RANGE"

    # Critical architectural check:
    # MarketState must describe the market, not trade it.
    assert not hasattr(bullish, "action")

    print("=" * 72)
    print("MARKET STATE V1 AUDIT")
    print("=" * 72)
    print("Bullish classification       = PASS")
    print("Bearish classification       = PASS")
    print("Neutral/range classification = PASS")
    print("Volatility classification    = PASS")
    print("No BUY/SELL decision         = PASS")
    print("No trading performed         = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
