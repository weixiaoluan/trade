"""
============================================
市场情报官 Agent
Market Info Agent
============================================
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from .array_manager import QuantArrayManager
from .event_engine import QuantEventEngine, EVENT_ANALYSIS


class MarketRegimeAnalyzer:
    """
    市场情报官 Agent
    
    职责：
    - 模拟 AI 对非结构化数据的感知
    - 分析市场情绪和宏观因子
    - 捕捉盘后微弱波动背后的潜在情绪
    
    输出：
    - 情绪评分 (Sentiment Score)
    - 波动率预测
    - 市场状态判断
    """
    
    def __init__(self, event_engine: QuantEventEngine):
        self.event_engine = event_engine
        self.sentiment_score = 50.0  # 情绪评分 0-100
        self.volatility_forecast = "medium"  # 波动率预测
        self.market_regime = "unknown"  # 市场状态
        
    def analyze_market_sentiment(
        self,
        price_data: np.ndarray,
        volume_data: np.ndarray,
        external_factors: Optional[Dict] = None
    ) -> Dict:
        """
        分析市场情绪
        
        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            external_factors: 外部因素（新闻、宏观数据等）
            
        Returns:
            情绪分析结果
        """
        # 1. 价格动量情绪
        price_momentum = self._analyze_price_momentum(price_data)
        
        # 2. 成交量情绪
        volume_sentiment = self._analyze_volume_sentiment(volume_data)
        
        # 3. 波动率情绪
        volatility_sentiment = self._analyze_volatility(price_data)
        
        # 4. 趋势强度
        trend_strength = self._analyze_trend_strength(price_data)
        
        # 综合情绪评分
        self.sentiment_score = (
            price_momentum * 0.35 +
            volume_sentiment * 0.25 +
            volatility_sentiment * 0.20 +
            trend_strength * 0.20
        )
        
        # 外部因素调整
        if external_factors:
            self.sentiment_score = self._adjust_for_external_factors(
                self.sentiment_score,
                external_factors
            )
        
        # 判断市场状态
        self.market_regime = self._determine_market_regime(
            price_data,
            self.sentiment_score
        )
        
        # 预测波动率
        self.volatility_forecast = self._forecast_volatility(price_data)
        
        result = {
            "sentiment_score": round(self.sentiment_score, 1),
            "market_regime": self.market_regime,
            "volatility_forecast": self.volatility_forecast,
            "confidence": self._calculate_confidence(),
            "components": {
                "price_momentum": round(price_momentum, 1),
                "volume_sentiment": round(volume_sentiment, 1),
                "volatility_sentiment": round(volatility_sentiment, 1),
                "trend_strength": round(trend_strength, 1)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送分析事件
        self.event_engine.emit(EVENT_ANALYSIS, result)
        
        return result
    
    def _analyze_price_momentum(self, price_data: np.ndarray) -> float:
        """分析价格动量情绪"""
        if len(price_data) < 20:
            return 50.0
        
        # 计算多周期收益率
        returns_5d = (price_data[-1] / price_data[-6] - 1) * 100 if len(price_data) >= 6 else 0
        returns_10d = (price_data[-1] / price_data[-11] - 1) * 100 if len(price_data) >= 11 else 0
        returns_20d = (price_data[-1] / price_data[-21] - 1) * 100 if len(price_data) >= 21 else 0
        
        # 加权平均
        momentum_score = (
            returns_5d * 0.5 +
            returns_10d * 0.3 +
            returns_20d * 0.2
        )
        
        # 归一化到 0-100
        # 假设 ±10% 为极值
        normalized = 50 + (momentum_score / 10) * 50
        return np.clip(normalized, 0, 100)
    
    def _analyze_volume_sentiment(self, volume_data: np.ndarray) -> float:
        """分析成交量情绪"""
        if len(volume_data) < 20:
            return 50.0
        
        recent_volume = np.mean(volume_data[-5:])
        baseline_volume = np.mean(volume_data[-20:])
        
        if baseline_volume == 0:
            return 50.0
        
        volume_ratio = recent_volume / baseline_volume
        
        # 成交量放大 → 情绪高涨
        if volume_ratio > 1.5:
            return 75.0
        elif volume_ratio > 1.2:
            return 65.0
        elif volume_ratio < 0.7:
            return 35.0
        else:
            return 50.0
    
    def _analyze_volatility(self, price_data: np.ndarray) -> float:
        """分析波动率情绪"""
        if len(price_data) < 20:
            return 50.0
        
        returns = np.diff(price_data) / price_data[:-1]
        volatility = np.std(returns[-20:]) * 100
        
        # 高波动 → 恐慌或贪婪
        if volatility > 3:
            return 30.0  # 恐慌情绪
        elif volatility < 1:
            return 60.0  # 平静情绪
        else:
            return 50.0
    
    def _analyze_trend_strength(self, price_data: np.ndarray) -> float:
        """分析趋势强度"""
        if len(price_data) < 20:
            return 50.0
        
        # 计算线性回归斜率
        x = np.arange(len(price_data[-20:]))
        y = price_data[-20:]
        
        slope, _ = np.polyfit(x, y, 1)
        
        # 归一化斜率
        avg_price = np.mean(y)
        if avg_price > 0:
            normalized_slope = (slope / avg_price) * 100 * 20  # 20天的变化百分比
            return 50 + np.clip(normalized_slope * 5, -50, 50)
        
        return 50.0
    
    def _adjust_for_external_factors(
        self,
        base_score: float,
        factors: Dict
    ) -> float:
        """根据外部因素调整情绪"""
        adjustment = 0.0
        
        # 新闻情绪
        if "news_sentiment" in factors:
            news_score = factors["news_sentiment"]
            adjustment += (news_score - 50) * 0.2
        
        # 宏观数据
        if "macro_indicators" in factors:
            macro_score = factors["macro_indicators"]
            adjustment += (macro_score - 50) * 0.15
        
        return np.clip(base_score + adjustment, 0, 100)
    
    def _determine_market_regime(
        self,
        price_data: np.ndarray,
        sentiment: float
    ) -> str:
        """判断市场状态"""
        if len(price_data) < 20:
            return "unknown"
        
        # 计算趋势和波动
        returns = np.diff(price_data[-20:])
        trend = np.mean(returns)
        volatility = np.std(returns)
        
        # 判断市场状态
        if abs(trend) > 2 * volatility and sentiment > 60:
            return "trending"  # 趋势市
        elif abs(trend) < volatility:
            return "ranging"  # 震荡市
        elif volatility < np.std(np.diff(price_data)) * 0.5:
            return "squeeze"  # 窄幅整理
        else:
            return "unknown"
    
    def _forecast_volatility(self, price_data: np.ndarray) -> str:
        """预测波动率"""
        if len(price_data) < 20:
            return "medium"
        
        returns = np.diff(price_data) / price_data[:-1]
        recent_vol = np.std(returns[-5:])
        hist_vol = np.std(returns[-20:])
        
        if recent_vol > hist_vol * 1.5:
            return "high"
        elif recent_vol < hist_vol * 0.7:
            return "low"
        else:
            return "medium"
    
    def _calculate_confidence(self) -> str:
        """计算置信度"""
        if abs(self.sentiment_score - 50) > 30:
            return "high"
        elif abs(self.sentiment_score - 50) > 15:
            return "medium"
        else:
            return "low"
    
    def get_analysis(self) -> Dict:
        """获取当前分析结果"""
        return {
            "sentiment_score": round(self.sentiment_score, 1),
            "market_regime": self.market_regime,
            "volatility_forecast": self.volatility_forecast,
            "interpretation": self._interpret_results()
        }
    
    def _interpret_results(self) -> str:
        """解释分析结果"""
        if self.sentiment_score >= 70:
            mood = "乐观"
        elif self.sentiment_score >= 55:
            mood = "偏乐观"
        elif self.sentiment_score >= 45:
            mood = "中性"
        elif self.sentiment_score >= 30:
            mood = "偏悲观"
        else:
            mood = "悲观"
        
        regime_desc = {
            "trending": "趋势明显",
            "ranging": "震荡整理",
            "squeeze": "窄幅盘整",
            "unknown": "待观察"
        }.get(self.market_regime, "未知")
        
        return f"市场情绪{mood}，{regime_desc}，预计{self.volatility_forecast}波动"
