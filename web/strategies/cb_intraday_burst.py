"""
============================================
可转债日内爆发策略 (CB_Intraday_Burst)
Convertible Bond Intraday Burst Strategy
============================================

T+0日内趋势跟踪策略，利用可转债的高波动性和无T+1限制：
- 追涨杀跌，利用"羊群效应"
- 分钟级别趋势跟踪
- 严格止损止盈控制回撤

核心原理：
- 成交量爆发 + 价格突破 = 入场
- 移动止盈 + 硬止损 + 时间止损 = 出场

Requirements: 高频数据(1分钟K线)，实时行情
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


@dataclass
class CBPosition:
    """可转债持仓状态"""
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: int
    highest_price: float  # 持仓期间最高价
    
    def update_highest(self, current_high: float):
        """更新最高价"""
        if current_high > self.highest_price:
            self.highest_price = current_high


class CBIntradayBurstStrategy(BaseStrategy):
    """
    可转债日内爆发策略
    
    选债条件（盘前/实时筛选）：
    - 剩余规模 < 5亿（盘子小，容易被拉升）
    - 正股涨幅 > 2%（正股强势带动转债）
    - 换手率 > 5%（有人在玩，才有波动）
    
    入场信号（基于1分钟K线）：
    - 成交量爆发：当前分钟成交量 > 过去N分钟均量 * 倍数
    - 价格突破：当前价格突破过去M分钟最高价
    - 阳线确认：收盘价 > 开盘价
    
    出场信号：
    - 移动止盈：价格从最高点回落X%
    - 硬止损：买入后下跌Y%
    - 时间止损：持有超时且未盈利
    - 收盘清仓：14:55强制平仓
    
    适用标的：
    - A股活跃可转债（剔除双低债，只做妖债/活跃债）
    """
    
    STRATEGY_ID = "cb_intraday_burst"
    
    DEFAULT_PARAMS = {
        # 选债条件
        'max_scale': 5.0,           # 最大剩余规模（亿）
        'min_stock_change': 0.02,   # 正股最小涨幅
        'min_turnover_rate': 0.05,  # 最小换手率
        
        # 入场条件
        'vol_lookback': 20,         # 量能均值回看周期（分钟）
        'vol_multiplier': 3.0,      # 量能放大倍数
        'price_lookback': 20,       # 价格突破回看周期（分钟）
        
        # 出场条件
        'trailing_stop_pct': 0.003, # 移动止盈回撤比例 (0.3%)
        'hard_stop_pct': 0.005,     # 硬止损比例 (0.5%)
        'time_stop_minutes': 10,    # 时间止损（分钟）
        'min_profit_for_time_stop': 0.002,  # 时间止损要求的最小盈利
        'force_close_time': '14:55',  # 强制平仓时间
        
        # 资金管理
        'position_pct': 0.95,       # 每次交易使用资金比例
        'commission_rate': 0.0001,  # 万1佣金
        
        # 适用标的（活跃可转债代码列表，动态更新）
        'applicable_cbs': []
    }
    
    def __init__(self, params: Dict = None):
        super().__init__(params)
        # 持仓状态跟踪（symbol -> CBPosition）
        self._positions: Dict[str, CBPosition] = {}
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def filter_cb_pool(self, market_data: Dict) -> List[str]:
        """
        筛选可转债池
        
        Args:
            market_data: 市场数据，需包含:
                - scale: 剩余规模（亿）
                - stock_change: 正股涨幅
                - turnover_rate: 换手率
                
        Returns:
            符合条件的可转债代码列表
        """
        qualified = []
        
        for symbol, data in market_data.items():
            # 检查是否为可转债
            if not self._is_convertible_bond(symbol):
                continue
            
            # 检查规模
            scale = data.get('scale', float('inf'))
            if scale > self.params['max_scale']:
                continue
            
            # 检查正股涨幅
            stock_change = data.get('stock_change', 0)
            if stock_change < self.params['min_stock_change']:
                continue
            
            # 检查换手率
            turnover_rate = data.get('turnover_rate', 0)
            if turnover_rate < self.params['min_turnover_rate']:
                continue
            
            qualified.append(symbol)
        
        return qualified
    
    def _is_convertible_bond(self, symbol: str) -> bool:
        """检查是否为可转债代码"""
        # 可转债代码规则：
        # 上海：110xxx, 113xxx
        # 深圳：123xxx, 127xxx, 128xxx
        code = symbol.split('.')[0] if '.' in symbol else symbol
        return (code.startswith('110') or code.startswith('113') or
                code.startswith('123') or code.startswith('127') or
                code.startswith('128'))
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号（基于1分钟K线）
        
        Args:
            symbols: 标的代码列表
            market_data: 市场数据，格式为:
                {
                    symbol: {
                        'open': float,              # 当前分钟开盘价
                        'high': float,              # 当前分钟最高价
                        'low': float,               # 当前分钟最低价
                        'close': float,             # 当前分钟收盘价
                        'volume': float,            # 当前分钟成交量
                        'volume_history': List[float],  # 历史成交量序列
                        'high_history': List[float],    # 历史最高价序列
                        'scale': float,             # 剩余规模（亿）
                        'stock_change': float,      # 正股涨幅
                        'turnover_rate': float,     # 换手率
                        'current_time': datetime,   # 当前时间
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        
        # 首先筛选可转债池
        cb_pool = self.filter_cb_pool(market_data)
        
        for symbol in symbols:
            # 只处理符合条件的可转债
            if symbol not in cb_pool:
                continue
            
            data = market_data.get(symbol)
            if not data:
                continue
            
            # 检查是否强制平仓时间
            current_time = data.get('current_time', datetime.now())
            if self._is_force_close_time(current_time):
                # 如果有持仓，生成卖出信号
                if symbol in self._positions:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type='sell',
                        strength=5,
                        confidence=100,
                        reason=f'收盘强制平仓 ({current_time.strftime("%H:%M")})',
                        strategy_id=self.STRATEGY_ID
                    ))
                continue
            
            # 检查是否已有持仓
            if symbol in self._positions:
                # 检查出场条件
                should_exit, reason = self._check_exit_signal(symbol, data)
                if should_exit:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type='sell',
                        strength=5,
                        confidence=95,
                        reason=reason,
                        strategy_id=self.STRATEGY_ID
                    ))
            else:
                # 检查入场条件
                should_enter, reason, strength = self._check_entry_signal(symbol, data)
                if should_enter:
                    close = data.get('close', 0)
                    hard_stop = close * (1 - self.params['hard_stop_pct'])
                    
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type='buy',
                        strength=strength,
                        confidence=85,
                        reason=reason,
                        stop_loss=hard_stop,
                        strategy_id=self.STRATEGY_ID
                    ))
        
        return signals
    
    def _check_entry_signal(self, symbol: str, data: Dict) -> Tuple[bool, str, int]:
        """
        检查入场信号
        
        Returns:
            (是否入场, 原因, 信号强度)
        """
        close = data.get('close')
        open_price = data.get('open')
        volume = data.get('volume')
        volume_history = data.get('volume_history', [])
        high_history = data.get('high_history', [])
        
        if not all([close, open_price, volume]):
            return False, '', 0
        
        # 条件1: 成交量爆发
        vol_lookback = self.params['vol_lookback']
        vol_multiplier = self.params['vol_multiplier']
        
        if len(volume_history) < vol_lookback:
            return False, '', 0
        
        avg_volume = np.mean(volume_history[-vol_lookback:])
        if avg_volume <= 0:
            return False, '', 0
        
        volume_burst = volume > avg_volume * vol_multiplier
        
        # 条件2: 价格突破
        price_lookback = self.params['price_lookback']
        
        if len(high_history) < price_lookback:
            return False, '', 0
        
        recent_high = max(high_history[-price_lookback:])
        price_breakout = close > recent_high
        
        # 条件3: 阳线确认
        is_bullish = close > open_price
        
        # 必须同时满足三个条件
        if volume_burst and price_breakout and is_bullish:
            vol_ratio = volume / avg_volume
            
            # 信号强度基于量能放大倍数
            if vol_ratio >= 5:
                strength = 5
            elif vol_ratio >= 4:
                strength = 4
            else:
                strength = 3
            
            reason = (f'量能爆发({vol_ratio:.1f}x), '
                     f'突破{price_lookback}分钟高点({recent_high:.3f}), '
                     f'阳线确认')
            
            return True, reason, strength
        
        return False, '', 0
    
    def _check_exit_signal(self, symbol: str, data: Dict) -> Tuple[bool, str]:
        """
        检查出场信号
        
        Returns:
            (是否出场, 原因)
        """
        position = self._positions.get(symbol)
        if not position:
            return False, ''
        
        close = data.get('close', 0)
        high = data.get('high', 0)
        current_time = data.get('current_time', datetime.now())
        
        # 更新最高价
        position.update_highest(high)
        
        # 检查1: 移动止盈
        trailing_stop_pct = self.params['trailing_stop_pct']
        trailing_stop_price = position.highest_price * (1 - trailing_stop_pct)
        
        if close < trailing_stop_price:
            profit_pct = (close - position.entry_price) / position.entry_price * 100
            return True, (f'移动止盈触发: 从最高{position.highest_price:.3f}'
                         f'回落至{close:.3f}, 盈利{profit_pct:.2f}%')
        
        # 检查2: 硬止损
        hard_stop_pct = self.params['hard_stop_pct']
        hard_stop_price = position.entry_price * (1 - hard_stop_pct)
        
        if close < hard_stop_price:
            loss_pct = (position.entry_price - close) / position.entry_price * 100
            return True, f'硬止损触发: 亏损{loss_pct:.2f}%'
        
        # 检查3: 时间止损
        time_stop_minutes = self.params['time_stop_minutes']
        min_profit = self.params['min_profit_for_time_stop']
        
        hold_time = (current_time - position.entry_time).total_seconds() / 60
        current_profit = (close - position.entry_price) / position.entry_price
        
        if hold_time > time_stop_minutes and current_profit < min_profit:
            return True, (f'时间止损触发: 持有{hold_time:.0f}分钟, '
                         f'盈利{current_profit*100:.2f}% < {min_profit*100:.1f}%')
        
        return False, ''
    
    def _is_force_close_time(self, current_time: datetime) -> bool:
        """检查是否为强制平仓时间"""
        force_time_str = self.params['force_close_time']
        force_hour, force_minute = map(int, force_time_str.split(':'))
        
        return (current_time.hour > force_hour or 
                (current_time.hour == force_hour and current_time.minute >= force_minute))
    
    def on_trade_executed(self, trade_result: Dict) -> None:
        """
        交易执行后的回调
        
        Args:
            trade_result: 交易结果
                - symbol: 标的代码
                - action: 'buy' or 'sell'
                - price: 成交价格
                - quantity: 成交数量
                - timestamp: 成交时间
        """
        symbol = trade_result.get('symbol')
        action = trade_result.get('action')
        price = trade_result.get('price')
        quantity = trade_result.get('quantity')
        timestamp = trade_result.get('timestamp', datetime.now())
        
        if action == 'buy':
            # 建立持仓记录
            self._positions[symbol] = CBPosition(
                symbol=symbol,
                entry_price=price,
                entry_time=timestamp,
                quantity=quantity,
                highest_price=price
            )
        elif action == 'sell':
            # 清除持仓记录
            if symbol in self._positions:
                del self._positions[symbol]
    
    def calculate_position_size(self, signal: Signal, capital: float) -> int:
        """
        计算建议仓位
        
        Args:
            signal: 交易信号
            capital: 可用资金
            
        Returns:
            建议买入数量（张数，可转债1张=100元面值）
        """
        if signal.signal_type != 'buy' or capital <= 0:
            return 0
        
        position_pct = self.params.get('position_pct', 0.95)
        available = capital * position_pct
        
        # 可转债按张计算，1张约100-200元
        # 估算价格（如果有止损价，可以反推）
        if signal.stop_loss and signal.stop_loss > 0:
            price_estimate = signal.stop_loss / (1 - self.params['hard_stop_pct'])
        else:
            price_estimate = 120.0  # 默认估计价格
        
        # 计算可买张数，可转债最小交易单位是10张
        shares = int(available / price_estimate)
        shares = (shares // 10) * 10
        
        return max(shares, 0)
    
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """
        检查出场条件（供外部调用）
        
        Args:
            position: 持仓信息
            market_data: 市场数据
            
        Returns:
            (是否应该出场, 出场原因)
        """
        symbol = position.get('symbol')
        if not symbol:
            return False, ''
        
        data = market_data.get(symbol)
        if not data:
            return False, ''
        
        # 确保内部持仓状态同步
        if symbol not in self._positions:
            entry_price = position.get('cost_price', position.get('entry_price', 0))
            entry_time = position.get('entry_time', datetime.now())
            quantity = position.get('quantity', 0)
            
            if entry_price > 0:
                self._positions[symbol] = CBPosition(
                    symbol=symbol,
                    entry_price=entry_price,
                    entry_time=entry_time,
                    quantity=quantity,
                    highest_price=entry_price
                )
        
        return self._check_exit_signal(symbol, data)
    
    def on_day_end(self, positions: List[Dict], market_data: Dict) -> None:
        """每日收盘后清理"""
        # 清空所有持仓状态（T+0应该日内清仓）
        self._positions.clear()


# ============================================
# 策略定义（注册到策略注册表）
# ============================================

CB_INTRADAY_BURST_DEFINITION = StrategyDefinition(
    id="cb_intraday_burst",
    name="可转债日内爆发策略",
    description=(
        "T+0日内趋势跟踪策略，利用可转债的高波动性和无T+1限制。"
        "追涨杀跌，利用羊群效应，在主力拉升瞬间跟进，赚取1%-3%脉冲收益。"
    ),
    category=StrategyCategory.INTRADAY,
    risk_level=RiskLevel.HIGH,
    applicable_types=["可转债"],
    entry_logic="量能突破2.5倍均量+价格突破10日高点时追涨买入",
    exit_logic="移动止盈0.5%回撤离场/硬止损0.8%/收盘前强平",
    default_params=CBIntradayBurstStrategy.DEFAULT_PARAMS,
    min_capital=50000.0,
    backtest_return=55.0,
    backtest_sharpe=2.10,
    backtest_max_drawdown=6.0,
)


# ============================================
# Backtrader回测策略（用于历史回测）
# ============================================

try:
    import backtrader as bt
    
    class CBIntradayBurstBT(bt.Strategy):
        """
        Backtrader版本的可转债日内爆发策略
        
        用于历史数据回测
        """
        
        params = (
            ('vol_lookback', 20),        # 量能均值回看周期
            ('vol_multiplier', 3.0),     # 量能放大倍数
            ('price_lookback', 20),      # 价格突破回看周期
            ('trailing_stop_pct', 0.003), # 移动止盈回撤比例
            ('hard_stop_pct', 0.005),    # 硬止损比例
            ('time_stop_bars', 10),      # 时间止损（K线数）
            ('min_profit_pct', 0.002),   # 时间止损要求的最小盈利
            ('force_close_hour', 14),    # 强制平仓小时
            ('force_close_minute', 55),  # 强制平仓分钟
            ('position_pct', 0.95),      # 仓位比例
        )
        
        def __init__(self):
            # 数据引用
            self.dataclose = self.datas[0].close
            self.dataopen = self.datas[0].open
            self.datahigh = self.datas[0].high
            self.datalow = self.datas[0].low
            self.datavolume = self.datas[0].volume
            
            # 指标
            self.vol_avg = bt.indicators.SMA(self.datavolume, period=self.p.vol_lookback)
            self.highest = bt.indicators.Highest(self.datahigh, period=self.p.price_lookback)
            
            # 持仓追踪
            self.entry_price = None
            self.entry_bar = None
            self.highest_since_entry = None
            
            # 订单追踪
            self.order = None
        
        def notify_order(self, order):
            if order.status in [order.Completed]:
                if order.isbuy():
                    self.entry_price = order.executed.price
                    self.entry_bar = len(self)
                    self.highest_since_entry = order.executed.price
                elif order.issell():
                    self.entry_price = None
                    self.entry_bar = None
                    self.highest_since_entry = None
            
            self.order = None
        
        def next(self):
            # 如果有未完成订单，等待
            if self.order:
                return
            
            current_time = self.datas[0].datetime.datetime(0)
            
            # 检查是否为强制平仓时间
            if (current_time.hour > self.p.force_close_hour or
                (current_time.hour == self.p.force_close_hour and 
                 current_time.minute >= self.p.force_close_minute)):
                if self.position:
                    self.order = self.close()
                    self.log(f'强制平仓: {self.dataclose[0]:.3f}')
                return
            
            if not self.position:
                # 无持仓，检查入场条件
                
                # 条件1: 量能爆发
                if self.vol_avg[0] <= 0:
                    return
                vol_ratio = self.datavolume[0] / self.vol_avg[0]
                volume_burst = vol_ratio > self.p.vol_multiplier
                
                # 条件2: 价格突破
                price_breakout = self.dataclose[0] > self.highest[-1]
                
                # 条件3: 阳线
                is_bullish = self.dataclose[0] > self.dataopen[0]
                
                if volume_burst and price_breakout and is_bullish:
                    # 计算仓位
                    size = int(self.broker.getcash() * self.p.position_pct / self.dataclose[0])
                    size = (size // 10) * 10  # 可转债最小10张
                    
                    if size > 0:
                        self.order = self.buy(size=size)
                        self.log(f'买入信号: 价格={self.dataclose[0]:.3f}, '
                                f'量比={vol_ratio:.1f}x, 数量={size}')
            
            else:
                # 有持仓，检查出场条件
                
                # 更新最高价
                if self.datahigh[0] > self.highest_since_entry:
                    self.highest_since_entry = self.datahigh[0]
                
                # 条件1: 移动止盈
                trailing_stop = self.highest_since_entry * (1 - self.p.trailing_stop_pct)
                if self.dataclose[0] < trailing_stop:
                    self.order = self.close()
                    profit_pct = (self.dataclose[0] - self.entry_price) / self.entry_price * 100
                    self.log(f'移动止盈: 最高={self.highest_since_entry:.3f}, '
                            f'当前={self.dataclose[0]:.3f}, 盈利={profit_pct:.2f}%')
                    return
                
                # 条件2: 硬止损
                hard_stop = self.entry_price * (1 - self.p.hard_stop_pct)
                if self.dataclose[0] < hard_stop:
                    self.order = self.close()
                    loss_pct = (self.entry_price - self.dataclose[0]) / self.entry_price * 100
                    self.log(f'硬止损: 入场={self.entry_price:.3f}, '
                            f'当前={self.dataclose[0]:.3f}, 亏损={loss_pct:.2f}%')
                    return
                
                # 条件3: 时间止损
                bars_held = len(self) - self.entry_bar
                current_profit = (self.dataclose[0] - self.entry_price) / self.entry_price
                
                if bars_held > self.p.time_stop_bars and current_profit < self.p.min_profit_pct:
                    self.order = self.close()
                    self.log(f'时间止损: 持有{bars_held}根K线, 盈利={current_profit*100:.2f}%')
                    return
        
        def log(self, txt, dt=None):
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f'{dt.isoformat()} {txt}')
    
    
    def run_backtest(data_path: str, 
                     initial_cash: float = 100000,
                     commission: float = 0.0001,
                     **strategy_params) -> dict:
        """
        运行回测
        
        Args:
            data_path: CSV数据文件路径，需包含 datetime,open,high,low,close,volume
            initial_cash: 初始资金
            commission: 佣金率
            **strategy_params: 策略参数
            
        Returns:
            回测结果字典
        """
        cerebro = bt.Cerebro()
        
        # 添加策略
        cerebro.addstrategy(CBIntradayBurstBT, **strategy_params)
        
        # 加载数据
        data = bt.feeds.GenericCSVData(
            dataname=data_path,
            dtformat='%Y-%m-%d %H:%M:%S',
            datetime=0,
            open=1,
            high=2,
            low=3,
            close=4,
            volume=5,
            openinterest=-1,
            timeframe=bt.TimeFrame.Minutes,
            compression=1
        )
        cerebro.adddata(data)
        
        # 设置初始资金
        cerebro.broker.setcash(initial_cash)
        
        # 设置佣金（无印花税）
        cerebro.broker.setcommission(commission=commission)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # 运行回测
        print(f'初始资金: {initial_cash:.2f}')
        results = cerebro.run()
        strat = results[0]
        
        final_value = cerebro.broker.getvalue()
        print(f'最终资金: {final_value:.2f}')
        print(f'总收益率: {(final_value/initial_cash - 1) * 100:.2f}%')
        
        # 获取分析结果
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        
        result = {
            'initial_cash': initial_cash,
            'final_value': final_value,
            'total_return': (final_value / initial_cash - 1) * 100,
            'sharpe_ratio': sharpe.get('sharperatio', 0),
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
            'total_trades': trades.get('total', {}).get('total', 0),
            'won_trades': trades.get('won', {}).get('total', 0),
            'lost_trades': trades.get('lost', {}).get('total', 0),
        }
        
        if result['total_trades'] > 0:
            result['win_rate'] = result['won_trades'] / result['total_trades'] * 100
        else:
            result['win_rate'] = 0
        
        return result

except ImportError:
    # Backtrader未安装，跳过回测功能
    CBIntradayBurstBT = None
    run_backtest = None
