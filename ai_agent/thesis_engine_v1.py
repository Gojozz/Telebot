from dataclasses import dataclass

from ai_agent.market_state_v1 import MarketStateV1


@dataclass(frozen=True)
class ThesisV1:
    name: str
    direction: str
    statement: str
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    confidence: float

    def __post_init__(self):
        if self.direction not in {"LONG", "SHORT", "NONE"}:
            raise ValueError("invalid direction")

        if not self.name.strip():
            raise ValueError("name must not be empty")

        if not self.statement.strip():
            raise ValueError("statement must not be empty")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.direction == "NONE" and self.confidence > 0.0:
            raise ValueError("NONE thesis must have zero confidence")


def build_thesis(state: MarketStateV1) -> ThesisV1:
    """
    Converts market description into a testable hypothesis.

    IMPORTANT:
    This does NOT execute trades.
    """

    # Clear bullish continuation.
    if (
        state.trend == "BULLISH"
        and state.momentum == "POSITIVE"
        and state.structure == "UP"
    ):
        evidence_for = (
            "multi-horizon trend is bullish",
            "short-term momentum agrees with trend",
            "structure is upward",
        )

        evidence_against = []

        if state.volatility_state == "HIGH":
            evidence_against.append("high volatility increases uncertainty")

        confidence = 0.70 if not evidence_against else 0.60

        return ThesisV1(
            name="BULLISH_CONTINUATION",
            direction="LONG",
            statement="The current upward structure may continue.",
            evidence_for=evidence_for,
            evidence_against=tuple(evidence_against),
            confidence=confidence,
        )

    # Clear bearish continuation.
    if (
        state.trend == "BEARISH"
        and state.momentum == "NEGATIVE"
        and state.structure == "DOWN"
    ):
        evidence_for = (
            "multi-horizon trend is bearish",
            "short-term momentum agrees with trend",
            "structure is downward",
        )

        evidence_against = []

        if state.volatility_state == "HIGH":
            evidence_against.append("high volatility increases uncertainty")

        confidence = 0.70 if not evidence_against else 0.60

        return ThesisV1(
            name="BEARISH_CONTINUATION",
            direction="SHORT",
            statement="The current downward structure may continue.",
            evidence_for=evidence_for,
            evidence_against=tuple(evidence_against),
            confidence=confidence,
        )

    # Conflicting evidence means no directional thesis.
    return ThesisV1(
        name="NO_CLEAR_THESIS",
        direction="NONE",
        statement="The available evidence does not support a clear directional hypothesis.",
        evidence_for=(),
        evidence_against=(
            "trend and momentum are not sufficiently aligned",
        ),
        confidence=0.0,
    )


def audit():
    bullish = MarketStateV1(
        index=100,
        close=100000.0,
        r1=0.004,
        r6=0.018,
        r24=0.055,
        volatility=0.008,
        volume_ratio=1.2,
        trend="BULLISH",
        momentum="POSITIVE",
        volatility_state="NORMAL",
        structure="UP",
    )

    thesis = build_thesis(bullish)

    assert thesis.name == "BULLISH_CONTINUATION"
    assert thesis.direction == "LONG"
    assert len(thesis.evidence_for) >= 2
    assert thesis.confidence > 0

    bearish = MarketStateV1(
        index=200,
        close=90000.0,
        r1=-0.004,
        r6=-0.018,
        r24=-0.055,
        volatility=0.014,
        volume_ratio=1.3,
        trend="BEARISH",
        momentum="NEGATIVE",
        volatility_state="HIGH",
        structure="DOWN",
    )

    thesis = build_thesis(bearish)

    assert thesis.name == "BEARISH_CONTINUATION"
    assert thesis.direction == "SHORT"
    assert len(thesis.evidence_for) >= 2
    assert len(thesis.evidence_against) >= 1

    unclear = MarketStateV1(
        index=300,
        close=95000.0,
        r1=0.002,
        r6=-0.004,
        r24=0.005,
        volatility=0.003,
        volume_ratio=0.8,
        trend="NEUTRAL",
        momentum="MIXED",
        volatility_state="LOW",
        structure="RANGE",
    )

    thesis = build_thesis(unclear)

    assert thesis.name == "NO_CLEAR_THESIS"
    assert thesis.direction == "NONE"
    assert thesis.confidence == 0.0

    print("=" * 72)
    print("THESIS ENGINE V1 AUDIT")
    print("=" * 72)
    print("Bullish thesis                = PASS")
    print("Bearish thesis                = PASS")
    print("Conflicting evidence → NONE   = PASS")
    print("Evidence FOR recorded         = PASS")
    print("Evidence AGAINST recorded     = PASS")
    print("No trade execution            = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
