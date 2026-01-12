"""
============================================
交易信号系统模块
Trading Signal System Module
============================================

提供买入/卖出信号触发、风险管理计算、多周期确认等功能
仅供技术分析参考，不构成投资建议
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import numpy as np


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"           # 买入信号
    SELL = "sell"         # 卖出信号
    HOLD = "hold"         # 持有/观望


class SignalStrength(Enum):
    """信号强度"""
    STRONG = 5            # 强信号 (多指标共振)
    MODERATE = 3          # 中等信号
    WEAK = 1              # 弱信号


@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: SignalType
    strength: int                    # 1-5 强度评级
    triggered_conditions: List[str]  # 触发的条件列表
    pending_conditions: List[str]    # 待确认的条件
    confidence: float                # 置信度 0-1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RiskManagement:
    """风险管理参数"""
    stop_loss: float                 # 止损价位
    stop_loss_pct: float             # 止损百分比
    take_profit_1: float             # 止盈目标1 (1:2风险收益比)
    take_profit_2: float             # 止盈目标2 (1:3风险收益比)
    take_profit_3: float             # 止盈目标3 (1:5风险收益比)
    suggested_position_pct: float    # 建议仓位百分比
    risk_reward_ratio: str           # 风险收益比
    max_loss_per_trade: float        # 单笔最大亏损金额(假设10万本金)


@dataclass
class MultiTimeframeSignal:
    """多周期信号确认"""
    daily_signal: SignalType
    weekly_signal: Optional[SignalType]
    monthly_signal: Optional[SignalType]
    confirmation_level: str          # strong/medium/weak
    description: str


class TradingSignalGenerator:
    """
    交易信号生成器
    
    基于多维技术指标生成买入/卖出信号
    仅供技术分析参考，不构成投资建议
    """
    
    def __init__(self):
        # 买入信号触发条件权重
        self.buy_conditions = {
            "price_above_ma20": 1,
            "price_above_ma60": 1,
            "macd_golden_cross": 2,
            "macd_bullish": 1,
            "rsi_oversold_recovery": 2,
            "kdj_golden_cross": 1,
            "kdj_oversold": 1,
            "bb_near_lower": 1,
            "volume_breakout": 1,
            "adx_strong_bullish": 2,
            "sar_bullish": 1,
            "ichimoku_above_cloud": 2,
            "mfi_inflow": 1,
            "dmi_bullish": 1,
            "bias_oversold": 1,
        }
        
        # 卖出信号触发条件权重
        self.sell_conditions = {
            "price_below_ma20": 1,
            "price_below_ma60": 1,
            "macd_death_cross": 2,
            "macd_bearish": 1,
            "rsi_overbought": 2,
            "kdj_death_cross": 1,
            "kdj_overbought": 1,
            "bb_near_upper": 1,
            "volume_decline": 1,
            "adx_strong_bearish": 2,
            "sar_bearish": 1,
            "ichimoku_below_cloud": 2,
            "mfi_outflow": 1,
            "dmi_bearish": 1,
            "bias_overbought": 1,
        }

    def generate_signal(self, indicators: Dict) -> TradingSignal:
        """
        根据技术指标生成交易信号
        
        Args:
            indicators: 技术指标字典 (来自 calculate_all_indicators)
        
        Returns:
            TradingSignal 对象
        """
        buy_triggered = []
        buy_pending = []
        sell_triggered = []
        sell_pending = []
        
        buy_score = 0
        sell_score = 0
        
        # 1. 均线系统检查
        ma_trend = indicators.get("ma_trend", "")
        ma_values = indicators.get("moving_averages", {})
        latest_price = indicators.get("latest_price", 0)
        
        if ma_trend == "bullish_alignment":
            buy_triggered.append("均线多头排列")
            buy_score += 2
        elif ma_trend == "bearish_alignment":
            sell_triggered.append("均线空头排列")
            sell_score += 2
        
        ma20 = ma_values.get("MA20", 0)
        ma60 = ma_values.get("MA60", 0)
        
        if latest_price > 0 and ma20 > 0:
            if latest_price > ma20:
                buy_triggered.append("价格站上MA20")
                buy_score += self.buy_conditions["price_above_ma20"]
            else:
                sell_triggered.append("价格跌破MA20")
                sell_score += self.sell_conditions["price_below_ma20"]
        
        if latest_price > 0 and ma60 > 0:
            if latest_price > ma60:
                buy_triggered.append("价格站上MA60")
                buy_score += self.buy_conditions["price_above_ma60"]
            else:
                sell_triggered.append("价格跌破MA60")
                sell_score += self.sell_conditions["price_below_ma60"]
        
        # 2. MACD检查
        macd = indicators.get("macd", {})
        if macd.get("crossover") == "golden_cross":
            buy_triggered.append("MACD金叉")
            buy_score += self.buy_conditions["macd_golden_cross"]
        elif macd.get("crossover") == "death_cross":
            sell_triggered.append("MACD死叉")
            sell_score += self.sell_conditions["macd_death_cross"]
        
        if macd.get("trend") == "bullish":
            buy_triggered.append("MACD柱状图为正")
            buy_score += self.buy_conditions["macd_bullish"]
        elif macd.get("trend") == "bearish":
            sell_triggered.append("MACD柱状图为负")
            sell_score += self.sell_conditions["macd_bearish"]

        # 3. RSI检查
        rsi = indicators.get("rsi", {})
        rsi_value = rsi.get("value", 50)
        if rsi.get("status") == "oversold":
            buy_triggered.append(f"RSI超卖({rsi_value:.1f})")
            buy_score += self.buy_conditions["rsi_oversold_recovery"]
        elif rsi.get("status") == "overbought":
            sell_triggered.append(f"RSI超买({rsi_value:.1f})")
            sell_score += self.sell_conditions["rsi_overbought"]
        else:
            if rsi_value < 40:
                buy_pending.append(f"RSI偏低({rsi_value:.1f})，待进入超卖区")
            elif rsi_value > 60:
                sell_pending.append(f"RSI偏高({rsi_value:.1f})，待进入超买区")
        
        # 4. KDJ检查
        kdj = indicators.get("kdj", {})
        if kdj.get("crossover") == "golden_cross":
            buy_triggered.append("KDJ金叉")
            buy_score += self.buy_conditions["kdj_golden_cross"]
        elif kdj.get("crossover") == "death_cross":
            sell_triggered.append("KDJ死叉")
            sell_score += self.sell_conditions["kdj_death_cross"]
        
        if kdj.get("status") == "oversold":
            buy_triggered.append("KDJ超卖区域")
            buy_score += self.buy_conditions["kdj_oversold"]
        elif kdj.get("status") == "overbought":
            sell_triggered.append("KDJ超买区域")
            sell_score += self.sell_conditions["kdj_overbought"]
        
        # 5. 布林带检查
        bb = indicators.get("bollinger_bands", {})
        if bb.get("status") == "near_lower":
            buy_triggered.append("触及布林带下轨")
            buy_score += self.buy_conditions["bb_near_lower"]
        elif bb.get("status") == "near_upper":
            sell_triggered.append("触及布林带上轨")
            sell_score += self.sell_conditions["bb_near_upper"]
        
        # 6. 成交量检查
        vol = indicators.get("volume_analysis", {})
        vol_ratio = vol.get("volume_ratio", 1)
        if vol.get("status") == "high_volume" and vol_ratio > 1.5:
            if buy_score > sell_score:
                buy_triggered.append(f"放量确认({vol_ratio:.1f}倍)")
                buy_score += self.buy_conditions["volume_breakout"]
            else:
                sell_triggered.append(f"放量下跌({vol_ratio:.1f}倍)")
                sell_score += self.sell_conditions["volume_decline"]
        elif vol.get("status") == "low_volume":
            buy_pending.append("成交量萎缩，待放量确认")

        # 7. ADX趋势强度检查
        adx = indicators.get("adx", {})
        if adx.get("trend_strength") == "strong":
            if adx.get("trend_direction") == "bullish":
                buy_triggered.append(f"ADX强势上涨({adx.get('adx', 0):.1f})")
                buy_score += self.buy_conditions["adx_strong_bullish"]
            else:
                sell_triggered.append(f"ADX强势下跌({adx.get('adx', 0):.1f})")
                sell_score += self.sell_conditions["adx_strong_bearish"]
        
        # 8. SAR抛物线检查
        sar = indicators.get("sar", {})
        if sar.get("signal") == "buy":
            buy_triggered.append("SAR趋势反转向上")
            buy_score += self.buy_conditions["sar_bullish"]
        elif sar.get("signal") == "sell":
            sell_triggered.append("SAR趋势反转向下")
            sell_score += self.sell_conditions["sar_bearish"]
        elif sar.get("status") == "bullish":
            buy_triggered.append("SAR上升趋势")
            buy_score += 0.5
        elif sar.get("status") == "bearish":
            sell_triggered.append("SAR下降趋势")
            sell_score += 0.5
        
        # 9. Ichimoku云图检查
        ichimoku = indicators.get("ichimoku", {})
        if ichimoku.get("status") == "strong_bullish":
            buy_triggered.append("云图强势看多")
            buy_score += self.buy_conditions["ichimoku_above_cloud"]
        elif ichimoku.get("status") == "strong_bearish":
            sell_triggered.append("云图强势看空")
            sell_score += self.sell_conditions["ichimoku_below_cloud"]
        elif ichimoku.get("cloud_position") == "above_cloud":
            buy_triggered.append("价格在云层上方")
            buy_score += 1
        elif ichimoku.get("cloud_position") == "below_cloud":
            sell_triggered.append("价格在云层下方")
            sell_score += 1
        
        # 10. MFI资金流向检查
        mfi = indicators.get("money_flow", {})
        if mfi.get("mfi_status") == "inflow":
            buy_triggered.append("资金净流入")
            buy_score += self.buy_conditions["mfi_inflow"]
        elif mfi.get("mfi_status") == "outflow":
            sell_triggered.append("资金净流出")
            sell_score += self.sell_conditions["mfi_outflow"]
        elif mfi.get("mfi_status") == "oversold":
            buy_triggered.append("MFI超卖")
            buy_score += 1
        elif mfi.get("mfi_status") == "overbought":
            sell_triggered.append("MFI超买")
            sell_score += 1

        # 11. DMI趋向指标检查
        dmi = indicators.get("dmi", {})
        if dmi.get("status") in ["strong_bullish", "bullish"]:
            buy_triggered.append(f"DMI看多(+DI>{dmi.get('plus_di', 0):.1f})")
            buy_score += self.buy_conditions["dmi_bullish"]
        elif dmi.get("status") in ["strong_bearish", "bearish"]:
            sell_triggered.append(f"DMI看空(-DI>{dmi.get('minus_di', 0):.1f})")
            sell_score += self.sell_conditions["dmi_bearish"]
        
        # 12. BIAS乖离率检查
        bias = indicators.get("bias", {})
        if bias.get("signal") == "buy":
            buy_triggered.append(f"BIAS超卖({bias.get('bias_6', 0):.1f}%)")
            buy_score += self.buy_conditions["bias_oversold"]
        elif bias.get("signal") == "sell":
            sell_triggered.append(f"BIAS超买({bias.get('bias_6', 0):.1f}%)")
            sell_score += self.sell_conditions["bias_overbought"]
        
        # 计算信号类型和强度
        total_score = buy_score + sell_score
        if total_score == 0:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        elif buy_score > sell_score:
            signal_type = SignalType.BUY
            strength = min(5, int(buy_score / 3) + 1)
            confidence = buy_score / (buy_score + sell_score + 1)
        elif sell_score > buy_score:
            signal_type = SignalType.SELL
            strength = min(5, int(sell_score / 3) + 1)
            confidence = sell_score / (buy_score + sell_score + 1)
        else:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        
        # 合并触发条件
        if signal_type == SignalType.BUY:
            triggered = buy_triggered
            pending = buy_pending + [f"⚠️ {c}" for c in sell_triggered[:2]]
        elif signal_type == SignalType.SELL:
            triggered = sell_triggered
            pending = sell_pending + [f"⚠️ {c}" for c in buy_triggered[:2]]
        else:
            triggered = []
            pending = buy_pending + sell_pending
        
        return TradingSignal(
            signal_type=signal_type,
            strength=strength,
            triggered_conditions=triggered,
            pending_conditions=pending,
            confidence=confidence
        )

    def calculate_risk_management(
        self,
        current_price: float,
        support_levels: List[float],
        resistance_levels: List[float],
        atr: float,
        signal_type: SignalType,
        account_capital: float = 100000
    ) -> RiskManagement:
        """
        计算风险管理参数
        
        Args:
            current_price: 当前价格
            support_levels: 支撑位列表
            resistance_levels: 阻力位列表
            atr: 平均真实波幅
            signal_type: 信号类型
            account_capital: 账户资金(默认10万)
        
        Returns:
            RiskManagement 对象
        """
        if current_price <= 0:
            return self._default_risk_management(current_price)
        
        # 计算止损位
        if signal_type == SignalType.BUY:
            # 买入信号：止损设在最近支撑位下方 1-1.5 个 ATR
            if support_levels and len(support_levels) > 0:
                nearest_support = max([s for s in support_levels if s < current_price], default=current_price * 0.95)
                stop_loss = nearest_support - atr * 1.5
            else:
                stop_loss = current_price - atr * 2
            
            # 确保止损不会太远
            max_stop_loss = current_price * 0.92  # 最大8%止损
            stop_loss = max(stop_loss, max_stop_loss)
            
        elif signal_type == SignalType.SELL:
            # 卖出信号：止损设在最近阻力位上方 1-1.5 个 ATR
            if resistance_levels and len(resistance_levels) > 0:
                nearest_resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.05)
                stop_loss = nearest_resistance + atr * 1.5
            else:
                stop_loss = current_price + atr * 2
            
            # 确保止损不会太远
            min_stop_loss = current_price * 1.08  # 最大8%止损
            stop_loss = min(stop_loss, min_stop_loss)
        else:
            stop_loss = current_price * 0.95
        
        # 计算止损百分比
        stop_loss_pct = abs(current_price - stop_loss) / current_price * 100
        
        # 计算风险金额
        risk_per_share = abs(current_price - stop_loss)
        
        # 计算止盈目标 (基于风险收益比)
        if signal_type == SignalType.BUY:
            take_profit_1 = current_price + risk_per_share * 2   # 1:2
            take_profit_2 = current_price + risk_per_share * 3   # 1:3
            take_profit_3 = current_price + risk_per_share * 5   # 1:5
        elif signal_type == SignalType.SELL:
            take_profit_1 = current_price - risk_per_share * 2
            take_profit_2 = current_price - risk_per_share * 3
            take_profit_3 = current_price - risk_per_share * 5
        else:
            take_profit_1 = current_price * 1.05
            take_profit_2 = current_price * 1.08
            take_profit_3 = current_price * 1.12

        # 计算建议仓位 (基于单笔最大亏损2%原则)
        max_risk_pct = 0.02  # 单笔最大亏损2%
        max_loss_amount = account_capital * max_risk_pct
        
        if risk_per_share > 0:
            suggested_shares = max_loss_amount / risk_per_share
            suggested_position_value = suggested_shares * current_price
            suggested_position_pct = (suggested_position_value / account_capital) * 100
        else:
            suggested_position_pct = 10
        
        # 限制最大仓位
        suggested_position_pct = min(suggested_position_pct, 30)  # 最大30%
        suggested_position_pct = max(suggested_position_pct, 5)   # 最小5%
        
        return RiskManagement(
            stop_loss=round(stop_loss, 4),
            stop_loss_pct=round(stop_loss_pct, 2),
            take_profit_1=round(take_profit_1, 4),
            take_profit_2=round(take_profit_2, 4),
            take_profit_3=round(take_profit_3, 4),
            suggested_position_pct=round(suggested_position_pct, 1),
            risk_reward_ratio="1:2 / 1:3 / 1:5",
            max_loss_per_trade=round(max_loss_amount, 2)
        )
    
    def _default_risk_management(self, price: float) -> RiskManagement:
        """默认风险管理参数"""
        return RiskManagement(
            stop_loss=price * 0.95,
            stop_loss_pct=5.0,
            take_profit_1=price * 1.10,
            take_profit_2=price * 1.15,
            take_profit_3=price * 1.25,
            suggested_position_pct=10.0,
            risk_reward_ratio="1:2 / 1:3 / 1:5",
            max_loss_per_trade=2000
        )

    def get_signal_strength_label(self, strength: int) -> str:
        """获取信号强度标签"""
        labels = {
            5: "★★★★★ 强信号",
            4: "★★★★☆ 较强信号",
            3: "★★★☆☆ 中等信号",
            2: "★★☆☆☆ 较弱信号",
            1: "★☆☆☆☆ 弱信号",
            0: "☆☆☆☆☆ 无明确信号"
        }
        return labels.get(strength, "☆☆☆☆☆ 无明确信号")
    
    def get_signal_description(self, signal: TradingSignal) -> str:
        """获取信号描述"""
        if signal.signal_type == SignalType.BUY:
            return f"买入信号触发 ({len(signal.triggered_conditions)}个条件满足)"
        elif signal.signal_type == SignalType.SELL:
            return f"卖出信号触发 ({len(signal.triggered_conditions)}个条件满足)"
        else:
            return "观望信号 (条件不充分)"


def generate_trading_analysis(indicators: Dict, support_resistance: Dict) -> Dict:
    """
    生成完整的交易分析结果
    
    Args:
        indicators: 技术指标数据
        support_resistance: 支撑阻力位数据
    
    Returns:
        包含信号、风险管理、操作建议的完整分析结果
    """
    generator = TradingSignalGenerator()
    
    # 生成交易信号
    signal = generator.generate_signal(indicators)
    
    # 获取价格和ATR
    current_price = indicators.get("latest_price", 0)
    atr_data = indicators.get("atr", {})
    atr = atr_data.get("value", current_price * 0.02)
    
    # 获取支撑阻力位
    support_levels = [l.get("price", 0) for l in support_resistance.get("support_levels", [])]
    resistance_levels = [l.get("price", 0) for l in support_resistance.get("resistance_levels", [])]
    
    # 计算风险管理
    risk_mgmt = generator.calculate_risk_management(
        current_price=current_price,
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        atr=atr,
        signal_type=signal.signal_type
    )

    # 生成操作建议
    if signal.signal_type == SignalType.BUY:
        if signal.strength >= 4:
            action_suggestion = "多个指标共振看多，可考虑分批建仓"
        elif signal.strength >= 2:
            action_suggestion = "偏多信号，可小仓位试探"
        else:
            action_suggestion = "弱多信号，建议等待更多确认"
    elif signal.signal_type == SignalType.SELL:
        if signal.strength >= 4:
            action_suggestion = "多个指标共振看空，持仓者考虑减仓"
        elif signal.strength >= 2:
            action_suggestion = "偏空信号，注意风险控制"
        else:
            action_suggestion = "弱空信号，密切关注走势"
    else:
        action_suggestion = "多空力量均衡，建议观望等待明确信号"
    
    return {
        "signal": {
            "type": signal.signal_type.value,
            "type_cn": "买入" if signal.signal_type == SignalType.BUY else ("卖出" if signal.signal_type == SignalType.SELL else "观望"),
            "strength": signal.strength,
            "strength_label": generator.get_signal_strength_label(signal.strength),
            "confidence": round(signal.confidence * 100, 1),
            "description": generator.get_signal_description(signal),
            "triggered_conditions": signal.triggered_conditions,
            "pending_conditions": signal.pending_conditions,
        },
        "risk_management": {
            "stop_loss": risk_mgmt.stop_loss,
            "stop_loss_pct": risk_mgmt.stop_loss_pct,
            "take_profit_targets": [
                {"level": 1, "price": risk_mgmt.take_profit_1, "ratio": "1:2"},
                {"level": 2, "price": risk_mgmt.take_profit_2, "ratio": "1:3"},
                {"level": 3, "price": risk_mgmt.take_profit_3, "ratio": "1:5"},
            ],
            "suggested_position_pct": risk_mgmt.suggested_position_pct,
            "max_loss_per_trade": risk_mgmt.max_loss_per_trade,
            "risk_reward_ratio": risk_mgmt.risk_reward_ratio,
        },
        "action_suggestion": action_suggestion,
        "current_price": current_price,
        "disclaimer": "以上内容仅为技术分析工具输出，不构成投资建议，请独立判断并自行承担风险。"
    }
