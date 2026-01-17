"""
============================================
策略基类
Strategy Base Class
============================================

所有策略必须继承此基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


@dataclass
class Signal:
    """交易信号数据类"""
    symbol: str                              # 标的代码
    signal_type: str                         # 信号类型: 'buy', 'sell', 'hold'
    strength: int                            # 信号强度: 1-5
    confidence: float                        # 置信度: 0-100
    reason: str                              # 信号原因
    target_price: Optional[float] = None     # 目标价格
    stop_loss: Optional[float] = None        # 止损价格
    strategy_id: Optional[str] = None        # 策略ID
    allocated_capital: Optional[float] = None  # 分配资金
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    
    def __post_init__(self):
        """验证信号数据"""
        if self.signal_type not in ('buy', 'sell', 'hold'):
            raise ValueError(f"Invalid signal_type: {self.signal_type}")
        if not 1 <= self.strength <= 5:
            raise ValueError(f"Signal strength must be 1-5, got: {self.strength}")
        if not 0 <= self.confidence <= 100:
            raise ValueError(f"Confidence must be 0-100, got: {self.confidence}")


class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""
    
    # 策略ID，子类必须覆盖
    STRATEGY_ID: str = ""
    
    def __init__(self, params: Dict = None):
        """
        初始化策略
        
        Args:
            params: 策略参数，如果为None则使用默认参数
        """
        self.params = params or self.get_default_params()
    
    @classmethod
    def get_default_params(cls) -> Dict:
        """获取默认参数，子类可覆盖"""
        return {}
    
    @abstractmethod
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            symbols: 标的代码列表
            market_data: 市场数据字典，格式为 {symbol: {指标数据}}
            
        Returns:
            信号列表
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, capital: float) -> int:
        """
        计算建议仓位
        
        Args:
            signal: 交易信号
            capital: 可用资金
            
        Returns:
            建议买入数量（股数/份数）
        """
        pass
    
    @abstractmethod
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """
        检查出场条件
        
        Args:
            position: 持仓信息
            market_data: 市场数据
            
        Returns:
            (是否应该出场, 出场原因)
        """
        pass
    
    def validate_params(self) -> Tuple[bool, str]:
        """
        验证策略参数
        
        Returns:
            (是否有效, 错误信息)
        """
        return True, ""
    
    def get_applicable_symbols(self) -> List[str]:
        """
        获取适用的标的列表
        
        优先从数据库获取，如果数据库没有则使用默认参数
        
        Returns:
            标的代码列表
        """
        # 优先从数据库获取
        try:
            from web.database import db_get_strategy_asset_symbols
            db_symbols = db_get_strategy_asset_symbols(self.STRATEGY_ID)
            if db_symbols:
                return db_symbols
        except Exception:
            pass
        
        # 回退到默认参数
        return (self.params.get('applicable_etfs') or 
                self.params.get('sector_etfs') or 
                [])
    
    def on_trade_executed(self, trade_result: Dict) -> None:
        """
        交易执行后的回调
        
        Args:
            trade_result: 交易结果
        """
        pass
    
    def on_day_end(self, positions: List[Dict], market_data: Dict) -> None:
        """
        每日收盘后的回调
        
        Args:
            positions: 当前持仓列表
            market_data: 市场数据
        """
        pass
