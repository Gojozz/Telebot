import csv
from statistics import mean, median

from ai_agent.environment_v3 import TradingEnvironmentV3
from ai_agent.trade_experience_memory_v1 import TradeExperienceMemoryV1
from ai_agent.trade_journal_v1 import TradeJournalV1
from ai_agent.learning_loop_v3 import LearningLoopV3
from ai_agent.knowledge_decision_v4 import KnowledgeDecisionV4
from ai_agent.hybrid_context_v1 import HybridContextV1


TRAIN_END = 12000
VAL_END = 16000
TRAIN_STEPS = 3000
FEE_RATE = 0.0004
SLIPPAGE_RATE = 0.0002


def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })
    return rows


def context_from_row(rows, index):
    close = rows[index]["close"]
    prev1 = rows[index - 1]["close"]
    prev6 = rows[index - 6]["close"]
    prev24 = rows[index - 24]["close"]

    r1 = close / prev1 - 1.0
    r6 = close / prev6 - 1.0
    r24 = close / prev24 - 1.0
    volatility = (rows[index]["high"] - rows[index]["low"]) / close

    context_key = HybridContextV1.from_features(
        r1, r6, r24, volatility
    )

    return context_key


def build_train_knowledge(rows):
    train_rows = rows[:TRAIN_END]

    memory = TradeExperienceMemoryV1()
    journal = TradeJournalV1(
        memory,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )
    learning = LearningLoopV3(
        min_trades=3,
        prior_weight=5.0,
        min_confidence=0.55,
    )

    start = 24
    end = min(start + TRAIN_STEPS, len(train_rows))

    for index in range(start, end):
        row = train_rows[index]
        context_key = context_from_row(train_rows, index)

        close = row["close"]
        r1 = close / train_rows[index - 1]["close"] - 1.0
        r6 = close / train_rows[index - 6]["close"] - 1.0
        r24 = close / train_rows[index - 24]["close"] - 1.0
        volatility = (row["high"] - row["low"]) / close

        decision = KnowledgeDecisionV4(
            min_trades=3,
            min_confidence=0.55,
        ).decide(
            learning.all_knowledge(),
            context_key,
        )

        action = decision.action

        if action not in ("BUY", "SELL"):
            phase = (index - start) % 5
            action = (
                "BUY" if phase in (0, 1)
                else "SELL" if phase in (2, 3)
                else "HOLD"
            )

        current_position = (
            journal.open_trade.position
            if journal.open_trade is not None
            else 0
        )

        desired_position = (
            1 if action == "BUY"
            else -1 if action == "SELL"
            else 0
        )

        if (
            current_position != 0
            and desired_position != 0
            and current_position != desired_position
        ):
            journal.observe_market(row["high"], row["low"])
            journal.close(
                market_price=close,
                index=index,
                high=row["high"],
                low=row["low"],
            )
            learning.process(memory.all())

        if desired_position != 0 and journal.open_trade is None:
            journal.open(
                action=action,
                position=desired_position,
                market_price=close,
                index=index,
                r1=r1,
                r6=r6,
                r24=r24,
                volatility=volatility,
                volume_ratio=1.0,
                close_position=0.5,
                high=row["high"],
                low=row["low"],
            )

        journal.observe_market(row["high"], row["low"])
        learning.process(memory.all())

    learning.process(memory.all())

    return learning


def max_drawdown(equity_curve):
    peak = 1.0
    max_dd = 0.0

    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    return max_dd


def pct(x):
    return x * 100.0


def main():
    rows = load_rows("data/btcusdt_1h_ohlcv_new.csv")
    assert len(rows) >= VAL_END

    learning = build_train_knowledge(rows)
    frozen_knowledge = tuple(learning.all_knowledge())
    frozen_processed = learning.processed_count

    warmup = rows[TRAIN_END - 24:TRAIN_END]
    validation_rows = rows[TRAIN_END:VAL_END]
    run_rows = warmup + validation_rows

    assert len(validation_rows) == 4000

    env = TradingEnvironmentV3(
        run_rows,
        fee_rate=FEE_RATE,
        slippage_rate=SLIPPAGE_RATE,
    )

    decision_engine = KnowledgeDecisionV4(
        min_trades=3,
        min_confidence=0.55,
    )

    env.reset(24)

    equity_curve = []
    trades = []

    open_trade = None
    decision_counts = {
        "HOLD": 0,
        "BUY": 0,
        "SELL": 0,
        "EXIT": 0,
    }

    reason_counts = {}

    for step in range(4000):
        current_index = env.index
        original_index = TRAIN_END - 24 + current_index

        assert TRAIN_END <= original_index < VAL_END

        context_key = context_from_row(rows, original_index)

        result = decision_engine.decide(
            frozen_knowledge,
            context_key,
        )

        action = result.action
        decision_counts[action] += 1
        reason_counts[result.reason] = (
            reason_counts.get(result.reason, 0) + 1
        )

        row = rows[original_index]
        price = row["close"]

        old_position = env.position
        old_entry_price = env.entry_price

        if old_position == 0 and action in ("BUY", "SELL"):
            side = 1 if action == "BUY" else -1

            entry_execution = env._execution_price(
                price,
                side,
            )

            open_trade = {
                "side": side,
                "position": "LONG" if side == 1 else "SHORT",
                "action": action,
                "entry_index": original_index,
                "entry_price": entry_execution,
                "mfe": 0.0,
                "mae": 0.0,
            }

        env_action = {
            "HOLD": TradingEnvironmentV3.HOLD,
            "BUY": TradingEnvironmentV3.BUY,
            "SELL": TradingEnvironmentV3.SELL,
            "EXIT": TradingEnvironmentV3.EXIT,
        }[action]

        _, _, done, _ = env.step(env_action)

        # A reversal closes the old position before opening the new one.
        if old_position != 0 and action in ("BUY", "SELL"):
            new_position = 1 if action == "BUY" else -1

            if old_position != new_position and open_trade is not None:
                exit_execution = env._execution_price(
                    price,
                    -old_position,
                )

                if open_trade["side"] == 1:
                    pnl = (
                        exit_execution / open_trade["entry_price"]
                        - 1.0
                    )
                else:
                    pnl = (
                        open_trade["entry_price"] / exit_execution
                        - 1.0
                    )

                trades.append({
                    **open_trade,
                    "exit_index": original_index,
                    "exit_price": exit_execution,
                    "pnl": pnl,
                    "holding_bars": max(
                        1,
                        original_index
                        - open_trade["entry_index"]
                        + 1,
                    ),
                })

                open_trade = {
                    "side": new_position,
                    "position": (
                        "LONG" if new_position == 1 else "SHORT"
                    ),
                    "action": action,
                    "entry_index": original_index,
                    "entry_price": env.entry_price,
                    "mfe": 0.0,
                    "mae": 0.0,
                }

        # EXIT closes the current position.
        if (
            old_position != 0
            and action == "EXIT"
            and open_trade is not None
        ):
            exit_execution = env._execution_price(
                price,
                -old_position,
            )

            if open_trade["side"] == 1:
                pnl = (
                    exit_execution / open_trade["entry_price"]
                    - 1.0
                )
            else:
                pnl = (
                    open_trade["entry_price"] / exit_execution
                    - 1.0
                )

            trades.append({
                **open_trade,
                "exit_index": original_index,
                "exit_price": exit_execution,
                "pnl": pnl,
                "holding_bars": max(
                    1,
                    original_index
                    - open_trade["entry_index"]
                    + 1,
                ),
            })

            open_trade = None

        equity_curve.append(env.equity)

        if done:
            break

    # If environment closed a final position automatically, record it.
    if open_trade is not None:
        final_index = VAL_END - 1
        final_price = rows[final_index]["close"]
        exit_execution = env._execution_price(
            final_price,
            -open_trade["side"],
        )

        if open_trade["side"] == 1:
            pnl = (
                exit_execution / open_trade["entry_price"]
                - 1.0
            )
        else:
            pnl = (
                open_trade["entry_price"] / exit_execution
                - 1.0
            )

        trades.append({
            **open_trade,
            "exit_index": final_index,
            "exit_price": exit_execution,
            "pnl": pnl,
            "holding_bars": max(
                1,
                final_index
                - open_trade["entry_index"]
                + 1,
            ),
        })

    assert len(equity_curve) == 4000
    assert learning.processed_count == frozen_processed
    assert tuple(learning.all_knowledge()) == frozen_knowledge

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    long_trades = [t for t in trades if t["position"] == "LONG"]
    short_trades = [t for t in trades if t["position"] == "SHORT"]

    top_sorted = sorted(pnls, reverse=True)

    top3 = sum(top_sorted[:3]) if top_sorted else 0.0
    top5 = sum(top_sorted[:5]) if top_sorted else 0.0
    top10 = sum(top_sorted[:10]) if top_sorted else 0.0
    total_pnl = sum(pnls)

    def side_stats(items):
        if not items:
            return {
                "trades": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
            }

        side_pnls = [t["pnl"] for t in items]

        return {
            "trades": len(items),
            "win_rate": sum(p > 0 for p in side_pnls) / len(side_pnls),
            "avg_pnl": mean(side_pnls),
        }

    print("=" * 80)
    print("KNOWLEDGE TRADE-LEVEL AUDIT V1")
    print("=" * 80)
    print("TRAIN rows                 =", TRAIN_END)
    print("TRAIN learning steps       =", TRAIN_STEPS)
    print("Frozen knowledge records  =", len(frozen_knowledge))
    print("Validation rows            =", 4000)
    print("Completed trades            =", len(trades))
    print()

    print("DECISIONS")
    print("Actions                    =", decision_counts)
    print("Reasons                    =", reason_counts)
    print()

    print("TRADE STATISTICS")
    print("Win rate                   = %.2f%%" % (
        (len(wins) / len(pnls) * 100.0) if pnls else 0.0
    ))
    print("Average PnL/trade          = %+0.4f%%" % (
        pct(mean(pnls)) if pnls else 0.0
    ))
    print("Median PnL/trade           = %+0.4f%%" % (
        pct(median(pnls)) if pnls else 0.0
    ))
    print("Profit factor              = %.4f" % profit_factor)
    print("Average holding bars       = %.2f" % (
        mean(t["holding_bars"] for t in trades)
        if trades else 0.0
    ))
    print()

    print("LONG")
    print("Trades                     =", side_stats(long_trades)["trades"])
    print("Win rate                   = %.2f%%" % (
        pct(side_stats(long_trades)["win_rate"])
    ))
    print("Average PnL                = %+0.4f%%" % (
        pct(side_stats(long_trades)["avg_pnl"])
    ))
    print()

    print("SHORT")
    print("Trades                     =", side_stats(short_trades)["trades"])
    print("Win rate                   = %.2f%%" % (
        pct(side_stats(short_trades)["win_rate"])
    ))
    print("Average PnL                = %+0.4f%%" % (
        pct(side_stats(short_trades)["avg_pnl"])
    ))
    print()

    print("PNL CONCENTRATION")
    print("Total individual PnL       = %+0.4f%%" % pct(total_pnl))
    print("Top 3 contribution         = %+0.4f%%" % pct(top3))
    print("Top 5 contribution         = %+0.4f%%" % pct(top5))
    print("Top 10 contribution        = %+0.4f%%" % pct(top10))

    if total_pnl > 0:
        print("Top 3 / total              = %.2f%%" % (
            pct(top3 / total_pnl)
        ))
        print("Top 5 / total              = %.2f%%" % (
            pct(top5 / total_pnl)
        ))
        print("Top 10 / total             = %.2f%%" % (
            pct(top10 / total_pnl)
        ))

    print()

    print("EQUITY")
    print("Final equity               = %.6f" % env.equity)
    print("Total return               = %+0.2f%%" % (
        pct(env.equity - 1.0)
    ))
    print("Max drawdown               = %.2f%%" % (
        pct(max_drawdown(equity_curve))
    ))
    print()

    print("FROZEN STATE")
    print("Knowledge unchanged        = PASS")
    print("Validation experiences     = NONE")
    print("TRAIN boundary             = PASS")
    print("OOS contamination          = NO")

    import json
    with open("data/validation_knowledge_trades_v1.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "train_end": TRAIN_END,
                "validation_end": VAL_END,
                "train_steps": TRAIN_STEPS,
                "fee_rate": FEE_RATE,
                "slippage_rate": SLIPPAGE_RATE,
                "trades": trades,
            },
            f,
            indent=2,
        )

    print("Trade log saved            = data/validation_knowledge_trades_v1.json")
    print("AUDIT RESULT               = COMPLETE")


if __name__ == "__main__":
    main()
