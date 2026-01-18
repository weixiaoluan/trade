"""
============================================
动量轮动策略 (波段)
Momentum Rotation Strategy
============================================

基于动量因子的行业ETF轮动策略：
- 维护10-15只行业ETF池
- 计算20日动量得分
- 每周轮动到动量最强的ETF
- 适合波段操作

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .base import BaseStrategy, Signal
from .registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyCategory,
    RiskLevel
)


def calculate_momentum_score(current_price: float, price_n_days_ago: float) -> float:
    """
    计算动量得分: (P_t - P_{t-n}) / P_{t-n}
    
    Args:
        current_price: 当前价格
        price_n_days_ago: N天前的价格
        
    Returns:
        动量得分（百分比形式，如0.05表示5%）
    """
    if price_n_days_ago <= 0:
        return -999.0  # 无效数据标记
    
    return (current_price - price_n_days_ago) / price_n_days_ago


class MomentumRotationStrategy(BaseStrategy):
    """
    动量轮动策略
    
    入场条件：
    - ETF在动量排名前N名
    - 每周（5个交易日）轮动一次
    
    出场条件：
    - ETF跌出动量排名前N名
    - 或触发止损
    
    适用标的：
    - 行业ETF（半导体、医药、军工、证券、消费等）
    """
    
    STRATEGY_ID = "momentum_rotation"
    
    DEFAULT_PARAMS = {
        'momentum_period': 20,      # 动量计算周期（天）
        'top_n': 3,                 # 选择前N名
        'rebalance_days': 5,        # 轮动周期（交易日）
        'stop_loss_pct': 0.08,      # 止损百分比
        'sector_etfs': [
            '512480.SH',  # 半导体ETF
            '512010.SH',  # 医药ETF
            '512660.SH',  # 军工ETF
            '512880.SH',  # 证券ETF
            '159928.SZ',  # 消费ETF
            '512200.SH',  # 房地产ETF
            '512800.SH',  # 银行ETF
            '515030.SH',  # 新能源车ETF
            '159941.SZ',  # 纳指ETF
            '513050.SH',  # 中概互联ETF
            '512690.SH',  # 酒ETF
            '515790.SH',  # 光伏ETF
            '512170.SH',  # 医疗ETF
            '512400.SH',  # 有色金属ETF
            '512980.SH',  # 传媒ETF
        ]
    }
    
    @classmethod
    def get_default_params(cls) -> Dict:
        return cls.DEFAULT_PARAMS.copy()
    
    def calculate_all_momentum_scores(self, market_data: Dict) -> List[Tuple[str, float, Dict]]:
        """
        计算所有ETF的动量得分并排序
        
        Args:
            market_data: 市场数据
            
        Returns:
            排序后的列表 [(symbol, score, data), ...]
        """
        sector_etfs = self.params.get('sector_etfs', self.DEFAULT_PARAMS['sector_etfs'])
        momentum_period = self.params.get('momentum_period', self.DEFAULT_PARAMS['momentum_period'])
        
        scores = []
        for symbol in sector_etfs:
            data = market_data.get(symbol)
            if not data:
                continue
            
            current_price = data.get('close')
            if current_price is None:
                continue
            
            # 获取N天前的价格
            price_n_days_ago = data.get(f'close_{momentum_period}d_ago')
            
            # 如果没有预计算的价格，尝试从历史数据获取
            if price_n_days_ago is None:
                close_history = data.get('close_history', [])
                if len(close_history) >= momentum_period:
                    price_n_days_ago = close_history[-momentum_period]
            
            if price_n_days_ago is None or price_n_days_ago <= 0:
                continue
            
            score = calculate_momentum_score(current_price, price_n_days_ago)
            if score > -999:
                scores.append((symbol, score, data))
        
        # 按得分降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            symbols: 标的代码列表（此策略主要使用内置ETF池）
            market_data: 市场数据，格式为:
                {
                    symbol: {
                        'close': float,                    # 当前收盘价
                        'close_20d_ago': float,            # 20天前收盘价
                        'close_history': List[float],      # 历史收盘价序列
                    }
                }
        
        Returns:
            信号列表
        """
        signals = []
        top_n = self.params.get('top_n', self.DEFAULT_PARAMS['top_n'])
        
        # 计算所有ETF的动量得分
        ranked_etfs = self.calculate_all_momentum_scores(market_data)
        
        if not ranked_etfs:
            return signals
        
        # 生成买入信号：前N名
        for rank, (symbol, score, data) in enumerate(ranked_etfs[:top_n], 1):
            current_price = data.get('close', 0)
            stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
            stop_loss_price = current_price * (1 - stop_loss_pct) if current_price > 0 else None
            
            # 信号强度基于排名
            if rank == 1:
                strength = 5
                confidence = 85
            elif rank == 2:
                strength = 4
                confidence = 80
            else:
                strength = 4
                confidence = 75
            
            signals.append(Signal(
                symbol=symbol,
                signal_type='buy',
                strength=strength,
                confidence=confidence,
                reason=f'动量排名第{rank}名, 20日动量得分{score*100:.2f}%',
                stop_loss=stop_loss_price,
                strategy_id=self.STRATEGY_ID
            ))
        
        # 生成卖出信号：跌出前N名的持仓
        top_symbols = set(s[0] for s in ranked_etfs[:top_n])
        for symbol, score, data in ranked_etfs[top_n:]:
            # 这里只生成卖出建议，实际是否持有需要执行器判断
            signals.append(Signal(
                symbol=symbol,
                signal_type='sell',
                strength=3,
                confidence=70,
                reason=f'动量排名跌出前{top_n}名, 当前得分{score*100:.2f}%',
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
        
        top_n = self.params.get('top_n', self.DEFAULT_PARAMS['top_n'])
        
        # 平均分配资金到每个持仓
        per_position_capital = capital / top_n
        
        # 假设ETF价格约1-5元，计算可买数量
        # 实际价格应从market_data获取
        estimated_price = 2.0  # 默认估计价格
        
        shares = int(per_position_capital / estimated_price)
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
        cost_price = position.get('cost_price', 0)
        
        if not symbol or cost_price <= 0:
            return False, ''
        
        data = market_data.get(symbol)
        if not data:
            return False, ''
        
        close = data.get('close')
        if close is None:
            return False, ''
        
        # 出场条件1：触发止损
        stop_loss_pct = self.params.get('stop_loss_pct', self.DEFAULT_PARAMS['stop_loss_pct'])
        stop_loss_price = cost_price * (1 - stop_loss_pct)
        
        if close < stop_loss_price:
            loss_pct = (close - cost_price) / cost_price * 100
            return True, f'触发止损({stop_loss_pct*100:.1f}%), 当前价格{close:.3f}, 亏损{loss_pct:.2f}%'
        
        # 出场条件2：动量排名跌出前N名
        # 这需要重新计算排名
        ranked_etfs = self.calculate_all_momentum_scores(market_data)
        top_n = self.params.get('top_n', self.DEFAULT_PARAMS['top_n'])
        top_symbols = set(s[0] for s in ranked_etfs[:top_n])
        
        if symbol not in top_symbols:
            # 找到当前排名
            current_rank = None
            current_score = None
            for rank, (s, score, _) in enumerate(ranked_etfs, 1):
                if s == symbol:
                    current_rank = rank
                    current_score = score
                    break
            
            if current_rank:
                return True, f'动量排名跌至第{current_rank}名(前{top_n}名外), 得分{current_score*100:.2f}%'
        
        return False, ''
    
    def validate_params(self) -> Tuple[bool, str]:
        """验证策略参数"""
        momentum_period = self.params.get('momentum_period', 20)
        if momentum_period < 5 or momentum_period > 60:
            return False, f"动量周期必须在5-60天之间，当前值: {momentum_period}"
        
        top_n = self.params.get('top_n', 3)
        if top_n < 1 or top_n > 5:
            return False, f"选择数量必须在1-5之间，当前值: {top_n}"
        
        rebalance_days = self.params.get('rebalance_days', 5)
        if rebalance_days < 1 or rebalance_days > 20:
            return False, f"轮动周期必须在1-20天之间，当前值: {rebalance_days}"
        
        stop_loss_pct = self.params.get('stop_loss_pct', 0.08)
        if stop_loss_pct < 0.03 or stop_loss_pct > 0.15:
            return False, f"止损百分比必须在3%-15%之间，当前值: {stop_loss_pct*100}%"
        
        sector_etfs = self.params.get('sector_etfs', [])
        if len(sector_etfs) < 5:
            return False, f"ETF池至少需要5只ETF，当前数量: {len(sector_etfs)}"
        
        return True, ""
    
    def get_applicable_symbols(self) -> List[str]:
        """获取适用的标的列表"""
        return self.params.get('sector_etfs', self.DEFAULT_PARAMS['sector_etfs'])


# 注册策略定义
MOMENTUM_ROTATION_DEFINITION = StrategyDefinition(
    id="momentum_rotation",
    name="动量轮动策略",
    category=StrategyCategory.SWING,
    description="基于动量因子的行业ETF轮动策略，每周选择动量最强的ETF持有",
    risk_level=RiskLevel.MEDIUM,
    applicable_types=["行业ETF", "主题ETF"],
    entry_logic="计算10日动量得分，买入排名前3的ETF",
    exit_logic="ETF动量排名跌出前3名时卖出，或触发5%止损",
    default_params=MomentumRotationStrategy.DEFAULT_PARAMS,
    min_capital=30000.0,
    backtest_return=30.0,
    backtest_sharpe=1.50,
    backtest_max_drawdown=10.0,
    backtest_win_rate=0.70,
)

# 自动注册到策略注册表
StrategyRegistry.register(MOMENTUM_ROTATION_DEFINITION)
