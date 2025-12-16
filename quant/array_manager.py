"""
============================================
量化数组管理器 (参考 vnpy ArrayManager)
Quantitative Array Manager (Based on vnpy ArrayManager)
============================================
"""

import numpy as np
from collections import deque
from typing import Optional


class QuantArrayManager:
    """
    量化数组管理器 (参考 vnpy.trader.utility.ArrayManager)
    
    用于序列数据的高效存储和技术指标计算
    """
    
    def __init__(self, size: int = 250):
        """
        Args:
            size: 数组大小，默认250个交易日(约1年)
        """
        self.size = size
        self.count = 0
        
        # K线数据数组
        self.open_array = np.zeros(size)
        self.high_array = np.zeros(size)
        self.low_array = np.zeros(size)
        self.close_array = np.zeros(size)
        self.volume_array = np.zeros(size)
        
    def update_bar(self, bar_data: dict):
        """更新K线数据"""
        self.count += 1
        
        if self.count > self.size:
            # 数组满时，移除最早数据
            self.open_array[:-1] = self.open_array[1:]
            self.high_array[:-1] = self.high_array[1:]
            self.low_array[:-1] = self.low_array[1:]
            self.close_array[:-1] = self.close_array[1:]
            self.volume_array[:-1] = self.volume_array[1:]
            
            self.open_array[-1] = bar_data['Open']
            self.high_array[-1] = bar_data['High']
            self.low_array[-1] = bar_data['Low']
            self.close_array[-1] = bar_data['Close']
            self.volume_array[-1] = bar_data['Volume']
        else:
            # 数组未满时，添加数据
            self.open_array[self.count - 1] = bar_data['Open']
            self.high_array[self.count - 1] = bar_data['High']
            self.low_array[self.count - 1] = bar_data['Low']
            self.close_array[self.count - 1] = bar_data['Close']
            self.volume_array[self.count - 1] = bar_data['Volume']
    
    @property
    def inited(self) -> bool:
        """是否初始化完成"""
        return self.count >= self.size
    
    def sma(self, n: int, array: bool = False) -> float | np.ndarray:
        """简单移动平均 (Simple Moving Average)"""
        result = np.mean(self.close_array[-n:])
        if array:
            return self._calculate_indicator(lambda: np.convolve(
                self.close_array, np.ones(n)/n, mode='valid'
            ))
        return result
    
    def ema(self, n: int, array: bool = False) -> float | np.ndarray:
        """指数移动平均 (Exponential Moving Average)"""
        if array:
            weights = np.exp(np.linspace(-1., 0., n))
            weights /= weights.sum()
            result = np.convolve(self.close_array, weights, mode='valid')
            return result
        else:
            weights = np.exp(np.linspace(-1., 0., n))
            weights /= weights.sum()
            return (self.close_array[-n:] * weights).sum()
    
    def std(self, n: int) -> float:
        """标准差 (Standard Deviation)"""
        return np.std(self.close_array[-n:])
    
    def atr(self, n: int, array: bool = False) -> float | np.ndarray:
        """平均真实波幅 (Average True Range)"""
        high = self.high_array[-n:]
        low = self.low_array[-n:]
        close = self.close_array[-n:]
        
        tr = np.maximum(
            high - low,
            np.maximum(
                abs(high - np.roll(close, 1)),
                abs(low - np.roll(close, 1))
            )
        )
        tr[0] = high[0] - low[0]  # 第一个值特殊处理
        
        if array:
            return tr
        return np.mean(tr)
    
    def rsi(self, n: int) -> float:
        """相对强弱指标 (Relative Strength Index)"""
        close = self.close_array[-n-1:]
        diff = np.diff(close)
        
        gains = diff.copy()
        losses = diff.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def macd(
        self, 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> tuple[float, float, float]:
        """
        MACD指标 (Moving Average Convergence Divergence)
        
        Returns:
            (dif, dea, macd) 元组
        """
        ema_fast = self._ema_array(self.close_array, fast_period)
        ema_slow = self._ema_array(self.close_array, slow_period)
        
        dif = ema_fast - ema_slow
        dea = self._ema_array(dif, signal_period)
        macd = (dif - dea) * 2
        
        return dif[-1], dea[-1], macd[-1]
    
    def bollinger(self, n: int, dev: float = 2.0) -> tuple[float, float, float]:
        """
        布林带指标 (Bollinger Bands)
        
        Returns:
            (upper, middle, lower) 元组
        """
        middle = self.sma(n)
        std = self.std(n)
        upper = middle + dev * std
        lower = middle - dev * std
        
        return upper, middle, lower
    
    def kdj(self, n: int = 9, m1: int = 3, m2: int = 3) -> tuple[float, float, float]:
        """
        KDJ指标 (Stochastic Oscillator)
        
        Returns:
            (k, d, j) 元组
        """
        high = self.high_array[-n:]
        low = self.low_array[-n:]
        close = self.close_array[-n:]
        
        highest = np.max(high)
        lowest = np.min(low)
        
        if highest == lowest:
            rsv = 50
        else:
            rsv = (close[-1] - lowest) / (highest - lowest) * 100
        
        # 简化计算，使用SMA近似
        k = (rsv + 2 * 50) / 3  # 初始值50
        d = (k + 2 * 50) / 3
        j = 3 * k - 2 * d
        
        return k, d, j
    
    def _ema_array(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算EMA数组（内部方法）"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _calculate_indicator(self, func) -> np.ndarray:
        """计算指标数组（内部方法）"""
        try:
            return func()
        except Exception as e:
            print(f"指标计算错误: {e}")
            return np.array([])
