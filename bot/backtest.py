import csv

from bot.config import CONFIG
from bot.strategy import TrendStrategy
from bot.strategy_v2 import MomentumVolatilityStrategy
from bot.strategy_v2r import RegimeTrendStrategy
from bot.research_strategies import BollingerMeanReversionStrategy
from bot.research_strategies import MeanReversionStrategy
from bot.research_strategies import VolatilityBreakoutStrategy
from bot.risk import RiskEngine
from bot.execution import PaperExecution
from bot.metrics import calculate_metrics


class Backtester:
    def __init__(self, initial_balance=None):
        self.initial_balance = (
            CONFIG.initial_balance
            if initial_balance is None
            else initial_balance
        )

        self.balance = self.initial_balance
        self.equity_curve = [self.initial_balance]
        self.trades = []

        if CONFIG.strategy_version == "volbreak":
            self.strategy = VolatilityBreakoutStrategy(
                channel_period=20,
                channel_std=2.0,
                atr_period=14,
                atr_stop_mult=2.0,
                reward_r=2.0,
                min_atr_pct=0.005,
            )
        elif CONFIG.strategy_version == "mean_reversion":
            self.strategy = MeanReversionStrategy(
                ema_period=20,
                deviation_pct=0.015,
                min_atr_pct=0.003,
            )
        elif CONFIG.strategy_version == "bollinger":
            self.strategy = BollingerMeanReversionStrategy(
                bb_period=20,
                bb_std=2.0,
                regime_ema_period=50,
                atr_period=14,
                atr_stop_mult=2.0,
                reward_r=1.5,
            )
        elif CONFIG.strategy_version == "v2r":
            self.strategy = RegimeTrendStrategy(
                fast_period=CONFIG.fast_ema,
                slow_period=CONFIG.slow_ema,
            )
        elif CONFIG.strategy_version == "v2":
            self.strategy = MomentumVolatilityStrategy(
                fast_period=CONFIG.fast_ema,
                slow_period=CONFIG.slow_ema,
            )
        else:
            self.strategy = TrendStrategy(
                fast_period=CONFIG.fast_ema,
                slow_period=CONFIG.slow_ema,
            )

        self.risk = RiskEngine(
            risk_per_trade=CONFIG.risk_per_trade,
            max_daily_loss=CONFIG.max_daily_loss,
            max_open_positions=CONFIG.max_open_positions,
            max_consecutive_losses=CONFIG.max_consecutive_losses,
            max_notional_pct=CONFIG.max_notional_pct,
        )

        self.execution = PaperExecution(
            fee_rate=CONFIG.fee_rate,
            slippage_pct=CONFIG.slippage_pct,
        )

        self.position = None

    @staticmethod
    def load_csv(path):
        rows = []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            required = {
                "timestamp",
                "open",
                "high",
                "low",
                "close",
            }

            if not required.issubset(reader.fieldnames or set()):
                raise ValueError(
                    "CSV must contain timestamp, open, high, low, close"
                )

            for row in reader:
                rows.append({
                    "timestamp": row["timestamp"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

        return rows

    def _open_position(self, candle, metadata=None):
        # Execution happens at the NEXT candle open.
        entry_reference = candle["open"]
        metadata = dict(metadata or {})

        # Determine the actual BUY execution price first. PaperExecution
        # applies deterministic slippage without changing any state.
        actual_entry = self.execution.buy_price(entry_reference)

        # Strategy-specific ATR stop/reward, when supplied.
        # Otherwise preserve the legacy fixed SL/TP behavior.
        stop_distance = metadata.get("stop_distance")
        reward_r = metadata.get("reward_r")

        if stop_distance is not None and float(stop_distance) > 0:
            stop_distance = float(stop_distance)
            stop = actual_entry - stop_distance
            reward_r = 1.0 if reward_r is None else float(reward_r)
            take_profit = actual_entry + (stop_distance * reward_r)
        else:
            stop = actual_entry * (1 - CONFIG.stop_loss_pct)
            take_profit = actual_entry * (1 + CONFIG.take_profit_pct)

        # Risk/reward is now defined from the actual executed entry.
        risk_distance = actual_entry - stop
        reward_distance = take_profit - actual_entry

        if risk_distance <= 0:
            return

        risk_reward = reward_distance / risk_distance
        if risk_reward < CONFIG.min_risk_reward:
            return

        if not self.risk.can_open_position(self.balance):
            return

        # Position sizing also uses the actual executed entry so the
        # configured risk-per-trade remains consistent after slippage.
        quantity = self.risk.position_size(
            self.balance,
            actual_entry,
            stop,
        )

        if quantity <= 0:
            return

        execution = self.execution.open_long(
            entry_reference,
            quantity,
        )

        total_cost = (
            execution["gross_cost"]
            + execution["fee"]
        )

        if total_cost > self.balance:
            return

        self.balance -= total_cost
        self.risk.open_positions += 1

        # The execution price should match the deterministic price
        # calculated above. Store the execution result as source of truth.
        self.position = {
            "timestamp": candle["timestamp"],
            "entry_reference": entry_reference,
            "regime": metadata.get("regime", ""),
            "strategy": metadata.get("strategy", ""),
            "entry_price": execution["price"],
            "quantity": quantity,
            "stop_loss": stop,
            "take_profit": take_profit,
            "entry_fee": execution["fee"],

            # MFE/MAE tracking
            "mfe_price": execution["price"],
            "mae_price": execution["price"],
            "mfe_pct": 0.0,
            "mae_pct": 0.0,
        }

    def _close_position(self, candle, reason, trigger_price):
        if self.position is None:
            return

        p = self.position

        execution = self.execution.close_long(
            trigger_price,
            p["quantity"],
        )

        exit_value = execution["gross_value"]
        exit_fee = execution["fee"]

        gross_pnl = (
            (execution["price"] - p["entry_price"])
            * p["quantity"]
        )

        total_fees = p["entry_fee"] + exit_fee
        pnl = gross_pnl - total_fees

        self.balance += exit_value - exit_fee

        self.risk.open_positions = max(
            0,
            self.risk.open_positions - 1,
        )

        self.risk.register_trade(pnl)

        self.trades.append({
            "entry_timestamp": p["timestamp"],
            "exit_timestamp": candle["timestamp"],
            "entry_price": p["entry_price"],
            "exit_price": execution["price"],
            "quantity": p["quantity"],
            "regime": p.get("regime", ""),
            "strategy": p.get("strategy", ""),
            "stop_loss": p["stop_loss"],
            "take_profit": p["take_profit"],

            # MFE/MAE
            "mfe_price": p.get("mfe_price", p["entry_price"]),
            "mae_price": p.get("mae_price", p["entry_price"]),
            "mfe_pct": p.get("mfe_pct", 0.0),
            "mae_pct": p.get("mae_pct", 0.0),

            "reason": reason,
            "gross_pnl": gross_pnl,
            "fees": total_fees,
            "pnl": pnl,
        })

        self.position = None

    def run(self, rows, start_index=0):
        if start_index < 0 or start_index > len(rows):
            raise ValueError(
                "start_index must be between 0 and len(rows)"
            )

        closes = []
        highs = []
        lows = []
        pending_signal = None
        pending_metadata = {}

        # OOS equity starts from initial test balance.
        self.equity_curve = [self.initial_balance]

        for index, candle in enumerate(rows):

            # ---------------------------------------------------------
            # TRAIN = indicator context only.
            # ---------------------------------------------------------
            if index < start_index:
                closes.append(candle["close"])
                highs.append(candle["high"])
                lows.append(candle["low"])
                continue

            # ---------------------------------------------------------
            # Daily risk state
            #
            # The first tradable candle of each UTC day establishes
            # that day's starting balance. Daily realized PnL is then
            # measured against that fixed balance.
            # ---------------------------------------------------------
            self.risk.update_day(candle["timestamp"], self.balance)

            # ---------------------------------------------------------
            # Signal from the PREVIOUS candle is executed at the
            # CURRENT candle OPEN.
            #
            # Example:
            # candle N closes -> signal
            # candle N+1 opens -> entry
            # ---------------------------------------------------------
            if pending_signal == "BUY" and self.position is None:
                self._open_position(
                    candle,
                    metadata=pending_metadata,
                )

            pending_signal = None
            pending_metadata = {}

            # ---------------------------------------------------------
            # Existing position gets priority.
            # Since entry occurs at candle OPEN, this candle's
            # high/low can legitimately trigger SL/TP.
            #
            # Conservative assumption:
            # if SL and TP are both touched in one candle,
            # assume SL happened first.
            # ---------------------------------------------------------
            if self.position is not None:
                p = self.position

                # -------------------------------------------------
                # MFE / MAE
                #
                # Long position:
                #   MFE = highest price reached above entry
                #   MAE = lowest price reached below entry
                #
                # This is updated BEFORE SL/TP processing so the
                # candle that closes the trade is also included.
                # -------------------------------------------------
                entry_price = p["entry_price"]

                candle_high = candle["high"]
                candle_low = candle["low"]

                if candle_high > p.get("mfe_price", entry_price):
                    p["mfe_price"] = candle_high

                if candle_low < p.get("mae_price", entry_price):
                    p["mae_price"] = candle_low

                p["mfe_pct"] = (
                    (p["mfe_price"] - entry_price)
                    / entry_price
                    * 100
                )

                p["mae_pct"] = (
                    (p["mae_price"] - entry_price)
                    / entry_price
                    * 100
                )

                if candle["low"] <= p["stop_loss"]:
                    self._close_position(
                        candle,
                        "stop_loss",
                        p["stop_loss"],
                    )

                elif candle["high"] >= p["take_profit"]:
                    self._close_position(
                        candle,
                        "take_profit",
                        p["take_profit"],
                    )

            # ---------------------------------------------------------
            # Candle CLOSE becomes available only AFTER all intrabar
            # processing for this candle.
            # ---------------------------------------------------------
            closes.append(candle["close"])
            highs.append(candle["high"])
            lows.append(candle["low"])

            # ---------------------------------------------------------
            # Generate signal for the NEXT candle.
            # This is the key lookahead fix.
            # ---------------------------------------------------------
            if self.position is None:
                # Preserve compatibility with legacy strategies while
                # allowing OHLC-aware research strategies.
                if CONFIG.strategy_version in ("v2", "v2r"):
                    signal = self.strategy.analyze(
                        closes,
                        highs=highs,
                        lows=lows,
                    )
                else:
                    try:
                        signal = self.strategy.analyze(
                            closes,
                            highs=highs,
                            lows=lows,
                        )
                    except TypeError as exc:
                        if "unexpected keyword argument" not in str(exc):
                            raise
                        signal = self.strategy.analyze(closes)

                if signal["signal"] == "BUY":
                    pending_signal = "BUY"
                    pending_metadata = {
                        "regime": signal.get("regime", ""),
                        "strategy": signal.get("strategy", ""),
                        "stop_distance": signal.get("stop_distance"),
                        "reward_r": signal.get("reward_r"),
                        "atr": signal.get("atr"),
                        "atr_pct": signal.get("atr_pct"),
                        "breakout_level": signal.get("breakout_level"),
                    }

            # ---------------------------------------------------------
            # Mark-to-market TEST equity.
            # ---------------------------------------------------------
            equity = self.balance

            if self.position is not None:
                equity += (
                    self.position["quantity"]
                    * candle["close"]
                )

            self.equity_curve.append(equity)

            if self.risk.halted:
                break

        # -------------------------------------------------------------
        # Force-close remaining TEST position at the final candle close.
        # -------------------------------------------------------------
        if self.position is not None and rows:
            self._close_position(
                rows[-1],
                "end_of_test",
                rows[-1]["close"],
            )

            self.equity_curve.append(self.balance)

        return {
            "trades": self.trades,
            "metrics": calculate_metrics(
                self.trades,
                self.initial_balance,
                self.equity_curve,
            ),
            "final_balance": self.balance,
            "halted": self.risk.halted,
            "halt_reason": self.risk.halt_reason,
        }
