from bot.config import CONFIG
from bot.risk import RiskEngine, RiskState
from bot.strategy import TrendStrategy
from bot.portfolio import PaperPortfolio


class TradingEngine:
    def __init__(self):
        if CONFIG.trading_mode != "paper":
            raise RuntimeError(
                "Safety lock: v0.1 only supports TRADING_MODE=paper"
            )

        self.portfolio = PaperPortfolio(CONFIG.initial_balance)
        self.risk = RiskEngine(CONFIG)
        self.strategy = TrendStrategy(CONFIG)

        self.risk_state = RiskState(
            starting_balance=CONFIG.initial_balance
        )

    def analyze(self, symbol, prices):
        return self.strategy.analyze(prices)

    def try_buy(self, symbol, prices):
        if not prices:
            return {"status": "rejected", "reason": "no prices"}

        entry = prices[-1]

        signal = self.strategy.analyze(prices)

        if signal.action != "BUY":
            return {
                "status": "rejected",
                "reason": f"signal={signal.action}: {signal.reason}",
            }

        allowed, reason = self.risk.can_open_position(self.risk_state)

        if not allowed:
            return {"status": "rejected", "reason": reason}

        stop = entry * (1 - CONFIG.stop_loss_pct)
        target = entry * (1 + CONFIG.take_profit_pct)

        quantity = self.risk.position_size(
            self.portfolio.cash,
            entry,
            stop,
        )

        if quantity <= 0:
            return {
                "status": "rejected",
                "reason": "invalid position size",
            }

        ok, message = self.portfolio.open_long(
            symbol,
            entry,
            quantity,
            stop,
            target,
        )

        if ok:
            self.risk_state.open_positions += 1

        return {
            "status": "opened" if ok else "rejected",
            "reason": message,
            "symbol": symbol,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
            "quantity": quantity,
        }

    def status(self):
        return {
            "mode": CONFIG.trading_mode,
            "cash": self.portfolio.cash,
            "realized_pnl": self.portfolio.realized_pnl,
            "open_positions": len(self.portfolio.positions),
            "consecutive_losses": self.risk_state.consecutive_losses,
            "halted": self.risk_state.halted,
            "halt_reason": self.risk_state.halt_reason,
        }
