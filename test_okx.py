from main import TradingBot
from okx_api import OKXAPI

class TestTradingBot:
    def __init__(self):
        self.bot = TradingBot()

    def test_initialize(self):
        self.bot.api.initialize()
        assert self.bot.api.initialized

    def test_get_ohlcv(self):
        df = self.bot.api.get_ohlcv()
        print(df)
        assert not df.empty
        assert 'close' in df.columns

    def test_generate_signals(self):
        df = self.bot.strategy.generate_signals(pd.DataFrame({'close': [1, 2, 3]}))
        assert 'signal' in df.columns
        assert 'signal_strength' in df.columns

    def test_execute_trade_buy(self):
        self.bot.execute_trade('buy', 1, 95000.0, 98000.0)
        assert self.bot.api.last_trade['side'] == 'buy'
        assert self.bot.api.last_trade['amount'] == 1
        assert self.bot.api.last_trade['stop_loss'] == 1
        assert self.bot.api.last_trade['take_profit'] == 2

    def test_execute_trade_sell(self):
        self.bot.execute_trade('sell', 1, None, None)
        assert self.bot.api.last_trade['side'] == 'sell'
        assert self.bot.api.last_trade['amount'] == 1

    def test_check_market_conditions(self):
        df = self.bot.api.get_ohlcv()
        self.bot.check_market_conditions()
    
if __name__ == "__main__":
    test_bot = TestTradingBot()
    api = OKXAPI()
    # api.get_balance()
    # test_bot.test_execute_trade_buy()
    test_bot.test_execute_trade_sell()
