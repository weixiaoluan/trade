"""
============================================
策略执行器
Strategy Executor
============================================

负责加载和执行用户配置的策略：
- 加载用户策略配置
- 并行执行多策略
- 处理信号冲突
- 管理策略资金隔离

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from typing import Dict, List, Tuple, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .base import BaseStrategy, Signal
from .registry import StrategyRegistry
from .rsi_reversal import RSIReversalStrategy
from .overnight import OvernightStrategy
from .momentum_rotation import MomentumRotationStrategy
from .bias_reversion import BiasReversionStrategy
from .risk_parity import RiskParityStrategy
from .adaptive_ma import AdaptiveMAStrategy
from .etf_rotation import (
    ETFMomentumRotationStrategy, 
    BinaryRotationStrategy, 
    IndustryMomentumStrategy
)
from .cb_intraday_burst import CBIntradayBurstStrategy
from .rsrs_rotation import RSRSSectorRotationStrategy


logger = logging.getLogger(__name__)


# 策略类映射
STRATEGY_CLASSES: Dict[str, Type[BaseStrategy]] = {
    'rsi_reversal': RSIReversalStrategy,
    'overnight': OvernightStrategy,
    'momentum_rotation': MomentumRotationStrategy,
    'bias_reversion': BiasReversionStrategy,
    'risk_parity': RiskParityStrategy,
    'adaptive_ma': AdaptiveMAStrategy,
    'etf_momentum_rotation': ETFMomentumRotationStrategy,
    'binary_rotation': BinaryRotationStrategy,
    'industry_momentum': IndustryMomentumStrategy,
    'cb_intraday_burst': CBIntradayBurstStrategy,
    'rsrs_sector_rotation': RSRSSectorRotationStrategy,
}


@dataclass
class UserStrategyConfig:
    """用户策略配置"""
    strategy_id: str                    # 策略ID
    enabled: bool = True                # 是否启用
    allocated_capital: float = 10000.0  # 分配资金
    params: Dict = field(default_factory=dict)  # 自定义参数
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    """执行结果"""
    strategy_id: str                    # 策略ID
    signals: List[Signal]               # 生成的信号
    resolved_signals: List[Signal]      # 冲突解决后的信号
    errors: List[str] = field(default_factory=list)  # 错误信息
    execution_time_ms: float = 0.0      # 执行时间（毫秒）


def resolve_signal_conflicts(signals: List[Signal]) -> List[Signal]:
    """
    解决信号冲突
    
    优先级规则：
    1. 卖出信号 > 买入信号（同一标的）
    2. 信号强度高 > 信号强度低
    3. 置信度高 > 置信度低
    
    Args:
        signals: 原始信号列表
        
    Returns:
        解决冲突后的信号列表
    """
    if not signals:
        return []
    
    # 按标的分组
    signals_by_symbol: Dict[str, List[Signal]] = {}
    for signal in signals:
        if signal.symbol not in signals_by_symbol:
            signals_by_symbol[signal.symbol] = []
        signals_by_symbol[signal.symbol].append(signal)
    
    resolved = []
    
    for symbol, symbol_signals in signals_by_symbol.items():
        if len(symbol_signals) == 1:
            resolved.append(symbol_signals[0])
            continue
        
        # 分离买入和卖出信号
        buy_signals = [s for s in symbol_signals if s.signal_type == 'buy']
        sell_signals = [s for s in symbol_signals if s.signal_type == 'sell']
        hold_signals = [s for s in symbol_signals if s.signal_type == 'hold']
        
        # 优先处理卖出信号
        if sell_signals:
            # 选择强度最高的卖出信号
            best_sell = max(sell_signals, key=lambda s: (s.strength, s.confidence))
            resolved.append(best_sell)
            # 卖出信号存在时，忽略买入信号
            continue
        
        # 处理买入信号
        if buy_signals:
            # 选择强度最高的买入信号
            best_buy = max(buy_signals, key=lambda s: (s.strength, s.confidence))
            resolved.append(best_buy)
            continue
        
        # 只有hold信号，选择第一个
        if hold_signals:
            resolved.append(hold_signals[0])
    
    return resolved


class StrategyExecutor:
    """
    策略执行器
    
    负责加载、执行和管理多个策略
    """
    
    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}
        self._configs: Dict[str, UserStrategyConfig] = {}
        self._capital_allocation: Dict[str, float] = {}
    
    def load_user_strategies(self, configs: List[UserStrategyConfig]) -> Tuple[int, List[str]]:
        """
        加载用户策略配置
        
        Args:
            configs: 用户策略配置列表
            
        Returns:
            (成功加载数量, 错误信息列表)
        """
        loaded = 0
        errors = []
        
        self._strategies.clear()
        self._configs.clear()
        self._capital_allocation.clear()
        
        for config in configs:
            if not config.enabled:
                continue
            
            strategy_id = config.strategy_id
            
            # 检查策略是否存在
            if strategy_id not in STRATEGY_CLASSES:
                errors.append(f"未知策略ID: {strategy_id}")
                continue
            
            # 获取策略定义
            definition = StrategyRegistry.get_by_id(strategy_id)
            if not definition:
                errors.append(f"策略定义未注册: {strategy_id}")
                continue
            
            # 检查最小资金要求
            if config.allocated_capital < definition.min_capital:
                errors.append(
                    f"策略 {strategy_id} 资金不足: "
                    f"已分配 {config.allocated_capital}, 最小要求 {definition.min_capital}"
                )
                continue
            
            try:
                # 合并默认参数和用户自定义参数
                strategy_class = STRATEGY_CLASSES[strategy_id]
                params = strategy_class.get_default_params()
                if config.params:
                    params.update(config.params)
                
                # 实例化策略
                strategy = strategy_class(params)
                
                # 验证参数
                is_valid, error_msg = strategy.validate_params()
                if not is_valid:
                    errors.append(f"策略 {strategy_id} 参数无效: {error_msg}")
                    continue
                
                self._strategies[strategy_id] = strategy
                self._configs[strategy_id] = config
                self._capital_allocation[strategy_id] = config.allocated_capital
                loaded += 1
                
                logger.info(f"策略加载成功: {strategy_id}, 分配资金: {config.allocated_capital}")
                
            except Exception as e:
                errors.append(f"策略 {strategy_id} 加载失败: {str(e)}")
                logger.exception(f"策略 {strategy_id} 加载异常")
        
        return loaded, errors
    
    def get_loaded_strategies(self) -> List[str]:
        """获取已加载的策略ID列表"""
        return list(self._strategies.keys())
    
    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """获取策略实例"""
        return self._strategies.get(strategy_id)
    
    def get_allocated_capital(self, strategy_id: str) -> float:
        """获取策略分配资金"""
        return self._capital_allocation.get(strategy_id, 0.0)
    
    def execute_strategy(self, strategy_id: str, market_data: Dict) -> ExecutionResult:
        """
        执行单个策略
        
        Args:
            strategy_id: 策略ID
            market_data: 市场数据
            
        Returns:
            执行结果
        """
        result = ExecutionResult(
            strategy_id=strategy_id,
            signals=[],
            resolved_signals=[]
        )
        
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            result.errors.append(f"策略未加载: {strategy_id}")
            return result
        
        start_time = datetime.now()
        
        try:
            # 获取适用标的
            symbols = strategy.get_applicable_symbols()
            
            # 生成信号
            signals = strategy.generate_signals(symbols, market_data)
            
            # 为信号添加策略ID和分配资金
            allocated_capital = self._capital_allocation.get(strategy_id, 0)
            for signal in signals:
                signal.strategy_id = strategy_id
                signal.allocated_capital = allocated_capital
            
            result.signals = signals
            result.resolved_signals = signals  # 单策略不需要冲突解决
            
        except Exception as e:
            result.errors.append(f"策略执行异常: {str(e)}")
            logger.exception(f"策略 {strategy_id} 执行异常")
        
        end_time = datetime.now()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return result
    
    def execute_all(self, market_data: Dict) -> Tuple[List[Signal], List[ExecutionResult]]:
        """
        执行所有已加载策略
        
        Args:
            market_data: 市场数据
            
        Returns:
            (合并后的信号列表, 各策略执行结果列表)
        """
        all_signals = []
        results = []
        
        for strategy_id in self._strategies:
            result = self.execute_strategy(strategy_id, market_data)
            results.append(result)
            all_signals.extend(result.signals)
        
        # 解决跨策略的信号冲突
        resolved_signals = resolve_signal_conflicts(all_signals)
        
        # 更新结果中的解决后信号
        for result in results:
            result.resolved_signals = [
                s for s in resolved_signals 
                if s.strategy_id == result.strategy_id
            ]
        
        logger.info(
            f"策略执行完成: {len(self._strategies)}个策略, "
            f"原始信号{len(all_signals)}个, 解决冲突后{len(resolved_signals)}个"
        )
        
        return resolved_signals, results
    
    def check_capital_sufficiency(self, signal: Signal, current_price: float) -> Tuple[bool, str]:
        """
        检查策略资金是否充足
        
        Args:
            signal: 交易信号
            current_price: 当前价格
            
        Returns:
            (是否充足, 原因)
        """
        if signal.signal_type != 'buy':
            return True, ""
        
        strategy_id = signal.strategy_id
        allocated = self._capital_allocation.get(strategy_id, 0)
        
        if allocated <= 0:
            return False, f"策略 {strategy_id} 未分配资金"
        
        # 获取策略实例计算仓位
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False, f"策略 {strategy_id} 未加载"
        
        # 计算建议仓位
        suggested_shares = strategy.calculate_position_size(signal, allocated)
        required_capital = suggested_shares * current_price
        
        if required_capital > allocated:
            return False, (
                f"策略 {strategy_id} 资金不足: "
                f"需要 {required_capital:.2f}, 可用 {allocated:.2f}"
            )
        
        if suggested_shares == 0:
            return False, f"策略 {strategy_id} 计算仓位为0"
        
        return True, ""
    
    def update_capital_allocation(self, strategy_id: str, new_capital: float) -> bool:
        """
        更新策略资金分配
        
        Args:
            strategy_id: 策略ID
            new_capital: 新的资金分配
            
        Returns:
            是否更新成功
        """
        if strategy_id not in self._strategies:
            return False
        
        definition = StrategyRegistry.get_by_id(strategy_id)
        if definition and new_capital < definition.min_capital:
            logger.warning(
                f"策略 {strategy_id} 资金分配 {new_capital} 低于最小要求 {definition.min_capital}"
            )
            return False
        
        self._capital_allocation[strategy_id] = new_capital
        return True
    
    def deduct_capital(self, strategy_id: str, amount: float) -> bool:
        """
        扣减策略资金（交易后调用）
        
        Args:
            strategy_id: 策略ID
            amount: 扣减金额
            
        Returns:
            是否扣减成功
        """
        if strategy_id not in self._capital_allocation:
            return False
        
        current = self._capital_allocation[strategy_id]
        if amount > current:
            return False
        
        self._capital_allocation[strategy_id] = current - amount
        return True
    
    def add_capital(self, strategy_id: str, amount: float) -> bool:
        """
        增加策略资金（平仓后调用）
        
        Args:
            strategy_id: 策略ID
            amount: 增加金额
            
        Returns:
            是否增加成功
        """
        if strategy_id not in self._capital_allocation:
            return False
        
        self._capital_allocation[strategy_id] += amount
        return True
    
    def get_all_applicable_symbols(self) -> List[str]:
        """获取所有策略适用的标的列表（去重）"""
        symbols = set()
        for strategy in self._strategies.values():
            symbols.update(strategy.get_applicable_symbols())
        return list(symbols)
    
    def on_trade_executed(self, strategy_id: str, trade_result: Dict) -> None:
        """
        交易执行后的回调
        
        Args:
            strategy_id: 策略ID
            trade_result: 交易结果
        """
        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.on_trade_executed(trade_result)
    
    def on_day_end(self, positions: List[Dict], market_data: Dict) -> None:
        """
        每日收盘后的回调
        
        Args:
            positions: 当前持仓列表
            market_data: 市场数据
        """
        for strategy_id, strategy in self._strategies.items():
            # 过滤出该策略的持仓
            strategy_positions = [
                p for p in positions 
                if p.get('strategy_id') == strategy_id
            ]
            strategy.on_day_end(strategy_positions, market_data)


def validate_capital_allocation(configs: List[UserStrategyConfig], 
                                 total_available: float) -> Tuple[bool, str]:
    """
    验证资金分配
    
    Args:
        configs: 用户策略配置列表
        total_available: 可用总资金
        
    Returns:
        (是否有效, 错误信息)
    """
    total_allocated = sum(c.allocated_capital for c in configs if c.enabled)
    
    if total_allocated > total_available:
        return False, (
            f"总分配资金 {total_allocated:.2f} 超过可用资金 {total_available:.2f}"
        )
    
    # 检查每个策略的最小资金要求
    for config in configs:
        if not config.enabled:
            continue
        
        definition = StrategyRegistry.get_by_id(config.strategy_id)
        if definition and config.allocated_capital < definition.min_capital:
            return False, (
                f"策略 {config.strategy_id} 分配资金 {config.allocated_capital:.2f} "
                f"低于最小要求 {definition.min_capital:.2f}"
            )
    
    return True, ""
