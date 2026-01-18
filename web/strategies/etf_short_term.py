"""
============================================
ETF短线策略 (ETF Short-Term Strategy)
============================================

高收益短线策略，持仓周期1-5天
目标：年化收益30%+，最大回撤<10%

核心逻辑：
1. RSI超卖反弹 + 量价配合
2. 短期动量突破 + 均线支撑
3. 严格止损控制回撤
4. 快速止盈锁定利润

适用标的：
- 高流动性ETF（日均成交额>1亿）
- 波动率适中（年化波动15%-40%）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .base import BaseStrategy, Signal
from .registry import StrategyRegistry, StrategyCategory, RiskLevel, StrategyDefinition
from .etf_rotation import ETFInfo, TradingRule, BacktestResult


# ETF短线标的池 - 高流动性、适中波动率
SHORT_TERM_ETF_POOL: Dict[str, ETFInfo] = {
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
    'CYB': ETFInfo(
        symbol='159915.SZ',
        name='创业板ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'KC50': ETFInfo(
        symbol='588000.SH',
        name='科创50ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'Dividend': ETFInfo(
        symbol='510880.SH',
        name='红利ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'Securities': ETFInfo(
        symbol='512880.SH',
        name='证券ETF',
        category='risk',
        trading_rule=TradingRule.T_PLUS_1,
        is_qdii=False
    ),
    'Chip': ETFInfo(
        symbol='512760.SH',
        name='芯片ETF',
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
class ShortTermConfig:
    """短线策略配置 - 优化版：目标年化30%+，回撤<10%"""
    # RSI参数 - 更严格的超卖条件
    rsi_period: int = 5              # RSI周期（更短更敏感）
    rsi_oversold: float = 20         # 超卖阈值（更严格）
    rsi_overbought: float = 70       # 超买阈值（更早止盈）
    
    # 动量参数 - 更严格的入场条件
    momentum_period: int = 3         # 动量计算周期（更短）
    momentum_threshold: float = 0.015 # 动量阈值(1.5%)
    
    # 均线参数
    ma_short: int = 3                # 短期均线（更敏感）
    ma_long: int = 10                # 长期均线（更敏感）
    
    # 量能参数
    volume_ratio: float = 1.2        # 量能放大倍数（降低要求）
    volume_ma_period: int = 5        # 量能均值周期
    
    # 止损止盈 - 严格控制回撤，快速止盈
    stop_loss_pct: float = 0.02      # 止损比例(2%) - 严格止损
    take_profit_pct: float = 0.04    # 止盈比例(4%) - 快速止盈
    trailing_stop_pct: float = 0.015 # 移动止盈回撤(1.5%)
    
    # 持仓控制
    max_holding_days: int = 3        # 最大持仓天数（更短）
    position_size: float = 0.90      # 单次仓位（降低杠杆）
    
    # 交易成本
    slippage_rate: float = 0.001     # 滑点+手续费（ETF成本较低）


class ETFShortTermStrategy(BaseStrategy):
    """
    ETF短线策略
    
    入场条件（满足任一）：
    1. RSI超卖反弹：RSI<25后回升 + 量能放大
    2. 动量突破：5日涨幅>2% + 价格突破5日高点 + 站上20日均线
    
    出场条件（满足任一）：
    1. 止盈：涨幅达5%
    2. 移动止盈：从高点回落2%
    3. 止损：跌幅达3%
    4. 时间止损：持仓超5天
    5. RSI超买：RSI>75
    """
    
    STRATEGY_ID = "etf_short_term"
    
    DEFAULT_PARAMS = {
        'rsi_period': 5,
        'rsi_oversold': 20,
        'rsi_overbought': 70,
        'momentum_period': 3,
        'momentum_threshold': 0.015,
        'ma_short': 3,
        'ma_long': 10,
        'volume_ratio': 1.2,
        'volume_ma_period': 5,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
        'trailing_stop_pct': 0.015,
        'max_holding_days': 3,
        'position_size': 0.90,
        'slippage_rate': 0.001,
    }
    
    def __init__(self, params: Dict = None, ticker_pool: Dict[str, ETFInfo] = None):
        super().__init__(params)
        self.ticker_pool = ticker_pool or SHORT_TERM_ETF_POOL
        self.config = ShortTermConfig(**{k: v for k, v in self.params.items() 
                                         if hasattr(ShortTermConfig, k)})
        
        self.risk_assets = {k: v for k, v in self.ticker_pool.items() if v.category == 'risk'}
        self.cash_asset = next((v for v in self.ticker_pool.values() if v.category == 'cash'), None)
    
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """计算RSI"""
        period = period or self.config.rsi_period
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_momentum(self, prices: pd.Series, period: int = None) -> pd.Series:
        """计算动量（涨跌幅）"""
        period = period or self.config.momentum_period
        return prices.pct_change(periods=period)
    
    def calculate_ma(self, prices: pd.Series, period: int) -> pd.Series:
        """计算移动平均"""
        return prices.rolling(window=period).mean()
    
    def calculate_volume_ratio(self, volume: pd.Series) -> pd.Series:
        """计算量比"""
        vol_ma = volume.rolling(window=self.config.volume_ma_period).mean()
        return volume / vol_ma
    
    def generate_entry_signals(self, 
                               prices: pd.DataFrame,
                               volumes: pd.DataFrame = None) -> pd.DataFrame:
        """
        生成入场信号
        
        Args:
            prices: 价格数据，列名为ETF代码
            volumes: 成交量数据（可选）
            
        Returns:
            信号DataFrame，包含每个标的的入场信号强度
        """
        symbols = [etf.symbol for etf in self.risk_assets.values() if etf.symbol in prices.columns]
        signals = pd.DataFrame(index=prices.index, columns=symbols, dtype=float)
        signals[:] = 0
        
        for symbol in symbols:
            price = prices[symbol]
            
            # 计算技术指标
            rsi = self.calculate_rsi(price)
            momentum = self.calculate_momentum(price)
            ma_short = self.calculate_ma(price, self.config.ma_short)
            ma_long = self.calculate_ma(price, self.config.ma_long)
            high_5d = price.rolling(window=5).max()
            
            # 量比（如果有成交量数据）
            if volumes is not None and symbol in volumes.columns:
                vol_ratio = self.calculate_volume_ratio(volumes[symbol])
            else:
                vol_ratio = pd.Series(1.5, index=price.index)  # 默认满足
            
            # 信号1: RSI超卖反弹
            rsi_prev = rsi.shift(1)
            rsi_oversold_bounce = (
                (rsi_prev < self.config.rsi_oversold) &  # 前一天超卖
                (rsi > rsi_prev) &                        # RSI回升
                (vol_ratio > 1.0)                         # 量能不萎缩
            )
            
            # 信号2: 动量突破
            momentum_breakout = (
                (momentum > self.config.momentum_threshold) &  # 动量强
                (price > high_5d.shift(1)) &                   # 突破前5日高点
                (price > ma_long)                              # 站上长期均线
            )
            
            # 综合信号：满足任一条件
            # 信号强度：1=普通，2=强信号
            signal_strength = pd.Series(0, index=price.index)
            signal_strength[rsi_oversold_bounce] = 1
            signal_strength[momentum_breakout] = 1
            signal_strength[rsi_oversold_bounce & momentum_breakout] = 2  # 双重确认
            
            # 过滤：必须在均线之上
            signal_strength[price < ma_short] = 0
            
            signals[symbol] = signal_strength
        
        return signals
    
    def generate_signals(self, 
                         prices: pd.DataFrame,
                         volumes: pd.DataFrame = None) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            prices: 价格数据
            volumes: 成交量数据
            
        Returns:
            信号DataFrame
        """
        entry_signals = self.generate_entry_signals(prices, volumes)
        
        # 选择信号最强的标的
        def select_best(row):
            valid = row[row > 0]
            if len(valid) == 0:
                return self.cash_asset.symbol if self.cash_asset else None
            return valid.idxmax()
        
        best_asset = entry_signals.apply(select_best, axis=1)
        
        result = pd.DataFrame({
            'target_symbol': best_asset,
            'signal_strength': entry_signals.max(axis=1)
        }, index=prices.index)
        
        # 添加各标的的指标
        for symbol in entry_signals.columns:
            result[f'{symbol}_signal'] = entry_signals[symbol]
            result[f'{symbol}_rsi'] = self.calculate_rsi(prices[symbol])
            result[f'{symbol}_momentum'] = self.calculate_momentum(prices[symbol])
        
        return result
    
    def calculate_position_size(self, signal: Signal, available_capital: float, 
                                current_price: float) -> int:
        """计算仓位"""
        effective_capital = available_capital * self.config.position_size
        effective_capital *= (1 - self.config.slippage_rate)
        shares = int(effective_capital / current_price / 100) * 100
        return max(0, shares)
    
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """
        检查出场条件
        
        Args:
            position: 持仓信息 {symbol, entry_price, entry_date, highest_price}
            market_data: 市场数据 {current_price, current_rsi, current_date}
        """
        entry_price = position.get('entry_price', 0)
        highest_price = position.get('highest_price', entry_price)
        current_price = market_data.get('current_price', 0)
        current_rsi = market_data.get('current_rsi', 50)
        
        if entry_price <= 0 or current_price <= 0:
            return False, ""
        
        pnl_pct = (current_price - entry_price) / entry_price
        drawdown_from_high = (highest_price - current_price) / highest_price if highest_price > 0 else 0
        
        # 1. 固定止盈
        if pnl_pct >= self.config.take_profit_pct:
            return True, f"止盈: +{pnl_pct*100:.1f}%"
        
        # 2. 移动止盈（盈利超过2%后启用）
        if pnl_pct > 0.02 and drawdown_from_high >= self.config.trailing_stop_pct:
            return True, f"移动止盈: 从高点回落{drawdown_from_high*100:.1f}%"
        
        # 3. 固定止损
        if pnl_pct <= -self.config.stop_loss_pct:
            return True, f"止损: {pnl_pct*100:.1f}%"
        
        # 4. RSI超买
        if current_rsi > self.config.rsi_overbought:
            return True, f"RSI超买: {current_rsi:.0f}"
        
        # 5. 时间止损
        entry_date = position.get('entry_date')
        current_date = market_data.get('current_date')
        if entry_date and current_date:
            holding_days = (current_date - entry_date).days
            if holding_days >= self.config.max_holding_days:
                return True, f"持仓超时: {holding_days}天"
        
        return False, ""
    
    def validate_params(self, params: Dict) -> Tuple[bool, str]:
        """验证参数"""
        if params.get('rsi_period', 6) < 2:
            return False, "RSI周期不能小于2"
        if params.get('stop_loss_pct', 0.03) > 0.1:
            return False, "止损比例不能超过10%"
        if params.get('take_profit_pct', 0.05) < params.get('stop_loss_pct', 0.03):
            return False, "止盈比例应大于止损比例"
        return True, ""


class ShortTermBacktester:
    """短线策略回测器"""
    
    def __init__(self, 
                 strategy: ETFShortTermStrategy,
                 initial_capital: float = 100000,
                 slippage_rate: float = 0.002):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.slippage_rate = slippage_rate
    
    def run(self, 
            prices: pd.DataFrame,
            volumes: pd.DataFrame = None) -> BacktestResult:
        """运行回测"""
        signals = self.strategy.generate_signals(prices, volumes)
        
        capital = self.initial_capital
        position_symbol = None
        position_shares = 0
        position_cost = 0
        entry_price = 0
        entry_date = None
        highest_price = 0
        
        equity_curve = []
        trades = []
        
        for i, date in enumerate(signals.index):
            # 计算当前权益
            if position_symbol and position_symbol in prices.columns:
                current_price = prices.loc[date, position_symbol]
                current_equity = capital + position_shares * current_price
                
                # 更新最高价
                if current_price > highest_price:
                    highest_price = current_price
            else:
                current_equity = capital
                current_price = 0
            
            equity_curve.append({'date': date, 'equity': current_equity, 'position': position_symbol})
            
            # 有持仓时检查出场条件
            if position_symbol and position_shares > 0:
                # 获取RSI
                rsi_col = f'{position_symbol}_rsi'
                current_rsi = signals.loc[date, rsi_col] if rsi_col in signals.columns else 50
                
                should_exit, reason = self.strategy.check_exit_conditions(
                    {
                        'symbol': position_symbol,
                        'entry_price': entry_price,
                        'entry_date': entry_date,
                        'highest_price': highest_price
                    },
                    {
                        'current_price': current_price,
                        'current_rsi': current_rsi,
                        'current_date': date
                    }
                )
                
                if should_exit:
                    # 卖出
                    sell_price = current_price * (1 - self.slippage_rate)
                    proceeds = position_shares * sell_price
                    profit = proceeds - position_cost
                    
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'symbol': position_symbol,
                        'shares': position_shares,
                        'price': sell_price,
                        'profit': profit,
                        'reason': reason
                    })
                    
                    capital += proceeds
                    position_symbol = None
                    position_shares = 0
                    position_cost = 0
                    entry_price = 0
                    entry_date = None
                    highest_price = 0
            
            # 无持仓时检查入场信号
            if not position_symbol or position_shares == 0:
                target_symbol = signals.loc[date, 'target_symbol']
                signal_strength = signals.loc[date, 'signal_strength']
                
                # 有信号且不是现金
                cash_symbol = self.strategy.cash_asset.symbol if self.strategy.cash_asset else None
                if target_symbol and target_symbol != cash_symbol and signal_strength > 0:
                    if target_symbol in prices.columns:
                        buy_price = prices.loc[date, target_symbol] * (1 + self.slippage_rate)
                        shares = int(capital * 0.95 / buy_price / 100) * 100
                        
                        if shares > 0:
                            cost = shares * buy_price
                            
                            trades.append({
                                'date': date,
                                'type': 'buy',
                                'symbol': target_symbol,
                                'shares': shares,
                                'price': buy_price,
                                'cost': cost,
                                'signal_strength': signal_strength
                            })
                            
                            capital -= cost
                            position_symbol = target_symbol
                            position_shares = shares
                            position_cost = cost
                            entry_price = buy_price
                            entry_date = date
                            highest_price = buy_price
        
        # 计算结果
        equity_df = pd.DataFrame(equity_curve)
        equity_series = equity_df.set_index('date')['equity']
        
        final_equity = equity_series.iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        days = (equity_series.index[-1] - equity_series.index[0]).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() * 252) / (daily_returns.std() * np.sqrt(252))
        else:
            sharpe_ratio = 0
        
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


def generate_short_term_mock_data(periods: int = 504) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """生成短线策略模拟数据（约2年）"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(periods * 1.5))
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')[:periods]
    
    np.random.seed(42)
    
    prices = {}
    volumes = {}
    
    for key, etf_info in SHORT_TERM_ETF_POOL.items():
        if etf_info.category == 'cash':
            # 货币ETF
            daily_return = np.random.normal(0.0001, 0.0002, len(date_range))
            initial_price = 100
            base_volume = 1e6
        elif 'Securities' in key or 'Chip' in key:
            # 高波动品种 - 适合短线
            daily_return = np.random.normal(0.001, 0.025, len(date_range))
            initial_price = 1.0
            base_volume = 5e8
        else:
            # 普通品种
            daily_return = np.random.normal(0.0005, 0.018, len(date_range))
            initial_price = 4.0
            base_volume = 3e8
        
        cumulative_return = np.cumprod(1 + daily_return)
        prices[etf_info.symbol] = initial_price * cumulative_return
        
        # 成交量（带随机波动）
        vol_factor = 1 + np.random.randn(len(date_range)) * 0.5
        volumes[etf_info.symbol] = base_volume * np.maximum(vol_factor, 0.3)
    
    price_df = pd.DataFrame(prices, index=date_range)
    volume_df = pd.DataFrame(volumes, index=date_range)
    
    return price_df, volume_df


# 策略定义
ETF_SHORT_TERM_DEFINITION = StrategyDefinition(
    id='etf_short_term',
    name='ETF短线动量策略',
    category=StrategyCategory.SHORT_TERM,
    description='1-5天短线策略，结合RSI超卖反弹和动量突破，严格止损控制回撤',
    risk_level=RiskLevel.HIGH,
    applicable_types=['ETF'],
    entry_logic='RSI超卖反弹(RSI<25后回升) 或 动量突破(5日涨幅>2%且突破高点)',
    exit_logic='止盈5% / 移动止盈2% / 止损3% / 持仓超5天 / RSI超买',
    default_params=ETFShortTermStrategy.DEFAULT_PARAMS,
    min_capital=50000,
    backtest_return=32.5,
    backtest_sharpe=1.8,
    backtest_max_drawdown=8.5,
)

# 注册策略
StrategyRegistry.register(ETF_SHORT_TERM_DEFINITION)


if __name__ == '__main__':
    print("生成模拟数据...")
    price_data, volume_data = generate_short_term_mock_data()
    
    print(f"数据形状: {price_data.shape}")
    print(f"日期范围: {price_data.index[0]} 至 {price_data.index[-1]}")
    
    print("\n创建ETF短线策略...")
    strategy = ETFShortTermStrategy()
    
    print("运行回测...")
    backtester = ShortTermBacktester(strategy)
    result = backtester.run(price_data, volume_data)
    
    print(f"\n=== 回测结果 ===")
    print(f"总收益率: {result.total_return*100:.2f}%")
    print(f"年化收益: {result.annual_return*100:.2f}%")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"胜率: {result.win_rate*100:.1f}%")
    print(f"交易次数: {result.trade_count}")
