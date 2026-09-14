from bot.backtest import Backtester


def test_backtest_loads_csv():
    rows = Backtester.load_csv("data/sample_btc.csv")

    assert len(rows) >= 100
    assert rows[0]["close"] == 100
    assert rows[-1]["close"] == 140


def test_backtest_runs():
    rows = Backtester.load_csv("data/sample_btc.csv")

    result = Backtester(initial_balance=1000).run(rows)

    assert "metrics" in result
    assert "trades" in result
    assert result["final_balance"] > 0


def test_position_notional_is_capped():
    from bot.risk import RiskEngine

    risk = RiskEngine(
        risk_per_trade=0.005,
        max_notional_pct=0.25,
    )

    qty = risk.position_size(
        balance=1000,
        entry=100,
        stop=99,
    )

    assert qty * 100 <= 250.000001


def test_signal_executes_on_next_candle_open():
    rows = [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
        },
        {
            "timestamp": "2026-01-01T01:00:00+00:00",
            "open": 200.0,
            "high": 202.0,
            "low": 199.0,
            "close": 201.0,
        },
        {
            "timestamp": "2026-01-01T02:00:00+00:00",
            "open": 210.0,
            "high": 212.0,
            "low": 209.0,
            "close": 211.0,
        },
    ]

    backtester = Backtester(initial_balance=1000.0)

    # Force a BUY signal after the first candle.
    class FakeStrategy:
        def analyze(self, closes):
            if len(closes) >= 1:
                return {"signal": "BUY"}
            return {"signal": "HOLD"}

    backtester.strategy = FakeStrategy()

    result = backtester.run(rows, start_index=0)

    assert result["trades"], "Expected at least one trade"

    trade = result["trades"][0]

    # The signal comes from candle 0.
    # Therefore entry must happen on candle 1 OPEN = 200,
    # never on candle 0 CLOSE = 100.
    assert trade["entry_timestamp"] == rows[1]["timestamp"]
    assert trade["entry_price"] > 200.0
    assert trade["entry_price"] < 201.0
