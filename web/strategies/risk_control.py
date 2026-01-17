"""
============================================
策略风控模块
Strategy Risk Control
============================================

实现策略级别的风险控制：
- 单策略仓位限制
- 策略回撤监控
- 日亏损限制
- 策略暂停机制

Requirements: 12.1, 12.2, 12.3, 12.4
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class PauseReason(Enum):
    """暂停原因"""
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"    # 回撤超阈值
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"  # 日亏损超限
    MANUAL = "manual"                          # 手动暂停
    RISK_EVENT = "risk_event"                  # 风险事件


@dataclass
class RiskConfig:
    """风控配置"""
    max_position_pct: float = 0.3          # 单策略最大仓位比例（占策略资金）
    max_drawdown_pct: float = 0.15         # 最大回撤阈值（15%触发暂停）
    daily_loss_limit_pct: float = 0.05     # 日亏损限制（5%）
    max_trades_per_day: int = 10           # 每日最大交易次数
    min_trade_interval_minutes: int = 5    # 最小交易间隔（分钟）
    

@dataclass
class RiskState:
    """风控状态"""
    strategy_id: str
    is_paused: bool = False
    pause_reason: Optional[PauseReason] = None
    paused_at: Optional[datetime] = None
    peak_value: float = 0.0                # 历史最高净值
    current_drawdown: float = 0.0          # 当前回撤
    daily_pnl: float = 0.0                 # 当日盈亏
    daily_trade_count: int = 0             # 当日交易次数
    last_trade_time: Optional[datetime] = None  # 最后交易时间
    last_check_date: Optional[date] = None  # 最后检查日期


class StrategyRiskControl:
    """策略风控管理器"""
    
    def __init__(self, strategy_id: str, config: RiskConfig = None):
        """
        初始化风控管理器
        
        Args:
            strategy_id: 策略ID
            config: 风控配置
        """
        self.strategy_id = strategy_id
        self.config = config or RiskConfig()
        self.state = RiskState(strategy_id=strategy_id)
        self._pause_callbacks = []
    
    def check_position_limit(self, 
                             current_position_value: float,
                             allocated_capital: float) -> Tuple[bool, str]:
        """
        检查仓位是否超限
        
        Args:
            current_position_value: 当前持仓市值
            allocated_capital: 策略分配资金
            
        Returns:
            (是否合规, 原因)
        """
        if allocated_capital <= 0:
            return False, "策略资金为0"
        
        position_pct = current_position_value / allocated_capital
        
        if position_pct > self.config.max_position_pct:
            return False, (
                f"仓位{position_pct*100:.1f}%超过限制"
                f"{self.config.max_position_pct*100:.1f}%"
            )
        
        return True, ""
    
    def check_trade_allowed(self, 
                            trade_amount: float,
                            allocated_capital: float) -> Tuple[bool, str]:
        """
        检查是否允许交易
        
        Args:
            trade_amount: 交易金额
            allocated_capital: 策略分配资金
            
        Returns:
            (是否允许, 原因)
        """
        # 检查是否暂停
        if self.state.is_paused:
            return False, f"策略已暂停: {self.state.pause_reason.value if self.state.pause_reason else '未知原因'}"
        
        # 重置日统计（如果是新的一天）
        self._reset_daily_stats_if_needed()
        
        # 检查日交易次数
        if self.state.daily_trade_count >= self.config.max_trades_per_day:
            return False, f"当日交易次数已达上限 {self.config.max_trades_per_day}"
        
        # 检查交易间隔
        if self.state.last_trade_time:
            elapsed = (datetime.now() - self.state.last_trade_time).total_seconds() / 60
            if elapsed < self.config.min_trade_interval_minutes:
                return False, f"交易间隔不足 {self.config.min_trade_interval_minutes} 分钟"
        
        # 检查单笔交易金额
        if allocated_capital > 0:
            trade_pct = trade_amount / allocated_capital
            if trade_pct > self.config.max_position_pct:
                return False, (
                    f"单笔交易金额{trade_pct*100:.1f}%超过限制"
                    f"{self.config.max_position_pct*100:.1f}%"
                )
        
        return True, ""
    
    def update_after_trade(self, trade_result: Dict) -> None:
        """
        交易后更新状态
        
        Args:
            trade_result: 交易结果
        """
        self._reset_daily_stats_if_needed()
        
        self.state.daily_trade_count += 1
        self.state.last_trade_time = datetime.now()
        
        # 更新日盈亏
        pnl = trade_result.get('profit_amount', 0)
        if trade_result.get('trade_type') == 'sell':
            self.state.daily_pnl += pnl
        
        logger.info(
            f"[风控] 策略 {self.strategy_id} 交易后更新: "
            f"日交易次数={self.state.daily_trade_count}, 日盈亏={self.state.daily_pnl:.2f}"
        )
    
    def update_equity(self, current_equity: float, allocated_capital: float) -> None:
        """
        更新净值并检查风控
        
        Args:
            current_equity: 当前净值
            allocated_capital: 分配资金
        """
        # 更新峰值
        if current_equity > self.state.peak_value:
            self.state.peak_value = current_equity
        
        # 计算回撤
        if self.state.peak_value > 0:
            self.state.current_drawdown = (
                (self.state.peak_value - current_equity) / self.state.peak_value
            )
        
        # 检查回撤是否超阈值
        if self.state.current_drawdown > self.config.max_drawdown_pct:
            self._pause_strategy(
                PauseReason.DRAWDOWN_EXCEEDED,
                f"回撤{self.state.current_drawdown*100:.1f}%超过阈值{self.config.max_drawdown_pct*100:.1f}%"
            )
        
        # 检查日亏损
        if allocated_capital > 0:
            daily_loss_pct = abs(min(0, self.state.daily_pnl)) / allocated_capital
            if daily_loss_pct > self.config.daily_loss_limit_pct:
                self._pause_strategy(
                    PauseReason.DAILY_LOSS_EXCEEDED,
                    f"日亏损{daily_loss_pct*100:.1f}%超过限制{self.config.daily_loss_limit_pct*100:.1f}%"
                )
    
    def check_drawdown(self) -> Tuple[bool, float, str]:
        """
        检查回撤状态
        
        Returns:
            (是否正常, 当前回撤, 描述)
        """
        is_normal = self.state.current_drawdown <= self.config.max_drawdown_pct
        desc = f"当前回撤 {self.state.current_drawdown*100:.1f}%"
        if not is_normal:
            desc += f" (超过阈值 {self.config.max_drawdown_pct*100:.1f}%)"
        return is_normal, self.state.current_drawdown, desc
    
    def check_daily_loss(self, allocated_capital: float) -> Tuple[bool, float, str]:
        """
        检查日亏损状态
        
        Args:
            allocated_capital: 分配资金
            
        Returns:
            (是否正常, 日亏损比例, 描述)
        """
        self._reset_daily_stats_if_needed()
        
        if allocated_capital <= 0:
            return True, 0, "无分配资金"
        
        daily_loss_pct = abs(min(0, self.state.daily_pnl)) / allocated_capital
        is_normal = daily_loss_pct <= self.config.daily_loss_limit_pct
        
        desc = f"日亏损 {daily_loss_pct*100:.1f}%"
        if not is_normal:
            desc += f" (超过限制 {self.config.daily_loss_limit_pct*100:.1f}%)"
        
        return is_normal, daily_loss_pct, desc
    
    def pause(self, reason: PauseReason = PauseReason.MANUAL, message: str = "") -> None:
        """
        手动暂停策略
        
        Args:
            reason: 暂停原因
            message: 暂停说明
        """
        self._pause_strategy(reason, message)
    
    def resume(self) -> bool:
        """
        恢复策略
        
        Returns:
            是否恢复成功
        """
        if not self.state.is_paused:
            return True
        
        # 检查是否可以恢复
        is_normal, _, _ = self.check_drawdown()
        if not is_normal:
            logger.warning(f"[风控] 策略 {self.strategy_id} 无法恢复: 回撤仍超阈值")
            return False
        
        self.state.is_paused = False
        self.state.pause_reason = None
        self.state.paused_at = None
        
        logger.info(f"[风控] 策略 {self.strategy_id} 已恢复运行")
        return True
    
    def is_paused(self) -> bool:
        """检查策略是否暂停"""
        return self.state.is_paused
    
    def get_state(self) -> Dict:
        """获取风控状态"""
        return {
            'strategy_id': self.strategy_id,
            'is_paused': self.state.is_paused,
            'pause_reason': self.state.pause_reason.value if self.state.pause_reason else None,
            'paused_at': self.state.paused_at.isoformat() if self.state.paused_at else None,
            'current_drawdown': self.state.current_drawdown,
            'daily_pnl': self.state.daily_pnl,
            'daily_trade_count': self.state.daily_trade_count,
            'peak_value': self.state.peak_value,
        }
    
    def on_pause(self, callback) -> None:
        """
        注册暂停回调
        
        Args:
            callback: 回调函数，签名为 (strategy_id, reason, message)
        """
        self._pause_callbacks.append(callback)
    
    def _pause_strategy(self, reason: PauseReason, message: str) -> None:
        """内部暂停方法"""
        if self.state.is_paused:
            return
        
        self.state.is_paused = True
        self.state.pause_reason = reason
        self.state.paused_at = datetime.now()
        
        logger.warning(f"[风控] 策略 {self.strategy_id} 已暂停: {message}")
        
        # 触发回调
        for callback in self._pause_callbacks:
            try:
                callback(self.strategy_id, reason, message)
            except Exception as e:
                logger.error(f"[风控] 暂停回调执行失败: {e}")
    
    def _reset_daily_stats_if_needed(self) -> None:
        """如果是新的一天，重置日统计"""
        today = date.today()
        if self.state.last_check_date != today:
            self.state.daily_pnl = 0.0
            self.state.daily_trade_count = 0
            self.state.last_check_date = today
            
            # 新的一天，如果是因为日亏损暂停的，自动恢复
            if (self.state.is_paused and 
                self.state.pause_reason == PauseReason.DAILY_LOSS_EXCEEDED):
                self.resume()


class RiskControlManager:
    """风控管理器 - 管理所有策略的风控"""
    
    def __init__(self):
        self._controllers: Dict[str, StrategyRiskControl] = {}
        self._default_config = RiskConfig()
    
    def get_or_create(self, strategy_id: str, 
                      config: RiskConfig = None) -> StrategyRiskControl:
        """
        获取或创建策略风控器
        
        Args:
            strategy_id: 策略ID
            config: 风控配置
            
        Returns:
            策略风控器
        """
        if strategy_id not in self._controllers:
            self._controllers[strategy_id] = StrategyRiskControl(
                strategy_id, 
                config or self._default_config
            )
        return self._controllers[strategy_id]
    
    def get(self, strategy_id: str) -> Optional[StrategyRiskControl]:
        """获取策略风控器"""
        return self._controllers.get(strategy_id)
    
    def remove(self, strategy_id: str) -> bool:
        """移除策略风控器"""
        if strategy_id in self._controllers:
            del self._controllers[strategy_id]
            return True
        return False
    
    def check_all_strategies(self, 
                             equity_data: Dict[str, float],
                             capital_data: Dict[str, float]) -> Dict[str, Dict]:
        """
        检查所有策略的风控状态
        
        Args:
            equity_data: 各策略当前净值 {strategy_id: equity}
            capital_data: 各策略分配资金 {strategy_id: capital}
            
        Returns:
            各策略风控状态
        """
        results = {}
        
        for strategy_id, controller in self._controllers.items():
            equity = equity_data.get(strategy_id, 0)
            capital = capital_data.get(strategy_id, 0)
            
            controller.update_equity(equity, capital)
            results[strategy_id] = controller.get_state()
        
        return results
    
    def get_paused_strategies(self) -> List[str]:
        """获取所有暂停的策略ID"""
        return [
            sid for sid, ctrl in self._controllers.items() 
            if ctrl.is_paused()
        ]
    
    def get_all_states(self) -> Dict[str, Dict]:
        """获取所有策略的风控状态"""
        return {
            sid: ctrl.get_state() 
            for sid, ctrl in self._controllers.items()
        }


def validate_risk_config(config: Dict) -> Tuple[bool, str]:
    """
    验证风控配置
    
    Args:
        config: 风控配置字典
        
    Returns:
        (是否有效, 错误信息)
    """
    if 'max_position_pct' in config:
        val = config['max_position_pct']
        if not 0.1 <= val <= 1.0:
            return False, f"最大仓位比例必须在10%-100%之间，当前: {val*100}%"
    
    if 'max_drawdown_pct' in config:
        val = config['max_drawdown_pct']
        if not 0.05 <= val <= 0.5:
            return False, f"最大回撤阈值必须在5%-50%之间，当前: {val*100}%"
    
    if 'daily_loss_limit_pct' in config:
        val = config['daily_loss_limit_pct']
        if not 0.01 <= val <= 0.2:
            return False, f"日亏损限制必须在1%-20%之间，当前: {val*100}%"
    
    if 'max_trades_per_day' in config:
        val = config['max_trades_per_day']
        if not 1 <= val <= 50:
            return False, f"每日最大交易次数必须在1-50之间，当前: {val}"
    
    return True, ""
