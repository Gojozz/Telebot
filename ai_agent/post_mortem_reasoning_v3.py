from dataclasses import dataclass


from ai_agent.hybrid_context_v1 import HybridContextV1
@dataclass(frozen=True)
class PostMortemInsightV3:
    context_key: tuple
    action: str
    outcome: str
    diagnosis: str
    trades: int
    avg_pnl_pct: float
    avg_mfe_pct: float
    avg_mae_pct: float
    avg_holding_bars: float
    confidence: float


class PostMortemReasoningV3:
    """
    Stateful incremental post-mortem learner.

    New completed experiences are accumulated into per-context/action
    statistics. Historical evidence remains available for later decisions,
    while each process() call only incorporates newly completed trades.

    This layer does not decide BUY/SELL/HOLD and does not mutate memory.
    """

    FAILURE_DIAGNOSES = frozenset({
        "ADVERSE_MOVE",
        "MISSED_PROFIT",
        "PERSISTENT_LOSS",
        "LOSS_PATTERN",
    })

    SUCCESS_DIAGNOSES = frozenset({
        "GOOD_ENTRY",
        "PROFIT_PATTERN",
    })

    def __init__(self, min_trades=3, prior_weight=5.0):
        if min_trades < 1:
            raise ValueError("min_trades must be >= 1")
        if prior_weight <= 0:
            raise ValueError("prior_weight must be > 0")

        self.min_trades = int(min_trades)
        self.prior_weight = float(prior_weight)
        self._groups = {}
        self._processed_count = 0

    @property
    def processed_count(self):
        return self._processed_count

    @staticmethod
    def context_key(experience):
        if hasattr(experience, "context_key"):
            return tuple(experience.context_key)

        return HybridContextV1.from_experience(experience)

    @staticmethod
    def _diagnose(stats):
        losses = stats["losses"]
        wins = stats["wins"]
        avg_pnl = stats["pnl_sum"] / stats["trades"]
        avg_mfe = stats["mfe_sum"] / stats["trades"]
        avg_mae = stats["mae_sum"] / stats["trades"]
        avg_hold = stats["holding_sum"] / stats["trades"]

        if (
            losses > wins
            and abs(avg_mae) > avg_mfe
            and avg_mae < -0.005
        ):
            return "ADVERSE_MOVE"

        if losses > 0 and avg_mfe > 0.01 and avg_pnl < 0:
            return "MISSED_PROFIT"

        if avg_pnl > 0 and avg_mfe > abs(avg_mae):
            return "GOOD_ENTRY"

        if avg_pnl < 0 and avg_hold >= 12:
            return "PERSISTENT_LOSS"

        if avg_pnl < 0:
            return "LOSS_PATTERN"

        if avg_pnl > 0:
            return "PROFIT_PATTERN"

        return "NEUTRAL"

    def _add(self, experience):
        key = (self.context_key(experience), experience.action)

        stats = self._groups.setdefault(
            key,
            {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl_sum": 0.0,
                "mfe_sum": 0.0,
                "mae_sum": 0.0,
                "holding_sum": 0.0,
            },
        )

        stats["trades"] += 1

        if experience.outcome == "WIN":
            stats["wins"] += 1
        elif experience.outcome == "LOSS":
            stats["losses"] += 1

        stats["pnl_sum"] += experience.pnl_pct
        stats["mfe_sum"] += experience.max_favorable_excursion
        stats["mae_sum"] += experience.max_adverse_excursion
        stats["holding_sum"] += experience.holding_bars

        return key, stats

    def _insight(self, key, stats):
        trades = stats["trades"]

        if trades < self.min_trades:
            return None

        context_key, action = key

        confidence = (
            stats["wins"] + 0.5 * self.prior_weight
        ) / (
            trades + self.prior_weight
        )

        avg_pnl = stats["pnl_sum"] / trades
        avg_mfe = stats["mfe_sum"] / trades
        avg_mae = stats["mae_sum"] / trades
        avg_holding = stats["holding_sum"] / trades
        diagnosis = self._diagnose(stats)

        return PostMortemInsightV3(
            context_key=context_key,
            action=action,
            outcome=diagnosis,
            diagnosis=diagnosis,
            trades=trades,
            avg_pnl_pct=avg_pnl,
            avg_mfe_pct=avg_mfe,
            avg_mae_pct=avg_mae,
            avg_holding_bars=avg_holding,
            confidence=confidence,
        )

    def process(self, experiences):
        """
        Incorporate only experiences after processed_count.

        Returns one current insight for each context/action group touched
        by the newly completed experiences.
        """
        total = len(experiences)

        if total < self._processed_count:
            raise ValueError("experience history cannot shrink")

        if total == self._processed_count:
            return tuple()

        new_experiences = experiences[self._processed_count:]
        touched = []

        for experience in new_experiences:
            key, _ = self._add(experience)
            if key not in touched:
                touched.append(key)

        self._processed_count = total

        insights = []
        for key in touched:
            insight = self._insight(key, self._groups[key])
            if insight is not None:
                insights.append(insight)

        return tuple(insights)

    def all_insights(self):
        result = []

        for key, stats in self._groups.items():
            insight = self._insight(key, stats)
            if insight is not None:
                result.append(insight)

        return tuple(result)
