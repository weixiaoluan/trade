"""
============================================
策略池模块
Strategy Pool Module
============================================

提供多策略并行执行能力，包含6种预设量化策略：
- RSI极限反转策略 (短线)
- 隔夜效应策略 (短线)
- 动量轮动策略 (波段)
- 乖离率回归策略 (波段)
- 风险平价策略 (长线)
- 自适应均线择时策略 (长线)
"""

from .registry import (
    StrategyCategory,
    RiskLevel,
    StrategyDefinition,
    StrategyRegistry
)
from .base import Signal, BaseStrategy
from .rsi_reversal import RSIReversalStrategy, RSI_REVERSAL_DEFINITION
from .overnight import OvernightStrategy, OVERNIGHT_DEFINITION
from .momentum_rotation import MomentumRotationStrategy, MOMENTUM_ROTATION_DEFINITION
from .bias_reversion import BiasReversionStrategy, BIAS_REVERSION_DEFINITION

__all__ = [
    'StrategyCategory',
    'RiskLevel',
    'StrategyDefinition',
    'StrategyRegistry',
    'Signal',
    'BaseStrategy',
    'RSIReversalStrategy',
    'RSI_REVERSAL_DEFINITION',
    'OvernightStrategy',
    'OVERNIGHT_DEFINITION',
    'MomentumRotationStrategy',
    'MOMENTUM_ROTATION_DEFINITION',
    'BiasReversionStrategy',
    'BIAS_REVERSION_DEFINITION',
]
