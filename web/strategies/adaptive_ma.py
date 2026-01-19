"""
============================================
自适应均线择时策略 (长线)
Adaptive Moving Average Timing Strategy
============================================

基于均线的市场择时策略：
- 监控基准指数与均线的关系
- 牛市持有股票ETF，熊市持有现金/债券ETF
- 支持可配置的均线周期
- 实现缓冲区逻辑避免频繁切换

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


class MarketRegime(Enum):
    """市场状态"""
    BULL = "bull"      # 牛市（指数在均线上方）
    BEAR = "bear"      # 熊市（指数在均线下方）
    NEUTRAL = "neutral"  # 中性（在缓冲区内）


def calculate_moving_average(close_history: List[float], period: int) -> Optional[float]:
    """
    计算移动平均线
    
    Args:
        close_history: 历史收盘价序列
        period: 均线周期
        
    Returns:
        移动平均值，如果数据不足返回None
    """
    if len(close_history) < period:
        return None
    
    prices = close_history[-period:]
    return sum(prices) / len(prices)


def determine_market_regime(current_price: float, 
                            ma_value: float, 
                            buffer_pct: float = 0.01,
                            previous_regime: MarketRegime = None) -> MarketRegime:
    """
    判断市场状态
    
    Args:
        current_price: 当前价格
        ma_value: 均线值
        buffer_pct: 缓冲区百分比（默认1%）
        previous_regime: 前一个市场状态（用于缓冲区逻辑）
        
    Returns:
        当前市场状态
    """
    if ma_value <= 0:
        return MarketRegime.NEUTRAL
    
    # 计算价格相对均线的偏离度
    deviation = (current_price - ma_value) / ma_value
    
    # 上轨和下轨
    upper_buffer = buffer_pct
    lower_buffer = -buffer_pct
    
    if deviation > upper_buffer:
        return MarketRegime.BULL
    elif deviation < lower_buffer:
        return MarketRegime.BEAR
    else:
        # 在缓冲区内，保持前一状态（避免频繁切换）
        if previous_regime:
            return previous_regime
        # 如果没有前状态，根据偏离方向判断
        return MarketRegime.BULL if deviation >= 0 else MarketRegime.BEAR


def generate_timing_signal(current_regime: MarketRegime, 
                           previous_regime: MarketRegime) -> str:
    """
    生成择时信号
    
    Args:
        current_regime: 当前市场状态
        previous_regime: 前一市场状态
        
    Returns:
        信号类型: 'enter_equity', 'exit_equity', 'hold'
    """
    if current_regime == previous_regime:
        return 'hold'
    
    if current_regime == MarketRegime.BULL and previous_regime == MarketRegime.BEAR:
        return 'enter_equity'
    elif current_regime == MarketRegime.BEAR and previous_regime == MarketRegime.BULL:
        return 'exit_equity'
    
    return 'hold'


class AdaptiveMAStrategy(BaseStrategy):
    """
    自适应均线择时策略
    
    入场条件：
    - 基准指数站上均线（超过缓冲区）
    - 信号为进入股票市场
    
    出场条件：
    - 基准指数跌破均线（超过缓冲区）
    - 信号为退出股票市场
    
    适用标的：
    - 股票ETF（牛市持有）
    - 债券ETF/货币ETF（熊市持有）
    """
    
    STRATEGY_ID = "adaptive_ma"
    
    DEFAULT_PARAMS = {
        'ma_period': 60,              # 均线周期（天）
        'buffer_pct': 0.01,           # 缓冲区百分比（1%）
        'benchmark_symbol': '000300',  # 基准指数代码（沪深300）
        'equity_etfs': [
            '510300',   # 沪深300ETF
            '510500',   # 中证500ETF
            '159915',   # 创业板ETF
        ],
        'safe_etfs': [
            '511010',   # 国债ETF
            '511880',   # 银华日利（货币ETF）
        ],
        'equity_weight': 0.8,         # 牛市时股票ETF配置比例
        'safe_weight': 0.2,           # 牛市时安全资产配置比例
    }
    
    def __init__(self, params: Dict = None):
        super().__init__(params)
        self._previous_regime: MarketRegime = None
        self._current_regime: MarketRegime = None
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def get_benchmark_data(self, market_data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """
        获取基准指数数据
        
        Args:
            market_data: 市场数据
            
        Returns:
            (当前价格, 均线值)
        """
        benchmark = self.params.get('benchmark_symbol', self.DEFAULT_PARAMS['benchmark_symbol'])
        ma_period = self.params.get('ma_period', self.DEFAULT_PARAMS['ma_period'])
        
        data = market_data.get(benchmark)
        if not data:
            return None, None
        
        current_price = data.get('close')
        
        # 优先使用预计算的均线值
        ma_key = f'ma_{ma_period}'
        ma_value = data.get(ma_key)
        
        if ma_value is None:
            # 从历史数据计算
            close_history = data.get('close_history', [])
            ma_value = calculate_moving_average(close_history, ma_period)
        
        return current_price, ma_value
    
    def update_market_regime(self, market_data: Dict) -> MarketRegime:
        """
        更新市场状态
        
        Args:
            market_data: 市场数据
            
        Returns:
            当前市场状态
        """
        current_price, ma_value = self.get_benchmark_data(market_data)
        
        if current_price is None or ma_value is None:
            # 数据不足，保持中性
            if self._current_regime:
                return self._current_regime
            return MarketRegime.NEUTRAL
        
        buffer_pct = self.params.get('buffer_pct', self.DEFAULT_PARAMS['buffer_pct'])
        
        # 保存前一状态
        self._previous_regime = self._current_regime
        
        # 判断当前状态
        self._current_regime = determine_market_regime(
            current_price, ma_value, buffer_pct, self._previous_regime
        )
        
        return self._current_regime
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            symbols: 标的代码列表
            market_data: 市场数据，格式为:
                {
                    symbol: {
                        'close': float,                    # 当前收盘价
                        'close_history': List[float],      # 历史收盘价序列
                        'ma_60': float,                    # 60日均线（可选）
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        
        # 更新市场状态
        current_regime = self.update_market_regime(market_data)
        
        current_price, ma_value = self.get_benchmark_data(market_data)
        
        if current_price is None or ma_value is None:
            return signals
        
        # 生成择时信号
        timing_signal = 'hold'
        if self._previous_regime:
            timing_signal = generate_timing_signal(current_regime, self._previous_regime)
        else:
            # 首次运行，根据当前状态决定
            timing_signal = 'enter_equity' if current_regime == MarketRegime.BULL else 'exit_equity'
        
        equity_etfs = self.params.get('equity_etfs', self.DEFAULT_PARAMS['equity_etfs'])
        safe_etfs = self.params.get('safe_etfs', self.DEFAULT_PARAMS['safe_etfs'])
        equity_weight = self.params.get('equity_weight', self.DEFAULT_PARAMS['equity_weight'])
        safe_weight = self.params.get('safe_weight', self.DEFAULT_PARAMS['safe_weight'])
        
        deviation = (current_price - ma_value) / ma_value * 100
        
        if timing_signal == 'enter_equity':
            # 进入股票市场
            # 买入股票ETF
            per_equity_weight = equity_weight / len(equity_etfs) if equity_etfs else 0
            for symbol in equity_etfs:
                data = market_data.get(symbol, {})
                price = data.get('close', 0)
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=4,
                    confidence=80,
                    reason=f'均线择时转牛: 指数{current_price:.2f}站上{self.params.get("ma_period")}日均线{ma_value:.2f}, 偏离{deviation:.2f}%',
                    target_price=price,
                    strategy_id=self.STRATEGY_ID
                ))
            
            # 卖出安全资产
            for symbol in safe_etfs:
                data = market_data.get(symbol, {})
                price = data.get('close', 0)
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='sell',
                    strength=3,
                    confidence=75,
                    reason=f'均线择时转牛: 减持安全资产，增持股票ETF',
                    target_price=price,
                    strategy_id=self.STRATEGY_ID
                ))
                
        elif timing_signal == 'exit_equity':
            # 退出股票市场
            # 卖出股票ETF
            for symbol in equity_etfs:
                data = market_data.get(symbol, {})
                price = data.get('close', 0)
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='sell',
                    strength=4,
                    confidence=80,
                    reason=f'均线择时转熊: 指数{current_price:.2f}跌破{self.params.get("ma_period")}日均线{ma_value:.2f}, 偏离{deviation:.2f}%',
                    target_price=price,
                    strategy_id=self.STRATEGY_ID
                ))
            
            # 买入安全资产
            per_safe_weight = 1.0 / len(safe_etfs) if safe_etfs else 0
            for symbol in safe_etfs:
                data = market_data.get(symbol, {})
                price = data.get('close', 0)
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=3,
                    confidence=75,
                    reason=f'均线择时转熊: 增持安全资产，规避风险',
                    target_price=price,
                    strategy_id=self.STRATEGY_ID
                ))
        
        # hold状态不生成信号
        
        return signals
    
    def calculate_position_size(self, signal: Signal, capital: float) -> int:
        """
        计算建议仓位
        
        Args:
            signal: 交易信号
            capital: 可用资金
            
        Returns:
            建议买入数量（份数）
        """
        if signal.signal_type != 'buy' or capital <= 0:
            return 0
        
        equity_etfs = self.params.get('equity_etfs', self.DEFAULT_PARAMS['equity_etfs'])
        safe_etfs = self.params.get('safe_etfs', self.DEFAULT_PARAMS['safe_etfs'])
        equity_weight = self.params.get('equity_weight', self.DEFAULT_PARAMS['equity_weight'])
        
        # 判断是股票ETF还是安全资产
        if signal.symbol in equity_etfs:
            # 股票ETF等分equity_weight
            per_position_weight = equity_weight / len(equity_etfs)
        elif signal.symbol in safe_etfs:
            # 安全资产等分剩余权重
            per_position_weight = (1 - equity_weight) / len(safe_etfs) if safe_etfs else 0
        else:
            per_position_weight = 0.1  # 默认10%
        
        position_capital = capital * per_position_weight
        
        # 使用信号中的目标价格
        price = signal.target_price if signal.target_price and signal.target_price > 0 else 1.0
        
        shares = int(position_capital / price)
        shares = (shares // 100) * 100  # 取整到100的倍数
        
        return max(shares, 0)
    
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """
        检查出场条件
        
        Args:
            position: 持仓信息
            market_data: 市场数据
            
        Returns:
            (是否应该出场, 出场原因)
        """
        symbol = position.get('symbol')
        
        if not symbol:
            return False, ''
        
        equity_etfs = self.params.get('equity_etfs', self.DEFAULT_PARAMS['equity_etfs'])
        safe_etfs = self.params.get('safe_etfs', self.DEFAULT_PARAMS['safe_etfs'])
        
        # 更新市场状态
        current_regime = self.update_market_regime(market_data)
        
        current_price, ma_value = self.get_benchmark_data(market_data)
        
        if current_price is None or ma_value is None:
            return False, ''
        
        deviation = (current_price - ma_value) / ma_value * 100
        ma_period = self.params.get('ma_period', self.DEFAULT_PARAMS['ma_period'])
        
        # 如果持有股票ETF且市场转熊，需要卖出
        if symbol in equity_etfs and current_regime == MarketRegime.BEAR:
            return True, f'均线择时转熊: 指数{current_price:.2f}跌破{ma_period}日均线{ma_value:.2f}, 偏离{deviation:.2f}%'
        
        # 如果持有安全资产且市场转牛，需要卖出
        if symbol in safe_etfs and current_regime == MarketRegime.BULL:
            return True, f'均线择时转牛: 指数{current_price:.2f}站上{ma_period}日均线{ma_value:.2f}, 偏离{deviation:.2f}%'
        
        return False, ''
    
    def validate_params(self) -> Tuple[bool, str]:
        """验证策略参数"""
        ma_period = self.params.get('ma_period', 60)
        if ma_period not in [20, 60, 120]:
            # 允许自定义周期，但范围受限
            if ma_period < 10 or ma_period > 250:
                return False, f"均线周期必须在10-250天之间，当前值: {ma_period}"
        
        buffer_pct = self.params.get('buffer_pct', 0.01)
        if buffer_pct < 0.005 or buffer_pct > 0.05:
            return False, f"缓冲区必须在0.5%-5%之间，当前值: {buffer_pct*100}%"
        
        equity_etfs = self.params.get('equity_etfs', [])
        if len(equity_etfs) < 1:
            return False, f"至少需要配置1只股票ETF，当前数量: {len(equity_etfs)}"
        
        safe_etfs = self.params.get('safe_etfs', [])
        if len(safe_etfs) < 1:
            return False, f"至少需要配置1只安全资产ETF，当前数量: {len(safe_etfs)}"
        
        equity_weight = self.params.get('equity_weight', 0.8)
        if equity_weight < 0.5 or equity_weight > 1.0:
            return False, f"股票权重必须在50%-100%之间，当前值: {equity_weight*100}%"
        
        return True, ""
    
    def get_applicable_symbols(self) -> List[str]:
        """获取适用的标的列表"""
        equity_etfs = self.params.get('equity_etfs', self.DEFAULT_PARAMS['equity_etfs'])
        safe_etfs = self.params.get('safe_etfs', self.DEFAULT_PARAMS['safe_etfs'])
        return equity_etfs + safe_etfs
    
    def get_current_regime(self) -> Optional[MarketRegime]:
        """获取当前市场状态"""
        return self._current_regime


# 注册策略定义
ADAPTIVE_MA_DEFINITION = StrategyDefinition(
    id="adaptive_ma",
    name="自适应均线择时策略",
    category=StrategyCategory.LONG_TERM,
    description="基于均线的市场择时策略，牛市持有股票ETF，熊市持有债券/货币ETF",
    risk_level=RiskLevel.MEDIUM,
    applicable_types=["宽基ETF", "债券ETF", "货币ETF"],
    entry_logic="基准指数站上20日均线（超过0.5%缓冲区）时买入股票ETF",
    exit_logic="基准指数跌破均线（超过0.5%缓冲区）时卖出股票ETF，买入债券ETF",
    default_params=AdaptiveMAStrategy.DEFAULT_PARAMS,
    min_capital=30000.0,
    backtest_return=None,  # 点击回测获取真实数据
    backtest_sharpe=None,
    backtest_max_drawdown=None,
    backtest_win_rate=None,
)

# 自动注册到策略注册表
StrategyRegistry.register(ADAPTIVE_MA_DEFINITION)
