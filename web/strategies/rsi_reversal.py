"""
============================================
RSI极限反转策略 (短线)
RSI Extreme Reversal Strategy
============================================

基于Connors RSI的短线反转策略：
- 使用2日RSI捕捉极度超卖
- 结合200日均线确认长期趋势
- 5日均线作为出场信号
- 3%止损保护

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    计算RSI指标
    
    Args:
        prices: 价格序列（从旧到新）
        period: RSI周期
        
    Returns:
        RSI值 (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # 数据不足时返回中性值
    
    series = pd.Series(prices)
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 避免除零
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    result = rsi.iloc[-1]
    return float(result) if not pd.isna(result) else 50.0


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


class RSIReversalStrategy(BaseStrategy):
    """
    RSI极限反转策略
    
    入场条件：
    - 价格在200日均线上方（确认长期上升趋势）
    - 2日RSI < 10（极度超卖）
    
    出场条件：
    - 收盘价高于5日均线（短期反弹完成）
    - 或触发3%止损
    
    适用标的：
    - 高流动性宽基ETF（创业板ETF、沪深300ETF等）
    """
    
    STRATEGY_ID = "rsi_reversal"
    
    DEFAULT_PARAMS = {
        'rsi_period': 2,           # RSI周期
        'rsi_oversold': 10,        # RSI超卖阈值
        'ma_long_period': 200,     # 长期均线周期
        'ma_exit_period': 5,       # 出场均线周期
        'stop_loss_pct': 0.03,     # 止损百分比
        'applicable_etfs': [
            '159915.SZ',  # 创业板ETF
            '510300.SH',  # 沪深300ETF
            '510500.SH',  # 中证500ETF
            '159919.SZ',  # 沪深300ETF
            '510050.SH',  # 上证50ETF
            '159901.SZ',  # 深100ETF
        ]
    }
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            symbols: 标的代码列表
            market_data: 市场数据，格式为:
                {
                    symbol: {
                        'close': float,           # 当前收盘价
                        'close_history': List[float],  # 历史收盘价序列
                        'ma200': float,           # 200日均线（可选，会自动计算）
                        'ma5': float,             # 5日均线（可选，会自动计算）
                        'rsi2': float,            # 2日RSI（可选，会自动计算）
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        applicable_etfs = self.params.get('applicable_etfs', self.DEFAULT_PARAMS['applicable_etfs'])
        
        for symbol in symbols:
            # 只处理适用的ETF
            if symbol not in applicable_etfs:
                continue
            
            data = market_data.get(symbol)
            if not data:
                continue
            
            # 获取或计算指标
            close = data.get('close')
            if close is None:
                continue
            
            # 获取历史价格用于计算指标
            close_history = data.get('close_history', [])
            
            # 获取或计算200日均线
            ma200 = data.get('ma200')
            if ma200 is None and len(close_history) >= self.params['ma_long_period']:
                ma200 = calculate_sma(close_history, self.params['ma_long_period'])
            
            # 获取或计算2日RSI
            rsi2 = data.get('rsi2')
            if rsi2 is None and len(close_history) >= self.params['rsi_period'] + 1:
                rsi2 = calculate_rsi(close_history, self.params['rsi_period'])
            
            # 数据不足，跳过
            if ma200 is None or rsi2 is None:
                continue
            
            # 买入条件：价格在200日均线上方 且 2日RSI < 10
            rsi_threshold = self.params.get('rsi_oversold', self.DEFAULT_PARAMS['rsi_oversold'])
            
            if close > ma200 and rsi2 < rsi_threshold:
                stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
                stop_loss_price = close * (1 - stop_loss_pct)
                
                # 信号强度基于RSI超卖程度
                if rsi2 < 5:
                    strength = 5
                    confidence = 90
                elif rsi2 < 8:
                    strength = 4
                    confidence = 85
                else:
                    strength = 4
                    confidence = 80
                
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=strength,
                    confidence=confidence,
                    reason=f'RSI极度超卖({rsi2:.1f}), 价格({close:.3f})在MA200({ma200:.3f})上方',
                    stop_loss=stop_loss_price,
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
            建议买入数量（份数，ETF通常100份为1手）
        """
        if signal.signal_type != 'buy' or capital <= 0:
            return 0
        
        # 使用全部分配资金
        # ETF价格通常较低，按100份为单位计算
        if signal.stop_loss and signal.stop_loss > 0:
            # 基于止损计算仓位（风险控制）
            price_estimate = signal.stop_loss / (1 - self.params.get('stop_loss_pct', 0.03))
        else:
            price_estimate = 1.0  # 默认估计
        
        # 计算可买数量，向下取整到100的倍数
        shares = int(capital / price_estimate)
        shares = (shares // 100) * 100
        
        return max(shares, 0)
    
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """
        检查出场条件
        
        Args:
            position: 持仓信息，包含:
                - symbol: 标的代码
                - cost_price: 成本价
                - quantity: 持仓数量
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
        
        # 获取或计算5日均线
        ma5 = data.get('ma5')
        close_history = data.get('close_history', [])
        if ma5 is None and len(close_history) >= self.params['ma_exit_period']:
            ma5 = calculate_sma(close_history, self.params['ma_exit_period'])
        
        # 出场条件1：收盘价高于5日均线（止盈）
        if ma5 is not None and close > ma5:
            profit_pct = (close - cost_price) / cost_price * 100
            return True, f'价格({close:.3f})突破5日均线({ma5:.3f}), 止盈出场, 收益{profit_pct:.2f}%'
        
        # 出场条件2：触发止损
        stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
        stop_loss_price = cost_price * (1 - stop_loss_pct)
        
        if close < stop_loss_price:
            loss_pct = (close - cost_price) / cost_price * 100
            return True, f'触发止损({stop_loss_pct*100:.1f}%), 当前价格{close:.3f}, 亏损{loss_pct:.2f}%'
        
        return False, ''
    
    def validate_params(self) -> Tuple[bool, str]:
        """验证策略参数"""
        rsi_period = self.params.get('rsi_period', 2)
        if rsi_period < 1 or rsi_period > 14:
            return False, f"RSI周期必须在1-14之间，当前值: {rsi_period}"
        
        rsi_oversold = self.params.get('rsi_oversold', 10)
        if rsi_oversold < 1 or rsi_oversold > 30:
            return False, f"RSI超卖阈值必须在1-30之间，当前值: {rsi_oversold}"
        
        stop_loss_pct = self.params.get('stop_loss_pct', 0.03)
        if stop_loss_pct < 0.01 or stop_loss_pct > 0.10:
            return False, f"止损百分比必须在1%-10%之间，当前值: {stop_loss_pct*100}%"
        
        return True, ""


# 注册策略定义
RSI_REVERSAL_DEFINITION = StrategyDefinition(
    id="rsi_reversal",
    name="RSI极限反转策略",
    category=StrategyCategory.SHORT_TERM,
    description="基于Connors RSI的短线反转策略，在极度超卖时买入，短期反弹后卖出",
    risk_level=RiskLevel.HIGH,
    applicable_types=["宽基ETF", "高流动性ETF"],
    entry_logic="价格在200日均线上方（确认长期上升趋势）且2日RSI<10（极度超卖）时买入",
    exit_logic="收盘价高于5日均线时止盈出场，或触发2%止损",
    default_params=RSIReversalStrategy.DEFAULT_PARAMS,
    min_capital=10000.0,
    backtest_return=None,  # 点击回测获取真实数据
    backtest_sharpe=None,
    backtest_max_drawdown=None,
    backtest_win_rate=None,
)

# 自动注册到策略注册表
StrategyRegistry.register(RSI_REVERSAL_DEFINITION)
