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
from .risk_parity import RiskParityStrategy, RISK_PARITY_DEFINITION
from .adaptive_ma import AdaptiveMAStrategy, ADAPTIVE_MA_DEFINITION
from .cb_intraday_burst import (
    CBIntradayBurstStrategy, CB_INTRADAY_BURST_DEFINITION,
    CBPosition, CBIntradayBurstBT, run_backtest
)
from .rsrs_rotation import (
    RSRSSectorRotationStrategy, RSRS_SECTOR_ROTATION_DEFINITION,
    calculate_rsrs_beta, calculate_rsrs_score, calculate_momentum,
    RSRSSectorRotationBTStrategy, run_rsrs_backtest
)
from .executor import (
    StrategyExecutor, UserStrategyConfig, ExecutionResult,
    resolve_signal_conflicts, validate_capital_allocation, STRATEGY_CLASSES
)
from .performance import (
    PerformanceMetrics, StrategyPerformanceCalculator,
    calculate_total_return, calculate_daily_return, calculate_win_rate,
    calculate_max_drawdown, calculate_sharpe_ratio, calculate_profit_factor,
    compare_strategies_performance, aggregate_performance_by_period
)
from .risk_control import (
    RiskConfig, RiskState, PauseReason,
    StrategyRiskControl, RiskControlManager, validate_risk_config
)
from .etf_rotation import (
    ETFMomentumRotationStrategy, BinaryRotationStrategy, IndustryMomentumStrategy,
    ETF_ROTATION_DEFINITION, BINARY_ROTATION_DEFINITION, INDUSTRY_MOMENTUM_DEFINITION,
    TICKER_POOL, BINARY_ROTATION_POOL, ETFInfo, TradingRule,
    Backtester, BacktestResult, generate_mock_data, generate_mock_premium_data
)
from .strategy_trader import (
    StrategyTrader, TradeOrder,
    execute_etf_strategy, get_etf_strategy_status,
    execute_strategy_signal
)

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
    'RiskParityStrategy',
    'RISK_PARITY_DEFINITION',
    'AdaptiveMAStrategy',
    'ADAPTIVE_MA_DEFINITION',
    # CB Intraday Burst
    'CBIntradayBurstStrategy',
    'CB_INTRADAY_BURST_DEFINITION',
    'CBPosition',
    'CBIntradayBurstBT',
    'run_backtest',
    # RSRS Sector Rotation
    'RSRSSectorRotationStrategy',
    'RSRS_SECTOR_ROTATION_DEFINITION',
    'calculate_rsrs_beta',
    'calculate_rsrs_score',
    'calculate_momentum',
    'RSRSSectorRotationBTStrategy',
    'run_rsrs_backtest',
    # Executor
    'StrategyExecutor',
    'UserStrategyConfig',
    'ExecutionResult',
    'resolve_signal_conflicts',
    'validate_capital_allocation',
    'STRATEGY_CLASSES',
    # Performance
    'PerformanceMetrics',
    'StrategyPerformanceCalculator',
    'calculate_total_return',
    'calculate_daily_return',
    'calculate_win_rate',
    'calculate_max_drawdown',
    'calculate_sharpe_ratio',
    'calculate_profit_factor',
    'compare_strategies_performance',
    'aggregate_performance_by_period',
    # Risk Control
    'RiskConfig',
    'RiskState',
    'PauseReason',
    'StrategyRiskControl',
    'RiskControlManager',
    'validate_risk_config',
    # ETF Rotation
    'ETFMomentumRotationStrategy',
    'BinaryRotationStrategy',
    'IndustryMomentumStrategy',
    'ETF_ROTATION_DEFINITION',
    'BINARY_ROTATION_DEFINITION',
    'INDUSTRY_MOMENTUM_DEFINITION',
    'TICKER_POOL',
    'BINARY_ROTATION_POOL',
    'ETFInfo',
    'TradingRule',
    'Backtester',
    'BacktestResult',
    'generate_mock_data',
    'generate_mock_premium_data',
    # Strategy Trader
    'StrategyTrader',
    'TradeOrder',
    'execute_etf_strategy',
    'get_etf_strategy_status',
    'execute_strategy_signal',
]

# ============================================
# 确保所有策略都已注册到 StrategyRegistry
# ============================================
def _ensure_strategies_registered():
    """确保所有预设策略都已注册"""
    strategies_to_register = [
        RSI_REVERSAL_DEFINITION,
        OVERNIGHT_DEFINITION,
        MOMENTUM_ROTATION_DEFINITION,
        BIAS_REVERSION_DEFINITION,
        RISK_PARITY_DEFINITION,
        ADAPTIVE_MA_DEFINITION,
        ETF_ROTATION_DEFINITION,
        BINARY_ROTATION_DEFINITION,
        INDUSTRY_MOMENTUM_DEFINITION,
        CB_INTRADAY_BURST_DEFINITION,
        RSRS_SECTOR_ROTATION_DEFINITION,
    ]
    for strategy in strategies_to_register:
        if StrategyRegistry.get_by_id(strategy.id) is None:
            StrategyRegistry.register(strategy)

_ensure_strategies_registered()
