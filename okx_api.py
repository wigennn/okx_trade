import ccxt
import pandas as pd
import time
import os
import hmac
import base64
import json
import urllib3
import requests
from datetime import datetime, timezone
from config import API_KEY, SECRET_KEY, PASSPHRASE, SYMBOL, TIMEFRAME, LEVERAGE

# 禁用SSL警告
urllib3.disable_warnings()

class OKXAPI:
    def __init__(self):
        self.api_key = API_KEY
        self.secret_key = SECRET_KEY
        self.passphrase = PASSPHRASE
        self.base_url = 'https://www.okx.com'  # 主API地址
        self.simulated_url = 'https://www.okx.com'  # 模拟盘API地址
        self.is_simulated = True  # 设置为模拟盘模式
        
        # 配置代理（如果需要）
        self.proxies = {}
        if os.getenv('HTTP_PROXY'):
            self.proxies['http'] = os.getenv('HTTP_PROXY')
        if os.getenv('HTTPS_PROXY'):
            self.proxies['https'] = os.getenv('HTTPS_PROXY')

        # 配置ccxt
        self.exchange = ccxt.okx({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'password': self.passphrase,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'swap',
                'adjustForTimeDifference': True,
                'test': True,  # 设置为模拟盘模式
            },
            'urls': {
                'api': {
                    'rest': self.simulated_url,
                    'fapiPublic': self.simulated_url,
                    'fapiPrivate': self.simulated_url,
                }
            },
            'headers': {
                'Content-Type': 'application/json',
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-PASSPHRASE': self.passphrase,
                'x-simulated-trading': '1',  # 模拟盘标识
            },
            'proxies': self.proxies,
        })
        self.symbol = SYMBOL
        self.timeframe = TIMEFRAME
        self.leverage = LEVERAGE
        self.max_retries = 5
        self.retry_delay = 10
        self.initialized = False

    def _get_timestamp(self):
        """生成ISO 8601标准UTC时间戳（含'Z'标识）"""
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp, method, request_path, body=''):
        """生成签名"""
        if body is None:
            body = ''
        elif isinstance(body, dict):
            body = json.dumps(body)
        elif not isinstance(body, str):
            body = str(body)
            
        # 构建签名字符串
        message = timestamp + method + request_path
        if method == 'GET' and body:
            message += '?' + body
        else:
            message += body
            
        # 生成签名
        mac = hmac.new(bytes(self.secret_key, encoding='utf8'), 
                      bytes(message, encoding='utf-8'), 
                      digestmod='sha256')
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _make_request(self, method, endpoint, params=None, body=None):
        """直接发送请求到OKX API"""
        # 使用模拟盘API地址
        url = f"{self.simulated_url}{endpoint}"
        timestamp = self._get_timestamp()
        
        # 处理GET请求的查询参数
        if method == 'GET' and params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            sign = self._sign(timestamp, method, endpoint, query_string)
        else:
            sign = self._sign(timestamp, method, endpoint, body)
        
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': sign,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'x-simulated-trading': '1',  # 模拟盘标识
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        print(f"请求URL: {url}", f"请求方法: {method}", f"请求时间戳: {timestamp}", f"请求参数: {params}", f"请求体: {body}", f"请求头: {headers}")
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, proxies=self.proxies, verify=False, timeout=30)
            else:
                response = requests.post(url, json=body, headers=headers, proxies=self.proxies, verify=False, timeout=30)
            
            response.raise_for_status()
            result = response.json()
            print(f"请求结果: {result}")
            
            # 检查OKX API的响应码
            if result.get('code') != '0':
                error_msg = result.get('msg', '未知错误')
                error_code = result.get('code', '未知错误码')
                print(f"API错误: {error_msg} (错误码: {error_code})")
                if params:
                    print(f"请求参数: {params}")
                if body:
                    print(f"请求体: {body}")
                raise Exception(f"API错误: {error_msg}")
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    print(f"错误响应: {error_response}")
                except:
                    print(f"响应内容: {e.response.text}")
            raise
        except Exception as e:
            print(f"处理响应时出错: {e}")
            raise

    def initialize(self):
        """初始化交易所连接"""
        if not self.initialized:
            try:
                # 测试网络连接
                print("正在测试网络连接...")
                if not self._test_connection():
                    raise Exception("网络连接测试失败")

                # 测试API连接
                print("正在测试API连接...")
                try:
                    # 测试公共API
                    print("测试公共API...")
                    public_response = self._make_request('GET', '/api/v5/public/time')
                    print(f"API时间: {public_response}")
                    
                    # 测试私有API
                    print("测试私有API...")
                    private_response = self._make_request('GET', '/api/v5/account/balance')
                    print(f"账户信息: {private_response}")
                    
                    # 设置杠杆
                    print("设置杠杆...")
                    leverage_response = self._make_request('POST', '/api/v5/account/set-leverage', body={
                        'instId': self.symbol,
                        'lever': str(self.leverage),
                        'mgnMode': 'cross'
                    })
                    print(f"杠杆设置: {leverage_response}")
                    
                    self.initialized = True
                    print("交易所初始化成功")
                except Exception as e:
                    print(f"API错误: {e}")
                    raise
            except Exception as e:
                print(f"初始化失败: {e}")
                raise

    def _test_connection(self):
        """测试网络连接"""
        try:
            response = requests.get('https://www.okx.com', timeout=10, verify=False)
            if response.status_code == 200:
                print("网络连接正常")
                return True
            else:
                print(f"网络连接异常，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"网络连接测试失败: {e}")
            return False

    def get_ohlcv(self, limit=100):
        """获取K线数据"""
        def _fetch():
            # 将时间周期转换为OKX API要求的格式
            timeframe_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1H',
                '4h': '4H',
                '1d': '1D',
                '1w': '1W',
                '1M': '1M'
            }
            
            bar = timeframe_map.get(self.timeframe)
            if not bar:
                raise ValueError(f"不支持的时间周期: {self.timeframe}")
            
            response = self._make_request('GET', '/api/v5/market/candles', params={
                'instId': self.symbol,
                'bar': bar,
                'limit': limit
            })
            
            ohlcv = response['data']
            # 将字符串转换为数值类型
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
            
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype('int64'), unit='ms')
            df['open'] = df['open'].astype('float64')
            df['high'] = df['high'].astype('float64')
            df['low'] = df['low'].astype('float64')
            df['close'] = df['close'].astype('float64')
            df['volume'] = df['volume'].astype('float64')
            
            return df
        return self._retry_on_failure(_fetch)

    # def get_balance(self):
    #     """获取账户余额"""
    #     def _fetch():
    #         response = self._make_request('GET', '/api/v5/account/balance')
    #         # 确保返回数值类型
    #         return float(response['data'][0]['details'][0]['availBal'])
    #     return self._retry_on_failure(_fetch)
    
    def get_balance(self, ccy_filter=None):
        """获取全币种或指定币种余额"""
        def _fetch():
            response = self._make_request('GET', '/api/v5/account/balance')
            details = response['data'][0]['details']
            balance_dict = {}
            
            # 遍历所有子账户的币种（网页3的账户结构说明）
            for item in details:
                ccy = item['ccy']  # 币种代码（如BTC、USDT）
                avail = float(item['availBal'])  # 可用余额
                frozen = float(item['frozenBal'])  # 冻结金额
                total = avail + frozen
                
                # 按币种聚合数据（跨子账户合并）
                if ccy not in balance_dict:
                    balance_dict[ccy] = {'available': 0.0, 'frozen': 0.0}
                balance_dict[ccy]['available'] += avail
                balance_dict[ccy]['frozen'] += frozen
            
            # 按条件过滤（如指定币种）
            if ccy_filter:
                return balance_dict.get(ccy_filter.upper(), {'available': 0.0, 'frozen': 0.0})
            return balance_dict
        
        return self._retry_on_failure(_fetch)

    def create_order(self, side, amount, price=None, stop_loss=None, take_profit=None):
        """创建订单（支持止盈止损）"""
        def _create():
            # 1. 基础参数构建
            body = {
                'instId': self.symbol,
                # 'tdMode': 'cross',  # 全仓模式
                'tdMode': 'isolated', # 逐仓模式
                'side': side,
                'ordType': 'limit' if price else 'market',
                'sz': f"{float(amount):.8f}".rstrip('0').rstrip('.')  # 避免科学计数法，保留最多8位小数
            }
            if price:
                body['px'] = f"{float(price):.8f}".rstrip('0').rstrip('.')  # 格式化价格
            
            # 2. 止盈止损逻辑修正
            if stop_loss:
                if price:
                    # 限价止损单：委托价需低于触发价（卖出方向）或高于触发价（买入方向）
                    sl_ord_px = (float(stop_loss) * 0.99) if side == 'sell' else (float(stop_loss) * 1.01)
                    sl_ord_px = f"{sl_ord_px:.8f}".rstrip('0').rstrip('.')
                else:
                    # 市价止损单：必须用-1
                    sl_ord_px = '-1'
                body.update({
                    'slTriggerPx': f"{float(stop_loss):.8f}".rstrip('0').rstrip('.'),
                    'slOrdPx': sl_ord_px
                })
            
            if take_profit:
                if price:
                    # 限价止盈单：委托价需高于触发价（卖出方向）或低于触发价（买入方向）
                    tp_ord_px = (float(take_profit) * 1.01) if side == 'sell' else (float(take_profit) * 0.99)
                    tp_ord_px = f"{tp_ord_px:.8f}".rstrip('0').rstrip('.')
                else:
                    # 市价止盈单：必须用-1
                    tp_ord_px = '-1'
                body.update({
                    'tpTriggerPx': f"{float(take_profit):.8f}".rstrip('0').rstrip('.'),
                    'tpOrdPx': tp_ord_px
                })
            
            # 3. 全仓模式预校验（防止错误码51010）
            if body['tdMode'] == 'cross':
                self._validate_account_mode('cross')
            
            return self._make_request('POST', '/api/v5/trade/order', body=body)
        return self._retry_on_failure(_create)

    def _validate_account_mode(self, mode='cross'):
        """验证账户模式是否匹配"""
        if not hasattr(self, '_account_mode_verified'):
            response = self._make_request('GET', '/api/v5/account/config')
            current_mode = response['data'][0]['acctLv']
            if current_mode != mode:
                raise ValueError(f"Account mode must be {mode}, current is {current_mode}")
            self._account_mode_verified = True

    def cancel_order(self, order_id):
        """取消订单"""
        def _cancel():
            return self._make_request('POST', '/api/v5/trade/cancel-order', body={
                'instId': self.symbol,
                'ordId': order_id
            })
        return self._retry_on_failure(_cancel)

    def get_open_orders(self):
        """获取未完成订单"""
        def _fetch():
            return self._make_request('GET', '/api/v5/trade/orders-pending', params={
                'instId': self.symbol
            })
        return self._retry_on_failure(_fetch)

    def get_position(self):
        """获取当前持仓"""
        def _fetch():
            response = self._make_request('GET', '/api/v5/account/positions', params={
                'instId': self.symbol
            })
            return response['data'][0] if response['data'] else None
        return self._retry_on_failure(_fetch)

    def set_leverage(self):
        """设置杠杆倍数"""
        def _set():
            return self._make_request('POST', '/api/v5/account/set-leverage', body={
                'instId': self.symbol,
                'lever': str(int(self.leverage)),  # 确保杠杆为字符串格式的整数
                'mgnMode': 'cross'
            })
        return self._retry_on_failure(_set)

    def get_ticker(self):
        """获取当前行情"""
        def _fetch():
            return self._make_request('GET', '/api/v5/market/ticker', params={
                'instId': self.symbol
            })
        return self._retry_on_failure(_fetch)

    def _retry_on_failure(self, func, *args, **kwargs):
        """重试机制"""
        last_error = None
        for i in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                print(f"操作失败，{self.retry_delay}秒后重试... 错误: {e}")
                time.sleep(self.retry_delay)
        
        if last_error:
            raise last_error 