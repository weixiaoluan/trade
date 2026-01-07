"""
============================================
量化-AI融合分析引擎
Quant-AI Fusion Analysis Engine
============================================

核心功能：
1. 交叉验证：量化信号 vs AI情绪
2. 动态调整：根据情绪调整策略参数
3. 深度联动：融合硬数据与软判断
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .quant_agent import QuantAgent
from .market_regime import MarketRegimeAnalyzer
from .after_hours_detector import AfterHoursDetector
from .event_engine import QuantEventEngine, Event, EVENT_ANALYSIS


class FusionAnalysisEngine:
    """
    量化-AI融合分析引擎
    
    实现：
    - 量化Agent（硬数据）+ 市场情报Agent（软判断）深度联动
    - 交叉验证降低误判
    - 盘后微波动智能处理
    """
    
    def __init__(self, event_engine: QuantEventEngine):
        self.event_engine = event_engine
        self.quant_agent = QuantAgent(event_engine)
        self.info_agent = MarketRegimeAnalyzer(event_engine)
        self.after_hours = AfterHoursDetector()
        
        # 融合结果
        self.fusion_score = 50.0
        self.fusion_confidence = "medium"
        self.fusion_recommendation = "hold"
        
    def analyze_with_fusion(
        self,
        ohlcv_data: List[Dict],
        market: str = "CN",
        external_factors: Optional[Dict] = None
    ) -> Dict:
        """
        执行融合分析
        
        Args:
            ohlcv_data: OHLCV历史数据
            market: 市场类型（CN/US）
            external_factors: 外部因素（新闻等）
            
        Returns:
            融合分析结果
        """
        # 0. 检查市场状态（盘后检测）
        market_status = self.after_hours.get_market_status(market)
        
        # 1. 量化Agent分析（硬数据）
        quant_result = self._run_quant_analysis(ohlcv_data)
        
        # 2. 市场情报Agent分析（软判断）
        info_result = self._run_info_analysis(ohlcv_data, external_factors)
        
        # 3. 盘后微波动处理
        after_hours_result = None
        if market_status['is_after_hours']:
            after_hours_result = self._analyze_after_hours(ohlcv_data)
        
        # 4. 深度融合：交叉验证
        fusion_result = self._cross_validate(
            quant_result,
            info_result,
            after_hours_result
        )
        
        # 5. 动态调整策略参数
        adjusted_strategy = self._adjust_strategy_params(
            quant_result,
            info_result
        )
        
        # 6. 生成综合报告
        final_report = {
            "fusion_score": round(self.fusion_score, 1),
            "fusion_confidence": self.fusion_confidence,
            "fusion_recommendation": self.fusion_recommendation,
            "market_status": market_status,
            "quant_analysis": quant_result,
            "info_analysis": info_result,
            "after_hours_analysis": after_hours_result,
            "cross_validation": fusion_result,
            "adjusted_strategy": adjusted_strategy,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "final_advice": self._generate_final_advice(
                fusion_result,
                after_hours_result,
                market_status
            )
        }
        
        # 发送融合分析事件
        self.event_engine.emit(EVENT_ANALYSIS, final_report)
        
        return final_report
    
    def _run_quant_analysis(self, ohlcv_data: List[Dict]) -> Dict:
        """运行量化分析"""
        # 将数据送入ArrayManager
        for bar in ohlcv_data:
            self.quant_agent.am.update_bar(bar)
        
        # 计算信号
        if self.quant_agent.am.inited:
            return self.quant_agent.calculate_signals()
        else:
            return {
                "score": 50.0,
                "pos": 0,
                "bullish_signals": 0,
                "bearish_signals": 0,
                "signals": ["数据不足"],
                "timestamp": datetime.now().isoformat()
            }
    
    def _run_info_analysis(
        self,
        ohlcv_data: List[Dict],
        external_factors: Optional[Dict]
    ) -> Dict:
        """运行市场情报分析"""
        import numpy as np
        
        # 提取价格和成交量
        prices = np.array([bar['Close'] for bar in ohlcv_data])
        volumes = np.array([bar['Volume'] for bar in ohlcv_data])
        
        return self.info_agent.analyze_market_sentiment(
            prices,
            volumes,
            external_factors
        )
    
    def _analyze_after_hours(self, ohlcv_data: List[Dict]) -> Dict:
        """分析盘后微波动"""
        import numpy as np
        
        # 提取最近的价格数据
        recent_prices = [bar['Close'] for bar in ohlcv_data[-30:]]
        recent_volumes = [bar['Volume'] for bar in ohlcv_data[-30:]]
        
        return self.after_hours.analyze_micro_movement(
            recent_prices,
            recent_volumes,
            lookback_period=20
        )
    
    def _cross_validate(
        self,
        quant_result: Dict,
        info_result: Dict,
        after_hours_result: Optional[Dict]
    ) -> Dict:
        """
        交叉验证：量化信号 vs AI情绪
        
        核心逻辑：
        - 信号一致 → 提升置信度
        - 信号矛盾 → 降低置信度，谨慎操作
        """
        quant_score = quant_result.get('score', 50.0)
        sentiment_score = info_result.get('sentiment_score', 50.0)
        
        # 1. 信号方向一致性检查
        quant_direction = "bullish" if quant_score > 55 else "bearish" if quant_score < 45 else "neutral"
        sentiment_direction = "bullish" if sentiment_score > 55 else "bearish" if sentiment_score < 45 else "neutral"
        
        is_aligned = (quant_direction == sentiment_direction)
        
        # 2. 计算融合评分（加权平均，但考虑一致性）
        if is_aligned:
            # 信号一致，提升权重
            self.fusion_score = quant_score * 0.6 + sentiment_score * 0.4
            alignment_bonus = 10
            self.fusion_confidence = "high"
        else:
            # 信号矛盾，降低置信度
            self.fusion_score = quant_score * 0.5 + sentiment_score * 0.5
            alignment_bonus = -15
            self.fusion_confidence = "low"
        
        # 3. 盘后微波动调整
        if after_hours_result and after_hours_result['is_significant']:
            movement_type = after_hours_result['movement_type']
            if movement_type in ['abnormal_volatility', 'volume_driven']:
                # 盘后异常，降低信心
                alignment_bonus -= 10
                self.fusion_confidence = "low"
        
        # 4. 应用调整
        self.fusion_score = max(0, min(100, self.fusion_score + alignment_bonus))
        
        # 5. 生成建议
        self.fusion_recommendation = self._map_score_to_recommendation(
            self.fusion_score
        )
        
        return {
            "is_aligned": is_aligned,
            "quant_direction": quant_direction,
            "sentiment_direction": sentiment_direction,
            "fusion_score": round(self.fusion_score, 1),
            "confidence": self.fusion_confidence,
            "alignment_bonus": alignment_bonus,
            "recommendation": self.fusion_recommendation,
            "reasoning": self._explain_cross_validation(
                is_aligned,
                quant_score,
                sentiment_score,
                after_hours_result
            )
        }
    
    def _adjust_strategy_params(
        self,
        quant_result: Dict,
        info_result: Dict
    ) -> Dict:
        """
        动态调整策略参数
        
        根据情绪评分动态调整：
        - 止损位
        - 开仓阈值
        - 仓位大小
        """
        sentiment_score = info_result.get('sentiment_score', 50.0)
        volatility_forecast = info_result.get('volatility_forecast', 'medium')
        
        # 基准参数
        base_stop_loss = 0.05  # 5%
        base_threshold = 60.0  # 量化评分阈值
        base_position_size = 1.0  # 标准仓位
        
        # 情绪系数（0.5 - 1.5）
        sentiment_coef = 0.5 + (sentiment_score / 100)
        
        # 根据情绪调整
        if sentiment_score < 40:
            # 情绪悲观：收紧止损，提高阈值，减仓
            adjusted_stop_loss = base_stop_loss * 0.8  # 更紧的止损
            adjusted_threshold = base_threshold + 10  # 更高的开仓要求
            adjusted_position = base_position_size * 0.6  # 减仓
        elif sentiment_score > 70:
            # 情绪乐观：适度放宽
            adjusted_stop_loss = base_stop_loss * 1.2
            adjusted_threshold = base_threshold - 5
            adjusted_position = base_position_size * 1.0
        else:
            # 中性
            adjusted_stop_loss = base_stop_loss
            adjusted_threshold = base_threshold
            adjusted_position = base_position_size * 0.8
        
        # 波动率调整
        if volatility_forecast == 'high':
            adjusted_stop_loss *= 1.5  # 高波动，放宽止损
            adjusted_position *= 0.7  # 减仓
        elif volatility_forecast == 'low':
            adjusted_stop_loss *= 0.9
            adjusted_position *= 1.1
        
        return {
            "stop_loss_pct": round(adjusted_stop_loss * 100, 2),
            "entry_threshold": round(adjusted_threshold, 1),
            "position_size": round(adjusted_position, 2),
            "sentiment_coefficient": round(sentiment_coef, 2),
            "rationale": f"基于情绪{sentiment_score:.1f}分和{volatility_forecast}波动预期调整"
        }
    
    def _generate_final_advice(
        self,
        fusion_result: Dict,
        after_hours_result: Optional[Dict],
        market_status: Dict
    ) -> str:
        """生成技术面状态描述（仅供学习研究参考，不构成投资建议）"""
        advice_parts = []
        
        # 1. 基于融合评分
        fusion_score = fusion_result['fusion_score']
        confidence = fusion_result['confidence']
        is_aligned = fusion_result['is_aligned']
        
        if is_aligned:
            advice_parts.append(f"✅ 量化信号与市场情绪一致，{confidence}置信度")
        else:
            advice_parts.append(f"⚠️ 量化信号与市场情绪分歧，需谨慎观察")
        
        # 2. 技术面状态描述（不构成投资建议）
        if fusion_score >= 75:
            advice_parts.append("📈 技术面状态：强势，多项指标看多")
        elif fusion_score >= 60:
            advice_parts.append("📊 技术面状态：偏强，整体偏多")
        elif fusion_score >= 40:
            advice_parts.append("🔄 技术面状态：中性，等待更明确信号")
        elif fusion_score >= 25:
            advice_parts.append("📉 技术面状态：偏弱，整体偏空")
        else:
            advice_parts.append("🚨 技术面状态：弱势，多项指标看空")
        
        # 3. 盘后特殊提示
        if market_status['is_after_hours'] and after_hours_result:
            if after_hours_result['is_significant']:
                advice_parts.append(
                    f"🌙 盘后提示：{after_hours_result['movement_type']}，"
                    f"{after_hours_result['recommendation']}"
                )
            else:
                advice_parts.append("🌙 盘后波动微弱，统计学不显著")
        
        return " | ".join(advice_parts)
    
    def _map_score_to_recommendation(self, score: float) -> str:
        """评分映射为技术面评级"""
        if score >= 80:
            return "strong_buy"  # 强势
        elif score >= 60:
            return "buy"  # 偏强
        elif score >= 40:
            return "hold"  # 中性
        elif score >= 20:
            return "sell"  # 偏弱
        else:
            return "strong_sell"  # 弱势
    
    def _explain_cross_validation(
        self,
        is_aligned: bool,
        quant_score: float,
        sentiment_score: float,
        after_hours_result: Optional[Dict]
    ) -> str:
        """解释交叉验证结果"""
        explanation = []
        
        if is_aligned:
            explanation.append(
                f"量化评分({quant_score:.1f})与情绪评分({sentiment_score:.1f})方向一致，"
                "信号可靠性较高"
            )
        else:
            explanation.append(
                f"量化评分({quant_score:.1f})与情绪评分({sentiment_score:.1f})出现背离，"
                "需谨慎判断，建议等待更多确认信号"
            )
        
        if after_hours_result and after_hours_result['is_significant']:
            explanation.append(
                f"盘后检测到{after_hours_result['movement_type']}，"
                "波动率比率达到{after_hours_result['volatility_ratio']}"
            )
        
        return "；".join(explanation)
    
    def get_fusion_report(self) -> Dict:
        """获取融合分析报告"""
        return {
            "fusion_score": round(self.fusion_score, 1),
            "confidence": self.fusion_confidence,
            "recommendation": self.fusion_recommendation,
            "quant_analysis": self.quant_agent.get_analysis(),
            "info_analysis": self.info_agent.get_analysis()
        }
