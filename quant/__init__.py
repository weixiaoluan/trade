"""
============================================
量化分析模块 (基于 vnpy 架构)
Quantitative Analysis Module (Based on vnpy Architecture)
============================================
"""

from .event_engine import QuantEventEngine
from .array_manager import QuantArrayManager
from .bar_generator import BarGenerator
from .quant_agent import QuantAgent
from .market_regime import MarketRegimeAnalyzer
from .after_hours_detector import AfterHoursDetector
from .trading_signals import (
    TradingSignalGenerator,
    TradingSignal,
    RiskManagement,
    SignalType,
    SignalStrength,
    generate_trading_analysis,
)

__all__ = [
    "QuantEventEngine",
    "QuantArrayManager",
    "BarGenerator",
    "QuantAgent",
    "MarketRegimeAnalyzer",
    "AfterHoursDetector",
    "TradingSignalGenerator",
    "TradingSignal",
    "RiskManagement",
    "SignalType",
    "SignalStrength",
    "generate_trading_analysis",
]
