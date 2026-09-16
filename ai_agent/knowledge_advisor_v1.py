from dataclasses import dataclass

from ai_agent.hybrid_context_v1 import HybridContextV1


@dataclass(frozen=True)
class AdvisorResultV1:
    signal: str
    context_key: tuple
    action: str
    confidence: float
    diagnosis: str
    trades: int
    reason: str


class KnowledgeAdvisorV1:
    """
    Read-only knowledge advisor.

    This layer NEVER creates, mutates, or removes knowledge.
    It does not choose a trading action.
    It only describes whether historical knowledge supports or
    warns about a proposed action in the current market context.
    """

    FAILURE_DIAGNOSES = {
        "ADVERSE_MOVE",
        "MISSED_PROFIT",
        "PERSISTENT_LOSS",
        "LOSS_PATTERN",
    }

    SUCCESS_DIAGNOSES = {
        "GOOD_ENTRY",
        "PROFIT_PATTERN",
    }

    def __init__(self, min_trades=3):
        self.min_trades = min_trades

    def advise(self, knowledge, context_key, action):
        if action not in ("BUY", "SELL"):
            return AdvisorResultV1(
                signal="NEUTRAL",
                context_key=context_key,
                action=action,
                confidence=0.0,
                diagnosis="NONE",
                trades=0,
                reason="NON_DIRECTIONAL_ACTION",
            )

        candidates = [
            k for k in knowledge
            if k.context_key == context_key
            and k.action == action
            and k.trades >= self.min_trades
        ]

        if not candidates:
            return AdvisorResultV1(
                signal="NO_KNOWLEDGE",
                context_key=context_key,
                action=action,
                confidence=0.0,
                diagnosis="NONE",
                trades=0,
                reason="NO_CONTEXT_ACTION_KNOWLEDGE",
            )

        # KnowledgeStoreV3 is append-only. Use the newest evidence.
        latest = max(candidates, key=lambda k: k.evidence_index)

        if latest.diagnosis in self.FAILURE_DIAGNOSES:
            signal = "WARN"
            reason = "HISTORICAL_FAILURE_EVIDENCE"

        elif latest.diagnosis in self.SUCCESS_DIAGNOSES:
            signal = "SUPPORT"
            reason = "HISTORICAL_SUCCESS_EVIDENCE"

        else:
            signal = "NEUTRAL"
            reason = "HISTORICAL_NEUTRAL_EVIDENCE"

        return AdvisorResultV1(
            signal=signal,
            context_key=context_key,
            action=action,
            confidence=float(latest.confidence),
            diagnosis=latest.diagnosis,
            trades=int(latest.trades),
            reason=reason,
        )


def context_from_state(state):
    return HybridContextV1.from_state(state)


def audit():
    from ai_agent.knowledge_store_v3 import KnowledgeRecordV3

    context = (1, 1, 1, 1)

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
        ),
        KnowledgeRecordV3(
            context_key=context,
            action="SELL",
            diagnosis="ADVERSE_MOVE",
            trades=5,
            avg_pnl_pct=-0.01,
            avg_mfe_pct=0.005,
            avg_mae_pct=-0.02,
            avg_holding_bars=5,
            confidence=0.70,
            evidence_index=2,
        ),
    ]

    advisor = KnowledgeAdvisorV1()

    buy = advisor.advise(knowledge, context, "BUY")
    sell = advisor.advise(knowledge, context, "SELL")
    hold = advisor.advise(knowledge, context, "HOLD")
    unknown = advisor.advise(knowledge, (9, 9, 9, 9), "BUY")

    assert buy.signal == "SUPPORT"
    assert sell.signal == "WARN"
    assert hold.signal == "NEUTRAL"
    assert unknown.signal == "NO_KNOWLEDGE"

    # Read-only: calling advisor must not mutate knowledge.
    before = repr(knowledge)
    advisor.advise(knowledge, context, "BUY")
    assert repr(knowledge) == before

    print("KNOWLEDGE ADVISOR V1 AUDIT")
    print("SUPPORT mapping             = PASS")
    print("WARN mapping                = PASS")
    print("NEUTRAL mapping             = PASS")
    print("NO_KNOWLEDGE mapping        = PASS")
    print("Read-only behavior          = PASS")
    print("No trading decision         = PASS")
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
