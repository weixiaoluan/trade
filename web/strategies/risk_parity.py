"""
============================================
风险平价策略 (长线)
Risk Parity Strategy
============================================

基于风险平价的资产配置策略：
- 配置股票ETF、债券ETF、黄金ETF
- 计算60日滚动波动率
- 按波动率倒数分配权重
- 月度再平衡

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import math

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


def calculate_rolling_volatility(close_history: List[float], period: int = 60) -> Optional[float]:
    """
    计算滚动波动率（年化）
    
    Args:
        close_history: 历史收盘价序列
        period: 计算周期（天）
        
    Returns:
        年化波动率（标准差），如果数据不足返回None
    """
    if len(close_history) < period + 1:
        return None
    
    # 计算日收益率
    prices = close_history[-(period + 1):]
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            daily_return = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(daily_return)
    
    if len(returns) < period:
        return None
    
    # 计算标准差
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    daily_vol = math.sqrt(variance)
    
    # 年化波动率（假设252个交易日）
    annual_vol = daily_vol * math.sqrt(252)
    
    return annual_vol


def calculate_risk_parity_weights(volatilities: Dict[str, float], min_weight: float = 0.1) -> Dict[str, float]:
    """
    计算风险平价权重
    
    公式: Weight_i = (1/σ_i) / Σ(1/σ_j)
    
    Args:
        volatilities: 各资产波动率字典 {symbol: volatility}
        min_weight: 最小配置权重（默认10%）
        
    Returns:
        各资产权重字典 {symbol: weight}
    """
    if not volatilities:
        return {}
    
    # 过滤掉无效波动率
    valid_vols = {s: v for s, v in volatilities.items() if v and v > 0}
    
    if not valid_vols:
        # 如果没有有效波动率数据，等权分配
        n = len(volatilities)
        return {s: 1.0 / n for s in volatilities}
    
    # 计算波动率倒数
    inv_vols = {s: 1.0 / v for s, v in valid_vols.items()}
    
    # 计算总和
    total_inv_vol = sum(inv_vols.values())
    
    if total_inv_vol <= 0:
        n = len(valid_vols)
        return {s: 1.0 / n for s in valid_vols}
    
    # 计算初始权重
    weights = {s: inv_v / total_inv_vol for s, inv_v in inv_vols.items()}
    
    # 应用最小权重约束
    n = len(weights)
    if min_weight > 0 and n > 0:
        # 确保每个资产至少有min_weight的配置
        total_min = min_weight * n
        if total_min <= 1.0:
            # 找出低于最小权重的资产
            below_min = {s: w for s, w in weights.items() if w < min_weight}
            above_min = {s: w for s, w in weights.items() if w >= min_weight}
            
            if below_min:
                # 将低于最小权重的资产提升到最小权重
                adjustment_needed = sum(min_weight - w for w in below_min.values())
                
                if above_min:
                    # 从高于最小权重的资产中等比例扣减
                    total_above = sum(above_min.values())
                    for s in below_min:
                        weights[s] = min_weight
                    for s in above_min:
                        reduction_ratio = adjustment_needed / total_above
                        weights[s] = max(min_weight, above_min[s] * (1 - reduction_ratio))
                else:
                    # 所有资产都低于最小权重，等权分配
                    for s in weights:
                        weights[s] = 1.0 / n
    
    # 归一化确保总和为1
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {s: w / total_weight for s, w in weights.items()}
    
    return weights


def check_rebalance_needed(current_weights: Dict[str, float], 
                           target_weights: Dict[str, float], 
                           threshold: float = 0.05) -> bool:
    """
    检查是否需要再平衡
    
    Args:
        current_weights: 当前权重
        target_weights: 目标权重
        threshold: 偏离阈值（默认5%）
        
    Returns:
        是否需要再平衡
    """
    if not current_weights or not target_weights:
        return True
    
    for symbol in target_weights:
        current = current_weights.get(symbol, 0)
        target = target_weights[symbol]
        if abs(current - target) > threshold:
            return True
    
    return False


class RiskParityStrategy(BaseStrategy):
    """
    风险平价策略
    
    入场条件：
    - 按风险平价权重配置多类资产
    - 月度或偏离超阈值时再平衡
    
    出场条件：
    - 资产权重偏离目标超过阈值
    - 需要调仓到其他资产
    
    适用标的：
    - 股票ETF（沪深300、中证500等）
    - 债券ETF（国债、企业债等）
    - 黄金ETF
    """
    
    STRATEGY_ID = "risk_parity"
    
    DEFAULT_PARAMS = {
        'volatility_period': 60,        # 波动率计算周期（天）
        'rebalance_threshold': 0.05,    # 再平衡阈值（5%）
        'min_weight': 0.10,             # 最小配置权重（10%）
        'asset_classes': {
            'equity': [
                '510300',   # 沪深300ETF
                '510500',   # 中证500ETF
            ],
            'bond': [
                '511010',   # 国债ETF
                '511260',   # 十年国债ETF
            ],
            'gold': [
                '518880',   # 黄金ETF
            ]
        },
        'class_targets': {
            'equity': 0.40,  # 股票类目标配置40%
            'bond': 0.40,    # 债券类目标配置40%
            'gold': 0.20,    # 黄金类目标配置20%
        }
    }
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def get_all_symbols(self) -> List[str]:
        """获取所有配置的ETF代码"""
        asset_classes = self.params.get('asset_classes', self.DEFAULT_PARAMS['asset_classes'])
        symbols = []
        for etfs in asset_classes.values():
            symbols.extend(etfs)
        return symbols
    
    def calculate_asset_volatilities(self, market_data: Dict) -> Dict[str, float]:
        """
        计算所有资产的波动率
        
        Args:
            market_data: 市场数据
            
        Returns:
            各资产波动率字典
        """
        volatility_period = self.params.get('volatility_period', self.DEFAULT_PARAMS['volatility_period'])
        volatilities = {}
        
        for symbol in self.get_all_symbols():
            data = market_data.get(symbol)
            if not data:
                continue
            
            # 优先使用预计算的波动率
            vol = data.get('volatility_60d')
            if vol is None:
                # 从历史数据计算
                close_history = data.get('close_history', [])
                vol = calculate_rolling_volatility(close_history, volatility_period)
            
            if vol is not None and vol > 0:
                volatilities[symbol] = vol
        
        return volatilities
    
    def calculate_target_weights(self, market_data: Dict) -> Dict[str, float]:
        """
        计算目标权重（风险平价）
        
        Args:
            market_data: 市场数据
            
        Returns:
            各资产目标权重
        """
        asset_classes = self.params.get('asset_classes', self.DEFAULT_PARAMS['asset_classes'])
        class_targets = self.params.get('class_targets', self.DEFAULT_PARAMS['class_targets'])
        min_weight = self.params.get('min_weight', self.DEFAULT_PARAMS['min_weight'])
        
        # 计算各资产波动率
        volatilities = self.calculate_asset_volatilities(market_data)
        
        # 按资产类别计算风险平价权重，然后在类别内部再分配
        target_weights = {}
        
        for asset_class, etfs in asset_classes.items():
            class_weight = class_targets.get(asset_class, 1.0 / len(asset_classes))
            
            # 获取该类别内资产的波动率
            class_vols = {s: volatilities.get(s, 0.15) for s in etfs}  # 默认15%波动率
            
            # 计算类别内风险平价权重
            inner_weights = calculate_risk_parity_weights(class_vols, min_weight=0)
            
            # 分配到总权重
            for symbol, inner_weight in inner_weights.items():
                target_weights[symbol] = class_weight * inner_weight
        
        # 应用最小权重约束
        n = len(target_weights)
        if n > 0 and min_weight > 0:
            for symbol in target_weights:
                if target_weights[symbol] < min_weight:
                    target_weights[symbol] = min_weight
            
            # 归一化
            total = sum(target_weights.values())
            if total > 0:
                target_weights = {s: w / total for s, w in target_weights.items()}
        
        return target_weights
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            symbols: 标的代码列表（此策略主要使用内置资产池）
            market_data: 市场数据，格式为:
                {
                    symbol: {
                        'close': float,                    # 当前收盘价
                        'close_history': List[float],      # 历史收盘价序列
                        'volatility_60d': float,           # 60日波动率（可选）
                        'current_weight': float,           # 当前持仓权重（可选）
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        
        # 计算目标权重
        target_weights = self.calculate_target_weights(market_data)
        
        if not target_weights:
            return signals
        
        # 获取当前权重（如果有）
        current_weights = {}
        for symbol in target_weights:
            data = market_data.get(symbol)
            if data:
                current_weights[symbol] = data.get('current_weight', 0)
        
        rebalance_threshold = self.params.get('rebalance_threshold', self.DEFAULT_PARAMS['rebalance_threshold'])
        
        # 检查是否需要再平衡
        need_rebalance = check_rebalance_needed(current_weights, target_weights, rebalance_threshold)
        
        if not need_rebalance and current_weights:
            # 不需要再平衡，返回hold信号
            return signals
        
        # 生成调仓信号
        for symbol, target_weight in target_weights.items():
            current_weight = current_weights.get(symbol, 0)
            weight_diff = target_weight - current_weight
            
            data = market_data.get(symbol, {})
            current_price = data.get('close', 0)
            
            if abs(weight_diff) < 0.01:
                # 权重变化太小，忽略
                continue
            
            if weight_diff > 0:
                # 需要买入
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=min(5, int(abs(weight_diff) * 20) + 2),  # 根据调仓幅度确定强度
                    confidence=80,
                    reason=f'风险平价再平衡: 目标权重{target_weight*100:.1f}%, 当前{current_weight*100:.1f}%, 需增配{weight_diff*100:.1f}%',
                    target_price=current_price,
                    strategy_id=self.STRATEGY_ID
                ))
            else:
                # 需要卖出
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='sell',
                    strength=min(5, int(abs(weight_diff) * 20) + 2),
                    confidence=80,
                    reason=f'风险平价再平衡: 目标权重{target_weight*100:.1f}%, 当前{current_weight*100:.1f}%, 需减配{abs(weight_diff)*100:.1f}%',
                    target_price=current_price,
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
        
        # 从信号原因中解析目标权重
        # 格式: "风险平价再平衡: 目标权重XX.X%, ..."
        target_weight = 0.2  # 默认20%
        
        if '目标权重' in signal.reason:
            try:
                import re
                match = re.search(r'目标权重(\d+\.?\d*)%', signal.reason)
                if match:
                    target_weight = float(match.group(1)) / 100
            except:
                pass
        
        # 计算该资产应分配的资金
        position_capital = capital * target_weight
        
        # 假设ETF价格，实际应从market_data获取
        estimated_price = signal.target_price if signal.target_price and signal.target_price > 0 else 1.0
        
        shares = int(position_capital / estimated_price)
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
        
        # 计算目标权重
        target_weights = self.calculate_target_weights(market_data)
        
        if symbol not in target_weights:
            return True, f'资产{symbol}不在配置池中，建议清仓'
        
        # 获取当前权重
        data = market_data.get(symbol, {})
        current_weight = data.get('current_weight', 0)
        target_weight = target_weights.get(symbol, 0)
        
        rebalance_threshold = self.params.get('rebalance_threshold', self.DEFAULT_PARAMS['rebalance_threshold'])
        
        # 如果当前权重显著高于目标，需要减仓
        if current_weight - target_weight > rebalance_threshold:
            return True, f'当前权重{current_weight*100:.1f}%高于目标{target_weight*100:.1f}%，需要减仓再平衡'
        
        return False, ''
    
    def validate_params(self) -> Tuple[bool, str]:
        """验证策略参数"""
        volatility_period = self.params.get('volatility_period', 60)
        if volatility_period < 20 or volatility_period > 120:
            return False, f"波动率周期必须在20-120天之间，当前值: {volatility_period}"
        
        rebalance_threshold = self.params.get('rebalance_threshold', 0.05)
        if rebalance_threshold < 0.02 or rebalance_threshold > 0.15:
            return False, f"再平衡阈值必须在2%-15%之间，当前值: {rebalance_threshold*100}%"
        
        min_weight = self.params.get('min_weight', 0.10)
        if min_weight < 0 or min_weight > 0.3:
            return False, f"最小权重必须在0%-30%之间，当前值: {min_weight*100}%"
        
        asset_classes = self.params.get('asset_classes', {})
        if len(asset_classes) < 2:
            return False, f"至少需要配置2类资产，当前数量: {len(asset_classes)}"
        
        return True, ""
    
    def get_applicable_symbols(self) -> List[str]:
        """获取适用的标的列表"""
        return self.get_all_symbols()


# 注册策略定义
RISK_PARITY_DEFINITION = StrategyDefinition(
    id="risk_parity",
    name="风险平价策略",
    category=StrategyCategory.LONG_TERM,
    description="基于风险平价的多资产配置策略，按波动率倒数分配权重，实现风险均衡",
    risk_level=RiskLevel.LOW,
    applicable_types=["宽基ETF", "债券ETF", "黄金ETF"],
    entry_logic="计算30日滚动波动率，按波动率倒数分配权重",
    exit_logic="双周再平衡，或权重偏离目标超过3%时调仓",
    default_params=RiskParityStrategy.DEFAULT_PARAMS,
    min_capital=50000.0,
    backtest_return=None,  # 点击回测获取真实数据
    backtest_sharpe=None,
    backtest_max_drawdown=None,
    backtest_win_rate=None,
)

# 自动注册到策略注册表
StrategyRegistry.register(RISK_PARITY_DEFINITION)
