from dataclasses import replace

from ai_agent.hybrid_context_v1 import HybridContextV1
from ai_agent.knowledge_advisor_v1 import KnowledgeAdvisorV1
from ai_agent.trader_brain_v1 import TraderDecisionV1


class TraderBrainAdvisorV1:
    """
    Read-only integration layer.

    Knowledge Advisor may add evidence to an existing decision,
    but it may never change direction, risk, reward, or invalidation.
    """

    def __init__(self, advisor=None):
        self.advisor = advisor or KnowledgeAdvisorV1()

    def enrich(self, decision: TraderDecisionV1, knowledge, state):
        if decision.action == "HOLD":
            return decision

        context_key = HybridContextV1.from_features(
            state.r1,
            state.r6,
            state.r24,
            state.volatility,
        )

        advice = self.advisor.advise(
            knowledge,
            context_key,
            decision.action,
        )

        evidence_for = tuple(decision.evidence_for)
        evidence_against = tuple(decision.evidence_against)

        if advice.signal == "SUPPORT":
            evidence_for += (
                f"historical knowledge supports {decision.action} "
                f"(trades={advice.trades}, "
                f"confidence={advice.confidence:.3f})",
            )

        elif advice.signal == "WARN":
            evidence_against += (
                f"historical knowledge warns against {decision.action} "
                f"(trades={advice.trades}, "
                f"confidence={advice.confidence:.3f})",
            )

        elif advice.signal == "NEUTRAL":
            evidence_against += (
                "historical knowledge is neutral",
            )

        # NO_KNOWLEDGE deliberately adds nothing.
        return replace(
            decision,
            evidence_for=evidence_for,
            evidence_against=evidence_against,
        )


def audit():
    class State:
        r1 = 0.005
        r6 = 0.012
        r24 = 0.025
        volatility = 0.008

    state = State()

    context = HybridContextV1.from_features(
        state.r1,
        state.r6,
        state.r24,
        state.volatility,
    )

    class Knowledge:
        pass

    from ai_agent.knowledge_store_v3 import KnowledgeRecordV3

    knowledge = [
        KnowledgeRecordV3(
            context_key=context,
            action="BUY",
            diagnosis="GOOD_ENTRY",
            trades=5,
            avg_pnl_pct=0.01,
            avg_mfe_pct=0.02,
            avg_mae_pct=-0.005,
            avg_holding_bars=5,
            confidence=0.75,
            evidence_index=1,
        )
    ]

    decision = TraderDecisionV1(
        regime="BULLISH",
        thesis="bullish continuation",
        evidence_for=("positive momentum",),
        evidence_against=("high volatility",),
        invalidation="recent structural low",
        risk_pct=0.01,
        reward_pct=0.03,
        confidence=0.70,
        action="BUY",
        reason="valid trade thesis",
    )

    original = decision.to_dict()

    integrated = TraderBrainAdvisorV1().enrich(
        decision,
        knowledge,
        state,
    )

    assert integrated.action == decision.action
    assert integrated.risk_pct == decision.risk_pct
    assert integrated.reward_pct == decision.reward_pct
    assert integrated.invalidation == decision.invalidation
    assert integrated.regime == decision.regime
    assert integrated.thesis == decision.thesis
    assert len(integrated.evidence_for) > len(decision.evidence_for)

    # Original object remains unchanged.
    assert decision.to_dict() == original

    # WARN test.
    warning_knowledge = [
        KnowledgeRecordV3(
            context_key=context,
            action="BUY",
            diagnosis="ADVERSE_MOVE",
            trades=5,
            avg_pnl_pct=-0.01,
            avg_mfe_pct=0.005,
            avg_mae_pct=-0.02,
            avg_holding_bars=5,
            confidence=0.70,
            evidence_index=2,
        )
    ]

    warned = TraderBrainAdvisorV1().enrich(
        decision,
        warning_knowledge,
        state,
    )

    assert warned.action == "BUY"
    assert any("warns against" in x for x in warned.evidence_against)

    print("TRADER BRAIN + ADVISOR V1 AUDIT")
    print("SUPPORT adds evidence_for    = PASS")
    print("WARN adds evidence_against   = PASS")
    print("Direction unchanged          = PASS")
    print("Risk unchanged               = PASS")
    print("Reward unchanged             = PASS")
    print("Invalidation unchanged       = PASS")
    print("Original decision immutable  = PASS")
    print("No direct trading decision   = PASS")
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
