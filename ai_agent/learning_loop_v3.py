from ai_agent.post_mortem_reasoning_v3 import PostMortemReasoningV3
from ai_agent.knowledge_store_v3 import KnowledgeStoreV3


class LearningLoopV3:
    """
    Cumulative experience -> post-mortem -> knowledge pipeline.

    Unlike LearningLoopV2, the post-mortem reasoner keeps cumulative
    evidence for each (context, action) group.

    Temporal rule:
        experience N can only affect knowledge after experience N
        has completed.

    This layer does not decide BUY/SELL/HOLD.
    """

    def __init__(
        self,
        min_trades=3,
        prior_weight=5.0,
        min_confidence=0.55,
    ):
        self.reasoner = PostMortemReasoningV3(
            min_trades=min_trades,
            prior_weight=prior_weight,
        )

        self.knowledge = KnowledgeStoreV3(
            min_trades=min_trades,
            min_profit_confidence=min_confidence,
        )

        self._processed_count = 0
        self._latest_by_key = {}

    @property
    def processed_count(self):
        return self._processed_count

    def process(self, experiences):
        """
        Process only newly completed experiences.

        The reasoner accumulates evidence cumulatively.
        KnowledgeStoreV3 receives a new record only when the
        current evidence state for a (context, action) changes.

        Returns newly accepted knowledge records.
        """
        total = len(experiences)

        if total < self._processed_count:
            raise ValueError("experience history cannot shrink")

        if total == self._processed_count:
            return tuple()

        insights = self.reasoner.process(experiences)

        new_records = []

        for insight in insights:
            key = (insight.context_key, insight.action)

            previous = self._latest_by_key.get(key)

            current_signature = (
                insight.diagnosis,
                insight.trades,
                round(insight.avg_pnl_pct, 12),
                round(insight.avg_mfe_pct, 12),
                round(insight.avg_mae_pct, 12),
                round(insight.avg_holding_bars, 12),
                round(insight.confidence, 12),
            )

            if previous == current_signature:
                continue

            before = self.knowledge.count()
            accepted = self.knowledge.add_insights((insight,))

            if accepted:
                record = self.knowledge.all()[before:]
                new_records.extend(record)
                self._latest_by_key[key] = current_signature

        self._processed_count = total

        return tuple(new_records)

    def all_knowledge(self):
        return self.knowledge.all()

    def latest_knowledge(self, n=1):
        return self.knowledge.latest(n)

    def failure_evidence(self):
        return self.knowledge.failure_evidence()

    def profit_evidence(self):
        return self.knowledge.profit_evidence()
