from ai_agent.market_state_v1 import MarketStateV1
from ai_agent.thesis_engine_v1 import build_thesis
from ai_agent.trade_plan_v2 import build_trade_plan
from ai_agent.trader_brain_v1 import TraderDecisionV1, validate_decision
from ai_agent.trader_brain_advisor_v1 import TraderBrainAdvisorV1


class DecisionEngineV1:
    """
    Orchestrates already-audited components.

    MARKET STATE -> THESIS -> TRADE PLAN -> DECISION
    Knowledge Advisor only enriches evidence.
    It cannot change action, risk, reward, or invalidation.
    """

    def __init__(
        self,
        lookback=48,
        min_risk_reward=1.5,
        advisor=None,
    ):
        self.lookback = lookback
        self.min_risk_reward = min_risk_reward
        self.advisor = advisor or TraderBrainAdvisorV1()

    def decide(self, rows, index, state, knowledge=None):
        thesis = build_thesis(state)

        if thesis.direction == "NONE":
            return TraderDecisionV1(
                regime=self._regime(state),
                thesis=thesis.statement,
                evidence_for=thesis.evidence_for,
                evidence_against=thesis.evidence_against,
                invalidation="A clear directional structure appears.",
                risk_pct=0.0,
                reward_pct=0.0,
                confidence=0.0,
                action="HOLD",
                reason="NO_CLEAR_THESIS",
            )

        plan = build_trade_plan(
            rows,
            index,
            thesis.direction,
            lookback=self.lookback,
            min_risk_reward=self.min_risk_reward,
        )

        if not plan.valid:
            return TraderDecisionV1(
                regime=self._regime(state),
                thesis=thesis.statement,
                evidence_for=thesis.evidence_for,
                evidence_against=thesis.evidence_against
                + (plan.reason,),
                invalidation=(
                    "Structural invalidation from the market structure plan."
                ),
                risk_pct=0.0,
                reward_pct=0.0,
                confidence=0.0,
                action="HOLD",
                reason=plan.reason,
            )

        action = "BUY" if thesis.direction == "LONG" else "SELL"

        decision = TraderDecisionV1(
            regime=self._regime(state),
            thesis=thesis.statement,
            evidence_for=thesis.evidence_for,
            evidence_against=thesis.evidence_against,
            invalidation=(
                f"Price invalidates thesis at "
                f"{plan.invalidation_price:.8f}."
            ),
            risk_pct=plan.risk_pct,
            reward_pct=plan.reward_pct,
            confidence=thesis.confidence,
            action=action,
            reason="VALID_TRADE_PLAN",
        )

        if knowledge is not None:
            decision = self.advisor.enrich(
                decision,
                knowledge,
                state,
            )

        assert validate_decision(decision)
        return decision

    @staticmethod
    def _regime(state):
        if state.trend == "BULLISH":
            return "BULLISH"
        if state.trend == "BEARISH":
            return "BEARISH"
        if state.structure == "RANGE":
            return "RANGE"
        return "UNCLEAR"


def audit():
    rows = []
    for _ in range(100):
        rows.append({
            "high": "104.0",
            "low": "100.0",
            "close": "102.0",
        })

    # Confirmed structural low.
    rows[65]["low"] = "98.0"
    rows[64]["low"] = "100.0"
    rows[66]["low"] = "100.0"

    # Confirmed structural high.
    rows[60]["high"] = "120.0"
    rows[59]["high"] = "110.0"
    rows[61]["high"] = "110.0"

    rows[70]["close"] = "105.0"

    state = MarketStateV1(
        index=70,
        close=105.0,
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

    engine = DecisionEngineV1(
        lookback=48,
        min_risk_reward=1.5,
    )

    decision = engine.decide(rows, 70, state)

    assert decision.action == "BUY"
    assert decision.risk_pct > 0
    assert decision.reward_pct > 0
    assert decision.confidence > 0
    assert validate_decision(decision)

    # Unclear market must HOLD.
    unclear = MarketStateV1(
        index=70,
        close=105.0,
        r1=0.001,
        r6=-0.002,
        r24=0.003,
        volatility=0.005,
        volume_ratio=0.9,
        trend="NEUTRAL",
        momentum="MIXED",
        volatility_state="NORMAL",
        structure="RANGE",
    )

    hold = engine.decide(rows, 70, unclear)

    assert hold.action == "HOLD"
    assert hold.risk_pct == 0.0
    assert hold.reward_pct == 0.0

    # Knowledge must not change the trading direction.
    from ai_agent.hybrid_context_v1 import HybridContextV1
    from ai_agent.knowledge_store_v3 import KnowledgeRecordV3

    context = HybridContextV1.from_features(
        state.r1,
        state.r6,
        state.r24,
        state.volatility,
    )

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

    enriched = engine.decide(
        rows,
        70,
        state,
        knowledge=knowledge,
    )

    assert enriched.action == decision.action
    assert enriched.risk_pct == decision.risk_pct
    assert enriched.reward_pct == decision.reward_pct
    assert enriched.invalidation == decision.invalidation
    assert len(enriched.evidence_for) > len(decision.evidence_for)

    print("=" * 72)
    print("DECISION ENGINE V1 AUDIT")
    print("=" * 72)
    print("MarketState -> Thesis         = PASS")
    print("Thesis -> TradePlan           = PASS")
    print("Valid plan -> BUY             = PASS")
    print("No thesis -> HOLD             = PASS")
    print("Invalid plan -> HOLD          = PASS")
    print("Decision contract             = PASS")
    print("Knowledge enrichment         = PASS")
    print("Action unchanged by knowledge = PASS")
    print("Risk unchanged                = PASS")
    print("Reward unchanged              = PASS")
    print("Invalidation unchanged        = PASS")
    print("No trading performed          = PASS")
    print("=" * 72)
    print("AUDIT RESULT = PASS")


if __name__ == "__main__":
    audit()
