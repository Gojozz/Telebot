from dataclasses import dataclass
from datetime import date


@dataclass
class RiskState:
    starting_balance: float = 0.0
    daily_realized_pnl: float = 0.0
    current_day: date | None = None
    consecutive_losses: int = 0
    open_positions: int = 0
    halted: bool = False
    halt_reason: str = ""

    @property
    def daily_pnl(self):
        return self.daily_realized_pnl

    @daily_pnl.setter
    def daily_pnl(self, value):
        self.daily_realized_pnl = value


class RiskEngine:
    def __init__(
        self,
        config=None,
        risk_per_trade=None,
        max_daily_loss=None,
        max_open_positions=None,
        max_consecutive_losses=None,
        max_notional_pct=None,
        state=None,
    ):
        # Support both:
        #   RiskEngine(CONFIG)
        # and:
        #   RiskEngine(
        #       risk_per_trade=...,
        #       max_daily_loss=...
        #   )
        if config is not None and not isinstance(config, (int, float)):
            risk_per_trade = (
                getattr(config, "risk_per_trade", 0.005)
                if risk_per_trade is None
                else risk_per_trade
            )
            max_daily_loss = (
                getattr(config, "max_daily_loss", 0.02)
                if max_daily_loss is None
                else max_daily_loss
            )
            max_open_positions = (
                getattr(config, "max_open_positions", 2)
                if max_open_positions is None
                else max_open_positions
            )
            max_consecutive_losses = (
                getattr(config, "max_consecutive_losses", 3)
                if max_consecutive_losses is None
                else max_consecutive_losses
            )
            max_notional_pct = (
                getattr(config, "max_notional_pct", 0.25)
                if max_notional_pct is None
                else max_notional_pct
            )

        self.risk_per_trade = (
            0.005 if risk_per_trade is None else float(risk_per_trade)
        )

        self.max_daily_loss = (
            0.02 if max_daily_loss is None else float(max_daily_loss)
        )

        self.max_open_positions = (
            2 if max_open_positions is None else int(max_open_positions)
        )

        self.max_consecutive_losses = (
            3
            if max_consecutive_losses is None
            else int(max_consecutive_losses)
        )

        self.max_notional_pct = (
            0.25
            if max_notional_pct is None
            else float(max_notional_pct)
        )

        self.state = state if state is not None else RiskState()

    @property
    def open_positions(self):
        return self.state.open_positions

    @open_positions.setter
    def open_positions(self, value):
        self.state.open_positions = value

    @property
    def daily_pnl(self):
        return self.state.daily_realized_pnl

    @daily_pnl.setter
    def daily_pnl(self, value):
        self.state.daily_realized_pnl = value

    @property
    def consecutive_losses(self):
        return self.state.consecutive_losses

    @consecutive_losses.setter
    def consecutive_losses(self, value):
        self.state.consecutive_losses = value

    @property
    def halted(self):
        return self.state.halted

    @halted.setter
    def halted(self, value):
        self.state.halted = value

    @property
    def halt_reason(self):
        return self.state.halt_reason

    @halt_reason.setter
    def halt_reason(self, value):
        self.state.halt_reason = value

    def daily_loss_limit_reached(self, state=None):
        state = state if state is not None else self.state

        if state.starting_balance <= 0:
            return False

        limit = state.starting_balance * self.max_daily_loss

        return state.daily_realized_pnl <= -limit

    def update_day(self, timestamp, balance=None):
        """Reset daily risk state when the trading day changes.

        The daily loss limit is measured from the balance at the
        beginning of the current trading day.
        """
        if timestamp is None:
            return

        if hasattr(timestamp, "date"):
            day = timestamp.date()
        elif isinstance(timestamp, date):
            day = timestamp
        else:
            day = str(timestamp)[:10]

        if self.state.current_day is None:
            self.state.current_day = day
            self.state.daily_realized_pnl = 0.0
            if balance is not None and balance > 0:
                self.state.starting_balance = float(balance)
            return

        if day != self.state.current_day:
            self.state.current_day = day
            self.state.daily_realized_pnl = 0.0

            if balance is not None and balance > 0:
                self.state.starting_balance = float(balance)

            # A daily-loss halt should not carry into the next day.
            if self.state.halt_reason == "daily loss limit reached":
                self.state.halted = False
                self.state.halt_reason = ""

    def can_open_position(self, balance=None):
        # Backward-compatible API:
        # can_open_position(RiskState(...))
        if isinstance(balance, RiskState):
            state = balance

            if self.daily_loss_limit_reached(state):
                return False, "daily loss limit reached"

            if state.consecutive_losses >= self.max_consecutive_losses:
                return False, "maximum consecutive losses reached"

            if state.open_positions >= self.max_open_positions:
                return False, "maximum open positions reached"

            return True, "risk checks passed"

        if self.halted:
            return False

        if balance is None:
            balance = self.state.starting_balance

        if balance is None or balance <= 0:
            return False

        # Use the balance at the start of the current day when available.
        # Fall back to the supplied balance for backward compatibility.
        daily_base = (
            self.state.starting_balance
            if self.state.starting_balance > 0
            else balance
        )
        daily_limit = daily_base * self.max_daily_loss

        if self.daily_pnl <= -daily_limit:
            self.halted = True
            self.halt_reason = "daily loss limit reached"
            return False

        if self.consecutive_losses >= self.max_consecutive_losses:
            self.halted = True
            self.halt_reason = "maximum consecutive losses reached"
            return False

        if self.open_positions >= self.max_open_positions:
            return False

        return True

    def position_size(self, balance, entry, stop):
        distance = abs(entry - stop)

        if balance <= 0 or entry <= 0 or distance <= 0:
            return 0.0

        risk_amount = balance * self.risk_per_trade
        quantity_by_risk = risk_amount / distance

        max_notional = balance * self.max_notional_pct
        quantity_by_notional = max_notional / entry

        return min(quantity_by_risk, quantity_by_notional)

    def register_trade(self, pnl):
        self.daily_pnl += pnl

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
