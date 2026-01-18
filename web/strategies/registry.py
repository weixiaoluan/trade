"""
============================================
策略注册表
Strategy Registry
============================================

管理所有预设策略的定义和元数据
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class StrategyCategory(Enum):
    """策略类别"""
    INTRADAY = "intraday"     # 日内 T+0
    SHORT_TERM = "short"      # 短线 1-5天
    SWING = "swing"           # 波段 1-4周
    LONG_TERM = "long"        # 长线 1月+


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class StrategyDefinition:
    """策略定义数据类"""
    id: str                                    # 策略唯一标识
    name: str                                  # 策略名称
    category: StrategyCategory                 # 策略类别
    description: str                           # 策略描述
    risk_level: RiskLevel                      # 风险等级
    applicable_types: List[str]                # 适用标的类型
    entry_logic: str                           # 入场逻辑描述
    exit_logic: str                            # 出场逻辑描述
    default_params: Dict = field(default_factory=dict)  # 默认参数
    min_capital: float = 10000.0               # 最小资金要求
    backtest_return: Optional[float] = None    # 历史回测收益率
    backtest_sharpe: Optional[float] = None    # 历史回测夏普比率
    backtest_max_drawdown: Optional[float] = None  # 历史回测最大回撤
    backtest_win_rate: Optional[float] = None  # 历史回测胜率


class StrategyRegistry:
    """策略注册表 - 管理所有预设策略"""
    _strategies: Dict[str, StrategyDefinition] = {}
    
    @classmethod
    def register(cls, strategy: StrategyDefinition) -> None:
        """注册策略"""
        cls._strategies[strategy.id] = strategy
    
    @classmethod
    def unregister(cls, strategy_id: str) -> bool:
        """取消注册策略"""
        if strategy_id in cls._strategies:
            del cls._strategies[strategy_id]
            return True
        return False
    
    @classmethod
    def get_all(cls) -> List[StrategyDefinition]:
        """获取所有策略"""
        return list(cls._strategies.values())
    
    @classmethod
    def get_by_id(cls, strategy_id: str) -> Optional[StrategyDefinition]:
        """根据ID获取策略"""
        return cls._strategies.get(strategy_id)
    
    @classmethod
    def get_by_category(cls, category: StrategyCategory) -> List[StrategyDefinition]:
        """根据类别获取策略"""
        return [s for s in cls._strategies.values() if s.category == category]
    
    @classmethod
    def get_by_risk_level(cls, risk_level: RiskLevel) -> List[StrategyDefinition]:
        """根据风险等级获取策略"""
        return [s for s in cls._strategies.values() if s.risk_level == risk_level]
    
    @classmethod
    def clear(cls) -> None:
        """清空所有策略（主要用于测试）"""
        cls._strategies.clear()
    
    @classmethod
    def count(cls) -> int:
        """获取策略数量"""
        return len(cls._strategies)
