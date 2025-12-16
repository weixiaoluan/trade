"""
============================================
量化-AI联动分析系统集成模块
Quant-AI Integration Module
============================================
"""

import json
from datetime import datetime
from typing import Dict, List
from .event_engine import QuantEventEngine
from .fusion_engine import FusionAnalysisEngine


def integrate_quant_with_existing_system(
    stock_data: dict,
    stock_info: dict,
    indicators: dict,
    trend: dict,
    levels: dict
) -> Dict:
    """
    集成量化系统到现有分析流程
    
    Args:
        stock_data: 现有系统的股票数据
        stock_info: 现有系统的基本信息
        indicators: 现有系统的技术指标
        trend: 现有系统的趋势分析
        levels: 现有系统的支撑阻力位
        
    Returns:
        增强后的分析结果
    """
    # 1. 启动量化事件引擎
    event_engine = QuantEventEngine()
    event_engine.start()
    
    # 2. 创建融合分析引擎
    fusion_engine = FusionAnalysisEngine(event_engine)
    
    # 3. 转换数据格式
    ohlcv_data = stock_data.get('ohlcv', [])
    
    # 4. 执行融合分析
    fusion_result = fusion_engine.analyze_with_fusion(
        ohlcv_data,
        market="CN" if any(code in stock_info.get('ticker', '') for code in ['SS', 'SZ', 'HK']) else "US"
    )
    
    # 5. 合并结果
    enhanced_result = {
        # 保留原有系统的数据
        "original_indicators": indicators,
        "original_trend": trend,
        "original_levels": levels,
        
        # 添加量化系统的增强分析
        "quant_fusion": fusion_result,
        
        # 提取关键指标供前端展示
        "enhanced_metrics": {
            "fusion_score": fusion_result['fusion_score'],
            "fusion_confidence": fusion_result['fusion_confidence'],
            "market_status": fusion_result['market_status'],
            "quant_signals": fusion_result['quant_analysis']['signals'],
            "sentiment_score": fusion_result['info_analysis']['sentiment_score'],
            "market_regime": fusion_result['info_analysis']['market_regime'],
            "after_hours_warning": fusion_result['after_hours_analysis'] if fusion_result['after_hours_analysis'] else None
        },
        
        # 生成综合建议
        "integrated_recommendation": _generate_integrated_recommendation(
            fusion_result,
            trend
        ),
        
        "timestamp": datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    }
    
    # 6. 关闭事件引擎
    event_engine.stop()
    
    return enhanced_result


def _generate_integrated_recommendation(
    fusion_result: Dict,
    trend: Dict
) -> str:
    """生成综合建议"""
    fusion_score = fusion_result['fusion_score']
    confidence = fusion_result['fusion_confidence']
    final_advice = fusion_result['final_advice']
    
    # 原有系统的建议
    original_recommendation = trend.get('quant_analysis', {}).get('recommendation', 'hold')
    
    # 融合建议
    fusion_recommendation = fusion_result['cross_validation']['recommendation']
    
    if fusion_recommendation == original_recommendation:
        consistency = "✅ 量化融合系统与原有分析一致"
    else:
        consistency = "⚠️ 量化融合系统与原有分析存在差异，建议综合判断"
    
    return f"""
## 🤖 量化-AI联动分析建议

**融合评分**: {fusion_score:.1f}/100 (置信度: {confidence})

**系统建议**: {final_advice}

**一致性检查**: {consistency}

**操作策略**: {fusion_result['adjusted_strategy']['rationale']}
- 建议止损: {fusion_result['adjusted_strategy']['stop_loss_pct']}%
- 入场阈值: {fusion_result['adjusted_strategy']['entry_threshold']}
- 仓位建议: {fusion_result['adjusted_strategy']['position_size']}倍标准仓位

**量化信号详情**:
{chr(10).join('- ' + sig for sig in fusion_result['quant_analysis']['signals'][:10])}

**市场情绪**: {fusion_result['info_analysis']['interpretation']}
"""


def format_for_api_response(enhanced_result: Dict) -> Dict:
    """
    格式化为API响应
    
    将增强结果整合到现有API响应格式中
    """
    metrics = enhanced_result['enhanced_metrics']
    
    return {
        "quantScore": metrics['fusion_score'],
        "marketRegime": metrics['market_regime'],
        "volatilityState": metrics['sentiment_score'] > 60 and "low" or "medium" if metrics['sentiment_score'] > 40 else "high",
        "quantConfidence": metrics['fusion_confidence'],
        "signalDetails": metrics['quant_signals'],
        "marketStatus": metrics['market_status']['status'],
        "afterHoursWarning": metrics['after_hours_warning'],
        "fusionRecommendation": enhanced_result['integrated_recommendation'],
        "timestamp": enhanced_result['timestamp']
    }
