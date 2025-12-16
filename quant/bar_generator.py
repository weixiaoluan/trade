"""
============================================
K线生成器 (参考 vnpy BarGenerator)
Bar Generator (Based on vnpy BarGenerator)
============================================
"""

from datetime import datetime
from typing import Callable, Optional
from .event_engine import Event, EVENT_BAR


class BarGenerator:
    """
    K线生成器（参考 vnpy.trader.utility.BarGenerator）
    
    功能：
    - Tick数据转K线
    - 多周期K线合成
    """
    
    def __init__(
        self,
        on_bar: Callable,
        window: int = 0,
        on_window_bar: Optional[Callable] = None
    ):
        """
        Args:
            on_bar: K线回调函数
            window: 时间窗口（分钟）
            on_window_bar: 窗口K线回调函数
        """
        self.on_bar = on_bar
        self.window = window
        self.on_window_bar = on_window_bar
        
        self.last_tick = None
        self.last_bar = None
        
        self.window_bar = None
        self.interval_count = 0
    
    def update_tick(self, tick_data: dict):
        """更新Tick数据"""
        # 简化实现：直接转换为1分钟K线
        bar = {
            "datetime": tick_data.get("datetime", datetime.now()),
            "Open": tick_data["last_price"],
            "High": tick_data["last_price"],
            "Low": tick_data["last_price"],
            "Close": tick_data["last_price"],
            "Volume": tick_data.get("volume", 0)
        }
        
        self.update_bar(bar)
    
    def update_bar(self, bar: dict):
        """更新K线"""
        if self.on_bar:
            self.on_bar(bar)
        
        # 如果需要合成更大周期
        if self.window > 0 and self.on_window_bar:
            self._update_window_bar(bar)
    
    def _update_window_bar(self, bar: dict):
        """更新窗口K线"""
        if not self.window_bar:
            self.window_bar = bar.copy()
            self.interval_count = 1
        else:
            self.window_bar["High"] = max(
                self.window_bar["High"],
                bar["High"]
            )
            self.window_bar["Low"] = min(
                self.window_bar["Low"],
                bar["Low"]
            )
            self.window_bar["Close"] = bar["Close"]
            self.window_bar["Volume"] += bar["Volume"]
            
            self.interval_count += 1
            
            if self.interval_count >= self.window:
                self.on_window_bar(self.window_bar)
                self.window_bar = None
                self.interval_count = 0
