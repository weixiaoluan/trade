"""
============================================
量化执行官 Agent (参考 vnpy StrategyTemplate)
Quant Agent (Based on vnpy StrategyTemplate)
============================================
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .array_manager import QuantArrayManager
from .event_engine import QuantEventEngine, Event, EVENT_SIGNAL, EVENT_ANALYSIS


class QuantAgent:
    """
    量化执行官 Agent
    
    职责：
    - 处理 OHLCV 数据
    - 利用 ArrayManager 计算技术指标
    - 基于硬数据生成多空信号和仓位建议
    
    参考 vnpy.app.cta_strategy.StrategyTemplate
    """
    
    def __init__(self, event_engine: QuantEventEngine, size: int = 250):
        self.event_engine = event_engine
        self.am = QuantArrayManager(size=size)
        self.inited = False
        self.trading = False
        
        # 信号和状态
        self.pos = 0  # 仓位：1多头，0空仓，-1空头
        self.signal_score = 50.0  # 量化评分 0-100
        self.signals = []  # 信号列表
        
        # 注册事件处理
        self.event_engine.register("eBar", self.on_bar)
        
    def on_bar(self, event: Event):
        """K线回调（类似 vnpy 的 on_bar）"""
        bar_data = event.data
        self.am.update_bar(bar_data)
        
        if not self.am.inited:
            return
        
        if not self.inited:
            self.inited = True
            self.on_init()
        
        if not self.trading:
            self.trading = True
            self.on_start()
        
        # 执行策略逻辑
        self.calculate_signals()
        
    def on_init(self):
        """初始化完成回调"""
        print(f"[QuantAgent] 初始化完成，数据量: {self.am.count}")
        
    def on_start(self):
        """启动策略回调"""
        print(f"[QuantAgent] 策略启动")
        
    def calculate_signals(self) -> Dict:
        """
        计算量化信号（核心策略逻辑）
        
        Returns:
            信号字典，包含评分和仓位建议
        """
        signals = []
        bullish_count = 0
        bearish_count = 0
        
        # 1. 均线系统信号
        ma_signal = self._check_ma_system()
        signals.extend(ma_signal['signals'])
        bullish_count += ma_signal['bullish']
        bearish_count += ma_signal['bearish']
        
        # 2. MACD 信号
        macd_signal = self._check_macd()
        signals.extend(macd_signal['signals'])
        bullish_count += macd_signal['bullish']
        bearish_count += macd_signal['bearish']
        
        # 3. RSI 信号
        rsi_signal = self._check_rsi()
        signals.extend(rsi_signal['signals'])
        bullish_count += rsi_signal['bullish']
        bearish_count += rsi_signal['bearish']
        
        # 4. KDJ 信号
        kdj_signal = self._check_kdj()
        signals.extend(kdj_signal['signals'])
        bullish_count += kdj_signal['bullish']
        bearish_count += kdj_signal['bearish']
        
        # 5. 布林带信号
        bb_signal = self._check_bollinger()
        signals.extend(bb_signal['signals'])
        bullish_count += bb_signal['bullish']
        bearish_count += bb_signal['bearish']
        
        # 6. ATR 波动率
        atr_signal = self._check_atr()
        signals.extend(atr_signal['signals'])
        
        # 计算综合评分 (0-100)
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            bullish_ratio = bullish_count / total_signals
            self.signal_score = bullish_ratio * 100
        else:
            self.signal_score = 50.0
        
        # 确定仓位
        if self.signal_score >= 70:
            self.pos = 1  # 多头
        elif self.signal_score <= 30:
            self.pos = -1  # 空头
        else:
            self.pos = 0  # 空仓
        
        # 保存信号
        self.signals = signals
        
        # 发送信号事件
        result = {
            "score": round(self.signal_score, 1),
            "pos": self.pos,
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "signals": signals,
            "timestamp": datetime.now().isoformat()
        }
        
        self.event_engine.emit(EVENT_SIGNAL, result)
        
        return result
    
    def _check_ma_system(self) -> Dict:
        """检查均线系统"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            ma5 = self.am.sma(5)
            ma10 = self.am.sma(10)
            ma20 = self.am.sma(20)
            ma60 = self.am.sma(60)
            
            close = self.am.close_array[-1]
            
            # 多头排列
            if ma5 > ma10 > ma20 > ma60:
                signals.append("均线多头排列")
                bullish += 1
            elif ma5 < ma10 < ma20 < ma60:
                signals.append("均线空头排列")
                bearish += 1
            
            # 价格与均线关系
            if close > ma20:
                signals.append("价格站上MA20")
                bullish += 1
            elif close < ma20:
                signals.append("价格跌破MA20")
                bearish += 1
                
        except Exception as e:
            print(f"均线计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_macd(self) -> Dict:
        """检查MACD"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            dif, dea, macd = self.am.macd()
            
            if dif > dea and macd > 0:
                signals.append("MACD金叉且柱状图为正")
                bullish += 1
            elif dif < dea and macd < 0:
                signals.append("MACD死叉且柱状图为负")
                bearish += 1
                
        except Exception as e:
            print(f"MACD计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_rsi(self) -> Dict:
        """检查RSI"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            rsi = self.am.rsi(14)
            
            if rsi < 30:
                signals.append("RSI超卖")
                bullish += 1
            elif rsi > 70:
                signals.append("RSI超买")
                bearish += 1
            elif 40 <= rsi <= 60:
                signals.append("RSI中性")
                
        except Exception as e:
            print(f"RSI计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_kdj(self) -> Dict:
        """检查KDJ"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            k, d, j = self.am.kdj()
            
            if k < 20 and d < 20:
                signals.append("KDJ超卖区域")
                bullish += 1
            elif k > 80 and d > 80:
                signals.append("KDJ超买区域")
                bearish += 1
            
            if k > d:
                signals.append("KDJ金叉")
                bullish += 1
            elif k < d:
                signals.append("KDJ死叉")
                bearish += 1
                
        except Exception as e:
            print(f"KDJ计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_bollinger(self) -> Dict:
        """检查布林带"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            upper, middle, lower = self.am.bollinger(20)
            close = self.am.close_array[-1]
            
            if close < lower:
                signals.append("价格触及布林下轨")
                bullish += 1
            elif close > upper:
                signals.append("价格触及布林上轨")
                bearish += 1
                
        except Exception as e:
            print(f"布林带计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_atr(self) -> Dict:
        """检查ATR"""
        signals = []
        
        try:
            atr = self.am.atr(14)
            close = self.am.close_array[-1]
            atr_pct = (atr / close) * 100
            
            if atr_pct > 3:
                signals.append(f"高波动(ATR {atr_pct:.2f}%)")
            elif atr_pct < 1:
                signals.append(f"低波动(ATR {atr_pct:.2f}%)")
                
        except Exception as e:
            print(f"ATR计算错误: {e}")
        
        return {"signals": signals, "bullish": 0, "bearish": 0}
    
    def get_analysis(self) -> Dict:
        """获取当前分析结果"""
        return {
            "score": round(self.signal_score, 1),
            "position": self.pos,
            "position_label": "多头" if self.pos == 1 else "空头" if self.pos == -1 else "空仓",
            "signals": self.signals,
            "recommendation": self._get_recommendation()
        }
    
    def _get_recommendation(self) -> str:
        """获取操作建议"""
        if self.signal_score >= 80:
            return "强力买入"
        elif self.signal_score >= 60:
            return "买入"
        elif self.signal_score >= 40:
            return "持有"
        elif self.signal_score >= 20:
            return "减持"
        else:
            return "卖出"
