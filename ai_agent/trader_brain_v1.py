from dataclasses import dataclass, asdict
from typing import Literal, Optional


Action = Literal["BUY", "SELL", "HOLD"]
Regime = Literal["BULLISH", "BEARISH", "RANGE", "UNCLEAR"]


@dataclass(frozen=True)
class TraderDecisionV1:
    """
    Structured decision contract for a human-like trading process.

    This class does NOT generate signals and does NOT trade.
    It only defines what a valid trader decision must contain.
    """

    regime: Regime
    thesis: str
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    invalidation: str
    risk_pct: float
    reward_pct: float
    confidence: float
    action: Action
    reason: str

    def __post_init__(self):
        if self.action not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("invalid action")

        if self.regime not in {
            "BULLISH",
            "BEARISH",
            "RANGE",
            "UNCLEAR",
        }:
            raise ValueError("invalid regime")

        if not self.thesis.strip():
            raise ValueError("thesis must not be empty")

        if not self.invalidation.strip():
            raise ValueError("invalidation must not be empty")

        if not self.reason.strip():
            raise ValueError("reason must not be empty")

        if self.risk_pct < 0:
            raise ValueError("risk_pct must be >= 0")

        if self.reward_pct < 0:
            raise ValueError("reward_pct must be >= 0")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        # A HOLD decision must not pretend that capital is being risked.
        if self.action == "HOLD" and self.risk_pct != 0:
            raise ValueError("HOLD must have zero risk")

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        if self.risk_pct == 0:
            return None
        return self.reward_pct / self.risk_pct

    def to_dict(self):
        return asdict(self)


def validate_decision(decision: TraderDecisionV1) -> bool:
    """
    Lightweight semantic guard.

    This intentionally does not judge whether the decision is profitable.
    It only checks whether the decision follows the required reasoning
    structure.
    """
    if decision.action == "HOLD":
        return True

    if not decision.evidence_for:
        return False

    if decision.confidence <= 0:
        return False

    if decision.risk_pct <= 0:
        return False

    if decision.reward_pct <= 0:
        return False

    if not decision.invalidation.strip():
        return False

    return True


def audit():
    # Valid BUY
    buy = TraderDecisionV1(
        regime="BULLISH",
        thesis="Price may continue higher after a confirmed pullback.",
        evidence_for=("higher-timeframe trend", "bullish structure"),
        evidence_against=("short-term volatility"),
        invalidation="Bullish structure breaks below the invalidation level.",
        risk_pct=0.40,
        reward_pct=1.20,
        confidence=0.68,
        action="BUY",
        reason="Evidence currently favors continuation.",
    )

    assert validate_decision(buy)
    assert abs(buy.risk_reward_ratio - 3.0) < 1e-9

    # Valid HOLD: uncertainty is itself a decision.
    hold = TraderDecisionV1(
        regime="UNCLEAR",
        thesis="Market direction is ambiguous.",
        evidence_for=(),
        evidence_against=("conflicting structure",),
        invalidation="A clear directional structure appears.",
        risk_pct=0.0,
        reward_pct=0.0,
        confidence=0.50,
        action="HOLD",
        reason="There is not enough evidence to justify risk.",
    )

    assert validate_decision(hold)
    assert hold.risk_reward_ratio is None

    # Invalid directional decision without evidence.
    bad = TraderDecisionV1(
        regime="BULLISH",
        thesis="Price might rise.",
        evidence_for=(),
        evidence_against=(),
        invalidation="Trend breaks.",
        risk_pct=0.40,
        reward_pct=1.20,
        confidence=0.60,
        action="BUY",
        reason="Test invalid decision.",
    )

    assert not validate_decision(bad)

    print("=" * 72)
    print("TRADER BRAIN V1 CONTRACT AUDIT")
    print("=" * 72)
    print("BUY structured decision      = PASS")
    print("HOLD uncertainty decision    = PASS")
    print("Risk/reward calculation      = PASS")
    print("Missing-evidence rejection   = PASS")
    print("No trading performed         = PASS")
    print("No market data accessed      = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
