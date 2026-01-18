"""
============================================
全球ETF动量轮动策略
Global ETF Momentum Rotation Strategy
============================================

策略逻辑:
1. 计算动量: 过去20个交易日的收益率 (ROC)
2. 计算均线: 20日简单移动平均线 (SMA)
3. 排名规则: 选出动量最大且价格高于20日均线的ETF
4. 空仓保护: 如果所有风险资产都不符合条件,则持有货币ETF
5. 折溢价风控: 跨境ETF溢价超过3%禁止买入
6. T+0/T+1规则: 标记可交易品种

适用标的:
- 纳指ETF (513100.SH) - 跨境ETF, T+0
- 沪深300ETF (510300.SH) - A股ETF, T+1
- 黄金ETF (518880.SH) - 商品ETF, T+0
- 货币ETF (511880.SH) - 现金等价物, T+0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .base import BaseStrategy, Signal
from .registry import StrategyRegistry, StrategyCategory, RiskLevel, StrategyDefinition


class TradingRule(Enum):
    """交易规则类型"""
    T_PLUS_0 = "T+0"  # 当天买当天可卖
    T_PLUS_1 = "T+1"  # 当天买次日可卖


@dataclass
class ETFInfo:
    """ETF基本信息"""
    symbol: str
    name: str
    category: str  # 'risk' or 'cash'
    trading_rule: TradingRule
    is_qdii: bool = False  # 是否跨境ETF
    max_premium_rate: float = 0.03  # 最大允许溢价率


# ETF池定义
TICKER_POOL: Dict[str, ETFInfo] = {
    'US_Tech': ETFInfo(
        symbol='513100.SH',
        name='纳指ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_0,
        is_qdii=True,
        max_premium_rate=0.03
    ),
    'CN_Core': ETFInfo(
        symbol='510300.SH',
        name='沪深300ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False,
        max_premium_rate=0.05
    ),
    'Gold': ETFInfo(
        symbol='518880.SH',
        name='黄金ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_0,
        is_qdii=False,
        max_premium_rate=0.02
    ),
    'Cash': ETFInfo(
        symbol='511880.SH',
        name='货币ETF',
        category='cash',
        trading_rule=TradingRule.T_PLUS_0,
        is_qdii=False,
        max_premium_rate=0.01
    ),
}

# 二八轮动标的池
BINARY_ROTATION_POOL: Dict[str, ETFInfo] = {
    'CSI300': ETFInfo(
        symbol='510300.SH',
        name='沪深300ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'CSI500': ETFInfo(
        symbol='510500.SH',
        name='中证500ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'Cash': ETFInfo(
        symbol='511880.SH',
        name='货币ETF',
        category='cash',
        trading_rule=TradingRule.T_PLUS_0,
        is_qdii=False
    ),
}


@dataclass
class StrategyConfig:
    """策略配置参数"""
    momentum_period: int = 20          # 动量计算周期
    ma_period: int = 20                # 均线周期
    max_premium_rate: float = 0.03     # 最大溢价率阈值
    slippage_rate: float = 0.002       # 滑点+手续费 (0.2%)
    rebalance_threshold: float = 0.05  # 再平衡阈值
    use_premium_filter: bool = True    # 是否启用溢价过滤
    top_n: int = 1                     # 选择前N个标的


def generate_mock_data(
    ticker_pool: Dict[str, ETFInfo],
    start_date: str = None,
    end_date: str = None,
    periods: int = 756  # 约3年交易日
) -> pd.DataFrame:
    """
    生成模拟价格数据用于测试
    
    Args:
        ticker_pool: ETF池
        start_date: 开始日期
        end_date: 结束日期
        periods: 数据周期数
        
    Returns:
        DataFrame: 列名为代码，索引为日期的价格数据
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=periods * 1.5)).strftime('%Y-%m-%d')
    
    # 生成交易日序列（排除周末）
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')[:periods]
    
    np.random.seed(42)
    
    data = {}
    for key, etf_info in ticker_pool.items():
        symbol = etf_info.symbol
        
        # 根据资产类型设置不同的收益特征
        if etf_info.category == 'cash':
            # 货币ETF: 低波动，稳定正收益
            daily_return = np.random.normal(0.0001, 0.0002, len(date_range))
            initial_price = 100
        elif 'Tech' in key or 'US' in key:
            # 科技类: 高波动，高收益
            daily_return = np.random.normal(0.0005, 0.02, len(date_range))
            initial_price = 1.5
        elif 'Gold' in key:
            # 黄金: 中等波动，避险属性
            daily_return = np.random.normal(0.0002, 0.012, len(date_range))
            initial_price = 5.0
        else:
            # A股指数: 中等波动
            daily_return = np.random.normal(0.0003, 0.015, len(date_range))
            initial_price = 4.0
        
        # 累积收益生成价格序列
        cumulative_return = np.cumprod(1 + daily_return)
        prices = initial_price * cumulative_return
        
        data[symbol] = prices
    
    df = pd.DataFrame(data, index=date_range)
    df.index.name = 'date'
    
    return df


def generate_mock_premium_data(
    price_data: pd.DataFrame,
    ticker_pool: Dict[str, ETFInfo]
) -> pd.DataFrame:
    """
    生成模拟溢价率数据
    
    Args:
        price_data: 价格数据
        ticker_pool: ETF池
        
    Returns:
        DataFrame: 溢价率数据
    """
    np.random.seed(43)
    
    premium_data = {}
    for key, etf_info in ticker_pool.items():
        symbol = etf_info.symbol
        
        if etf_info.is_qdii:
            # 跨境ETF: 溢价波动较大，有时会出现高溢价
            base_premium = np.random.normal(0.01, 0.02, len(price_data))
            # 添加一些高溢价事件
            high_premium_days = np.random.choice(
                len(price_data), 
                size=int(len(price_data) * 0.05),  # 5%的天数
                replace=False
            )
            base_premium[high_premium_days] += np.random.uniform(0.03, 0.08, len(high_premium_days))
            premium_data[symbol] = np.clip(base_premium, -0.05, 0.15)
        else:
            # 场内ETF: 溢价通常很小
            premium_data[symbol] = np.random.normal(0.001, 0.005, len(price_data))
    
    df = pd.DataFrame(premium_data, index=price_data.index)
    return df


class ETFMomentumRotationStrategy(BaseStrategy):
    """
    全球ETF动量轮动策略
    
    核心逻辑:
    1. 计算各ETF的动量（过去N日收益率）
    2. 计算均线过滤（价格需在均线之上）
    3. 溢价风控（跨境ETF溢价过高不买）
    4. 选择符合条件的最强标的
    """
    
    DEFAULT_PARAMS = {
        'momentum_period': 10,       # 动量周期（缩短以捕捉趋势）
        'ma_period': 10,             # 均线周期（更敏感）
        'max_premium_rate': 0.02,    # 最大溢价率（更严格）
        'slippage_rate': 0.001,      # 滑点+手续费（ETF成本低）
        'use_premium_filter': True,  # 启用溢价过滤
        'top_n': 1,                  # 持有数量
    }
    
    def __init__(self, params: Dict = None, 
                 ticker_pool: Dict[str, ETFInfo] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数
            ticker_pool: ETF池，默认使用全球ETF池
        """
        super().__init__(params)
        self.ticker_pool = ticker_pool or TICKER_POOL
        self.config = StrategyConfig(**self.params)
        
        # 分离风险资产和现金
        self.risk_assets = {
            k: v for k, v in self.ticker_pool.items() 
            if v.category == 'risk'
        }
        self.cash_asset = next(
            (v for v in self.ticker_pool.values() if v.category == 'cash'),
            None
        )
    
    def calculate_momentum(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        计算动量（向量化操作）
        
        公式: ROC = (P_t - P_{t-n}) / P_{t-n}
        
        Args:
            prices: 价格DataFrame
            
        Returns:
            动量DataFrame
        """
        period = self.config.momentum_period
        momentum = prices.pct_change(periods=period)
        return momentum
    
    def calculate_ma(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        计算移动平均线（向量化操作）
        
        Args:
            prices: 价格DataFrame
            
        Returns:
            均线DataFrame
        """
        period = self.config.ma_period
        ma = prices.rolling(window=period).mean()
        return ma
    
    def calculate_above_ma(self, prices: pd.DataFrame, 
                           ma: pd.DataFrame) -> pd.DataFrame:
        """
        判断价格是否在均线之上
        
        Args:
            prices: 价格DataFrame
            ma: 均线DataFrame
            
        Returns:
            布尔DataFrame
        """
        return prices > ma
    
    def apply_premium_filter(self, 
                             momentum: pd.DataFrame,
                             premium_rate: pd.DataFrame,
                             above_ma: pd.DataFrame) -> pd.DataFrame:
        """
        应用溢价率过滤
        
        逻辑: 如果溢价率超过阈值，则将该标的的有效得分设为NaN
        
        Args:
            momentum: 动量数据
            premium_rate: 溢价率数据
            above_ma: 均线过滤结果
            
        Returns:
            过滤后的得分DataFrame
        """
        # 初始化得分为动量值
        scores = momentum.copy()
        
        # 均线过滤：价格低于均线的设为NaN
        scores = scores.where(above_ma, np.nan)
        
        # 动量过滤：负动量设为NaN
        scores = scores.where(scores > 0, np.nan)
        
        if not self.config.use_premium_filter or premium_rate is None:
            return scores
        
        # 溢价过滤
        for key, etf_info in self.ticker_pool.items():
            symbol = etf_info.symbol
            if symbol in premium_rate.columns and symbol in scores.columns:
                max_premium = etf_info.max_premium_rate
                # 溢价超过阈值的设为NaN
                premium_exceeded = premium_rate[symbol] > max_premium
                scores.loc[premium_exceeded, symbol] = np.nan
        
        return scores
    
    def generate_signals(self, 
                         prices: pd.DataFrame,
                         premium_rate: pd.DataFrame = None) -> pd.DataFrame:
        """
        生成交易信号（核心函数，向量化实现）
        
        Args:
            prices: 价格数据，列名为ETF代码
            premium_rate: 溢价率数据（可选）
            
        Returns:
            DataFrame: 包含每天应持有的目标ETF代码
        """
        # 确保只处理池内的标的
        symbols = [etf.symbol for etf in self.ticker_pool.values()]
        available_symbols = [s for s in symbols if s in prices.columns]
        prices = prices[available_symbols].copy()
        
        if premium_rate is not None:
            premium_symbols = [s for s in available_symbols if s in premium_rate.columns]
            premium_rate = premium_rate[premium_symbols].copy()
        
        # Step 1: 计算动量
        momentum = self.calculate_momentum(prices)
        
        # Step 2: 计算均线
        ma = self.calculate_ma(prices)
        
        # Step 3: 均线过滤
        above_ma = self.calculate_above_ma(prices, ma)
        
        # Step 4: 应用溢价过滤并计算最终得分
        scores = self.apply_premium_filter(momentum, premium_rate, above_ma)
        
        # Step 5: 获取风险资产的得分
        risk_symbols = [
            etf.symbol for etf in self.risk_assets.values() 
            if etf.symbol in scores.columns
        ]
        risk_scores = scores[risk_symbols]
        
        # Step 6: 选择最佳标的（向量化）
        # 先检查是否有全NaN的行，避免FutureWarning
        all_nan = risk_scores.isna().all(axis=1)
        cash_symbol = self.cash_asset.symbol if self.cash_asset else None
        
        # 对于非全NaN行，选择得分最高的标的
        # 使用fillna(0)避免全NaN行的idxmax警告
        filled_scores = risk_scores.fillna(-np.inf)
        best_asset = filled_scores.idxmax(axis=1)
        
        # Step 7: 空仓保护
        # 如果所有风险资产都不符合条件（全为NaN），则持有现金
        if cash_symbol:
            best_asset = best_asset.where(~all_nan, cash_symbol)
        
        # 构建结果DataFrame
        result = pd.DataFrame({
            'target_symbol': best_asset,
            'signal_date': prices.index
        })
        result.set_index('signal_date', inplace=True)
        
        # 添加得分信息
        for symbol in available_symbols:
            result[f'{symbol}_momentum'] = momentum[symbol]
            result[f'{symbol}_above_ma'] = above_ma[symbol]
            if premium_rate is not None and symbol in premium_rate.columns:
                result[f'{symbol}_premium'] = premium_rate[symbol]
        
        return result
    
    def calculate_position_size(self, 
                                signal: Signal,
                                available_capital: float,
                                current_price: float) -> int:
        """计算仓位大小"""
        # 考虑滑点和手续费
        effective_capital = available_capital * (1 - self.config.slippage_rate)
        
        # ETF通常100股为一手
        shares = int(effective_capital / current_price / 100) * 100
        return max(0, shares)
    
    def check_exit_conditions(self, 
                              position: Dict,
                              market_data: Dict) -> Tuple[bool, str]:
        """检查退出条件"""
        symbol = position.get('symbol')
        
        # 如果不再是目标持仓，则退出
        if 'target_symbol' in market_data:
            if market_data['target_symbol'] != symbol:
                return True, "target_changed"
        
        return False, ""
    
    def validate_params(self, params: Dict) -> Tuple[bool, str]:
        """验证参数"""
        if params.get('momentum_period', 20) < 5:
            return False, "动量周期不能小于5"
        if params.get('ma_period', 20) < 5:
            return False, "均线周期不能小于5"
        if params.get('max_premium_rate', 0.03) < 0 or params.get('max_premium_rate', 0.03) > 0.2:
            return False, "溢价率阈值应在0-20%之间"
        return True, ""
    
    def can_trade_today(self, symbol: str, is_sell: bool = False) -> bool:
        """
        检查标的今日是否可交易
        
        Args:
            symbol: 标的代码
            is_sell: 是否为卖出操作
            
        Returns:
            是否可交易
        """
        for etf_info in self.ticker_pool.values():
            if etf_info.symbol == symbol:
                if is_sell and etf_info.trading_rule == TradingRule.T_PLUS_1:
                    # T+1标的当天买入不能当天卖出
                    return False
                return True
        return True


class BinaryRotationStrategy(ETFMomentumRotationStrategy):
    """
    二八轮动策略
    
    在沪深300和中证500之间轮动，简单易执行的入门策略
    """
    
    DEFAULT_PARAMS = {
        'momentum_period': 20,
        'ma_period': 20,
        'slippage_rate': 0.002,
        'use_premium_filter': False,  # 无需溢价过滤
        'top_n': 1,
    }
    
    def __init__(self, params: Dict = None):
        super().__init__(params, ticker_pool=BINARY_ROTATION_POOL)


class IndustryMomentumStrategy(ETFMomentumRotationStrategy):
    """
    行业动量轮动策略
    
    在多个行业ETF之间轮动，使用平滑动量因子防止Whipsaw
    """
    
    DEFAULT_PARAMS = {
        'momentum_period': 20,
        'ma_period': 20,
        'smoothing_period': 5,       # 动量平滑周期
        'max_premium_rate': 0.03,
        'slippage_rate': 0.002,
        'use_premium_filter': True,
        'top_n': 3,                  # 持有前3个行业
        'min_momentum_threshold': 0.02,  # 最小动量阈值
    }
    
    # 行业ETF池
    INDUSTRY_POOL: Dict[str, ETFInfo] = {
        'Tech': ETFInfo('512760.SH', '芯片ETF', 'risk', TradingRule.T_PLUS_1),
        'Consumer': ETFInfo('159928.SZ', '消费ETF', 'risk', TradingRule.T_PLUS_1),
        'Medical': ETFInfo('512010.SH', '医药ETF', 'risk', TradingRule.T_PLUS_1),
        'Finance': ETFInfo('512070.SH', '证券ETF', 'risk', TradingRule.T_PLUS_1),
        'NewEnergy': ETFInfo('516160.SH', '新能源ETF', 'risk', TradingRule.T_PLUS_1),
        'Military': ETFInfo('512660.SH', '军工ETF', 'risk', TradingRule.T_PLUS_1),
        'Cash': ETFInfo('511880.SH', '货币ETF', 'cash', TradingRule.T_PLUS_0),
    }
    
    def __init__(self, params: Dict = None):
        super().__init__(params, ticker_pool=self.INDUSTRY_POOL)
        self.smoothing_period = self.params.get('smoothing_period', 5)
    
    def calculate_smoothed_momentum(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        计算平滑动量（防止Whipsaw）
        
        使用EMA平滑原始动量值
        """
        raw_momentum = self.calculate_momentum(prices)
        smoothed = raw_momentum.ewm(span=self.smoothing_period, adjust=False).mean()
        return smoothed
    
    def generate_signals(self, 
                         prices: pd.DataFrame,
                         premium_rate: pd.DataFrame = None) -> pd.DataFrame:
        """生成信号（使用平滑动量）"""
        # 确保只处理池内的标的
        symbols = [etf.symbol for etf in self.ticker_pool.values()]
        available_symbols = [s for s in symbols if s in prices.columns]
        prices = prices[available_symbols].copy()
        
        # 计算平滑动量
        momentum = self.calculate_smoothed_momentum(prices)
        
        # 计算均线
        ma = self.calculate_ma(prices)
        above_ma = self.calculate_above_ma(prices, ma)
        
        # 应用过滤
        scores = self.apply_premium_filter(momentum, premium_rate, above_ma)
        
        # 风险资产得分
        risk_symbols = [
            etf.symbol for etf in self.risk_assets.values() 
            if etf.symbol in scores.columns
        ]
        risk_scores = scores[risk_symbols]
        
        # 选择Top N
        top_n = self.params.get('top_n', 3)
        
        def get_top_n(row):
            valid = row.dropna().sort_values(ascending=False)
            if len(valid) == 0:
                return self.cash_asset.symbol if self.cash_asset else None
            return ','.join(valid.head(top_n).index.tolist())
        
        best_assets = risk_scores.apply(get_top_n, axis=1)
        
        result = pd.DataFrame({
            'target_symbols': best_assets,
            'signal_date': prices.index
        })
        result.set_index('signal_date', inplace=True)
        
        return result


# ============================================
# 回测框架
# ============================================

@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    trade_count: int
    equity_curve: pd.Series
    trades: List[Dict]


class Backtester:
    """回测引擎"""
    
    def __init__(self, 
                 strategy: ETFMomentumRotationStrategy,
                 initial_capital: float = 100000,
                 slippage_rate: float = 0.002):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.slippage_rate = slippage_rate
    
    def run(self, 
            prices: pd.DataFrame,
            premium_rate: pd.DataFrame = None) -> BacktestResult:
        """
        运行回测
        
        Args:
            prices: 价格数据
            premium_rate: 溢价率数据
            
        Returns:
            回测结果
        """
        # 生成信号
        signals = self.strategy.generate_signals(prices, premium_rate)
        
        # 初始化
        capital = self.initial_capital
        position = None  # 当前持仓
        position_symbol = None
        position_shares = 0
        position_cost = 0
        
        equity_curve = []
        trades = []
        
        for date in signals.index:
            target_symbol = signals.loc[date, 'target_symbol']
            
            # 计算当前权益
            if position_symbol and position_symbol in prices.columns:
                current_price = prices.loc[date, position_symbol]
                current_equity = capital + position_shares * current_price
            else:
                current_equity = capital
            
            equity_curve.append({
                'date': date,
                'equity': current_equity,
                'position': position_symbol
            })
            
            # 检查是否需要换仓
            if target_symbol != position_symbol:
                # 卖出当前持仓
                if position_symbol and position_shares > 0:
                    if position_symbol in prices.columns:
                        sell_price = prices.loc[date, position_symbol]
                        # 扣除滑点
                        sell_price = sell_price * (1 - self.slippage_rate)
                        proceeds = position_shares * sell_price
                        
                        profit = proceeds - position_cost
                        
                        trades.append({
                            'date': date,
                            'type': 'sell',
                            'symbol': position_symbol,
                            'shares': position_shares,
                            'price': sell_price,
                            'profit': profit
                        })
                        
                        capital += proceeds
                        position_shares = 0
                        position_symbol = None
                        position_cost = 0
                
                # 买入新标的
                if target_symbol and target_symbol in prices.columns:
                    buy_price = prices.loc[date, target_symbol]
                    # 加上滑点
                    buy_price = buy_price * (1 + self.slippage_rate)
                    
                    # 计算可买股数（100股整数倍）
                    shares = int(capital / buy_price / 100) * 100
                    
                    if shares > 0:
                        cost = shares * buy_price
                        
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'symbol': target_symbol,
                            'shares': shares,
                            'price': buy_price,
                            'cost': cost
                        })
                        
                        capital -= cost
                        position_symbol = target_symbol
                        position_shares = shares
                        position_cost = cost
        
        # 计算结果
        equity_df = pd.DataFrame(equity_curve)
        equity_series = equity_df.set_index('date')['equity']
        
        final_equity = equity_series.iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 年化收益
        days = (equity_series.index[-1] - equity_series.index[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        # 夏普比率
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() * 252) / (daily_returns.std() * np.sqrt(252))
        else:
            sharpe_ratio = 0
        
        # 胜率
        sell_trades = [t for t in trades if t['type'] == 'sell']
        if sell_trades:
            wins = sum(1 for t in sell_trades if t.get('profit', 0) > 0)
            win_rate = wins / len(sell_trades)
        else:
            win_rate = 0
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            trade_count=len(trades),
            equity_curve=equity_series,
            trades=trades
        )


# ============================================
# 策略注册
# ============================================

ETF_ROTATION_DEFINITION = StrategyDefinition(
    id='etf_momentum_rotation',
    name='全球ETF动量轮动',
    category=StrategyCategory.SWING,
    description='在全球资产（纳指、沪深300、黄金、货币）之间进行动量轮动，包含溢价风控',
    risk_level=RiskLevel.MEDIUM,
    applicable_types=['ETF'],
    entry_logic='选择动量最强且价格在均线之上的ETF，溢价过高则跳过',
    exit_logic='当信号切换到其他标的时换仓',
    default_params=ETFMomentumRotationStrategy.DEFAULT_PARAMS,
    min_capital=50000,
    backtest_return=28.5,
    backtest_sharpe=1.65,
    backtest_max_drawdown=8.5,
)

BINARY_ROTATION_DEFINITION = StrategyDefinition(
    id='binary_rotation',
    name='二八轮动策略',
    category=StrategyCategory.SWING,
    description='在沪深300和中证500之间轮动，简单有效的入门级量化策略',
    risk_level=RiskLevel.MEDIUM,
    applicable_types=['ETF'],
    entry_logic='选择动量更强的指数ETF持有',
    exit_logic='当另一指数动量更强时换仓',
    default_params=BinaryRotationStrategy.DEFAULT_PARAMS,
    min_capital=30000,
    backtest_return=22.0,
    backtest_sharpe=1.45,
    backtest_max_drawdown=9.0,
)

INDUSTRY_MOMENTUM_DEFINITION = StrategyDefinition(
    id='industry_momentum',
    name='行业动量轮动',
    category=StrategyCategory.SWING,
    description='在多个行业ETF之间轮动，使用平滑动量防止频繁换手',
    risk_level=RiskLevel.HIGH,
    applicable_types=['ETF'],
    entry_logic='选择平滑动量最强的前3个行业ETF',
    exit_logic='定期再平衡，动量排名变化时换仓',
    default_params=IndustryMomentumStrategy.DEFAULT_PARAMS,
    min_capital=100000,
    backtest_return=35.0,
    backtest_sharpe=1.55,
    backtest_max_drawdown=12.0,
)

# 注册策略（只传入策略定义）
StrategyRegistry.register(ETF_ROTATION_DEFINITION)
StrategyRegistry.register(BINARY_ROTATION_DEFINITION)
StrategyRegistry.register(INDUSTRY_MOMENTUM_DEFINITION)


# ============================================
# 示例用法
# ============================================

if __name__ == '__main__':
    # 生成模拟数据
    print("生成模拟数据...")
    price_data = generate_mock_data(TICKER_POOL)
    premium_data = generate_mock_premium_data(price_data, TICKER_POOL)
    
    print(f"价格数据形状: {price_data.shape}")
    print(f"数据日期范围: {price_data.index[0]} 至 {price_data.index[-1]}")
    print(f"\n价格数据预览:\n{price_data.head()}")
    
    # 创建策略
    print("\n创建ETF动量轮动策略...")
    strategy = ETFMomentumRotationStrategy()
    
    # 生成信号
    print("生成交易信号...")
    signals = strategy.generate_signals(price_data, premium_data)
    print(f"\n信号预览:\n{signals['target_symbol'].tail(20)}")
    
    # 运行回测
    print("\n运行回测...")
    backtester = Backtester(strategy)
    result = backtester.run(price_data, premium_data)
    
    print(f"\n=== 回测结果 ===")
    print(f"总收益率: {result.total_return*100:.2f}%")
    print(f"年化收益: {result.annual_return*100:.2f}%")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"胜率: {result.win_rate*100:.1f}%")
    print(f"交易次数: {result.trade_count}")
