from dataclasses import dataclass, asdict


@dataclass
class ExitObservation:
    trade_id: int
    index: int
    position: int
    bar_age: int
    current_return: float
    r1: float
    r6: float
    r24: float
    volatility: float
    volume_ratio: float
    close_position: float


class ExitObservationLoggerV1:
    """
    Records only information available at decision time.
    Does not decide EXIT and does not modify TradeJournalV1.
    """

    def __init__(self):
        self.observations = []

    def record(
        self,
        trade_id,
        index,
        position,
        bar_age,
        current_return,
        r1,
        r6,
        r24,
        volatility,
        volume_ratio,
        close_position,
    ):
        obs = ExitObservation(
            trade_id=trade_id,
            index=index,
            position=position,
            bar_age=bar_age,
            current_return=current_return,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
            close_position=close_position,
        )
        self.observations.append(obs)
        return obs

    def all(self):
        return list(self.observations)

    def count(self):
        return len(self.observations)

    def by_trade(self, trade_id):
        return [x for x in self.observations if x.trade_id == trade_id]

    def to_dicts(self):
        return [asdict(x) for x in self.observations]
