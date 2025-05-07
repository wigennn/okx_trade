import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API配置
API_KEY = os.getenv('OKX_API_KEY')
SECRET_KEY = os.getenv('OKX_SECRET_KEY')
PASSPHRASE = os.getenv('OKX_PASSPHRASE')

# 交易配置
SYMBOL = 'BTC-USDT-SWAP'  # 交易对，添加-SWAP后缀表示永续合约
TIMEFRAME = '1m'     # 时间周期
LEVERAGE = 3         # 杠杆倍数
POSITION_SIZE = 0.05  # 仓位大小（占总资金的百分比）

# 策略参数
RSI_PERIOD = 9
RSI_OVERBOUGHT = 75
RSI_OVERSOLD = 25
MA_PERIOD = 10
MA_FAST = 5
MA_SLOW = 20

# 风险管理
STOP_LOSS_PERCENT = 0.01
TAKE_PROFIT_PERCENT = 0.02
MAX_DAILY_TRADES = 500 