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
    
    # ============================================
    # 新增技术指标计算方法
    # ============================================
    
    def vwap(self) -> float:
        """
        成交量加权平均价 (Volume Weighted Average Price)
        VWAP = Σ(典型价格 × 成交量) / Σ(成交量)
        """
        typical_price = (self.high_array + self.low_array + self.close_array) / 3
        total_volume = np.sum(self.volume_array)
        if total_volume == 0:
            return self.close_array[-1]
        return np.sum(typical_price * self.volume_array) / total_volume
    
    def mfi(self, n: int = 14) -> float:
        """
        资金流量指数 (Money Flow Index)
        类似RSI但考虑成交量
        """
        typical_price = (self.high_array[-n-1:] + self.low_array[-n-1:] + self.close_array[-n-1:]) / 3
        money_flow = typical_price * self.volume_array[-n-1:]
        
        # 判断资金流向
        price_diff = np.diff(typical_price)
        
        positive_flow = np.sum(money_flow[1:][price_diff > 0])
        negative_flow = np.sum(money_flow[1:][price_diff < 0])
        
        if negative_flow == 0:
            return 100
        
        money_ratio = positive_flow / negative_flow
        return 100 - (100 / (1 + money_ratio))
    
    def turnover_rate(self, avg_volume_period: int = 60) -> float:
        """
        相对换手率
        当前成交量 / 平均成交量 × 100
        """
        avg_volume = np.mean(self.volume_array[-avg_volume_period:])
        if avg_volume == 0:
            return 100
        return (self.volume_array[-1] / avg_volume) * 100
    
    def bias(self, n: int = 6) -> float:
        """
        乖离率 (BIAS)
        BIAS = (当前价格 - N日均线) / N日均线 × 100%
        """
        ma = self.sma(n)
        if ma == 0:
            return 0
        return (self.close_array[-1] - ma) / ma * 100
    
    def dmi(self, n: int = 14) -> tuple[float, float, float]:
        """
        趋向指标 (Directional Movement Index)
        
        Returns:
            (+DI, -DI, ADX) 元组
        """
        high = self.high_array[-n-1:]
        low = self.low_array[-n-1:]
        close = self.close_array[-n-1:]
        
        # 计算方向移动
        up_move = np.diff(high)
        down_move = -np.diff(low)
        
        # +DM 和 -DM
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 真实波幅
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        
        # 平滑处理
        atr = np.mean(tr)
        plus_dm_avg = np.mean(plus_dm)
        minus_dm_avg = np.mean(minus_dm)
        
        if atr == 0:
            return 0, 0, 0
        
        plus_di = 100 * plus_dm_avg / atr
        minus_di = 100 * minus_dm_avg / atr
        
        # DX 和 ADX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx = 0
        else:
            dx = 100 * abs(plus_di - minus_di) / di_sum
        
        adx = dx  # 简化处理，实际应该是DX的移动平均
        
        return plus_di, minus_di, adx
    
    def sar(self, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> tuple[float, int]:
        """
        抛物线指标 (Parabolic SAR)
        
        Returns:
            (SAR值, 趋势方向: 1=上升, -1=下降)
        """
        high = self.high_array
        low = self.low_array
        close = self.close_array
        n = len(close)
        
        if n < 2:
            return close[-1], 1
        
        # 简化计算：使用最近的趋势判断
        recent_trend = 1 if close[-1] > close[-5] else -1
        
        if recent_trend == 1:
            # 上升趋势，SAR在下方
            sar_value = np.min(low[-5:])
        else:
            # 下降趋势，SAR在上方
            sar_value = np.max(high[-5:])
        
        return sar_value, recent_trend
    
    def ichimoku(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52) -> dict:
        """
        一目均衡表 (Ichimoku Cloud)
        
        Returns:
            包含各线值的字典
        """
        high = self.high_array
        low = self.low_array
        
        # 转换线 (Tenkan-sen)
        tenkan_high = np.max(high[-tenkan_period:])
        tenkan_low = np.min(low[-tenkan_period:])
        tenkan_sen = (tenkan_high + tenkan_low) / 2
        
        # 基准线 (Kijun-sen)
        kijun_high = np.max(high[-kijun_period:])
        kijun_low = np.min(low[-kijun_period:])
        kijun_sen = (kijun_high + kijun_low) / 2
        
        # 先行带A (Senkou Span A)
        senkou_span_a = (tenkan_sen + kijun_sen) / 2
        
        # 先行带B (Senkou Span B)
        senkou_b_high = np.max(high[-senkou_b_period:])
        senkou_b_low = np.min(low[-senkou_b_period:])
        senkou_span_b = (senkou_b_high + senkou_b_low) / 2
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'cloud_top': max(senkou_span_a, senkou_span_b),
            'cloud_bottom': min(senkou_span_a, senkou_span_b)
        }
