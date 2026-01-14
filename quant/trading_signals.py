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


class TrendState(Enum):
    """趋势状态枚举 - 用于趋势识别"""
    STRONG_UP = "strong_up"       # 强势上涨
    UP = "up"                     # 上涨趋势
    WEAK_UP = "weak_up"           # 弱势上涨
    SIDEWAYS = "sideways"         # 横盘震荡
    WEAK_DOWN = "weak_down"       # 弱势下跌
    DOWN = "down"                 # 下跌趋势
    STRONG_DOWN = "strong_down"   # 强势下跌


class TradingSignalGenerator:
    """
    交易信号生成器 v2.0 - 优化版
    
    核心优化原则：
    1. 趋势跟随优先：在明确趋势中不轻易发出反向信号
    2. 多重确认机制：单一指标不够，需要多指标共振
    3. 区分回调与反转：超买超卖是警告，不是直接卖出信号
    4. 动态阈值：根据趋势强度调整信号敏感度
    5. 趋势保护：上涨趋势中提高卖出门槛，下跌趋势中提高买入门槛
    
    数据来源：
    1. 技术指标（均线/MACD/RSI/KDJ/布林带/成交量/ADX/SAR/云图/MFI/DMI/BIAS）
    2. 量化评分系统（0-100分）
    3. 趋势分析（多空信号统计）
    4. 市场状态（趋势市/震荡市）
    5. 支撑阻力位
    
    仅供技术分析参考，不构成投资建议
    """
    
    def __init__(self):
        # 信号触发的最低要求
        self.min_score_for_signal = 4      # 最低分数要求
        self.min_conditions_for_signal = 2  # 最少确认条件数
        
        # 趋势保护系数 - 在趋势中发出反向信号需要更高的分数
        self.trend_protection_factor = 1.5
        
        # 买入信号触发条件权重 (优化后)
        self.buy_conditions = {
            # 趋势类指标 (权重较高)
            "price_above_ma20": 1,
            "price_above_ma60": 1.5,
            "ma_bullish_alignment": 3,      # 均线多头排列
            "macd_golden_cross": 2.5,
            "macd_bullish": 1,
            "adx_strong_bullish": 2.5,
            "sar_bullish": 1.5,
            "ichimoku_above_cloud": 2.5,
            "dmi_bullish": 1.5,
            # 超卖反弹类 (在上涨趋势中权重更高)
            "rsi_oversold_recovery": 2,
            "kdj_golden_cross": 1.5,
            "kdj_oversold": 1.5,
            "bb_near_lower": 1.5,
            "bias_oversold": 1.5,
            # 量能确认
            "volume_breakout": 2,
            "mfi_inflow": 1.5,
            # 量化分析权重
            "quant_strong_buy": 3,
            "quant_buy": 2,
            "high_quant_score": 2,
            "bullish_trend": 2.5,
        }
        
        # 卖出信号触发条件权重 (优化后 - 整体降低权重，避免卖飞)
        self.sell_conditions = {
            # 趋势类指标 (只有趋势反转才给高权重)
            "price_below_ma20": 0.5,        # 降低权重，短期跌破不急于卖出
            "price_below_ma60": 1,          # 中期均线更重要
            "ma_bearish_alignment": 3,      # 均线空头排列才是强卖出信号
            "macd_death_cross": 2,          # 降低权重
            "macd_bearish": 0.5,            # 大幅降低，MACD为负不代表要卖
            "adx_strong_bearish": 2.5,
            "sar_bearish": 1,               # 降低权重
            "ichimoku_below_cloud": 2,
            "dmi_bearish": 1,
            # 超买类 (作为警告，不直接触发卖出)
            "rsi_overbought": 0.5,          # 大幅降低！超买不等于要卖
            "kdj_death_cross": 1,           # 降低权重
            "kdj_overbought": 0.5,          # 大幅降低！超买不等于要卖
            "bb_near_upper": 0.5,           # 大幅降低！触及上轨可能是强势
            "bias_overbought": 0.5,         # 大幅降低
            # 量能确认
            "volume_decline": 1,
            "mfi_outflow": 1.5,
            # 量化分析权重
            "quant_strong_sell": 3,
            "quant_sell": 2,
            "low_quant_score": 2,
            "bearish_trend": 2.5,
        }


    def _assess_trend_state(self, indicators: Dict, quant_analysis: Dict = None) -> Tuple[TrendState, int]:
        """
        评估当前趋势状态
        
        返回:
            (TrendState, trend_score): 趋势状态和趋势分数(-100到+100)
            正数表示上涨趋势，负数表示下跌趋势，绝对值越大趋势越强
        """
        trend_score = 0
        
        # 1. 均线系统评估 (权重最高)
        ma_trend = indicators.get("ma_trend", "")
        ma_values = indicators.get("moving_averages", {})
        latest_price = indicators.get("latest_price", 0)
        
        if ma_trend == "bullish_alignment":
            trend_score += 25
        elif ma_trend == "bearish_alignment":
            trend_score -= 25
        
        # 价格与均线的关系
        ma20 = ma_values.get("MA20", 0)
        ma60 = ma_values.get("MA60", 0)
        ma120 = ma_values.get("MA120", 0)
        
        if latest_price > 0:
            if ma20 > 0:
                trend_score += 8 if latest_price > ma20 else -8
            if ma60 > 0:
                trend_score += 10 if latest_price > ma60 else -10
            if ma120 > 0:
                trend_score += 12 if latest_price > ma120 else -12
        
        # 2. MACD趋势评估
        macd = indicators.get("macd", {})
        if macd.get("trend") == "bullish":
            trend_score += 10
        elif macd.get("trend") == "bearish":
            trend_score -= 10
        
        # MACD柱状图方向（动量）
        histogram = macd.get("histogram", 0)
        if histogram > 0:
            trend_score += 5
        elif histogram < 0:
            trend_score -= 5
        
        # 3. ADX趋势强度
        adx = indicators.get("adx", {})
        adx_value = adx.get("adx", 0)
        if adx_value > 25:  # 强趋势
            if adx.get("trend_direction") == "bullish":
                trend_score += 15
            else:
                trend_score -= 15
        elif adx_value > 15:  # 中等趋势
            if adx.get("trend_direction") == "bullish":
                trend_score += 8
            else:
                trend_score -= 8
        
        # 4. 云图评估
        ichimoku = indicators.get("ichimoku", {})
        if ichimoku.get("status") == "strong_bullish":
            trend_score += 15
        elif ichimoku.get("status") == "strong_bearish":
            trend_score -= 15
        elif ichimoku.get("cloud_position") == "above_cloud":
            trend_score += 8
        elif ichimoku.get("cloud_position") == "below_cloud":
            trend_score -= 8
        
        # 5. 量化评分参考
        if quant_analysis:
            quant_score = quant_analysis.get("quant_score", 50)
            if quant_score >= 70:
                trend_score += 10
            elif quant_score >= 60:
                trend_score += 5
            elif quant_score <= 30:
                trend_score -= 10
            elif quant_score <= 40:
                trend_score -= 5
        
        # 根据分数确定趋势状态
        if trend_score >= 50:
            state = TrendState.STRONG_UP
        elif trend_score >= 25:
            state = TrendState.UP
        elif trend_score >= 10:
            state = TrendState.WEAK_UP
        elif trend_score <= -50:
            state = TrendState.STRONG_DOWN
        elif trend_score <= -25:
            state = TrendState.DOWN
        elif trend_score <= -10:
            state = TrendState.WEAK_DOWN
        else:
            state = TrendState.SIDEWAYS
        
        return state, trend_score

    def _check_reversal_signals(self, indicators: Dict, current_trend: TrendState) -> Tuple[int, List[str]]:
        """
        检查趋势反转信号 - 需要多重确认
        
        返回:
            (reversal_score, reversal_conditions): 反转分数和反转条件列表
            正数表示向上反转信号，负数表示向下反转信号
        """
        reversal_score = 0
        reversal_conditions = []
        
        # 只有在下跌趋势中才检查向上反转
        if current_trend in [TrendState.DOWN, TrendState.STRONG_DOWN, TrendState.WEAK_DOWN]:
            # MACD金叉
            macd = indicators.get("macd", {})
            if macd.get("crossover") == "golden_cross":
                reversal_score += 3
                reversal_conditions.append("MACD金叉(反转信号)")
            
            # KDJ金叉 + 超卖
            kdj = indicators.get("kdj", {})
            if kdj.get("crossover") == "golden_cross" and kdj.get("status") == "oversold":
                reversal_score += 3
                reversal_conditions.append("KDJ超卖金叉(反转信号)")
            
            # RSI从超卖区回升
            rsi = indicators.get("rsi", {})
            rsi_value = rsi.get("value", 50)
            if rsi_value < 35 and rsi_value > 30:  # 刚从超卖区回升
                reversal_score += 2
                reversal_conditions.append(f"RSI超卖回升({rsi_value:.1f})")
            
            # 放量止跌
            vol = indicators.get("volume_analysis", {})
            if vol.get("status") == "high_volume" and vol.get("volume_ratio", 1) > 1.5:
                reversal_score += 2
                reversal_conditions.append("放量止跌")
        
        # 只有在上涨趋势中才检查向下反转
        elif current_trend in [TrendState.UP, TrendState.STRONG_UP, TrendState.WEAK_UP]:
            # MACD死叉
            macd = indicators.get("macd", {})
            if macd.get("crossover") == "death_cross":
                reversal_score -= 2  # 降低权重，上涨中的死叉可能只是调整
                reversal_conditions.append("MACD死叉(警告)")
            
            # KDJ死叉 + 超买 (需要同时满足才算反转信号)
            kdj = indicators.get("kdj", {})
            if kdj.get("crossover") == "death_cross" and kdj.get("status") == "overbought":
                reversal_score -= 2
                reversal_conditions.append("KDJ超买死叉(警告)")
            
            # 跌破关键均线
            ma_values = indicators.get("moving_averages", {})
            latest_price = indicators.get("latest_price", 0)
            ma60 = ma_values.get("MA60", 0)
            if latest_price > 0 and ma60 > 0 and latest_price < ma60:
                reversal_score -= 3
                reversal_conditions.append("跌破MA60(反转警告)")
        
        return reversal_score, reversal_conditions

    def _check_momentum_warnings(self, indicators: Dict, current_trend: TrendState) -> List[str]:
        """
        检查动量警告信号 - 超买超卖作为警告，不直接触发交易
        
        在上涨趋势中：
        - 超卖 = 买入机会
        - 超买 = 仅作为警告，不触发卖出
        
        在下跌趋势中：
        - 超买 = 卖出/做空机会
        - 超卖 = 仅作为警告，不触发买入
        """
        warnings = []
        
        rsi = indicators.get("rsi", {})
        rsi_value = rsi.get("value", 50)
        
        kdj = indicators.get("kdj", {})
        j_value = kdj.get("j", 50)
        
        bb = indicators.get("bollinger_bands", {})
        
        if current_trend in [TrendState.UP, TrendState.STRONG_UP, TrendState.WEAK_UP]:
            # 上涨趋势中的超买只是警告
            if rsi_value > 70:
                warnings.append(f"⚠️ RSI超买({rsi_value:.1f})，注意短期回调风险")
            if j_value > 80:
                warnings.append(f"⚠️ KDJ超买(J={j_value:.1f})，可能有短期调整")
            if bb.get("status") == "near_upper":
                warnings.append("⚠️ 触及布林上轨，短期可能回调")
        
        elif current_trend in [TrendState.DOWN, TrendState.STRONG_DOWN, TrendState.WEAK_DOWN]:
            # 下跌趋势中的超卖只是警告
            if rsi_value < 30:
                warnings.append(f"⚠️ RSI超卖({rsi_value:.1f})，但下跌趋势未改变")
            if j_value < 20:
                warnings.append(f"⚠️ KDJ超卖(J={j_value:.1f})，但趋势仍偏空")
            if bb.get("status") == "near_lower":
                warnings.append("⚠️ 触及布林下轨，但需等待企稳信号")
        
        return warnings

    def _check_volume_confirmation(self, indicators: Dict, signal_direction: str) -> Tuple[bool, str]:
        """
        检查成交量确认
        
        返回:
            (is_confirmed, message): 是否确认和确认信息
        """
        vol = indicators.get("volume_analysis", {})
        vol_ratio = vol.get("volume_ratio", 1)
        vol_status = vol.get("status", "normal")
        
        if signal_direction == "buy":
            if vol_status == "high_volume" and vol_ratio > 1.5:
                return True, f"放量确认({vol_ratio:.1f}倍)"
            elif vol_status == "low_volume":
                return False, "成交量萎缩，信号待确认"
            else:
                return True, "成交量正常"
        
        elif signal_direction == "sell":
            if vol_status == "high_volume" and vol_ratio > 2:
                return True, f"放量下跌({vol_ratio:.1f}倍)"
            else:
                return False, "缩量下跌，可能是洗盘"
        
        return True, ""

    def generate_signal(self, indicators: Dict, quant_analysis: Dict = None, trend_analysis: Dict = None) -> TradingSignal:
        """
        根据技术指标+量化分析+趋势分析生成交易信号 (优化版 v2.0)
        
        核心逻辑：
        1. 首先评估当前趋势状态
        2. 在趋势方向上寻找入场机会
        3. 反向信号需要多重确认
        4. 超买超卖作为警告，不直接触发交易
        
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
        
        # ========== 第一步：评估当前趋势状态 ==========
        trend_state, trend_score_val = self._assess_trend_state(indicators, quant_analysis)
        
        # 趋势保护：在明确趋势中，提高反向信号的门槛
        is_uptrend = trend_state in [TrendState.UP, TrendState.STRONG_UP, TrendState.WEAK_UP]
        is_downtrend = trend_state in [TrendState.DOWN, TrendState.STRONG_DOWN, TrendState.WEAK_DOWN]
        
        # ========== 第二步：量化分析数据 ==========
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

        
        # ========== 第四步：技术指标分析 (趋势感知) ==========
        # 1. 均线系统检查
        ma_trend = indicators.get("ma_trend", "")
        ma_values = indicators.get("moving_averages", {})
        latest_price = indicators.get("latest_price", 0)
        
        if ma_trend == "bullish_alignment":
            buy_triggered.append("均线多头排列")
            buy_score += self.buy_conditions["ma_bullish_alignment"]
        elif ma_trend == "bearish_alignment":
            sell_triggered.append("均线空头排列")
            sell_score += self.sell_conditions["ma_bearish_alignment"]
        
        ma20 = ma_values.get("MA20", 0)
        ma60 = ma_values.get("MA60", 0)
        
        if latest_price > 0 and ma20 > 0:
            if latest_price > ma20:
                buy_triggered.append("价格站上MA20")
                buy_score += self.buy_conditions["price_above_ma20"]
            else:
                # 在上涨趋势中，短期跌破MA20只是警告
                if is_uptrend:
                    sell_pending.append("⚠️ 短期跌破MA20")
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
            # 在上涨趋势中，MACD死叉权重降低
            if is_uptrend:
                sell_pending.append("⚠️ MACD死叉(趋势中可能是调整)")
                sell_score += self.sell_conditions["macd_death_cross"] * 0.5
            else:
                sell_triggered.append("MACD死叉")
                sell_score += self.sell_conditions["macd_death_cross"]
        
        if macd.get("trend") == "bullish":
            buy_triggered.append("MACD柱状图为正")
            buy_score += self.buy_conditions["macd_bullish"]
        elif macd.get("trend") == "bearish":
            # MACD为负在上涨趋势中不作为卖出信号
            if not is_uptrend:
                sell_triggered.append("MACD柱状图为负")
                sell_score += self.sell_conditions["macd_bearish"]

        # 3. RSI检查 (趋势感知 - 核心优化点)
        rsi = indicators.get("rsi", {})
        rsi_value = rsi.get("value", 50)
        
        if rsi.get("status") == "oversold":
            # 超卖在上涨趋势中是买入机会
            if is_uptrend:
                buy_triggered.append(f"RSI超卖回调买点({rsi_value:.1f})")
                buy_score += self.buy_conditions["rsi_oversold_recovery"] * 1.5
            else:
                buy_triggered.append(f"RSI超卖({rsi_value:.1f})")
                buy_score += self.buy_conditions["rsi_oversold_recovery"]
        elif rsi.get("status") == "overbought":
            # 超买在上涨趋势中只是警告，不触发卖出！
            if is_uptrend:
                sell_pending.append(f"⚠️ RSI超买({rsi_value:.1f})，强势股可持续超买")
            else:
                sell_triggered.append(f"RSI超买({rsi_value:.1f})")
                sell_score += self.sell_conditions["rsi_overbought"]
        else:
            if rsi_value < 40:
                buy_pending.append(f"RSI偏低({rsi_value:.1f})")
            elif rsi_value > 60:
                sell_pending.append(f"RSI偏高({rsi_value:.1f})")
        
        # 4. KDJ检查 (趋势感知)
        kdj = indicators.get("kdj", {})
        if kdj.get("crossover") == "golden_cross":
            buy_triggered.append("KDJ金叉")
            buy_score += self.buy_conditions["kdj_golden_cross"]
        elif kdj.get("crossover") == "death_cross":
            # 在上涨趋势中，KDJ死叉权重降低
            if is_uptrend:
                sell_pending.append("⚠️ KDJ死叉(可能是短期调整)")
                sell_score += self.sell_conditions["kdj_death_cross"] * 0.5
            else:
                sell_triggered.append("KDJ死叉")
                sell_score += self.sell_conditions["kdj_death_cross"]
        
        if kdj.get("status") == "oversold":
            if is_uptrend:
                buy_triggered.append("KDJ超卖(趋势中买点)")
                buy_score += self.buy_conditions["kdj_oversold"] * 1.5
            else:
                buy_triggered.append("KDJ超卖区域")
                buy_score += self.buy_conditions["kdj_oversold"]
        elif kdj.get("status") == "overbought":
            # 超买在上涨趋势中只是警告
            if is_uptrend:
                sell_pending.append("⚠️ KDJ超买(强势可持续)")
            else:
                sell_triggered.append("KDJ超买区域")
                sell_score += self.sell_conditions["kdj_overbought"]

        
        # 5. 布林带检查 (趋势感知)
        bb = indicators.get("bollinger_bands", {})
        if bb.get("status") == "near_lower":
            if is_uptrend:
                buy_triggered.append("触及布林下轨(趋势中买点)")
                buy_score += self.buy_conditions["bb_near_lower"] * 1.5
            else:
                buy_triggered.append("触及布林带下轨")
                buy_score += self.buy_conditions["bb_near_lower"]
        elif bb.get("status") == "near_upper":
            # 触及上轨在上涨趋势中可能是强势表现
            if is_uptrend:
                sell_pending.append("⚠️ 触及布林上轨(强势股特征)")
            else:
                sell_triggered.append("触及布林带上轨")
                sell_score += self.sell_conditions["bb_near_upper"]
        
        # 6. 成交量检查
        vol = indicators.get("volume_analysis", {})
        vol_ratio = vol.get("volume_ratio", 1)
        if vol.get("status") == "high_volume" and vol_ratio > 1.5:
            # 放量需要结合趋势判断
            if is_uptrend or buy_score > sell_score:
                buy_triggered.append(f"放量确认({vol_ratio:.1f}倍)")
                buy_score += self.buy_conditions["volume_breakout"]
            elif is_downtrend:
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
            # 在上涨趋势中，SAR卖出信号权重降低
            if is_uptrend:
                sell_pending.append("⚠️ SAR反转信号(趋势中需确认)")
                sell_score += self.sell_conditions["sar_bearish"] * 0.5
            else:
                sell_triggered.append("SAR趋势反转向下")
                sell_score += self.sell_conditions["sar_bearish"]
        elif sar.get("status") == "bullish":
            buy_triggered.append("SAR上升趋势")
            buy_score += 0.5
        elif sar.get("status") == "bearish":
            if not is_uptrend:
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
            # MFI超买在上涨趋势中只是警告
            if is_uptrend:
                sell_pending.append("⚠️ MFI超买")
            else:
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
            # BIAS超买在上涨趋势中只是警告
            if is_uptrend:
                sell_pending.append(f"⚠️ BIAS偏高({bias.get('bias_6', 0):.1f}%)")
            else:
                sell_triggered.append(f"BIAS超买({bias.get('bias_6', 0):.1f}%)")
                sell_score += self.sell_conditions["bias_overbought"]
        
        # ========== 第五步：趋势保护机制 ==========
        # 在明确趋势中，提高反向信号的门槛
        if is_uptrend and sell_score > 0:
            # 上涨趋势中，卖出信号需要更强的确认
            sell_score = sell_score / self.trend_protection_factor
            sell_pending.append(f"📈 当前处于上涨趋势(趋势分:{trend_score_val})")
        
        if is_downtrend and buy_score > 0:
            # 下跌趋势中，买入信号需要更强的确认
            buy_score = buy_score / self.trend_protection_factor
            buy_pending.append(f"📉 当前处于下跌趋势(趋势分:{trend_score_val})")
        
        # ========== 第六步：综合计算信号 ==========
        total_score = buy_score + sell_score
        
        # 信号判定需要满足最低要求
        if total_score == 0:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        elif buy_score > sell_score:
            # 买入信号需要满足最低分数和条件数
            if buy_score >= self.min_score_for_signal and len(buy_triggered) >= self.min_conditions_for_signal:
                signal_type = SignalType.BUY
                score_diff = buy_score - sell_score
                strength = min(5, max(1, int(score_diff / 3) + 1))
                confidence = buy_score / (buy_score + sell_score + 1)
            else:
                signal_type = SignalType.HOLD
                strength = 0
                confidence = 0.5
                buy_pending.append(f"买入信号不足(分数:{buy_score:.1f},条件:{len(buy_triggered)})")
        elif sell_score > buy_score:
            # 卖出信号需要满足最低分数和条件数
            if sell_score >= self.min_score_for_signal and len(sell_triggered) >= self.min_conditions_for_signal:
                signal_type = SignalType.SELL
                score_diff = sell_score - buy_score
                strength = min(5, max(1, int(score_diff / 3) + 1))
                confidence = sell_score / (buy_score + sell_score + 1)
            else:
                signal_type = SignalType.HOLD
                strength = 0
                confidence = 0.5
                sell_pending.append(f"卖出信号不足(分数:{sell_score:.1f},条件:{len(sell_triggered)})")
        else:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0.5
        
        # 合并触发条件
        if signal_type == SignalType.BUY:
            triggered = buy_triggered
            pending = buy_pending + [f"⚠️ {c}" for c in sell_triggered[:3] if not c.startswith("⚠️")]
        elif signal_type == SignalType.SELL:
            triggered = sell_triggered
            pending = sell_pending + [f"⚠️ {c}" for c in buy_triggered[:3] if not c.startswith("⚠️")]
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
                               quant_analysis: Dict = None, trend_analysis: Dict = None,
                               holding_period: str = "swing") -> Dict:
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
        holding_period: 持有周期 (short/swing/long)
    
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

    # 生成操作建议（根据信号类型生成对应的策略）
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
        "holding_period": holding_period,
        "disclaimer": "以上内容仅为技术分析工具输出，综合量化评分、技术指标、趋势分析等数据生成，不构成任何投资建议。市场有风险，投资需谨慎，请独立判断并自行承担风险。"
    }


def generate_multi_period_signals(indicators: Dict, support_resistance: Dict,
                                   quant_analysis: Dict = None, trend_analysis: Dict = None) -> Dict:
    """
    为所有三个周期（短线/波段/中长线）生成交易信号
    
    不同周期使用不同的参数权重：
    - 短线(short): 更关注短期指标（RSI/KDJ/MACD交叉）
    - 波段(swing): 均衡考虑各类指标
    - 中长线(long): 更关注趋势指标（均线排列/ADX/云图）
    
    Args:
        indicators: 技术指标数据
        support_resistance: 支撑阻力位数据
        quant_analysis: 量化分析数据（可选）
        trend_analysis: 趋势分析数据（可选）
    
    Returns:
        包含三个周期信号的字典
    """
    generator = TradingSignalGenerator()
    
    # 获取基础数据
    current_price = indicators.get("latest_price", 0)
    atr_data = indicators.get("atr", {})
    atr = atr_data.get("value", current_price * 0.02)
    
    support_levels = [l.get("price", 0) for l in support_resistance.get("support_levels", [])]
    resistance_levels = [l.get("price", 0) for l in support_resistance.get("resistance_levels", [])]
    
    # 生成基础信号（波段周期使用标准权重）
    base_signal = generator.generate_signal(indicators, quant_analysis, trend_analysis)
    
    # 为不同周期调整信号
    signals = {}
    
    # ========== 短线信号 ==========
    # 短线更关注：RSI/KDJ超买超卖、MACD交叉、布林带位置、成交量
    short_buy_score = 0
    short_sell_score = 0
    
    # RSI (短线权重更高)
    rsi = indicators.get("rsi", {})
    rsi_value = rsi.get("value", 50)
    if rsi.get("status") == "oversold":
        short_buy_score += 3
    elif rsi.get("status") == "overbought":
        short_sell_score += 3
    elif rsi_value < 40:
        short_buy_score += 1
    elif rsi_value > 60:
        short_sell_score += 1
    
    # KDJ (短线权重更高)
    kdj = indicators.get("kdj", {})
    if kdj.get("crossover") == "golden_cross":
        short_buy_score += 3
    elif kdj.get("crossover") == "death_cross":
        short_sell_score += 3
    if kdj.get("status") == "oversold":
        short_buy_score += 2
    elif kdj.get("status") == "overbought":
        short_sell_score += 2
    
    # MACD交叉 (短线关键信号)
    macd = indicators.get("macd", {})
    if macd.get("crossover") == "golden_cross":
        short_buy_score += 3
    elif macd.get("crossover") == "death_cross":
        short_sell_score += 3
    
    # 布林带
    bb = indicators.get("bollinger_bands", {})
    if bb.get("status") == "near_lower":
        short_buy_score += 2
    elif bb.get("status") == "near_upper":
        short_sell_score += 2
    
    # 成交量
    vol = indicators.get("volume_analysis", {})
    if vol.get("status") == "high_volume":
        if short_buy_score > short_sell_score:
            short_buy_score += 2
        else:
            short_sell_score += 2
    
    # 短线信号判定
    if short_buy_score > short_sell_score + 2:
        signals['short'] = 'buy'
    elif short_sell_score > short_buy_score + 2:
        signals['short'] = 'sell'
    else:
        signals['short'] = 'hold'
    
    # ========== 波段信号 ==========
    # 波段使用基础信号（均衡考虑所有指标）
    signals['swing'] = base_signal.signal_type.value
    
    # ========== 中长线信号 ==========
    # 中长线更关注：均线排列、ADX趋势强度、云图、资金流向
    long_buy_score = 0
    long_sell_score = 0
    
    # 均线排列 (中长线关键)
    ma_trend = indicators.get("ma_trend", "")
    if ma_trend == "bullish_alignment":
        long_buy_score += 4
    elif ma_trend == "bearish_alignment":
        long_sell_score += 4
    
    # 均线位置
    ma_values = indicators.get("moving_averages", {})
    ma60 = ma_values.get("MA60", 0)
    ma120 = ma_values.get("MA120", 0)
    if current_price > 0:
        if ma60 > 0 and current_price > ma60:
            long_buy_score += 2
        elif ma60 > 0 and current_price < ma60:
            long_sell_score += 2
        if ma120 > 0 and current_price > ma120:
            long_buy_score += 2
        elif ma120 > 0 and current_price < ma120:
            long_sell_score += 2
    
    # ADX趋势强度 (中长线关键)
    adx = indicators.get("adx", {})
    if adx.get("trend_strength") == "strong":
        if adx.get("trend_direction") == "bullish":
            long_buy_score += 3
        else:
            long_sell_score += 3
    
    # 云图 (中长线关键)
    ichimoku = indicators.get("ichimoku", {})
    if ichimoku.get("status") == "strong_bullish":
        long_buy_score += 3
    elif ichimoku.get("status") == "strong_bearish":
        long_sell_score += 3
    elif ichimoku.get("cloud_position") == "above_cloud":
        long_buy_score += 2
    elif ichimoku.get("cloud_position") == "below_cloud":
        long_sell_score += 2
    
    # 资金流向
    mfi = indicators.get("money_flow", {})
    if mfi.get("mfi_status") == "inflow":
        long_buy_score += 2
    elif mfi.get("mfi_status") == "outflow":
        long_sell_score += 2
    
    # 量化评分 (中长线参考)
    if quant_analysis:
        quant_score = quant_analysis.get("quant_score", 50)
        if quant_score >= 65:
            long_buy_score += 2
        elif quant_score <= 35:
            long_sell_score += 2
    
    # 中长线信号判定
    if long_buy_score > long_sell_score + 3:
        signals['long'] = 'buy'
    elif long_sell_score > long_buy_score + 3:
        signals['long'] = 'sell'
    else:
        signals['long'] = 'hold'
    
    return signals


def generate_multi_period_analysis(indicators: Dict, support_resistance: Dict,
                                    quant_analysis: Dict = None, trend_analysis: Dict = None) -> Dict:
    """
    为所有三个周期（短线/波段/中长线）生成完整的交易分析
    包含信号、风险管理、操作策略
    
    Args:
        indicators: 技术指标数据
        support_resistance: 支撑阻力位数据
        quant_analysis: 量化分析数据（可选）
        trend_analysis: 趋势分析数据（可选）
    
    Returns:
        包含三个周期完整交易分析的字典
    """
    generator = TradingSignalGenerator()
    
    # 获取基础数据
    current_price = indicators.get("latest_price", 0)
    atr_data = indicators.get("atr", {})
    atr = atr_data.get("value", current_price * 0.02)
    quant_score = quant_analysis.get("quant_score", 50) if quant_analysis else 50
    
    support_levels = [l.get("price", 0) for l in support_resistance.get("support_levels", [])]
    resistance_levels = [l.get("price", 0) for l in support_resistance.get("resistance_levels", [])]
    
    # 生成基础信号（波段周期使用标准权重）
    base_signal = generator.generate_signal(indicators, quant_analysis, trend_analysis)
    
    # 存储三个周期的完整分析结果
    result = {}
    
    # ========== 短线分析 ==========
    short_buy_score = 0
    short_sell_score = 0
    short_buy_conds = []
    short_sell_conds = []
    
    rsi = indicators.get("rsi", {})
    rsi_value = rsi.get("value", 50)
    if rsi.get("status") == "oversold":
        short_buy_score += 3
        short_buy_conds.append(f"RSI超卖({rsi_value:.1f})")
    elif rsi.get("status") == "overbought":
        short_sell_score += 3
        short_sell_conds.append(f"RSI超买({rsi_value:.1f})")
    
    kdj = indicators.get("kdj", {})
    if kdj.get("crossover") == "golden_cross":
        short_buy_score += 3
        short_buy_conds.append("KDJ金叉")
    elif kdj.get("crossover") == "death_cross":
        short_sell_score += 3
        short_sell_conds.append("KDJ死叉")
    if kdj.get("status") == "oversold":
        short_buy_score += 2
        short_buy_conds.append("KDJ超卖区")
    elif kdj.get("status") == "overbought":
        short_sell_score += 2
        short_sell_conds.append("KDJ超买区")
    
    macd = indicators.get("macd", {})
    if macd.get("crossover") == "golden_cross":
        short_buy_score += 3
        short_buy_conds.append("MACD金叉")
    elif macd.get("crossover") == "death_cross":
        short_sell_score += 3
        short_sell_conds.append("MACD死叉")
    
    bb = indicators.get("bollinger_bands", {})
    if bb.get("status") == "near_lower":
        short_buy_score += 2
        short_buy_conds.append("触及布林下轨")
    elif bb.get("status") == "near_upper":
        short_sell_score += 2
        short_sell_conds.append("触及布林上轨")
    
    vol = indicators.get("volume_analysis", {})
    vol_ratio = vol.get("volume_ratio", 1)
    if vol.get("status") == "high_volume" and vol_ratio > 1.5:
        if short_buy_score > short_sell_score:
            short_buy_score += 2
            short_buy_conds.append(f"放量({vol_ratio:.1f}倍)")
        else:
            short_sell_score += 2
            short_sell_conds.append(f"放量下跌")
    
    if short_buy_score > short_sell_score + 2:
        short_type = SignalType.BUY
        short_strength = min(5, max(1, int((short_buy_score - short_sell_score) / 2) + 1))
        short_conds = short_buy_conds
        short_conf = round(short_buy_score / (short_buy_score + short_sell_score + 1) * 100, 1)
    elif short_sell_score > short_buy_score + 2:
        short_type = SignalType.SELL
        short_strength = min(5, max(1, int((short_sell_score - short_buy_score) / 2) + 1))
        short_conds = short_sell_conds
        short_conf = round(short_sell_score / (short_buy_score + short_sell_score + 1) * 100, 1)
    else:
        short_type = SignalType.HOLD
        short_strength = 0
        short_conds = []
        short_conf = 50
    
    short_stop_pct = 3.0
    short_stop = current_price * (1 - short_stop_pct / 100) if short_type == SignalType.BUY else current_price * (1 + short_stop_pct / 100)
    short_risk = abs(current_price - short_stop)
    
    result['short'] = _build_period_result(short_type, short_strength, short_conds, short_conf, 
                                           current_price, short_stop, short_stop_pct, short_risk,
                                           '短线(1-5天)', quant_score, generator)
    
    # ========== 波段分析 ==========
    swing_risk_mgmt, swing_pos_strategy = generator.calculate_risk_management(
        current_price, support_levels, resistance_levels, atr, base_signal.signal_type, base_signal.strength
    )
    
    result['swing'] = {
        'signal_type': base_signal.signal_type.value,
        'type_cn': "买入" if base_signal.signal_type == SignalType.BUY else ("卖出" if base_signal.signal_type == SignalType.SELL else "观望"),
        'strength': base_signal.strength,
        'strength_label': generator.get_signal_strength_label(base_signal.strength),
        'confidence': round(base_signal.confidence * 100, 1),
        'triggered_conditions': base_signal.triggered_conditions,
        'period_label': '波段(1-4周)',
        'risk_management': {
            'stop_loss': swing_risk_mgmt.stop_loss,
            'stop_loss_pct': swing_risk_mgmt.stop_loss_pct,
            'take_profit_targets': [
                {"level": 1, "price": swing_risk_mgmt.take_profit_1, "ratio": "1:2"},
                {"level": 2, "price": swing_risk_mgmt.take_profit_2, "ratio": "1:3"},
                {"level": 3, "price": swing_risk_mgmt.take_profit_3, "ratio": "1:5"},
            ],
            'suggested_position_pct': swing_risk_mgmt.suggested_position_pct,
        },
        'action_suggestion': _get_action_text(base_signal.signal_type, base_signal.strength, '波段', quant_score, len(base_signal.triggered_conditions)),
        'position_strategy': {
            'empty_position': swing_pos_strategy.empty_position,
            'first_entry': swing_pos_strategy.first_entry,
            'add_position': swing_pos_strategy.add_position,
            'reduce_position': swing_pos_strategy.reduce_position,
            'full_exit': swing_pos_strategy.full_exit,
        }
    }
    
    # ========== 中长线分析 ==========
    long_buy_score = 0
    long_sell_score = 0
    long_buy_conds = []
    long_sell_conds = []
    
    ma_trend = indicators.get("ma_trend", "")
    if ma_trend == "bullish_alignment":
        long_buy_score += 4
        long_buy_conds.append("均线多头排列")
    elif ma_trend == "bearish_alignment":
        long_sell_score += 4
        long_sell_conds.append("均线空头排列")
    
    ma_values = indicators.get("moving_averages", {})
    ma60 = ma_values.get("MA60", 0)
    ma120 = ma_values.get("MA120", 0)
    if current_price > 0:
        if ma60 > 0 and current_price > ma60:
            long_buy_score += 2
            long_buy_conds.append("站上MA60")
        elif ma60 > 0 and current_price < ma60:
            long_sell_score += 2
            long_sell_conds.append("跌破MA60")
        if ma120 > 0 and current_price > ma120:
            long_buy_score += 2
            long_buy_conds.append("站上MA120")
        elif ma120 > 0 and current_price < ma120:
            long_sell_score += 2
            long_sell_conds.append("跌破MA120")
    
    adx = indicators.get("adx", {})
    if adx.get("trend_strength") == "strong":
        if adx.get("trend_direction") == "bullish":
            long_buy_score += 3
            long_buy_conds.append(f"ADX强势上涨({adx.get('adx', 0):.1f})")
        else:
            long_sell_score += 3
            long_sell_conds.append(f"ADX强势下跌({adx.get('adx', 0):.1f})")
    
    ichimoku = indicators.get("ichimoku", {})
    if ichimoku.get("status") == "strong_bullish":
        long_buy_score += 3
        long_buy_conds.append("云图强势看多")
    elif ichimoku.get("status") == "strong_bearish":
        long_sell_score += 3
        long_sell_conds.append("云图强势看空")
    elif ichimoku.get("cloud_position") == "above_cloud":
        long_buy_score += 2
        long_buy_conds.append("价格在云层上方")
    elif ichimoku.get("cloud_position") == "below_cloud":
        long_sell_score += 2
        long_sell_conds.append("价格在云层下方")
    
    mfi = indicators.get("money_flow", {})
    if mfi.get("mfi_status") == "inflow":
        long_buy_score += 2
        long_buy_conds.append("资金净流入")
    elif mfi.get("mfi_status") == "outflow":
        long_sell_score += 2
        long_sell_conds.append("资金净流出")
    
    if quant_score >= 65:
        long_buy_score += 2
        long_buy_conds.append(f"量化评分优秀({quant_score:.0f})")
    elif quant_score <= 35:
        long_sell_score += 2
        long_sell_conds.append(f"量化评分较低({quant_score:.0f})")
    
    if long_buy_score > long_sell_score + 3:
        long_type = SignalType.BUY
        long_strength = min(5, max(1, int((long_buy_score - long_sell_score) / 2.5) + 1))
        long_conds = long_buy_conds
        long_conf = round(long_buy_score / (long_buy_score + long_sell_score + 1) * 100, 1)
    elif long_sell_score > long_buy_score + 3:
        long_type = SignalType.SELL
        long_strength = min(5, max(1, int((long_sell_score - long_buy_score) / 2.5) + 1))
        long_conds = long_sell_conds
        long_conf = round(long_sell_score / (long_buy_score + long_sell_score + 1) * 100, 1)
    else:
        long_type = SignalType.HOLD
        long_strength = 0
        long_conds = []
        long_conf = 50
    
    long_stop_pct = 8.0
    long_stop = current_price * (1 - long_stop_pct / 100) if long_type == SignalType.BUY else current_price * (1 + long_stop_pct / 100)
    long_risk = abs(current_price - long_stop)
    
    result['long'] = _build_period_result(long_type, long_strength, long_conds, long_conf,
                                          current_price, long_stop, long_stop_pct, long_risk,
                                          '中长线(1月+)', quant_score, generator)
    
    return result


def _build_period_result(signal_type: SignalType, strength: int, conditions: List[str], confidence: float,
                         current_price: float, stop_loss: float, stop_loss_pct: float, risk: float,
                         period_label: str, quant_score: float, generator: TradingSignalGenerator) -> Dict:
    """构建周期分析结果"""
    is_buy = signal_type == SignalType.BUY
    is_sell = signal_type == SignalType.SELL
    
    # 止盈目标
    if is_buy:
        tp1 = current_price + risk * 2
        tp2 = current_price + risk * 3
        tp3 = current_price + risk * 5
    elif is_sell:
        tp1 = current_price - risk * 2
        tp2 = current_price - risk * 3
        tp3 = current_price - risk * 5
    else:
        tp1 = current_price * 1.05
        tp2 = current_price * 1.08
        tp3 = current_price * 1.12
    
    # 建议仓位
    if strength >= 4:
        pos_pct = 25 if '中长' in period_label else (20 if '波段' in period_label else 15)
    elif strength >= 2:
        pos_pct = 20 if '中长' in period_label else (15 if '波段' in period_label else 10)
    else:
        pos_pct = 10
    
    return {
        'signal_type': signal_type.value,
        'type_cn': "买入" if is_buy else ("卖出" if is_sell else "观望"),
        'strength': strength,
        'strength_label': generator.get_signal_strength_label(strength),
        'confidence': confidence,
        'triggered_conditions': conditions,
        'period_label': period_label,
        'risk_management': {
            'stop_loss': round(stop_loss, 4),
            'stop_loss_pct': stop_loss_pct,
            'take_profit_targets': [
                {"level": 1, "price": round(tp1, 4), "ratio": "1:2"},
                {"level": 2, "price": round(tp2, 4), "ratio": "1:3"},
                {"level": 3, "price": round(tp3, 4), "ratio": "1:5"},
            ],
            'suggested_position_pct': pos_pct,
        },
        'action_suggestion': _get_action_text(signal_type, strength, period_label.split('(')[0], quant_score, len(conditions)),
        'position_strategy': _get_position_strategy(signal_type, strength, stop_loss, period_label.split('(')[0])
    }


def _get_action_text(signal_type: SignalType, strength: int, period: str, quant_score: float, cond_count: int) -> str:
    """生成操作建议文本"""
    if signal_type == SignalType.BUY:
        if strength >= 4:
            return f"{period}多指标共振看多（{cond_count}项确认，量化评分{quant_score:.0f}），技术面偏强。可考虑分批建仓，严格设置止损。"
        elif strength >= 2:
            return f"{period}偏多信号（{cond_count}项确认），可小仓位试探，严格止损。"
        else:
            return f"{period}弱多信号，建议观望等待更多确认。"
    elif signal_type == SignalType.SELL:
        if strength >= 4:
            return f"{period}多指标共振看空（{cond_count}项确认，量化评分{quant_score:.0f}），技术面偏弱。持仓者建议减仓或清仓。"
        elif strength >= 2:
            return f"{period}偏空信号（{cond_count}项确认），注意风险控制，持仓者建议减仓。"
        else:
            return f"{period}弱空信号，密切关注走势变化，持仓者注意风险。"
    else:
        return f"{period}多空力量均衡，方向不明确。建议保持观望，等待明确信号。"


def _get_position_strategy(signal_type: SignalType, strength: int, stop_loss: float, period: str) -> Dict:
    """生成仓位策略"""
    if signal_type == SignalType.BUY:
        if strength >= 4:
            return {
                'empty_position': f"{period}多指标共振看多，可考虑分批建仓",
                'first_entry': f"建议首次建仓1-2成，设好止损后观察",
                'add_position': f"站稳支撑位且放量突破可加仓",
                'reduce_position': f"跌破止损位{stop_loss:.3f}减仓",
                'full_exit': f"跌破止损位{stop_loss:.3f}或出现明确卖出信号时清仓"
            }
        elif strength >= 2:
            return {
                'empty_position': f"{period}偏多信号，可小仓位试探",
                'first_entry': f"建议轻仓试探1成，严格止损",
                'add_position': f"确认突破阻力位后可加仓",
                'reduce_position': f"跌破止损位{stop_loss:.3f}建议清仓",
                'full_exit': f"跌破止损位{stop_loss:.3f}时清仓"
            }
        else:
            return {
                'empty_position': f"{period}弱多信号，建议观望",
                'first_entry': "如需建仓建议不超过0.5成",
                'add_position': "不建议加仓，等待信号增强",
                'reduce_position': f"跌破{stop_loss:.3f}立即止损",
                'full_exit': f"跌破{stop_loss:.3f}时清仓"
            }
    elif signal_type == SignalType.SELL:
        if strength >= 4:
            return {
                'empty_position': f"{period}多指标共振看空，保持空仓观望",
                'first_entry': "不建议此时建仓，等待企稳信号",
                'add_position': "不建议加仓，空头趋势明显",
                'reduce_position': "持仓者建议减仓至1成以内",
                'full_exit': f"跌破关键支撑或止损位{stop_loss:.3f}时清仓"
            }
        elif strength >= 2:
            return {
                'empty_position': f"{period}偏空信号，保持谨慎观望",
                'first_entry': "不建议建仓，等待止跌信号",
                'add_position': "不建议加仓",
                'reduce_position': "持仓者建议减仓或设好止损",
                'full_exit': f"跌破止损位{stop_loss:.3f}时清仓"
            }
        else:
            return {
                'empty_position': f"{period}弱空信号，可观望但需警惕",
                'first_entry': "暂不建议建仓",
                'add_position': "不建议加仓",
                'reduce_position': "持仓者注意风险控制",
                'full_exit': "出现明确方向信号后再做决策"
            }
    else:
        return {
            'empty_position': f"{period}多空力量均衡，建议保持空仓观望",
            'first_entry': "等待明确信号后再考虑建仓",
            'add_position': "不建议加仓，等待方向明确",
            'reduce_position': "持仓者可考虑减仓观望",
            'full_exit': "出现明确方向信号后再做决策"
        }
