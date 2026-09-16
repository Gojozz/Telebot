from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeRecordV3:
    context_key: tuple
    action: str
    diagnosis: str
    trades: int
    avg_pnl_pct: float
    avg_mfe_pct: float
    avg_mae_pct: float
    avg_holding_bars: float
    confidence: float
    evidence_index: int


class KnowledgeStoreV3:
    FAILURE_DIAGNOSES = frozenset({
        "ADVERSE_MOVE",
        "MISSED_PROFIT",
        "PERSISTENT_LOSS",
        "LOSS_PATTERN",
    })

    PROFIT_DIAGNOSES = frozenset({
        "GOOD_ENTRY",
        "PROFIT_PATTERN",
    })

    def __init__(self, min_trades=3, min_profit_confidence=0.55):
        self.min_trades = int(min_trades)
        self.min_profit_confidence = float(min_profit_confidence)
        self._records = []
        self._next_index = 0

    def add_insights(self, insights):
        accepted = 0

        for insight in insights:
            if insight.trades < self.min_trades:
                continue

            if insight.diagnosis in self.PROFIT_DIAGNOSES:
                if insight.confidence < self.min_profit_confidence:
                    continue

            elif insight.diagnosis == "NEUTRAL":
                pass

            elif insight.diagnosis not in self.FAILURE_DIAGNOSES:
                continue

            record = KnowledgeRecordV3(
                context_key=insight.context_key,
                action=insight.action,
                diagnosis=insight.diagnosis,
                trades=insight.trades,
                avg_pnl_pct=insight.avg_pnl_pct,
                avg_mfe_pct=insight.avg_mfe_pct,
                avg_mae_pct=insight.avg_mae_pct,
                avg_holding_bars=insight.avg_holding_bars,
                confidence=insight.confidence,
                evidence_index=self._next_index,
            )

            self._records.append(record)
            self._next_index += 1
            accepted += 1

        return accepted

    def all(self):
        return tuple(self._records)

    def count(self):
        return len(self._records)

    def by_action(self, action):
        return tuple(x for x in self._records if x.action == action)

    def by_diagnosis(self, diagnosis):
        return tuple(x for x in self._records if x.diagnosis == diagnosis)

    def latest(self, n=1):
        if n < 0:
            raise ValueError("n must be non-negative")
        return tuple(self._records[-n:] if n else ())

    def failure_evidence(self):
        return tuple(
            x for x in self._records
            if x.diagnosis in self.FAILURE_DIAGNOSES
        )

    def profit_evidence(self):
        return tuple(
            x for x in self._records
            if x.diagnosis in self.PROFIT_DIAGNOSES
        )
