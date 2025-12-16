"""
============================================
盘后微波动检测器
After-Hours Micro-Movement Detector
============================================
"""

import numpy as np
from datetime import datetime, time
from typing import Optional, Dict, List


class AfterHoursDetector:
    """
    盘后微波动检测器
    
    功能：
    1. 检测是否处于盘后时段
    2. 分析盘后微小波动的统计学意义
    3. 判断是否为噪音或具有信息价值
    """
    
    def __init__(self):
        self.trading_hours = {
            "US": [(time(9, 30), time(16, 0))],  # 美股交易时间（美东时间）
            "CN": [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))],  # A股交易时间
        }
        
    def is_after_hours(self, market: str = "CN", check_time: Optional[datetime] = None) -> bool:
        """
        判断是否为盘后时段
        
        Args:
            market: 市场类型 ("US" 或 "CN")
            check_time: 检查时间，默认为当前时间
            
        Returns:
            True 表示盘后，False 表示盘中
        """
        if check_time is None:
            check_time = datetime.now()
        
        current_time = check_time.time()
        trading_periods = self.trading_hours.get(market, self.trading_hours["CN"])
        
        # 检查是否在交易时段内
        for start, end in trading_periods:
            if start <= current_time <= end:
                return False
        
        return True
    
    def analyze_micro_movement(
        self,
        recent_prices: List[float],
        volume_data: Optional[List[float]] = None,
        lookback_period: int = 20
    ) -> Dict:
        """
        分析盘后微波动的统计学意义
        
        Args:
            recent_prices: 最近的价格序列（盘后tick数据）
            volume_data: 对应的成交量数据
            lookback_period: 回溯周期，用于计算基准波动率
            
        Returns:
            分析结果字典
        """
        if len(recent_prices) < 2:
            return {
                "is_significant": False,
                "movement_type": "insufficient_data",
                "volatility_ratio": 0.0,
                "recommendation": "观望"
            }
        
        # 计算盘后价格变化
        price_changes = np.diff(recent_prices)
        recent_volatility = np.std(price_changes) if len(price_changes) > 0 else 0
        mean_change = np.mean(price_changes) if len(price_changes) > 0 else 0
        
        # 计算基准波动率（使用历史数据）
        if lookback_period > len(recent_prices):
            lookback_period = len(recent_prices)
        
        historical_changes = np.diff(recent_prices[-lookback_period:])
        historical_volatility = np.std(historical_changes) if len(historical_changes) > 0 else 1e-6
        
        # 计算波动率比率（盘后 vs 历史）
        volatility_ratio = recent_volatility / historical_volatility if historical_volatility > 0 else 0
        
        # 统计学显著性检验
        is_significant = False
        movement_type = "noise"  # 默认为噪音
        
        if volatility_ratio > 2.0:
            # 盘后波动显著高于历史水平
            is_significant = True
            movement_type = "abnormal_volatility"
        elif abs(mean_change) > 2 * historical_volatility:
            # 价格变化超过2个标准差
            is_significant = True
            movement_type = "directional_move"
        elif volume_data and len(volume_data) > 1:
            # 如果有成交量数据，检查量价配合
            volume_change = np.diff(volume_data)
            if len(volume_change) > 0:
                avg_volume_change = np.mean(volume_change)
                if avg_volume_change > np.std(volume_change):
                    is_significant = True
                    movement_type = "volume_driven"
        
        # 生成建议
        recommendation = self._generate_recommendation(
            is_significant, 
            movement_type, 
            mean_change,
            volatility_ratio
        )
        
        return {
            "is_significant": is_significant,
            "movement_type": movement_type,
            "volatility_ratio": round(volatility_ratio, 2),
            "mean_change_pct": round(mean_change * 100, 4),
            "recommendation": recommendation,
            "details": {
                "recent_volatility": round(recent_volatility, 6),
                "historical_volatility": round(historical_volatility, 6),
                "price_trend": "上涨" if mean_change > 0 else "下跌" if mean_change < 0 else "横盘"
            }
        }
    
    def _generate_recommendation(
        self,
        is_significant: bool,
        movement_type: str,
        mean_change: float,
        volatility_ratio: float
    ) -> str:
        """生成操作建议"""
        if not is_significant:
            return "盘后微弱波动，统计学不显著，建议观望等待次日开盘"
        
        if movement_type == "noise":
            return "波动较小，可能为随机噪音，暂不调整仓位"
        
        if movement_type == "abnormal_volatility":
            return f"盘后波动异常放大（{volatility_ratio:.1f}倍），需关注突发消息，考虑设置预警"
        
        if movement_type == "directional_move":
            direction = "上涨" if mean_change > 0 else "下跌"
            return f"盘后出现{direction}趋势，可能有重大信息，建议次日开盘密切关注"
        
        if movement_type == "volume_driven":
            return "盘后成交量异常，可能存在大单交易，需评估流动性风险"
        
        return "需进一步观察"
    
    def get_market_status(self, market: str = "CN") -> Dict:
        """
        获取当前市场状态
        
        Returns:
            市场状态信息
        """
        now = datetime.now()
        is_after_hours = self.is_after_hours(market, now)
        
        status = {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "market": market,
            "status": "盘后 (After-Hours)" if is_after_hours else "盘中 (Trading Hours)",
            "is_after_hours": is_after_hours,
            "trading_hours": str(self.trading_hours[market])
        }
        
        return status
