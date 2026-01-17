"""
============================================
策略性能计算模块
Strategy Performance Calculator
============================================

计算策略的各项性能指标：
- 总收益率
- 胜率
- 最大回撤
- 夏普比率
- 交易统计

Requirements: 4.1, 4.4, 4.5
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math


@dataclass
class PerformanceMetrics:
    """策略性能指标"""
    strategy_id: str
    total_return: float = 0.0           # 总收益率 (%)
    daily_return: float = 0.0           # 日收益率 (%)
    win_rate: float = 0.0               # 胜率 (%)
    max_drawdown: float = 0.0           # 最大回撤 (%)
    sharpe_ratio: float = 0.0           # 夏普比率
    trade_count: int = 0                # 交易次数
    win_count: int = 0                  # 盈利次数
    loss_count: int = 0                 # 亏损次数
    avg_profit: float = 0.0             # 平均盈利 (%)
    avg_loss: float = 0.0               # 平均亏损 (%)
    profit_factor: float = 0.0          # 盈亏比
    position_value: float = 0.0         # 当前持仓市值
    calculated_at: datetime = field(default_factory=datetime.now)


def calculate_total_return(initial_capital: float, current_value: float) -> float:
    """
    计算总收益率
    
    Args:
        initial_capital: 初始资金
        current_value: 当前总价值（含持仓市值）
        
    Returns:
        总收益率（百分比）
    """
    if initial_capital <= 0:
        return 0.0
    return ((current_value - initial_capital) / initial_capital) * 100


def calculate_daily_return(previous_value: float, current_value: float) -> float:
    """
    计算日收益率
    
    Args:
        previous_value: 前一日价值
        current_value: 当前价值
        
    Returns:
        日收益率（百分比）
    """
    if previous_value <= 0:
        return 0.0
    return ((current_value - previous_value) / previous_value) * 100


def calculate_win_rate(win_count: int, total_trades: int) -> float:
    """
    计算胜率
    
    Args:
        win_count: 盈利交易数
        total_trades: 总交易数
        
    Returns:
        胜率（百分比）
    """
    if total_trades <= 0:
        return 0.0
    return (win_count / total_trades) * 100


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    计算最大回撤
    
    Args:
        equity_curve: 权益曲线（每日净值列表）
        
    Returns:
        最大回撤（百分比）
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    
    max_drawdown = 0.0
    peak = equity_curve[0]
    
    for value in equity_curve:
        if value > peak:
            peak = value
        
        if peak > 0:
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown


def calculate_sharpe_ratio(daily_returns: List[float], 
                           risk_free_rate: float = 0.03) -> float:
    """
    计算夏普比率
    
    公式: (平均收益率 - 无风险利率) / 收益率标准差
    
    Args:
        daily_returns: 日收益率列表（百分比）
        risk_free_rate: 年化无风险利率（默认3%）
        
    Returns:
        年化夏普比率
    """
    if not daily_returns or len(daily_returns) < 2:
        return 0.0
    
    # 转换为小数
    returns = [r / 100 for r in daily_returns]
    
    # 计算平均日收益率
    avg_return = sum(returns) / len(returns)
    
    # 计算日收益率标准差
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0:
        return 0.0
    
    # 日无风险利率
    daily_rf = risk_free_rate / 252
    
    # 计算夏普比率并年化
    sharpe = (avg_return - daily_rf) / std_dev
    annual_sharpe = sharpe * math.sqrt(252)
    
    return annual_sharpe


def calculate_profit_factor(total_profit: float, total_loss: float) -> float:
    """
    计算盈亏比
    
    Args:
        total_profit: 总盈利
        total_loss: 总亏损（正数）
        
    Returns:
        盈亏比
    """
    if total_loss <= 0:
        return float('inf') if total_profit > 0 else 0.0
    return total_profit / total_loss


class StrategyPerformanceCalculator:
    """策略性能计算器"""
    
    def __init__(self, strategy_id: str, initial_capital: float):
        """
        初始化性能计算器
        
        Args:
            strategy_id: 策略ID
            initial_capital: 初始资金
        """
        self.strategy_id = strategy_id
        self.initial_capital = initial_capital
        
        # 交易记录
        self._trades: List[Dict] = []
        
        # 每日净值记录
        self._equity_curve: List[Tuple[str, float]] = []
        
        # 每日收益率
        self._daily_returns: List[float] = []
        
        # 统计数据
        self._win_count = 0
        self._loss_count = 0
        self._total_profit = 0.0
        self._total_loss = 0.0
    
    def add_trade(self, trade: Dict) -> None:
        """
        添加交易记录
        
        Args:
            trade: 交易记录字典，需包含:
                - profit_pct: 盈亏百分比
                - profit_amount: 盈亏金额
                - trade_type: 交易类型 (buy/sell)
        """
        self._trades.append(trade)
        
        profit_pct = trade.get('profit_pct', 0)
        profit_amount = trade.get('profit_amount', 0)
        
        # 只统计卖出交易
        if trade.get('trade_type') == 'sell':
            if profit_pct > 0:
                self._win_count += 1
                self._total_profit += profit_amount
            elif profit_pct < 0:
                self._loss_count += 1
                self._total_loss += abs(profit_amount)
    
    def record_daily_equity(self, date: str, equity: float) -> None:
        """
        记录每日权益
        
        Args:
            date: 日期 (YYYY-MM-DD)
            equity: 当日权益（现金 + 持仓市值）
        """
        self._equity_curve.append((date, equity))
        
        # 计算日收益率
        if len(self._equity_curve) >= 2:
            prev_equity = self._equity_curve[-2][1]
            daily_return = calculate_daily_return(prev_equity, equity)
            self._daily_returns.append(daily_return)
    
    def calculate_metrics(self, current_equity: float = None, 
                          position_value: float = 0) -> PerformanceMetrics:
        """
        计算性能指标
        
        Args:
            current_equity: 当前权益（如不提供则使用最后记录的权益）
            position_value: 当前持仓市值
            
        Returns:
            性能指标对象
        """
        if current_equity is None:
            current_equity = self._equity_curve[-1][1] if self._equity_curve else self.initial_capital
        
        # 计算各项指标
        total_return = calculate_total_return(self.initial_capital, current_equity)
        
        daily_return = self._daily_returns[-1] if self._daily_returns else 0.0
        
        total_trades = self._win_count + self._loss_count
        win_rate = calculate_win_rate(self._win_count, total_trades)
        
        equity_values = [e[1] for e in self._equity_curve]
        max_drawdown = calculate_max_drawdown(equity_values)
        
        sharpe_ratio = calculate_sharpe_ratio(self._daily_returns)
        
        avg_profit = (self._total_profit / self._win_count) if self._win_count > 0 else 0
        avg_loss = (self._total_loss / self._loss_count) if self._loss_count > 0 else 0
        
        profit_factor = calculate_profit_factor(self._total_profit, self._total_loss)
        
        return PerformanceMetrics(
            strategy_id=self.strategy_id,
            total_return=total_return,
            daily_return=daily_return,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trade_count=total_trades,
            win_count=self._win_count,
            loss_count=self._loss_count,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            position_value=position_value
        )
    
    def get_equity_curve(self) -> List[Tuple[str, float]]:
        """获取权益曲线"""
        return self._equity_curve.copy()
    
    def get_daily_returns(self) -> List[float]:
        """获取日收益率序列"""
        return self._daily_returns.copy()
    
    def get_trade_count(self) -> int:
        """获取交易总数"""
        return self._win_count + self._loss_count
    
    def reset(self) -> None:
        """重置计算器"""
        self._trades.clear()
        self._equity_curve.clear()
        self._daily_returns.clear()
        self._win_count = 0
        self._loss_count = 0
        self._total_profit = 0.0
        self._total_loss = 0.0


def calculate_strategy_performance_from_trades(
    strategy_id: str,
    trades: List[Dict],
    initial_capital: float
) -> PerformanceMetrics:
    """
    从交易记录计算策略性能
    
    Args:
        strategy_id: 策略ID
        trades: 交易记录列表
        initial_capital: 初始资金
        
    Returns:
        性能指标
    """
    calculator = StrategyPerformanceCalculator(strategy_id, initial_capital)
    
    # 按日期排序交易记录
    sorted_trades = sorted(trades, key=lambda t: t.get('trade_time', ''))
    
    # 模拟计算每日权益
    current_capital = initial_capital
    daily_equity = {}
    
    for trade in sorted_trades:
        calculator.add_trade(trade)
        
        trade_time = trade.get('trade_time', '')
        if trade_time:
            date = trade_time[:10]  # 取日期部分
            profit = trade.get('profit_amount', 0)
            if trade.get('trade_type') == 'sell':
                current_capital += profit
            daily_equity[date] = current_capital
    
    # 记录每日权益
    for date in sorted(daily_equity.keys()):
        calculator.record_daily_equity(date, daily_equity[date])
    
    return calculator.calculate_metrics(current_capital)


def aggregate_performance_by_period(
    daily_performances: List[Dict],
    period: str = 'week'
) -> List[Dict]:
    """
    按周期聚合性能数据
    
    Args:
        daily_performances: 每日性能数据列表
        period: 聚合周期 ('week', 'month')
        
    Returns:
        聚合后的性能数据列表
    """
    if not daily_performances:
        return []
    
    aggregated = {}
    
    for perf in daily_performances:
        date_str = perf.get('date', '')
        if not date_str:
            continue
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            continue
        
        if period == 'week':
            # 按周聚合（取该周的周一）
            week_start = date - timedelta(days=date.weekday())
            key = week_start.strftime('%Y-%m-%d')
        elif period == 'month':
            # 按月聚合
            key = date.strftime('%Y-%m')
        else:
            key = date_str
        
        if key not in aggregated:
            aggregated[key] = {
                'period': key,
                'total_return': 0,
                'win_count': 0,
                'loss_count': 0,
                'trade_count': 0,
                'max_drawdown': 0,
                'days': 0
            }
        
        agg = aggregated[key]
        agg['days'] += 1
        agg['total_return'] = perf.get('total_return', 0)  # 取最后一天的累计收益
        agg['win_count'] += perf.get('win_count', 0)
        agg['loss_count'] += perf.get('loss_count', 0)
        agg['trade_count'] += perf.get('trade_count', 0)
        agg['max_drawdown'] = max(agg['max_drawdown'], perf.get('max_drawdown', 0))
    
    # 计算胜率
    result = []
    for key in sorted(aggregated.keys()):
        agg = aggregated[key]
        total = agg['win_count'] + agg['loss_count']
        agg['win_rate'] = (agg['win_count'] / total * 100) if total > 0 else 0
        result.append(agg)
    
    return result


def compare_strategies_performance(
    performances: List[PerformanceMetrics]
) -> Dict:
    """
    对比多个策略的性能
    
    Args:
        performances: 多个策略的性能指标
        
    Returns:
        对比结果字典
    """
    if not performances:
        return {}
    
    comparison = {
        'strategies': [],
        'best_return': None,
        'best_sharpe': None,
        'best_win_rate': None,
        'lowest_drawdown': None,
    }
    
    best_return = (None, float('-inf'))
    best_sharpe = (None, float('-inf'))
    best_win_rate = (None, float('-inf'))
    lowest_drawdown = (None, float('inf'))
    
    for perf in performances:
        strategy_data = {
            'strategy_id': perf.strategy_id,
            'total_return': perf.total_return,
            'win_rate': perf.win_rate,
            'max_drawdown': perf.max_drawdown,
            'sharpe_ratio': perf.sharpe_ratio,
            'trade_count': perf.trade_count,
        }
        comparison['strategies'].append(strategy_data)
        
        if perf.total_return > best_return[1]:
            best_return = (perf.strategy_id, perf.total_return)
        
        if perf.sharpe_ratio > best_sharpe[1]:
            best_sharpe = (perf.strategy_id, perf.sharpe_ratio)
        
        if perf.win_rate > best_win_rate[1]:
            best_win_rate = (perf.strategy_id, perf.win_rate)
        
        if perf.max_drawdown < lowest_drawdown[1]:
            lowest_drawdown = (perf.strategy_id, perf.max_drawdown)
    
    comparison['best_return'] = {
        'strategy_id': best_return[0],
        'value': best_return[1]
    }
    comparison['best_sharpe'] = {
        'strategy_id': best_sharpe[0],
        'value': best_sharpe[1]
    }
    comparison['best_win_rate'] = {
        'strategy_id': best_win_rate[0],
        'value': best_win_rate[1]
    }
    comparison['lowest_drawdown'] = {
        'strategy_id': lowest_drawdown[0],
        'value': lowest_drawdown[1]
    }
    
    return comparison
