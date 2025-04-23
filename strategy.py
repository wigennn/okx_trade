import pandas as pd
import numpy as np
from config import (
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MA_PERIOD, MA_FAST, MA_SLOW, STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, POSITION_SIZE
)

class TradingStrategy:
    def __init__(self):
        self.rsi_period = RSI_PERIOD
        self.rsi_overbought = RSI_OVERBOUGHT
        self.rsi_oversold = RSI_OVERSOLD
        self.ma_period = MA_PERIOD
        self.ma_fast = MA_FAST
        self.ma_slow = MA_SLOW
        self.stop_loss = STOP_LOSS_PERCENT
        self.take_profit = TAKE_PROFIT_PERCENT
        self.volume_ma_period = 10
        self.atr_period = 7

    def calculate_rsi(self, prices, period=14):
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    def calculate_atr(self, high, low, close, period=14):
        """计算ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def calculate_adx(self, high, low, close, period=14):
        """计算ADX"""
        tr = self.calculate_atr(high, low, close, period)
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        plus_dm = plus_dm.rolling(window=period).mean()
        minus_dm = abs(minus_dm.rolling(window=period).mean())
        tr14 = tr.rolling(window=period).mean()
        plus_di14 = 100 * (plus_dm / tr14)
        minus_di14 = 100 * (minus_dm / tr14)
        dx = 100 * abs(plus_di14 - minus_di14) / (plus_di14 + minus_di14)
        return dx.rolling(window=period).mean()

    def calculate_indicators(self, df):
        """计算技术指标"""
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # 移动平均线
        df['ma'] = df['close'].rolling(window=self.ma_period).mean()
        df['ma_fast'] = df['close'].rolling(window=self.ma_fast).mean()
        df['ma_slow'] = df['close'].rolling(window=self.ma_slow).mean()
        
        # MACD
        macd, signal = self.calculate_macd(df['close'], fast=6, slow=13, signal=4)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = macd - signal
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # ATR
        df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'], self.atr_period)
        
        # ADX
        df['adx'] = self.calculate_adx(df['high'], df['low'], df['close'], self.atr_period)
        
        return df

    def generate_signals(self, df):
        """生成交易信号"""
        df = self.calculate_indicators(df)
        
        # 初始化信号列
        df['signal'] = 0
        df['signal_strength'] = 0
        
        # 趋势判断
        trend_up = (df['ma_fast'] > df['ma_slow']) & (df['close'] > df['ma'])
        trend_down = (df['ma_fast'] < df['ma_slow']) & (df['close'] < df['ma'])
        
        # 买入信号条件
        buy_condition = (
            (df['rsi'] < self.rsi_oversold) &  # RSI超卖
            (df['macd'] > df['macd_signal']) & # MACD金叉
            (df['volume_ratio'] > 1.1) &       # 成交量略微放大
            (df['adx'] > 20) &                 # 降低趋势强度要求
            trend_up                           # 上升趋势
        )
        
        # 卖出信号条件
        sell_condition = (
            (df['rsi'] > self.rsi_overbought) &  # RSI超买
            (df['macd'] < df['macd_signal']) &   # MACD死叉
            (df['volume_ratio'] > 1.1) &         # 成交量略微放大
            (df['adx'] > 20) &                   # 降低趋势强度要求
            trend_down                           # 下降趋势
        )
        
        # 设置信号
        df.loc[buy_condition, 'signal'] = 1    # 1表示买入
        df.loc[sell_condition, 'signal'] = -1  # -1表示卖出
        
        # 计算信号强度
        df.loc[buy_condition, 'signal_strength'] = (
            (self.rsi_oversold - df['rsi']) / self.rsi_oversold * 0.4 +  # RSI权重
            (df['volume_ratio'] - 1) * 0.3 +                             # 成交量权重
            (df['adx'] - 20) / 80 * 0.3                                  # ADX权重
        )
        
        df.loc[sell_condition, 'signal_strength'] = (
            (df['rsi'] - self.rsi_overbought) / (100 - self.rsi_overbought) * 0.4 +
            (df['volume_ratio'] - 1) * 0.3 +
            (df['adx'] - 20) / 80 * 0.3
        )
        
        return df

    def calculate_position_size(self, balance, current_price, signal_strength):
        """计算仓位大小"""
        base_size = balance * POSITION_SIZE  # 使用配置中的仓位大小
        # 根据信号强度调整仓位
        adjusted_size = base_size * (0.5 + signal_strength * 0.5)
        return adjusted_size / current_price

    def calculate_stop_loss(self, entry_price, side, atr):
        """计算止损价格"""
        atr_multiplier = 1.5  # 降低ATR倍数
        if side == 'buy':
            return entry_price - atr * atr_multiplier
        else:
            return entry_price + atr * atr_multiplier

    def calculate_take_profit(self, entry_price, side, atr):
        """计算止盈价格"""
        risk_reward_ratio = 2  # 保持风险收益比
        stop_loss = self.calculate_stop_loss(entry_price, side, atr)
        if side == 'buy':
            return entry_price + (entry_price - stop_loss) * risk_reward_ratio
        else:
            return entry_price - (stop_loss - entry_price) * risk_reward_ratio 