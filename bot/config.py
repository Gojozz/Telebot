import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    trading_mode = os.getenv("TRADING_MODE", "paper")

    initial_balance = float(os.getenv("INITIAL_BALANCE", "1000"))

    risk_per_trade = float(os.getenv("RISK_PER_TRADE", "0.005"))
    max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
    max_open_positions = int(os.getenv("MAX_OPEN_POSITIONS", "2"))
    max_consecutive_losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))

    # Maximum portion of equity that may be committed to one position.
    max_notional_pct = float(os.getenv("MAX_NOTIONAL_PCT", "0.25"))

    fast_ema = int(os.getenv("FAST_EMA", "20"))
    slow_ema = int(os.getenv("SLOW_EMA", "50"))

    # Strategy selection.
    # v1 = EMA-only baseline.
    # v2 = trend + RSI momentum + ATR volatility.
    # v2r = regime-aware trend strategy.
    strategy_version = os.getenv("STRATEGY_VERSION", "v1")

    # Donchian + ATR research strategy
    donchian_lookback = int(os.getenv("DONCHIAN_LOOKBACK", "20"))
    donchian_atr_period = int(os.getenv("DONCHIAN_ATR_PERIOD", "14"))
    donchian_atr_stop_mult = float(
        os.getenv("DONCHIAN_ATR_STOP_MULT", "2.0")
    )
    donchian_reward_r = float(
        os.getenv("DONCHIAN_REWARD_R", "2.0")
    )

    min_risk_reward = float(os.getenv("MIN_RISK_REWARD", "1.5"))
    stop_loss_pct = float(os.getenv("STOP_LOSS_PCT", "0.02"))
    take_profit_pct = float(os.getenv("TAKE_PROFIT_PCT", "0.03"))

    # Backtest stress assumptions.
    # These are NOT exchange-specific fees.
    fee_rate = float(os.getenv("FEE_RATE", "0.001"))
    slippage_pct = float(os.getenv("SLIPPAGE_PCT", "0.0005"))

CONFIG = Config()
