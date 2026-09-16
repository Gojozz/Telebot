from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ai_agent.trade_experience_memory_v1 import (
    TradeExperience,
    TradeExperienceMemoryV1,
    make_experience,
)


@dataclass
class OpenTrade:
    trade_id: int
    action: str
    position: int
    entry_price: float
    entry_index: int
    r1: float
    r6: float
    r24: float
    volatility: float
    volume_ratio: float
    close_position: float
    mfe: float = 0.0
    mae: float = 0.0


class TradeJournalV1:
    """
    Converts completed simulator positions into TradeExperience records.

    Responsibilities:
    - capture entry context
    - track MFE / MAE
    - detect position closure/switch
    - calculate execution prices using environment fee/slippage convention
    - write completed experiences into memory

    This class does NOT choose actions.
    """

    def __init__(
        self,
        memory: TradeExperienceMemoryV1,
        fee_rate: float = 0.0004,
        slippage_rate: float = 0.0002,
    ):
        self.memory = memory
        self.fee_rate = float(fee_rate)
        self.slippage_rate = float(slippage_rate)

        self.next_trade_id = 1
        self.open_trade: Optional[OpenTrade] = None

    def _execution_price(self, price: float, side: int) -> float:
        return price * (1.0 + self.slippage_rate * side)

    def _update_excursion(
        self,
        high: float,
        low: float,
    ) -> None:
        if self.open_trade is None:
            return

        entry = self.open_trade.entry_price

        if self.open_trade.position == 1:
            favorable = high / entry - 1.0
            adverse = low / entry - 1.0
        else:
            favorable = entry / low - 1.0
            adverse = entry / high - 1.0

        self.open_trade.mfe = max(self.open_trade.mfe, favorable)
        self.open_trade.mae = min(self.open_trade.mae, adverse)

    def observe_market(
        self,
        high: float,
        low: float,
    ) -> None:
        self._update_excursion(high, low)

    def open(
        self,
        action: str,
        position: int,
        market_price: float,
        index: int,
        r1: float,
        r6: float,
        r24: float,
        volatility: float,
        volume_ratio: float,
        close_position: float,
        high: float,
        low: float,
    ) -> None:
        if self.open_trade is not None:
            raise RuntimeError("A trade is already open")

        if position not in (1, -1):
            raise ValueError("position must be 1 or -1")

        entry_price = self._execution_price(market_price, position)

        self.open_trade = OpenTrade(
            trade_id=self.next_trade_id,
            action=action,
            position=position,
            entry_price=entry_price,
            entry_index=index,
            r1=r1,
            r6=r6,
            r24=r24,
            volatility=volatility,
            volume_ratio=volume_ratio,
            close_position=close_position,
        )

        self.next_trade_id += 1

        self._update_excursion(high, low)

    def close(
        self,
        market_price: float,
        index: int,
        high: float,
        low: float,
    ) -> TradeExperience:
        if self.open_trade is None:
            raise RuntimeError("No open trade")

        self._update_excursion(high, low)

        trade = self.open_trade

        exit_price = self._execution_price(
            market_price,
            -trade.position,
        )

        holding_bars = max(1, index - trade.entry_index + 1)

        experience = make_experience(
            trade.trade_id,
            trade.action,
            trade.entry_price,
            exit_price,
            "LONG" if trade.position == 1 else "SHORT",
            holding_bars,
            trade.r1,
            trade.r6,
            trade.r24,
            trade.volatility,
            trade.volume_ratio,
            trade.close_position,
            trade.mfe,
            trade.mae,
        )

        self.memory.add(experience)
        self.open_trade = None

        return experience


def audit() -> None:
    print("=" * 80)
    print("TRADE JOURNAL V1 AUDIT")
    print("=" * 80)
    print("Synthetic trade lifecycle only")
    print("No market data accessed")
    print()

    memory = TradeExperienceMemoryV1()

    journal = TradeJournalV1(
        memory,
        fee_rate=0.0004,
        slippage_rate=0.0002,
    )

    # Synthetic LONG:
    # Entry at 100 -> execution 100.02
    # High reaches 103 -> positive MFE
    # Low reaches 99 -> negative MAE
    journal.open(
        action="BUY",
        position=1,
        market_price=100.0,
        index=10,
        r1=1,
        r6=2,
        r24=3,
        volatility=0.008,
        volume_ratio=1.5,
        close_position=0.8,
        high=103.0,
        low=99.0,
    )

    journal.observe_market(
        high=104.0,
        low=98.5,
    )

    exp = journal.close(
        market_price=102.0,
        index=15,
        high=103.0,
        low=99.0,
    )

    assert memory.count() == 1
    assert exp.trade_id == 1
    assert exp.action == "BUY"
    assert exp.position == "LONG"

    assert exp.entry_price > 100.0
    assert exp.exit_price < 102.0

    assert exp.holding_bars == 6

    assert exp.max_favorable_excursion > 0.0
    assert exp.max_adverse_excursion < 0.0

    assert exp.outcome == "WIN"
    assert exp.pnl_pct > 0.0

    assert journal.open_trade is None

    # Synthetic SHORT:
    # Entry at 100 -> execution 99.98
    # Favorable movement down to 96.
    journal.open(
        action="SELL",
        position=-1,
        market_price=100.0,
        index=20,
        r1=-1,
        r6=-2,
        r24=-3,
        volatility=0.010,
        volume_ratio=1.8,
        close_position=0.2,
        high=101.0,
        low=98.0,
    )

    journal.observe_market(
        high=102.0,
        low=96.0,
    )

    exp2 = journal.close(
        market_price=97.0,
        index=23,
        high=98.0,
        low=96.5,
    )

    assert memory.count() == 2
    assert exp2.trade_id == 2
    assert exp2.action == "SELL"
    assert exp2.position == "SHORT"
    assert exp2.outcome == "WIN"
    assert exp2.pnl_pct > 0.0
    assert exp2.max_favorable_excursion > 0.0
    assert exp2.max_adverse_excursion < 0.0

    # No open trade may remain.
    assert journal.open_trade is None

    # IDs must remain chronological.
    assert [e.trade_id for e in memory.all()] == [1, 2]

    print(f"completed trades       = {memory.count()}")
    print(
        f"LONG  pnl={exp.pnl_pct:+.4%} "
        f"MFE={exp.max_favorable_excursion:+.4%} "
        f"MAE={exp.max_adverse_excursion:+.4%} "
        f"holding={exp.holding_bars}"
    )
    print(
        f"SHORT pnl={exp2.pnl_pct:+.4%} "
        f"MFE={exp2.max_favorable_excursion:+.4%} "
        f"MAE={exp2.max_adverse_excursion:+.4%} "
        f"holding={exp2.holding_bars}"
    )
    print()
    print("Entry/exit accounting = PASS")
    print("LONG lifecycle        = PASS")
    print("SHORT lifecycle       = PASS")
    print("MFE/MAE tracking      = PASS")
    print("Chronological IDs      = PASS")
    print("Memory integration     = PASS")
    print()
    print("AUDIT RESULT: PASS")


if __name__ == "__main__":
    audit()
