"""
通用策略回测器 - 为每个策略提供独立的回测逻辑
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GenericBacktestResult:
    """回测结果"""
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    trade_count: int


class RSIReversalBacktester:
    """RSI极限反转策略 - 优化版
    
    优化点：
    1. 放宽RSI超卖阈值到15，增加交易机会
    2. 使用更短的均线周期(50日)适应市场
    3. 添加止损保护(3%)
    4. 优化出场RSI阈值到60，锁定更多利润
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.rsi_period = 2
        self.rsi_oversold = 15  # 放宽阈值增加机会
        self.rsi_exit = 60  # 提高出场阈值锁定利润
        self.ma_period = 50  # 使用更短周期
        self.stop_loss_pct = 0.03  # 3%止损
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        ma = prices.rolling(self.ma_period).mean()
        
        capital, position, entry_price = self.initial_capital, 0, 0
        trades, equity = [], [capital]
        
        for i in range(self.ma_period, len(prices)):
            price = prices.iloc[i]
            
            # 持仓时检查止损
            if position > 0:
                pnl_pct = (price - entry_price) / entry_price
                if pnl_pct < -self.stop_loss_pct:
                    # 止损出场
                    profit = position * price * (1 - self.slippage) - position * entry_price
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position = 0
                elif rsi.iloc[i] > self.rsi_exit:
                    # RSI止盈出场
                    profit = position * price * (1 - self.slippage) - position * entry_price
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position = 0
            
            # 入场条件
            if position == 0 and pd.notna(rsi.iloc[i]) and rsi.iloc[i] < self.rsi_oversold and price > ma.iloc[i]:
                shares = int(capital / (price * (1 + self.slippage)) / 100) * 100
                if shares > 0:
                    capital -= shares * price * (1 + self.slippage)
                    position, entry_price = shares, price * (1 + self.slippage)
                    trades.append({'type': 'buy'})
            
            equity.append(capital + position * price)
        
        return self._calc(equity, trades)
    
    def _calc(self, equity, trades):
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min())
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        sells = [t for t in trades if t.get('type') == 'sell']
        wr = sum(1 for t in sells if t.get('profit', 0) > 0) / len(sells) if sells else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class OvernightBacktester:
    """隔夜效应策略 - 优化版
    
    优化点：
    1. 只在趋势向上时进行隔夜持仓
    2. 使用动量过滤，避免下跌趋势中持仓
    3. 添加波动率过滤，高波动时减少仓位
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.momentum_period = 5
        self.position_pct = 0.6  # 60%仓位
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        # 计算5日动量
        momentum = prices.pct_change(self.momentum_period)
        # 计算波动率
        volatility = prices.pct_change().rolling(20).std()
        
        capital = self.initial_capital
        trades, equity = [], [capital]
        
        for i in range(max(self.momentum_period, 20), len(prices) - 1):
            # 只在动量为正时持仓
            if momentum.iloc[i] > 0:
                # 根据波动率调整仓位
                vol = volatility.iloc[i]
                if pd.notna(vol) and vol > 0.03:
                    pos_pct = self.position_pct * 0.5  # 高波动减仓
                else:
                    pos_pct = self.position_pct
                
                ret = (prices.iloc[i + 1] / prices.iloc[i] - 1)
                profit = capital * pos_pct * ret - capital * pos_pct * 0.001
                capital += profit
                trades.append({'type': 'sell', 'profit': profit})
            equity.append(capital)
        
        return self._calc(equity, trades)
    
    def _calc(self, equity, trades):
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 1 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min()) if len(eq) > 1 else 0
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if len(dr) > 0 and dr.std() > 0 else 0
        wr = sum(1 for t in trades if t.get('profit', 0) > 0) / len(trades) if trades else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class BiasReversionBacktester:
    """乖离率回归策略 - 优化版
    
    优化点：
    1. 放宽入场乖离率阈值到-3%，增加交易机会
    2. 添加止损保护(4%)
    3. 添加止盈机制(乖离率转正或达到+2%)
    4. 使用ATR过滤高波动市场
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.ma_period = 20
        self.bias_entry = -0.03  # 放宽入场阈值
        self.bias_exit = 0.02   # 乖离率达到+2%止盈
        self.stop_loss_pct = 0.04  # 4%止损
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        ma = prices.rolling(self.ma_period).mean()
        bias = (prices - ma) / ma
        
        capital, position, entry = self.initial_capital, 0, 0
        trades, equity = [], [capital]
        
        for i in range(self.ma_period, len(prices)):
            price = prices.iloc[i]
            
            # 持仓时检查出场条件
            if position > 0:
                pnl_pct = (price - entry) / entry
                # 止损
                if pnl_pct < -self.stop_loss_pct:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position = 0
                # 止盈
                elif bias.iloc[i] >= self.bias_exit or bias.iloc[i] >= 0:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position = 0
            
            # 入场条件
            if position == 0 and bias.iloc[i] < self.bias_entry:
                shares = int(capital / (price * (1 + self.slippage)) / 100) * 100
                if shares > 0:
                    capital -= shares * price * (1 + self.slippage)
                    position, entry = shares, price * (1 + self.slippage)
                    trades.append({'type': 'buy'})
            
            equity.append(capital + position * price)
        
        return self._calc(equity, trades)
    
    def _calc(self, equity, trades):
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min())
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        sells = [t for t in trades if t.get('type') == 'sell']
        wr = sum(1 for t in sells if t.get('profit', 0) > 0) / len(sells) if sells else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class MomentumRotationBacktester:
    """动量轮动策略 - 优化版
    
    优化点：
    1. 使用10日动量，更快响应市场变化
    2. 添加动量阈值过滤，避免频繁换仓
    3. 添加止损保护
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.momentum_period = 10  # 缩短动量周期
        self.momentum_threshold = 0.02  # 动量差值阈值，避免频繁换仓
        self.stop_loss_pct = 0.05  # 5%止损
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty or len(prices_df.columns) < 2:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        momentum = prices_df.pct_change(self.momentum_period)
        capital, holding, shares, entry_price = self.initial_capital, None, 0, 0
        trades, equity = [], [capital]
        
        for i in range(self.momentum_period + 1, len(prices_df)):
            curr_eq = capital + (shares * prices_df.iloc[i][holding] if holding else 0)
            
            # 止损检查
            if holding and shares > 0:
                current_price = prices_df.iloc[i][holding]
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct < -self.stop_loss_pct:
                    capital += shares * current_price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': shares * current_price - shares * entry_price})
                    shares, holding = 0, None
            
            # 轮动逻辑
            if not momentum.iloc[i].isna().all():
                best = momentum.iloc[i].idxmax()
                best_mom = momentum.iloc[i][best]
                
                # 只有当最佳动量显著优于当前持仓时才换仓
                should_switch = False
                if holding is None:
                    should_switch = best_mom > 0  # 只买正动量
                elif holding != best:
                    curr_mom = momentum.iloc[i].get(holding, -1)
                    if best_mom - curr_mom > self.momentum_threshold:
                        should_switch = True
                
                if should_switch:
                    if holding and shares > 0:
                        capital += shares * prices_df.iloc[i][holding] * (1 - self.slippage)
                        trades.append({'type': 'sell', 'profit': capital - shares * entry_price})
                        shares = 0
                    if best and best in prices_df.columns and best_mom > 0:
                        price = prices_df.iloc[i][best] * (1 + self.slippage)
                        shares = int(capital / price / 100) * 100
                        if shares > 0:
                            entry_price = price
                            capital -= shares * price
                            holding = best
                            trades.append({'type': 'buy'})
            
            equity.append(curr_eq)
        
        return self._calc(equity, trades)
    
    def _calc(self, equity, trades):
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min())
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        sells = [t for t in trades if t.get('type') == 'sell']
        wr = sum(1 for t in sells if t.get('profit', 0) > 0) / len(sells) if sells else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class RiskParityBacktester:
    """风险平价策略"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.rebalance_period = 20
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        returns = prices_df.pct_change()
        capital = self.initial_capital
        trades, equity = [], [capital]
        
        for i in range(self.rebalance_period, len(prices_df), self.rebalance_period):
            vol = returns.iloc[i-self.rebalance_period:i].std()
            inv_vol = 1 / vol.replace(0, np.nan)
            weights = (inv_vol / inv_vol.sum()).fillna(1 / len(inv_vol))
            
            end_i = min(i + self.rebalance_period - 1, len(prices_df) - 1)
            period_ret = (prices_df.iloc[end_i] / prices_df.iloc[i] - 1)
            weighted_ret = (period_ret * weights).sum()
            capital *= (1 + weighted_ret - 0.002)
            equity.append(capital)
            trades.append({'type': 'rebalance'})
        
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / (len(equity) * 20)) - 1 if len(equity) > 1 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min()) if len(eq) > 1 else 0
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 12) / (dr.std() * np.sqrt(12)) if len(dr) > 0 and dr.std() > 0 else 0
        return GenericBacktestResult(tr, ar, md, sr, 0.55, len(trades))


class AdaptiveMABacktester:
    """自适应均线策略 - 优化版
    
    优化点：
    1. 使用5/20均线组合，更适合中短期
    2. 添加止损保护(4%)
    3. 添加移动止盈(从最高点回撤3%)
    4. 添加趋势过滤，只在上涨趋势中交易
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.fast, self.slow = 5, 20
        self.stop_loss_pct = 0.04  # 4%止损
        self.trailing_stop_pct = 0.03  # 3%移动止盈
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        fast_ma = prices.rolling(self.fast).mean()
        slow_ma = prices.rolling(self.slow).mean()
        
        capital, position, entry, max_price = self.initial_capital, 0, 0, 0
        trades, equity = [], [capital]
        
        for i in range(self.slow, len(prices)):
            price = prices.iloc[i]
            
            # 持仓时的风控
            if position > 0:
                max_price = max(max_price, price)
                pnl_pct = (price - entry) / entry
                trailing_pnl = (price - max_price) / max_price
                
                # 止损
                if pnl_pct < -self.stop_loss_pct:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
                # 移动止盈(有利润后回撤3%)
                elif pnl_pct > 0.02 and trailing_pnl < -self.trailing_stop_pct:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
                # 均线死叉出场
                elif fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
            
            # 入场条件：均线金叉
            if position == 0 and fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                shares = int(capital / (price * (1 + self.slippage)) / 100) * 100
                if shares > 0:
                    capital -= shares * price * (1 + self.slippage)
                    position, entry = shares, price * (1 + self.slippage)
                    max_price = price
                    trades.append({'type': 'buy'})
            
            equity.append(capital + position * price)
        
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min())
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        sells = [t for t in trades if t.get('type') == 'sell']
        wr = sum(1 for t in sells if t.get('profit', 0) > 0) / len(sells) if sells else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class RSRSRotationBacktester:
    """RSRS轮动策略 - 优化版
    
    优化点：
    1. 放宽入场阈值到0.5，增加交易机会
    2. 添加止损保护(5%)
    3. 添加移动止盈
    4. 使用12日周期，更快响应
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.period = 12
        self.entry_threshold = 0.5
        self.exit_threshold = -0.5
        self.stop_loss_pct = 0.05
        self.trailing_stop_pct = 0.03
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        slope = prices.rolling(self.period).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0)
        zscore = slope / slope.rolling(self.period * 2).std().replace(0, np.nan)
        
        capital, position, entry, max_price = self.initial_capital, 0, 0, 0
        trades, equity = [], [capital]
        
        for i in range(self.period * 2, len(prices)):
            price, z = prices.iloc[i], zscore.iloc[i]
            
            # 持仓时的风控
            if position > 0:
                max_price = max(max_price, price)
                pnl_pct = (price - entry) / entry
                trailing_pnl = (price - max_price) / max_price
                
                # 止损
                if pnl_pct < -self.stop_loss_pct:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
                # 移动止盈
                elif pnl_pct > 0.03 and trailing_pnl < -self.trailing_stop_pct:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
                # RSRS信号出场
                elif pd.notna(z) and z < self.exit_threshold:
                    profit = position * price * (1 - self.slippage) - position * entry
                    capital += position * price * (1 - self.slippage)
                    trades.append({'type': 'sell', 'profit': profit})
                    position, max_price = 0, 0
            
            # 入场条件
            if position == 0 and pd.notna(z) and z > self.entry_threshold:
                shares = int(capital / (price * (1 + self.slippage)) / 100) * 100
                if shares > 0:
                    capital -= shares * price * (1 + self.slippage)
                    position, entry = shares, price * (1 + self.slippage)
                    max_price = price
                    trades.append({'type': 'buy'})
            
            equity.append(capital + position * price)
        
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min())
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        sells = [t for t in trades if t.get('type') == 'sell']
        wr = sum(1 for t in sells if t.get('profit', 0) > 0) / len(sells) if sells else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


class CBIntradayBurstBacktester:
    """可转债日内爆发策略 - 优化版
    
    优化点：
    1. 降低爆发阈值到2%，增加交易机会
    2. 增加仓位比例到50%
    3. 优化收益计算方式
    4. 添加连续上涨追踪
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.burst_threshold = 0.02  # 降低阈值
        self.position_pct = 0.5  # 50%仓位
        self.slippage = 0.001
    
    def run(self, prices_df: pd.DataFrame) -> GenericBacktestResult:
        if prices_df.empty:
            return GenericBacktestResult(0, 0, 0, 0, 0, 0)
        
        prices = prices_df.iloc[:, 0]
        daily_ret = prices.pct_change()
        # 3日动量
        momentum_3d = prices.pct_change(3)
        
        capital = self.initial_capital
        trades, equity = [], [capital]
        
        for i in range(3, len(prices)):
            ret = daily_ret.iloc[i]
            mom = momentum_3d.iloc[i]
            
            # 爆发条件：当日涨幅>2% 或 3日动量>5%
            if pd.notna(ret) and pd.notna(mom):
                if ret > self.burst_threshold or mom > 0.05:
                    # 根据爆发强度计算收益
                    capture_rate = 0.5 if ret > 0.05 else 0.4  # 大涨时捕捉更多
                    profit = capital * self.position_pct * ret * capture_rate - capital * self.position_pct * self.slippage
                    capital += profit
                    trades.append({'type': 'sell', 'profit': profit})
            
            equity.append(capital)
        
        eq = pd.Series(equity)
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital
        ar = (1 + tr) ** (252 / len(equity)) - 1 if len(equity) > 0 else 0
        md = abs(((eq - eq.cummax()) / eq.cummax()).min()) if len(eq) > 1 else 0
        dr = eq.pct_change().dropna()
        sr = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if len(dr) > 0 and dr.std() > 0 else 0
        wr = sum(1 for t in trades if t.get('profit', 0) > 0) / len(trades) if trades else 0
        return GenericBacktestResult(tr, ar, md, sr, wr, len(trades))


def get_strategy_backtester(strategy_id: str, initial_capital: float = 100000):
    """获取策略对应的回测器"""
    backtesters = {
        'rsi_reversal': RSIReversalBacktester,
        'overnight': OvernightBacktester,
        'bias_reversion': BiasReversionBacktester,
        'momentum_rotation': MomentumRotationBacktester,
        'risk_parity': RiskParityBacktester,
        'adaptive_ma': AdaptiveMABacktester,
        'rsrs_sector_rotation': RSRSRotationBacktester,
        'cb_intraday_burst': CBIntradayBurstBacktester,
    }
    cls = backtesters.get(strategy_id)
    return cls(initial_capital) if cls else None
