from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    side: str
    entry: float
    quantity: float
    stop_loss: float
    take_profit: float


class PaperPortfolio:
    def __init__(self, initial_balance):
        self.cash = float(initial_balance)
        self.positions = []
        self.realized_pnl = 0.0

    def open_long(self, symbol, entry, quantity, stop_loss, take_profit):
        cost = entry * quantity

        if cost > self.cash:
            return False, "insufficient virtual balance"

        self.cash -= cost

        self.positions.append(
            Position(
                symbol=symbol,
                side="LONG",
                entry=entry,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
        )

        return True, "paper position opened"

    def close_position(self, index, exit_price):
        position = self.positions[index]

        pnl = (exit_price - position.entry) * position.quantity

        self.cash += position.quantity * exit_price
        self.realized_pnl += pnl
        self.positions.pop(index)

        return pnl
