import time
import logging
from datetime import datetime
from okx_api import OKXAPI
from strategy import TradingStrategy
from config import SYMBOL, POSITION_SIZE, MAX_DAILY_TRADES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

class TradingBot:
    def __init__(self):
        self.api = OKXAPI()
        self.strategy = TradingStrategy()
        self.last_trade_time = None
        self.trades_today = 0
        self.last_price = None
        self.position = None
        self.balance = None
        self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        self.logger = logging.getLogger(__name__)

    def update_trade_count(self):
        """更新每日交易计数"""
        current_time = datetime.now()
        if self.last_trade_time is None or current_time.date() != self.last_trade_time.date():
            self.trades_today = 0
            self.logger.info("新的一天开始，重置交易计数")
        self.last_trade_time = current_time
        self.trades_today += 1
        self.logger.info(f"今日已执行 {self.trades_today} 笔交易")

    def check_market_conditions(self):
        """检查市场条件"""
        try:
            # 获取当前行情
            ticker = self.api.get_ticker()
            print("ticker:", ticker)
            current_price = ticker['data'][0]['last']
            print("current_price:", current_price)
            
            # 检查价格波动
            if self.last_price is not None:
                price_change = abs(current_price - self.last_price) / self.last_price
                if price_change > 0.05:  # 价格波动超过5%
                    self.logger.warning(f"价格波动过大: {price_change:.2%}")
                    return False
            
            self.last_price = current_price
            return True
            
        except Exception as e:
            self.logger.error(f"检查市场条件时出错: {e}")
            return False

    def execute_trade(self, side, amount, stop_loss, take_profit):
        """执行交易"""
        try:
            if self.trades_today >= MAX_DAILY_TRADES:
                self.logger.warning("达到每日最大交易次数限制")
                return False

            if not self.check_market_conditions():
                self.logger.warning("市场条件不满足，取消交易")
                return False

            order = self.api.create_order(
                side,
                amount,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            self.logger.info(f"{side}订单已创建: {order}")
            self.update_trade_count()
            return True
            
        except Exception as e:
            self.logger.error(f"执行交易时出错: {e}")
            return False

    def run(self):
        """运行交易机器人"""
        self.logger.info("启动交易机器人...")
        
        try:
            # 初始化交易所连接
            self.api.initialize()
            
            while True:
                try:
                    # 获取市场数据
                    df = self.api.get_ohlcv()
                    current_price = df['close'].iloc[-1]
                    
                    # 生成交易信号
                    df = self.strategy.generate_signals(df)
                    latest_signal = df['signal'].iloc[-1]
                    signal_strength = df['signal_strength'].iloc[-1]
                    
                    # 获取当前持仓和余额
                    self.position = self.api.get_position()
                    self.balance = self.api.get_balance('USDT')
                    
                    self.logger.info(f"当前价格: {current_price}, 信号: {latest_signal}, 强度: {signal_strength:.2f}, 持仓: {self.position}, 余额: {self.balance}")
                    
                    # 交易逻辑
                    if latest_signal == 1 and (self.position is None or self.position['contracts'] <= 0):
                        # 买入信号
                        amount = self.strategy.calculate_position_size(
                            self.balance,
                            current_price,
                            signal_strength
                        )
                        stop_loss = self.strategy.calculate_stop_loss(
                            current_price,
                            'buy',
                            df['atr'].iloc[-1]
                        )
                        take_profit = self.strategy.calculate_take_profit(
                            current_price,
                            'buy',
                            df['atr'].iloc[-1]
                        )
                        
                        self.execute_trade('buy', amount, stop_loss, take_profit)
                        
                    elif latest_signal == -1 and self.position is not None and self.position['contracts'] > 0:
                        # 卖出信号
                        self.execute_trade('sell', self.position['contracts'], None, None)
                    
                    # 等待下一个周期
                    time.sleep(60)
                    
                except Exception as e:
                    self.logger.error(f"主循环出错: {e}")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭机器人...")
        except Exception as e:
            self.logger.error(f"机器人运行出错: {e}")
        finally:
            self.logger.info("机器人已停止运行")

if __name__ == "__main__":
    bot = TradingBot()
    bot.run() 