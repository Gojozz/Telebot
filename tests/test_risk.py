from bot.config import CONFIG
from bot.risk import RiskEngine, RiskState


def test_position_size():
    risk = RiskEngine(CONFIG)

    size = risk.position_size(
        1000,
        100,
        98,
    )

    assert size > 0


def test_daily_loss_limit():
    risk = RiskEngine(CONFIG)

    state = RiskState(
        starting_balance=1000,
        daily_realized_pnl=-20,
    )

    assert risk.daily_loss_limit_reached(state)


def test_consecutive_loss_halt():
    risk = RiskEngine(CONFIG)

    state = RiskState(
        starting_balance=1000,
        consecutive_losses=3,
    )

    allowed, _ = risk.can_open_position(state)

    assert not allowed
