class PaperExecution:
    """
    Deterministic execution simulator.

    Slippage is applied against us:
      BUY  -> higher price
      SELL -> lower price
    """

    def __init__(self, fee_rate=0.001, slippage_pct=0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct

    def buy_price(self, market_price):
        return market_price * (1 + self.slippage_pct)

    def sell_price(self, market_price):
        return market_price * (1 - self.slippage_pct)

    def fee(self, notional):
        return abs(notional) * self.fee_rate

    def open_long(self, market_price, quantity):
        execution_price = self.buy_price(market_price)
        gross_cost = execution_price * quantity
        fee = self.fee(gross_cost)

        return {
            "price": execution_price,
            "quantity": quantity,
            "gross_cost": gross_cost,
            "fee": fee,
        }

    def close_long(self, market_price, quantity):
        execution_price = self.sell_price(market_price)
        gross_value = execution_price * quantity
        fee = self.fee(gross_value)

        return {
            "price": execution_price,
            "quantity": quantity,
            "gross_value": gross_value,
            "fee": fee,
        }
