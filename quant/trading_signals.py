"""
============================================
交易信号系统模块
Trading Signal System Module
============================================

综合AI分析+量化数据指标，生成可行的交易方案参考
基于以下数据源：
1. 技术指标分析（12+指标）
2. 量化评分系统
3. 趋势分析（多空信号统计）
4. 市场状态判断
5. 支撑阻力位分析

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


@dataclass
class PositionStrategy:
    """仓位策略"""
    empty_position: str              # 空仓时操作建议
    first_entry: str                 # 首次建仓建议
    add_position: str                # 加仓条件
    reduce_position: str             # 减仓条件
    full_exit: str                   # 清仓条件


class TradingSignalGenerator:
    """
    交易信号生成器
    
    综合AI分析+量化数据指标，生成可行的交易方案参考
    数据来源：
    1. 技术指标（均线/MACD/RSI/KDJ/布林带/成交量/ADX/SAR/云图/MFI/DMI/BIAS）
    2. 量化评分系统（0-100分）
    3. 趋势分析（多空信号统计）
    4. 市场状态（趋势市/震荡市）
    5. 支撑阻力位
    
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
            # 量化分析权重
            "quant_strong_buy": 3,
            "quant_buy": 2,
            "high_quant_score": 2,
            "bullish_trend": 2,
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
            # 量化分析权重
            "quant_strong_sell": 3,
            "quant_sell": 2,
            "low_quant_score": 2,
            "bearish_trend": 2,
        }


    def generate_signal(self, indicators: Dict, quant_analysis: Dict = None, trend_analysis: Dict = None) -> TradingSignal:
        """
        根据技术指标+量化分析+趋势分析生成交易信号
        
        Args:
            indicators: 技术指标字典 (来自 calculate_all_indicators)
            quant_analysis: 量化分析数据 (包含 quant_score, recommendation, market_regime 等)
            trend_analysis: 趋势分析数据 (包含 bullish_signals, bearish_signals 等)
        
        Returns:
            TradingSignal 对象
        """
        buy_triggered = []
        buy_pending = []
        sell_triggered = []
        sell_pending = []
        
        buy_score = 0
        sell_score = 0
        
        # ========== 第一部分：量化分析数据 ==========
        if quant_analysis:
            quant_score = quant_analysis.get("quant_score", 50)
            quant_reco = quant_analysis.get("recommendation", "hold")
            market_regime = quant_analysis.get("market_regime", "unknown")
            
            # 量化评分判断
            if quant_score >= 70:
                buy_triggered.append(f"量化评分优秀({quant_score:.0f}分)")
                buy_score += self.buy_conditions["high_quant_score"]
            elif quant_score <= 30:
                sell_triggered.append(f"量化评分较低({quant_score:.0f}分)")
                sell_score += self.sell_conditions["low_quant_score"]
            elif quant_score >= 55:
                buy_pending.append(f"量化评分中上({quant_score:.0f}分)")
            elif quant_score <= 45:
                sell_pending.append(f"量化评分中下({quant_score:.0f}分)")
            
            # 量化建议判断
            if quant_reco == "strong_buy":
                buy_triggered.append("量化建议：强烈看多")
                buy_score += self.buy_conditions["quant_strong_buy"]
            elif quant_reco == "buy":
                buy_triggered.append("量化建议：看多")
                buy_score += self.buy_conditions["quant_buy"]
            elif quant_reco == "strong_sell":
                sell_triggered.append("量化建议：强烈看空")
                sell_score += self.sell_conditions["quant_strong_sell"]
            elif quant_reco == "sell":
                sell_triggered.append("量化建议：看空")
                sell_score += self.sell_conditions["quant_sell"]
            
            # 市场状态判断
            if market_regime == "trending":
                buy_pending.append("市场处于趋势状态")
            elif market_regime == "ranging":
                sell_pending.append("市场处于震荡状态")
        
        # ========== 第二部分：趋势分析数据 ==========
        if trend_analysis:
            bullish_signals = trend_analysis.get("bullish_signals", 0)
            bearish_signals = trend_analysis.get("bearish_signals", 0)
            
            if bullish_signals > bearish_signals + 3:
                buy_triggered.append(f"多头信号占优({bullish_signals}:{bearish_signals})")
                buy_score += self.buy_conditions["bullish_trend"]
            elif bearish_signals > bullish_signals + 3:
                sell_triggered.append(f"空头信号占优({bearish_signals}:{bullish_signals})")
                sell_score += self.sell_conditions["bearish_trend"]
            elif bullish_signals > bearish_signals:
                buy_pending.append(f"多头略占优({bullish_signals}:{bearish_signals})")
            elif bearish_signals > bullish_signals:
                sell_pending.append(f"空头略占优({bearish_signals}:{bullish_signals})")

        
        # ========== 第三部分：技术指标分析 ==========
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
                buy_pending.append(f"RSI偏低({rsi_value:.1f})")
            elif rsi_value > 60:
                sell_pending.append(f"RSI偏高({rsi_value:.1f})")
        
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
        
        # ========== 第四部分：综合计算信号 ==========
        total_score = buy_score + sell_score
        if total_score == 0:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        elif buy_score > sell_score:
            signal_type = SignalType.BUY
            score_diff = buy_score - sell_score
            strength = min(5, max(1, int(score_diff / 2.5) + 1))
            confidence = buy_score / (buy_score + sell_score + 1)
        elif sell_score > buy_score:
            signal_type = SignalType.SELL
            score_diff = sell_score - buy_score
            strength = min(5, max(1, int(score_diff / 2.5) + 1))
            confidence = sell_score / (buy_score + sell_score + 1)
        else:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        
        # 合并触发条件
        if signal_type == SignalType.BUY:
            triggered = buy_triggered
            pending = buy_pending + [f"⚠️ {c}" for c in sell_triggered[:3]]
        elif signal_type == SignalType.SELL:
            triggered = sell_triggered
            pending = sell_pending + [f"⚠️ {c}" for c in buy_triggered[:3]]
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
        signal_strength: int = 3
    ) -> Tuple[RiskManagement, PositionStrategy]:
        """
        计算风险管理参数和仓位策略
        """
        if current_price <= 0:
            return self._default_risk_management(current_price)
        
        # 计算止损位
        if signal_type == SignalType.BUY:
            if support_levels and len(support_levels) > 0:
                nearest_support = max([s for s in support_levels if s < current_price], default=current_price * 0.95)
                stop_loss = nearest_support - atr * 1.5
            else:
                stop_loss = current_price - atr * 2
            max_stop_loss = current_price * 0.92
            stop_loss = max(stop_loss, max_stop_loss)
            
        elif signal_type == SignalType.SELL:
            if resistance_levels and len(resistance_levels) > 0:
                nearest_resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.05)
                stop_loss = nearest_resistance + atr * 1.5
            else:
                stop_loss = current_price + atr * 2
            min_stop_loss = current_price * 1.08
            stop_loss = min(stop_loss, min_stop_loss)
        else:
            stop_loss = current_price * 0.95
        
        stop_loss_pct = abs(current_price - stop_loss) / current_price * 100
        risk_per_share = abs(current_price - stop_loss)
        
        # 计算止盈目标
        if signal_type == SignalType.BUY:
            take_profit_1 = current_price + risk_per_share * 2
            take_profit_2 = current_price + risk_per_share * 3
            take_profit_3 = current_price + risk_per_share * 5
        elif signal_type == SignalType.SELL:
            take_profit_1 = current_price - risk_per_share * 2
            take_profit_2 = current_price - risk_per_share * 3
            take_profit_3 = current_price - risk_per_share * 5
        else:
            take_profit_1 = current_price * 1.05
            take_profit_2 = current_price * 1.08
            take_profit_3 = current_price * 1.12

        # 根据信号强度计算建议仓位
        if signal_strength >= 4:
            base_position = 25
        elif signal_strength >= 3:
            base_position = 20
        elif signal_strength >= 2:
            base_position = 15
        else:
            base_position = 10
        
        if stop_loss_pct > 5:
            base_position = base_position * 0.8
        elif stop_loss_pct < 3:
            base_position = base_position * 1.2
        
        suggested_position_pct = min(30, max(5, round(base_position, 1)))
        
        risk_mgmt = RiskManagement(
            stop_loss=round(stop_loss, 4),
            stop_loss_pct=round(stop_loss_pct, 2),
            take_profit_1=round(take_profit_1, 4),
            take_profit_2=round(take_profit_2, 4),
            take_profit_3=round(take_profit_3, 4),
            suggested_position_pct=suggested_position_pct,
            risk_reward_ratio="1:2 / 1:3 / 1:5"
        )
        
        position_strategy = self._generate_position_strategy(
            signal_type, signal_strength, suggested_position_pct, 
            stop_loss, take_profit_1, current_price
        )
        
        return risk_mgmt, position_strategy

    
    def _generate_position_strategy(
        self, 
        signal_type: SignalType, 
        strength: int,
        position_pct: float,
        stop_loss: float,
        take_profit: float,
        current_price: float
    ) -> PositionStrategy:
        """生成仓位策略建议"""
        position_cheng = round(position_pct / 10, 1)
        first_entry_cheng = round(position_cheng / 3, 1)
        add_cheng = round(position_cheng * 2 / 3, 1)
        
        if signal_type == SignalType.BUY:
            if strength >= 4:
                empty = f"多指标共振看多，可考虑分批建仓，首次{first_entry_cheng}成"
                first = f"建议首次建仓{first_entry_cheng}成，设好止损后观察"
                add = f"站稳支撑位且放量突破可加仓至{add_cheng}成"
                reduce = f"跌破止损位{stop_loss:.3f}减仓至{first_entry_cheng/2:.1f}成"
            elif strength >= 2:
                empty = f"偏多信号，可小仓位试探，建议{first_entry_cheng}成以内"
                first = f"建议轻仓试探{first_entry_cheng}成，严格止损"
                add = f"确认突破阻力位后可加仓至{position_cheng}成"
                reduce = f"跌破止损位{stop_loss:.3f}建议清仓"
            else:
                empty = "弱多信号，建议观望等待更多确认"
                first = f"如需建仓建议不超过{first_entry_cheng}成"
                add = "不建议加仓，等待信号增强"
                reduce = f"跌破{stop_loss:.3f}立即止损"
            full_exit = f"跌破止损位{stop_loss:.3f}或出现明确卖出信号时清仓"
        elif signal_type == SignalType.SELL:
            if strength >= 4:
                empty = "多指标共振看空，保持空仓观望"
                first = "不建议此时建仓，等待企稳信号"
                add = "不建议加仓，空头趋势明显"
                reduce = f"持仓者建议减仓至{first_entry_cheng}成以内"
            elif strength >= 2:
                empty = "偏空信号，保持谨慎观望"
                first = "不建议建仓，等待止跌信号"
                add = "不建议加仓"
                reduce = f"持仓者建议减仓或设好止损"
            else:
                empty = "弱空信号，可观望但需警惕"
                first = "暂不建议建仓"
                add = "不建议加仓"
                reduce = "持仓者注意风险控制"
            full_exit = f"跌破关键支撑或止损位{stop_loss:.3f}时清仓"
        else:
            empty = "多空力量均衡，建议保持空仓观望"
            first = "等待明确信号后再考虑建仓"
            add = "不建议加仓，等待方向明确"
            reduce = "持仓者可考虑减仓观望"
            full_exit = "出现明确方向信号后再做决策"
        
        return PositionStrategy(
            empty_position=empty,
            first_entry=first,
            add_position=add,
            reduce_position=reduce,
            full_exit=full_exit
        )
    
    def _default_risk_management(self, price: float) -> Tuple[RiskManagement, PositionStrategy]:
        """默认风险管理参数"""
        risk_mgmt = RiskManagement(
            stop_loss=price * 0.95,
            stop_loss_pct=5.0,
            take_profit_1=price * 1.10,
            take_profit_2=price * 1.15,
            take_profit_3=price * 1.25,
            suggested_position_pct=10.0,
            risk_reward_ratio="1:2 / 1:3 / 1:5"
        )
        position_strategy = PositionStrategy(
            empty_position="数据不足，建议观望",
            first_entry="建议等待更多数据",
            add_position="不建议加仓",
            reduce_position="持仓者注意风险",
            full_exit=f"跌破{price * 0.95:.3f}时止损"
        )
        return risk_mgmt, position_strategy

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
            return "观望信号 (多空力量均衡)"


def generate_trading_analysis(indicators: Dict, support_resistance: Dict, 
                               quant_analysis: Dict = None, trend_analysis: Dict = None) -> Dict:
    """
    生成完整的交易分析结果
    
    综合以下数据源生成交易信号：
    1. 技术指标分析（12+指标）
    2. 量化评分系统（0-100分）
    3. 趋势分析（多空信号统计）
    4. 市场状态判断
    5. 支撑阻力位分析
    
    Args:
        indicators: 技术指标数据
        support_resistance: 支撑阻力位数据
        quant_analysis: 量化分析数据（可选）
        trend_analysis: 趋势分析数据（可选）
    
    Returns:
        包含信号、风险管理、操作建议的完整分析结果
    """
    generator = TradingSignalGenerator()
    
    # 生成交易信号（整合量化分析和趋势分析）
    signal = generator.generate_signal(indicators, quant_analysis, trend_analysis)
    
    # 获取价格和ATR
    current_price = indicators.get("latest_price", 0)
    atr_data = indicators.get("atr", {})
    atr = atr_data.get("value", current_price * 0.02)
    
    # 获取支撑阻力位
    support_levels = [l.get("price", 0) for l in support_resistance.get("support_levels", [])]
    resistance_levels = [l.get("price", 0) for l in support_resistance.get("resistance_levels", [])]
    
    # 计算风险管理和仓位策略
    risk_mgmt, position_strategy = generator.calculate_risk_management(
        current_price=current_price,
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        atr=atr,
        signal_type=signal.signal_type,
        signal_strength=signal.strength
    )

    # 生成操作建议
    quant_score = quant_analysis.get("quant_score", 50) if quant_analysis else 50
    if signal.signal_type == SignalType.BUY:
        if signal.strength >= 4:
            action_suggestion = f"多指标共振看多（{len(signal.triggered_conditions)}项确认，量化评分{quant_score:.0f}），技术面偏强。可考虑分批建仓，首次建议{round(risk_mgmt.suggested_position_pct/30, 1)}成，站稳后逐步加仓。严格设置止损，控制风险。"
        elif signal.strength >= 2:
            action_suggestion = f"偏多信号（{len(signal.triggered_conditions)}项确认），可小仓位试探。建议轻仓参与，严格止损，等待更多确认信号后再考虑加仓。"
        else:
            action_suggestion = "弱多信号，建议观望等待更多确认。如需参与建议极轻仓位，做好止损准备。"
    elif signal.signal_type == SignalType.SELL:
        if signal.strength >= 4:
            action_suggestion = f"多指标共振看空（{len(signal.triggered_conditions)}项确认，量化评分{quant_score:.0f}），技术面偏弱。持仓者建议减仓或清仓，空仓者保持观望等待企稳。"
        elif signal.strength >= 2:
            action_suggestion = f"偏空信号（{len(signal.triggered_conditions)}项确认），注意风险控制。持仓者建议减仓，设好止损。空仓者继续观望。"
        else:
            action_suggestion = "弱空信号，密切关注走势变化。持仓者注意风险，可适当减仓。"
    else:
        action_suggestion = "多空力量均衡，方向不明确。建议保持观望，等待明确的方向信号出现后再做决策。"
    
    return {
        "status": "success",
        "trading_signal": {
            "signal_type": signal.signal_type.value,
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
            "risk_reward_ratio": risk_mgmt.risk_reward_ratio,
            "position_strategy": {
                "empty_position": position_strategy.empty_position,
                "first_entry": position_strategy.first_entry,
                "add_position": position_strategy.add_position,
                "reduce_position": position_strategy.reduce_position,
                "full_exit": position_strategy.full_exit,
            }
        },
        "action_suggestion": action_suggestion,
        "current_price": current_price,
        "disclaimer": "以上内容仅为技术分析工具输出，综合量化评分、技术指标、趋势分析等数据生成，不构成任何投资建议。市场有风险，投资需谨慎，请独立判断并自行承担风险。"
    }
