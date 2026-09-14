from bot.engine import TradingEngine


def main():
    engine = TradingEngine()

    # Synthetic prices used only to verify the engine.
    prices = [
        100 + i * 0.8
        for i in range(60)
    ]

    print("=== TELEBOT v0.1 ===")
    print("MODE:", engine.status()["mode"])

    signal = engine.analyze("BTC/USDT", prices)

    print("SIGNAL:", signal.action)
    print("REASON:", signal.reason)

    result = engine.try_buy("BTC/USDT", prices)

    print("ORDER:", result)
    print("STATUS:", engine.status())


if __name__ == "__main__":
    main()
