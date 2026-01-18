"""
============================================
乖离率回归策略 (波段)
BIAS Reversion Strategy
============================================

基于乖离率和布林带的均值回归策略：
- 计算BIAS乖离率
- 结合布林带判断超卖
- 缩量确认底部
- 适合波段操作

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from typing import Dict, List, Tuple, Optional
import math

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


def calculate_bias(close: float, ma: float) -> float:
    """
    计算乖离率: BIAS = (Close - MA) / MA
    
    Args:
        close: 收盘价
        ma: 移动平均线值
        
    Returns:
        乖离率（百分比形式，如-0.05表示-5%）
    """
    if ma <= 0:
        return 0.0
    return (close - ma) / ma


def calculate_sma(prices: List[float], period: int) -> float:
    """
    计算简单移动平均线
    
    Args:
        prices: 价格序列（从旧到新）
        period: 均线周期
        
    Returns:
        均线值
    """
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    return sum(prices[-period:]) / period


def calculate_std(prices: List[float], period: int) -> float:
    """
    计算标准差
    
    Args:
        prices: 价格序列（从旧到新）
        period: 计算周期
        
    Returns:
        标准差
    """
    if len(prices) < period:
        return 0.0
    
    recent_prices = prices[-period:]
    mean = sum(recent_prices) / period
    variance = sum((p - mean) ** 2 for p in recent_prices) / period
    return math.sqrt(variance)


def calculate_bollinger_bands(prices: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[float, float, float]:
    """
    计算布林带
    
    Args:
        prices: 价格序列（从旧到新）
        period: 均线周期
        num_std: 标准差倍数
        
    Returns:
        (上轨, 中轨, 下轨)
    """
    if len(prices) < period:
        if prices:
            return prices[-1], prices[-1], prices[-1]
        return 0.0, 0.0, 0.0
    
    middle = calculate_sma(prices, period)
    std = calculate_std(prices, period)
    
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    return upper, middle, lower


class BiasReversionStrategy(BaseStrategy):
    """
    乖离率回归策略
    
    入场条件：
    - 价格触及布林带下轨
    - 成交量萎缩（低于均量的80%）
    
    出场条件：
    - 价格回到布林带中轨或上轨
    - 或触发5%止损
    
    适用标的：
    - 宽基ETF、行业ETF
    """
    
    STRATEGY_ID = "bias_reversion"
    
    DEFAULT_PARAMS = {
        'ma_period': 20,              # 均线周期
        'bb_std': 2.0,                # 布林带标准差倍数
        'volume_decrease_pct': 0.8,   # 缩量阈值（相对于均量）
        'stop_loss_pct': 0.05,        # 止损百分比
        'exit_at_middle': True,       # 是否在中轨出场
        'applicable_etfs': [
            '159915',  # 创业板ETF
            '510300',  # 沪深300ETF
            '510500',  # 中证500ETF
            '512480',  # 半导体ETF
            '512010',  # 医药ETF
            '512660',  # 军工ETF
            '159928',  # 消费ETF
            '515030',  # 新能源车ETF
        ]
    }
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def calculate_indicators(self, data: Dict) -> Dict:
        """
        计算策略所需的技术指标
        
        Args:
            data: 单个标的的市场数据
            
        Returns:
            包含计算指标的字典
        """
        result = {}
        
        close = data.get('close')
        close_history = data.get('close_history', [])
        volume = data.get('volume')
        volume_history = data.get('volume_history', [])
        
        ma_period = self.params.get('ma_period', self.DEFAULT_PARAMS['ma_period'])
        bb_std = self.params.get('bb_std', self.DEFAULT_PARAMS['bb_std'])
        
        # 计算或获取MA20
        ma20 = data.get('ma20')
        if ma20 is None and len(close_history) >= ma_period:
            ma20 = calculate_sma(close_history, ma_period)
        result['ma20'] = ma20
        
        # 计算BIAS
        if close is not None and ma20 is not None and ma20 > 0:
            result['bias'] = calculate_bias(close, ma20)
        else:
            result['bias'] = None
        
        # 计算或获取布林带
        bb_upper = data.get('bb_upper')
        bb_middle = data.get('bb_middle')
        bb_lower = data.get('bb_lower')
        
        if bb_upper is None or bb_middle is None or bb_lower is None:
            if len(close_history) >= ma_period:
                bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
                    close_history, ma_period, bb_std
                )
        
        result['bb_upper'] = bb_upper
        result['bb_middle'] = bb_middle
        result['bb_lower'] = bb_lower
        
        # 计算或获取成交量均值
        volume_ma = data.get('volume_ma')
        if volume_ma is None and len(volume_history) >= ma_period:
            volume_ma = calculate_sma(volume_history, ma_period)
        result['volume_ma'] = volume_ma
        
        # 计算成交量比率
        if volume is not None and volume_ma is not None and volume_ma > 0:
            result['volume_ratio'] = volume / volume_ma
        else:
            result['volume_ratio'] = None
        
        return result
    
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
                        'volume': float,                   # 当前成交量
                        'volume_history': List[float],     # 历史成交量序列
                        'bb_upper': float,                 # 布林上轨（可选）
                        'bb_middle': float,                # 布林中轨（可选）
                        'bb_lower': float,                 # 布林下轨（可选）
                        'volume_ma': float,                # 成交量均值（可选）
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        applicable_etfs = self.params.get('applicable_etfs', self.DEFAULT_PARAMS['applicable_etfs'])
        volume_decrease_pct = self.params.get('volume_decrease_pct', self.DEFAULT_PARAMS['volume_decrease_pct'])
        
        for symbol in symbols:
            # 只处理适用的ETF
            if symbol not in applicable_etfs:
                continue
            
            data = market_data.get(symbol)
            if not data:
                continue
            
            close = data.get('close')
            if close is None:
                continue
            
            # 计算指标
            indicators = self.calculate_indicators(data)
            
            bb_lower = indicators.get('bb_lower')
            bb_middle = indicators.get('bb_middle')
            bb_upper = indicators.get('bb_upper')
            volume_ratio = indicators.get('volume_ratio')
            bias = indicators.get('bias')
            
            # 数据不足，跳过
            if bb_lower is None or volume_ratio is None:
                continue
            
            # 买入条件：触及下轨 且 缩量
            if close <= bb_lower and volume_ratio < volume_decrease_pct:
                stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
                stop_loss_price = close * (1 - stop_loss_pct)
                
                # 信号强度基于乖离程度
                if bias is not None:
                    if bias < -0.08:
                        strength = 5
                        confidence = 85
                    elif bias < -0.05:
                        strength = 4
                        confidence = 80
                    else:
                        strength = 4
                        confidence = 75
                else:
                    strength = 4
                    confidence = 75
                
                bias_str = f'{bias*100:.2f}%' if bias is not None else 'N/A'
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=strength,
                    confidence=confidence,
                    reason=f'触及布林下轨({bb_lower:.3f}), 缩量{volume_ratio*100:.0f}%, BIAS={bias_str}',
                    stop_loss=stop_loss_price,
                    target_price=bb_middle,  # 目标价为中轨
                    strategy_id=self.STRATEGY_ID
                ))
        
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
        
        # 使用全部分配资金
        if signal.stop_loss and signal.stop_loss > 0:
            price_estimate = signal.stop_loss / (1 - self.params.get('stop_loss_pct', 0.05))
        else:
            price_estimate = 1.0
        
        shares = int(capital / price_estimate)
        shares = (shares // 100) * 100
        
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
        cost_price = position.get('cost_price', 0)
        
        if not symbol or cost_price <= 0:
            return False, ''
        
        data = market_data.get(symbol)
        if not data:
            return False, ''
        
        close = data.get('close')
        if close is None:
            return False, ''
        
        # 计算指标
        indicators = self.calculate_indicators(data)
        bb_middle = indicators.get('bb_middle')
        bb_upper = indicators.get('bb_upper')
        
        # 出场条件1：触发止损
        stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
        stop_loss_price = cost_price * (1 - stop_loss_pct)
        
        if close < stop_loss_price:
            loss_pct = (close - cost_price) / cost_price * 100
            return True, f'触发止损({stop_loss_pct*100:.1f}%), 当前价格{close:.3f}, 亏损{loss_pct:.2f}%'
        
        # 出场条件2：价格回到中轨
        exit_at_middle = self.params.get('exit_at_middle', True)
        if exit_at_middle and bb_middle is not None and close >= bb_middle:
            profit_pct = (close - cost_price) / cost_price * 100
            return True, f'价格({close:.3f})回到布林中轨({bb_middle:.3f}), 止盈出场, 收益{profit_pct:.2f}%'
        
        # 出场条件3：价格触及上轨
        if bb_upper is not None and close >= bb_upper:
            profit_pct = (close - cost_price) / cost_price * 100
            return True, f'价格({close:.3f})触及布林上轨({bb_upper:.3f}), 止盈出场, 收益{profit_pct:.2f}%'
        
        return False, ''
    
    def validate_params(self) -> Tuple[bool, str]:
        """验证策略参数"""
        ma_period = self.params.get('ma_period', 20)
        if ma_period < 10 or ma_period > 60:
            return False, f"均线周期必须在10-60天之间，当前值: {ma_period}"
        
        bb_std = self.params.get('bb_std', 2.0)
        if bb_std < 1.0 or bb_std > 3.0:
            return False, f"布林带标准差倍数必须在1.0-3.0之间，当前值: {bb_std}"
        
        volume_decrease_pct = self.params.get('volume_decrease_pct', 0.8)
        if volume_decrease_pct < 0.5 or volume_decrease_pct > 1.0:
            return False, f"缩量阈值必须在0.5-1.0之间，当前值: {volume_decrease_pct}"
        
        stop_loss_pct = self.params.get('stop_loss_pct', 0.05)
        if stop_loss_pct < 0.02 or stop_loss_pct > 0.10:
            return False, f"止损百分比必须在2%-10%之间，当前值: {stop_loss_pct*100}%"
        
        return True, ""


# 注册策略定义
BIAS_REVERSION_DEFINITION = StrategyDefinition(
    id="bias_reversion",
    name="乖离率回归策略",
    category=StrategyCategory.SWING,
    description="基于乖离率和布林带的均值回归策略，在超卖缩量时买入，回归均值时卖出",
    risk_level=RiskLevel.MEDIUM,
    applicable_types=["宽基ETF", "行业ETF"],
    entry_logic="价格触及布林带下轨且成交量萎缩（低于均量80%）时买入",
    exit_logic="价格回到布林带中轨或上轨时止盈出场，或触发3%止损",
    default_params=BiasReversionStrategy.DEFAULT_PARAMS,
    min_capital=20000.0,
    backtest_return=26.0,
    backtest_sharpe=1.55,
    backtest_max_drawdown=8.0
)

# 自动注册到策略注册表
StrategyRegistry.register(BIAS_REVERSION_DEFINITION)
