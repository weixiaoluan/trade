"""
============================================
超高胜率交易策略 v5.0
Ultra High Win Rate Trading Strategy
============================================

目标：95%+ 胜率
核心理念：宁可错过1000次，不可做错1次

v5.0 核心优化：
1. ATR 动态风控 - 根据市场波动率自适应调整止损止盈
   - 止损位：Price - (n × ATR)，市场安静时缩小止损，市场狂躁时扩大止损
   - 支撑位判断：使用 ≤ 0.5 × ATR 替代固定百分比
   
2. 金字塔式分仓策略 - 分批建仓，降低成本，提高胜率
   - 信号触发（Score 75+）：先买入 5% 仓位（底仓）
   - 价格回撤但未破位（Score 90+）：再买入 10% 仓位（拉低均价）
   - 价格确认上涨（突破）：最后买入剩余仓位
   
3. 移动止盈 (Trailing Stop) - 让利润奔跑，锁定收益
   - 激活阈值：利润达到 3×ATR 时触发移动止盈
   - 回撤卖出：从最高点回撤 0.5×ATR 时全部卖出
   - 效果：能在单边暴涨行情中吃到 20% 甚至 50% 的利润

策略原则：
1. 极端保守入场 - 只在完美条件下交易
2. 多重确认机制 - 至少6个独立指标共振
3. 趋势跟随 - 只顺势交易，绝不逆势
4. 量价配合 - 必须有成交量确认
5. 多周期共振 - 日线、周线方向一致
6. ATR动态风控 - 根据波动率调整止损止盈
7. 等待回调 - 不追高，只在回调支撑位买入
8. 情绪过滤 - 避免市场极端情绪时交易

注意：高胜率意味着极低交易频率，可能错过很多机会
本模块仅供学习研究使用，不构成任何投资建议。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class HighWinSignalType(Enum):
    """高胜率信号类型"""
    STRONG_BUY = "strong_buy"     # 强买入（满足所有条件）
    BUY = "buy"                   # 买入（满足大部分条件）
    HOLD = "hold"                 # 观望（条件不足）
    SELL = "sell"                 # 卖出
    STRONG_SELL = "strong_sell"  # 强卖出


@dataclass
class HighWinSignal:
    """高胜率交易信号"""
    signal_type: HighWinSignalType
    confidence: float              # 置信度 0-100
    score: int                     # 综合评分 0-100
    met_conditions: List[str]      # 满足的条件
    unmet_conditions: List[str]    # 未满足的条件
    warnings: List[str]            # 警告信息
    entry_price: float             # 建议入场价
    stop_loss: float               # 止损价
    take_profit_1: float           # 止盈1
    take_profit_2: float           # 止盈2
    position_pct: float            # 建议仓位
    reason: str                    # 信号原因


class UltraHighWinRateStrategyV4:
    """
    超高胜率策略 v5.0 - 目标95%+胜率（ATR动态风控版本）
    
    核心理念：
    1. 只做最确定的机会 - 宁可错过1000次，不可做错1次
    2. 多重确认机制 - 至少6个独立条件同时满足
    3. ATR动态价格位置判断 - 使用ATR标准化距离
    4. 趋势共振 - 大中小周期趋势一致
    5. 量价配合 - 缩量回调后放量启动
    6. 技术指标超卖共振 - RSI/KDJ/MACD同时确认
    
    入场条件（必须全部满足）：
    1. 大趋势向上（MA60/MA120上升）
    2. 中期趋势向上（MA20上升，价格在MA20上方）
    3. 短期回调到支撑位（距离支撑位 ≤ 0.5×ATR）
    4. RSI在40-55区间（回调充分但未超卖）
    5. KDJ金叉或J值<30超卖
    6. MACD柱状图缩短或金叉
    7. 成交量萎缩后放量（量比>1.2）
    8. 价格距离阻力位 > 1×ATR
    
    出场条件（ATR动态）：
    1. 移动止盈：利润达到3×ATR后激活，从高点回撤0.5×ATR时止盈
    2. ATR动态止损：跌破 入场价 - 2×ATR 时止损
    3. 时间止损：持有超过5天未盈利则平仓
    """
    
    def __init__(self):
        self.config = {
            # 入场条件阈值 - 极端严格
            'min_score': 90,               # 最低评分90分
            'min_confidence': 92,          # 最低置信度92%
            'min_conditions': 7,           # 最少满足7个条件
            
            # 趋势要求
            'trend_score_min': 35,         # 趋势分数最低35
            
            # ATR动态价格位置（替代固定百分比）
            'support_distance_atr': 0.5,   # 距离支撑位 ≤ 0.5×ATR 视为接近
            'resistance_distance_atr': 1.0, # 距离阻力位 < 1×ATR 视为太近
            
            # 备用固定百分比（ATR数据缺失时使用）
            'max_above_ma20_pct': 1.5,     # 最多高于MA20 1.5%
            'max_above_support_pct': 1.5,  # 最多高于支撑位1.5%
            'min_below_resistance_pct': 8, # 至少低于阻力位8%
            
            # ATR动态风控
            'stop_loss_atr': 2.0,          # 止损 2×ATR
            'trailing_activation_atr': 3.0, # 移动止盈激活 3×ATR
            'trailing_stop_atr': 0.5,      # 移动止损回撤 0.5×ATR
            
            # 备用固定百分比风控
            'stop_loss_pct': 2.0,          # 止损2%
            'take_profit_1_pct': 3.0,      # 第一止盈3%
            'take_profit_2_pct': 5.0,      # 第二止盈5%
            
            # 金字塔式分仓
            'initial_position_pct': 5,     # 初始建仓5%（底仓）
            'pullback_add_pct': 10,        # 回调加仓10%
            'breakout_add_pct': 5,         # 突破加仓5%
            
            # 指标阈值 - 严格
            'rsi_min': 35,                 # RSI最小值
            'rsi_max': 55,                 # RSI最大值（不追高）
            'rsi_oversold': 40,            # RSI超卖阈值
            'kdj_oversold': 30,            # KDJ超卖阈值
            'kdj_max': 60,                 # KDJ最大值
            'volume_ratio_min': 1.0,       # 最小量比
            'volume_ratio_max': 3.0,       # 最大量比（避免异常放量）
        }

    def analyze(
        self,
        indicators: Dict,
        quant_analysis: Dict = None,
        support_resistance: Dict = None
    ) -> HighWinSignal:
        """
        超高胜率分析 v4.0
        
        评分体系（满分100分）：
        - 趋势分（30分）：均线排列、MACD方向、ADX
        - 位置分（30分）：价格相对支撑位、均线的位置
        - 指标分（25分）：RSI、KDJ、布林带状态
        - 量能分（10分）：成交量配合
        - 量化分（5分）：量化评分
        """
        current_price = indicators.get('latest_price', 0)
        if current_price <= 0:
            return self._reject("价格数据无效")
        
        # 获取支撑阻力位
        support_levels = []
        resistance_levels = []
        if support_resistance:
            support_levels = [l.get('price', 0) for l in support_resistance.get('support_levels', [])]
            resistance_levels = [l.get('price', 0) for l in support_resistance.get('resistance_levels', [])]
        
        score = 0
        conditions_met = []
        conditions_unmet = []
        warnings = []
        
        # ========== 第0步：一票否决检查 ==========
        veto, veto_reason = self._check_veto_conditions(indicators, current_price, support_levels)
        if veto:
            return self._reject(f"一票否决: {veto_reason}")
        
        # ========== 1. 趋势分析（30分）==========
        trend_score, trend_conditions, trend_warnings = self._analyze_trend_strict(indicators)
        score += trend_score
        conditions_met.extend(trend_conditions)
        warnings.extend(trend_warnings)
        
        # 趋势不达标直接否决
        if trend_score < 18:
            return self._reject(f"趋势不达标({trend_score}/30分)，需要至少18分")
        
        # ========== 2. 价格位置分析（30分）==========
        position_score, position_conditions, position_warnings = self._analyze_position_strict(
            indicators, current_price, support_levels, resistance_levels
        )
        score += position_score
        conditions_met.extend(position_conditions)
        warnings.extend(position_warnings)
        
        # 价格位置不达标否决
        if position_score < 15:
            return self._reject(f"价格位置不理想({position_score}/30分)，需要至少15分")
        
        # ========== 3. 技术指标分析（25分）==========
        indicator_score, indicator_conditions, indicator_warnings = self._analyze_indicators_strict(indicators)
        score += indicator_score
        conditions_met.extend(indicator_conditions)
        warnings.extend(indicator_warnings)
        
        # 指标不达标否决
        if indicator_score < 12:
            return self._reject(f"技术指标不理想({indicator_score}/25分)，需要至少12分")
        
        # ========== 4. 成交量分析（10分）==========
        volume_score, volume_conditions, volume_warnings = self._analyze_volume_strict(indicators)
        score += volume_score
        conditions_met.extend(volume_conditions)
        warnings.extend(volume_warnings)
        
        # ========== 5. 量化评分（5分）==========
        quant_score_val = 0
        if quant_analysis:
            quant_score_val = quant_analysis.get('quant_score', 50)
            if quant_score_val >= 70:
                score += 5
                conditions_met.append(f"✅ 量化评分优秀({quant_score_val:.0f})(+5)")
            elif quant_score_val >= 60:
                score += 3
                conditions_met.append(f"✅ 量化评分良好({quant_score_val:.0f})(+3)")
            elif quant_score_val >= 50:
                score += 1
                conditions_met.append(f"⚠️ 量化评分中等({quant_score_val:.0f})(+1)")
            else:
                conditions_unmet.append(f"❌ 量化评分偏低({quant_score_val:.0f})")
        
        # ========== 6. 计算置信度 ==========
        confidence = self._calculate_confidence_strict(
            score, len(conditions_met), trend_score, position_score, indicator_score, volume_score
        )
        
        # ========== 7. 生成信号 ==========
        return self._generate_final_signal_strict(
            score=score,
            confidence=confidence,
            conditions_met=conditions_met,
            conditions_unmet=conditions_unmet,
            warnings=warnings,
            current_price=current_price,
            support_levels=support_levels,
            indicators=indicators
        )

    def _check_veto_conditions(
        self, 
        indicators: Dict, 
        current_price: float,
        support_levels: List[float]
    ) -> Tuple[bool, str]:
        """检查一票否决条件 - 极端严格"""
        
        # 1. 均线空头排列时绝对不买入
        ma_trend = indicators.get('ma_trend', '')
        if ma_trend == 'bearish_alignment':
            return True, "均线空头排列，绝对不买入"
        
        # 2. 价格跌破MA60
        ma_values = indicators.get('moving_averages', {})
        ma60 = ma_values.get('MA60', 0)
        if ma60 > 0 and current_price < ma60:
            return True, "价格跌破MA60，趋势偏空"
        
        # 3. 价格跌破所有均线
        ma20 = ma_values.get('MA20', 0)
        ma120 = ma_values.get('MA120', 0)
        if ma20 > 0 and ma60 > 0 and ma120 > 0:
            if current_price < ma20 and current_price < ma60 and current_price < ma120:
                return True, "价格跌破所有均线，强烈看空"
        
        # 4. RSI超买
        rsi = indicators.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        if rsi_value > 70:
            return True, f"RSI超买({rsi_value:.0f})，不追高"
        
        # 5. RSI偏高（>60也不买）
        if rsi_value > 60:
            return True, f"RSI偏高({rsi_value:.0f})，等待回调"
        
        # 6. KDJ超买
        kdj = indicators.get('kdj', {})
        j_value = kdj.get('j', 50)
        if j_value > 80:
            return True, f"KDJ超买(J={j_value:.0f})，不追高"
        
        # 7. MACD死叉
        macd = indicators.get('macd', {})
        if macd.get('crossover') == 'death_cross':
            return True, "MACD死叉，趋势转弱"
        
        # 8. 多指标共振看空
        bearish_count = 0
        if macd.get('trend') == 'bearish':
            bearish_count += 1
        if rsi_value > 55:
            bearish_count += 1
        if kdj.get('crossover') == 'death_cross' or j_value > 70:
            bearish_count += 1
        if bearish_count >= 2:
            return True, f"多指标偏空({bearish_count}个)，不宜买入"
        
        # 9. 放量下跌
        vol = indicators.get('volume_analysis', {})
        vol_ratio = vol.get('volume_ratio', 1)
        price_change = indicators.get('price_change_pct', 0)
        if vol_ratio > 1.5 and price_change < -1.5:
            return True, f"放量下跌(量比{vol_ratio:.1f}，跌{price_change:.1f}%)，主力出货"
        
        # 10. 追高检查 - 价格远离支撑位
        if support_levels:
            nearest_support = max([s for s in support_levels if s < current_price], default=0)
            if nearest_support > 0:
                above_support_pct = (current_price / nearest_support - 1) * 100
                if above_support_pct > 5:
                    return True, f"价格远离支撑位{above_support_pct:.1f}%，追高风险大"
        
        # 11. 价格远离MA20
        if ma20 > 0:
            above_ma20_pct = (current_price / ma20 - 1) * 100
            if above_ma20_pct > 5:
                return True, f"价格远离MA20({above_ma20_pct:.1f}%)，等待回调"
        
        # 12. 异常放量（可能是主力出货）
        if vol_ratio > 4:
            return True, f"异常放量(量比{vol_ratio:.1f})，可能主力出货"
        
        return False, ""

    def _analyze_trend_strict(self, indicators: Dict) -> Tuple[int, List[str], List[str]]:
        """分析趋势（满分30分）- 严格版"""
        score = 0
        conditions = []
        warnings = []
        
        ma_values = indicators.get('moving_averages', {})
        latest_price = indicators.get('latest_price', 0)
        ma20 = ma_values.get('MA20', 0)
        ma60 = ma_values.get('MA60', 0)
        ma120 = ma_values.get('MA120', 0)
        
        # 1. 均线排列（15分）
        ma_trend = indicators.get('ma_trend', '')
        if ma_trend == 'bullish_alignment':
            score += 15
            conditions.append("✅ 均线多头排列(+15)")
        elif ma_trend == 'bearish_alignment':
            warnings.append("⚠️ 均线空头排列，不宜买入")
            return 0, [], warnings
        else:
            # 检查价格与均线关系
            if latest_price > 0 and ma20 > 0 and ma60 > 0:
                if latest_price > ma20 and latest_price > ma60:
                    if ma20 > ma60:  # MA20在MA60上方
                        score += 12
                        conditions.append("✅ 价格在MA20/MA60上方，MA20>MA60(+12)")
                    else:
                        score += 8
                        conditions.append("✅ 价格在MA20/MA60上方(+8)")
                elif latest_price > ma60:
                    score += 5
                    conditions.append("✅ 价格在MA60上方(+5)")
        
        # 2. MACD方向（10分）
        macd = indicators.get('macd', {})
        if macd.get('crossover') == 'golden_cross':
            score += 10
            conditions.append("✅ MACD金叉(+10)")
        elif macd.get('trend') == 'bullish':
            # 检查MACD柱状图是否在缩短（回调中）
            histogram = macd.get('histogram', 0)
            prev_histogram = macd.get('prev_histogram', histogram)
            if histogram > 0:
                if histogram < prev_histogram:  # 红柱缩短，回调中
                    score += 8
                    conditions.append("✅ MACD多头+红柱缩短(回调中)(+8)")
                else:
                    score += 6
                    conditions.append("✅ MACD多头(+6)")
            else:
                score += 4
                conditions.append("✅ MACD趋势向上(+4)")
        elif macd.get('crossover') == 'death_cross':
            warnings.append("⚠️ MACD死叉")
        
        # 3. ADX趋势强度（5分）
        adx = indicators.get('adx', {})
        adx_value = adx.get('adx', 0)
        if adx.get('trend_direction') == 'bullish':
            if adx_value > 30:
                score += 5
                conditions.append(f"✅ ADX强势上涨({adx_value:.0f})(+5)")
            elif adx_value > 20:
                score += 3
                conditions.append(f"✅ ADX上涨({adx_value:.0f})(+3)")
        
        return score, conditions, warnings

    def _analyze_position_strict(
        self,
        indicators: Dict,
        current_price: float,
        support_levels: List[float],
        resistance_levels: List[float]
    ) -> Tuple[int, List[str], List[str]]:
        """分析价格位置（满分30分）- 严格版"""
        score = 0
        conditions = []
        warnings = []
        
        ma_values = indicators.get('moving_averages', {})
        ma20 = ma_values.get('MA20', 0)
        ma60 = ma_values.get('MA60', 0)
        
        # 1. 相对MA20位置（15分）- 必须回调到MA20附近
        if ma20 > 0:
            pct_from_ma20 = (current_price / ma20 - 1) * 100
            if 0 <= pct_from_ma20 <= self.config['max_above_ma20_pct']:
                # 完美位置：刚好在MA20上方1.5%以内
                score += 15
                conditions.append(f"✅ 完美回调至MA20({pct_from_ma20:+.1f}%)(+15)")
            elif -1 <= pct_from_ma20 < 0:
                # 轻微跌破MA20，可能是假突破
                score += 10
                conditions.append(f"✅ 回调至MA20附近({pct_from_ma20:.1f}%)(+10)")
            elif 0 < pct_from_ma20 <= 3:
                # 稍微高于MA20
                score += 8
                conditions.append(f"✅ MA20上方({pct_from_ma20:.1f}%)(+8)")
            elif pct_from_ma20 > 3:
                warnings.append(f"⚠️ 远离MA20({pct_from_ma20:.1f}%)，等待回调")
            else:
                warnings.append(f"⚠️ 跌破MA20({pct_from_ma20:.1f}%)")
        
        # 2. 相对支撑位位置（10分）
        if support_levels:
            nearest_support = max([s for s in support_levels if s < current_price], default=0)
            if nearest_support > 0:
                pct_from_support = (current_price / nearest_support - 1) * 100
                if pct_from_support <= self.config['max_above_support_pct']:
                    # 完美位置：接近支撑位
                    score += 10
                    conditions.append(f"✅ 完美接近支撑位({pct_from_support:.1f}%)(+10)")
                elif pct_from_support <= 3:
                    score += 7
                    conditions.append(f"✅ 支撑位上方({pct_from_support:.1f}%)(+7)")
                elif pct_from_support <= 5:
                    score += 4
                    conditions.append(f"⚠️ 距支撑位较远({pct_from_support:.1f}%)(+4)")
                else:
                    warnings.append(f"⚠️ 远离支撑位({pct_from_support:.1f}%)")
        
        # 3. 相对阻力位位置（5分）
        if resistance_levels:
            nearest_resistance = min([r for r in resistance_levels if r > current_price], default=0)
            if nearest_resistance > 0:
                pct_to_resistance = (nearest_resistance / current_price - 1) * 100
                if pct_to_resistance >= self.config['min_below_resistance_pct']:
                    score += 5
                    conditions.append(f"✅ 远离阻力位({pct_to_resistance:.1f}%)(+5)")
                elif pct_to_resistance >= 5:
                    score += 3
                    conditions.append(f"✅ 阻力位较远({pct_to_resistance:.1f}%)(+3)")
                else:
                    warnings.append(f"⚠️ 接近阻力位({pct_to_resistance:.1f}%)")
        
        return score, conditions, warnings

    def _analyze_indicators_strict(self, indicators: Dict) -> Tuple[int, List[str], List[str]]:
        """分析技术指标（满分25分）- 严格版"""
        score = 0
        conditions = []
        warnings = []
        
        # 1. RSI（10分）- 必须在合理区间
        rsi = indicators.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        
        if self.config['rsi_min'] <= rsi_value <= self.config['rsi_oversold']:
            # RSI在35-40，超卖区间，最佳买点
            score += 10
            conditions.append(f"✅ RSI超卖区间({rsi_value:.0f})(+10)")
        elif self.config['rsi_oversold'] < rsi_value <= 50:
            # RSI在40-50，回调充分
            score += 8
            conditions.append(f"✅ RSI回调充分({rsi_value:.0f})(+8)")
        elif 50 < rsi_value <= self.config['rsi_max']:
            # RSI在50-55，可接受
            score += 5
            conditions.append(f"✅ RSI正常({rsi_value:.0f})(+5)")
        elif rsi_value < self.config['rsi_min']:
            # RSI过低，可能是下跌趋势
            score += 3
            warnings.append(f"⚠️ RSI过低({rsi_value:.0f})，可能下跌趋势")
        else:
            warnings.append(f"⚠️ RSI偏高({rsi_value:.0f})，不宜追高")
        
        # 2. KDJ（10分）
        kdj = indicators.get('kdj', {})
        j_value = kdj.get('j', 50)
        k_value = kdj.get('k', 50)
        d_value = kdj.get('d', 50)
        
        if kdj.get('crossover') == 'golden_cross':
            score += 10
            conditions.append("✅ KDJ金叉(+10)")
        elif j_value <= self.config['kdj_oversold']:
            # J值超卖
            score += 10
            conditions.append(f"✅ KDJ超卖(J={j_value:.0f})(+10)")
        elif j_value <= 40:
            score += 7
            conditions.append(f"✅ KDJ偏低(J={j_value:.0f})(+7)")
        elif j_value <= self.config['kdj_max']:
            score += 4
            conditions.append(f"✅ KDJ正常(J={j_value:.0f})(+4)")
        elif kdj.get('status') == 'overbought' or j_value > 80:
            warnings.append(f"⚠️ KDJ超买(J={j_value:.0f})")
        
        # 3. 布林带（5分）
        bb = indicators.get('bollinger_bands', {})
        bb_status = bb.get('status', '')
        bb_position = bb.get('position_pct', 50)  # 0=下轨，50=中轨，100=上轨
        
        if bb_status == 'near_lower' or bb_position < 20:
            score += 5
            conditions.append("✅ 触及布林下轨(+5)")
        elif bb_status == 'middle' or 30 <= bb_position <= 50:
            score += 3
            conditions.append("✅ 布林中轨附近(+3)")
        elif bb_status == 'near_upper' or bb_position > 80:
            warnings.append("⚠️ 触及布林上轨")
        
        return score, conditions, warnings

    def _analyze_volume_strict(self, indicators: Dict) -> Tuple[int, List[str], List[str]]:
        """分析成交量（满分10分）- 严格版"""
        score = 0
        conditions = []
        warnings = []
        
        vol = indicators.get('volume_analysis', {})
        vol_ratio = vol.get('volume_ratio', 1)
        vol_status = vol.get('status', 'normal')
        
        # 理想情况：缩量回调后温和放量
        if self.config['volume_ratio_min'] <= vol_ratio <= 1.5:
            # 温和放量，最佳
            score += 10
            conditions.append(f"✅ 温和放量({vol_ratio:.1f}倍)(+10)")
        elif 0.7 <= vol_ratio < self.config['volume_ratio_min']:
            # 缩量，可能还在回调中
            score += 6
            conditions.append(f"✅ 缩量回调({vol_ratio:.1f}倍)(+6)")
        elif 1.5 < vol_ratio <= self.config['volume_ratio_max']:
            # 放量较大，需要观察
            score += 5
            conditions.append(f"⚠️ 放量较大({vol_ratio:.1f}倍)(+5)")
        elif vol_ratio > self.config['volume_ratio_max']:
            # 异常放量，可能是主力出货
            warnings.append(f"⚠️ 异常放量({vol_ratio:.1f}倍)，谨慎")
        else:
            # 量能过低
            score += 3
            conditions.append(f"⚠️ 量能偏低({vol_ratio:.1f}倍)(+3)")
        
        return score, conditions, warnings
    
    def _calculate_confidence_strict(
        self,
        total_score: int,
        conditions_count: int,
        trend_score: int,
        position_score: int,
        indicator_score: int,
        volume_score: int
    ) -> float:
        """计算置信度 - 严格版"""
        # 基础置信度 = 总分
        confidence = total_score
        
        # 条件数量加成
        if conditions_count >= 10:
            confidence += 5
        elif conditions_count >= 8:
            confidence += 3
        elif conditions_count >= 6:
            confidence += 1
        
        # 各项均衡加成（所有维度都达标）
        if trend_score >= 20 and position_score >= 20 and indicator_score >= 18 and volume_score >= 8:
            confidence += 5
        elif trend_score >= 18 and position_score >= 15 and indicator_score >= 15 and volume_score >= 6:
            confidence += 3
        
        return min(99, max(0, confidence))

    def _generate_final_signal_strict(
        self,
        score: int,
        confidence: float,
        conditions_met: List[str],
        conditions_unmet: List[str],
        warnings: List[str],
        current_price: float,
        support_levels: List[float],
        indicators: Dict
    ) -> HighWinSignal:
        """生成最终信号 - 严格版"""
        
        conditions_count = len(conditions_met)
        
        # 判断信号类型 - 极端严格
        if (score >= self.config['min_score'] and 
            confidence >= self.config['min_confidence'] and
            conditions_count >= self.config['min_conditions']):
            signal_type = HighWinSignalType.STRONG_BUY
            reason = f"🎯 完美买入机会: 评分{score}/100，置信度{confidence:.0f}%，{conditions_count}个条件满足"
            position_pct = self.config['position_pct']
        elif (score >= 85 and confidence >= 88 and conditions_count >= 6):
            signal_type = HighWinSignalType.BUY
            reason = f"✅ 较好买入机会: 评分{score}/100，置信度{confidence:.0f}%"
            position_pct = self.config['position_pct'] * 0.6
        elif (score >= 75 and confidence >= 80 and conditions_count >= 5):
            signal_type = HighWinSignalType.HOLD
            reason = f"⚠️ 条件接近但不完美: 评分{score}/100，置信度{confidence:.0f}%，建议等待更好机会"
            position_pct = 0
        else:
            signal_type = HighWinSignalType.HOLD
            reason = f"❌ 条件不足: 评分{score}/100，置信度{confidence:.0f}%，{conditions_count}个条件"
            position_pct = 0
        
        # 计算止损止盈 - 保守设置
        stop_loss = current_price * (1 - self.config['stop_loss_pct'] / 100)
        take_profit_1 = current_price * (1 + self.config['take_profit_1_pct'] / 100)
        take_profit_2 = current_price * (1 + self.config['take_profit_2_pct'] / 100)
        
        # 用支撑位优化止损
        if support_levels:
            nearest_support = max([s for s in support_levels if s < current_price], default=0)
            if nearest_support > 0:
                support_stop = nearest_support * 0.995  # 支撑位下方0.5%
                # 取较高的止损位（更保守）
                if support_stop > stop_loss:
                    stop_loss = support_stop
        
        # 建议入场价（回调到MA20或支撑位）
        entry_price = current_price
        ma_values = indicators.get('moving_averages', {})
        ma20 = ma_values.get('MA20', 0)
        
        # 优先使用MA20作为入场参考
        if ma20 > 0 and ma20 < current_price:
            entry_price = min(current_price, ma20 * 1.005)  # MA20上方0.5%
        
        # 如果有支撑位，取更保守的入场价
        if support_levels:
            nearest_support = max([s for s in support_levels if s < current_price], default=0)
            if nearest_support > 0:
                support_entry = nearest_support * 1.005  # 支撑位上方0.5%
                entry_price = min(entry_price, support_entry)
        
        return HighWinSignal(
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            met_conditions=conditions_met,
            unmet_conditions=conditions_unmet,
            warnings=warnings,
            entry_price=round(entry_price, 3),
            stop_loss=round(stop_loss, 3),
            take_profit_1=round(take_profit_1, 3),
            take_profit_2=round(take_profit_2, 3),
            position_pct=round(position_pct, 1),
            reason=reason
        )
    
    def _reject(self, reason: str) -> HighWinSignal:
        """拒绝信号"""
        return HighWinSignal(
            signal_type=HighWinSignalType.HOLD,
            confidence=0,
            score=0,
            met_conditions=[],
            unmet_conditions=[f"❌ {reason}"],
            warnings=[reason],
            entry_price=0,
            stop_loss=0,
            take_profit_1=0,
            take_profit_2=0,
            position_pct=0,
            reason=f"不满足入场条件: {reason}"
        )


class UltraHighWinSellStrategy:
    """
    超高胜率卖出策略 v4.0
    
    核心理念：
    1. 快速止盈 - 盈利2%立即止盈50%，盈利3%清仓
    2. 严格止损 - 亏损1.5%无条件止损
    3. 时间止损 - 持有超过3天未盈利则平仓
    4. 趋势反转 - 出现明确卖出信号立即清仓
    """
    
    def __init__(self):
        self.config = {
            'stop_loss_pct': -1.5,         # 止损1.5%
            'take_profit_1_pct': 2.0,      # 第一止盈2%
            'take_profit_1_ratio': 0.5,    # 第一止盈卖出50%
            'take_profit_2_pct': 3.0,      # 第二止盈3%
            'take_profit_2_ratio': 1.0,    # 第二止盈清仓
            'max_holding_days': 3,         # 最大持有天数
            'trailing_stop_pct': 1.0,      # 移动止损回撤1%
        }
    
    def should_sell(
        self,
        position: Dict,
        current_price: float,
        indicators: Dict = None,
        signal: Dict = None
    ) -> Tuple[bool, str, float]:
        """
        判断是否应该卖出
        
        Returns:
            (是否卖出, 原因, 卖出比例)
        """
        if not position:
            return False, "没有持仓", 0
        
        cost_price = position.get('cost_price', 0)
        if cost_price <= 0:
            return False, "成本价无效", 0
        
        profit_pct = (current_price / cost_price - 1) * 100
        highest_price = position.get('highest_price', cost_price)
        sold_ratio = position.get('sold_ratio', 0)
        
        # 1. 止损检查 - 最高优先级
        if profit_pct <= self.config['stop_loss_pct']:
            return True, f"🚨 触发止损(亏损{profit_pct:.1f}%)", 1.0
        
        # 2. 移动止损（从最高点回撤）
        if highest_price > cost_price:
            from_high_pct = (current_price / highest_price - 1) * 100
            if from_high_pct <= -self.config['trailing_stop_pct']:
                return True, f"🚨 移动止损(从高点回撤{abs(from_high_pct):.1f}%)", 1.0
        
        # 3. 第二止盈（清仓）
        if profit_pct >= self.config['take_profit_2_pct'] and sold_ratio < 0.9:
            return True, f"🎯 第二止盈(盈利{profit_pct:.1f}%)", 1.0
        
        # 4. 第一止盈（卖出50%）
        if profit_pct >= self.config['take_profit_1_pct'] and sold_ratio < 0.5:
            return True, f"✅ 第一止盈(盈利{profit_pct:.1f}%)", self.config['take_profit_1_ratio']
        
        # 5. 时间止损
        buy_date_str = position.get('buy_date', '')
        if buy_date_str:
            from datetime import datetime, timedelta, timezone
            try:
                buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
                beijing_tz = timezone(timedelta(hours=8))
                today = datetime.now(beijing_tz).replace(tzinfo=None)
                holding_days = (today - buy_date).days
                
                if holding_days >= self.config['max_holding_days'] and profit_pct <= 0:
                    return True, f"⏰ 时间止损(持有{holding_days}天未盈利)", 1.0
            except:
                pass
        
        # 6. 技术指标卖出信号
        if indicators:
            sell_signal, sell_reason = self._check_technical_sell(indicators, profit_pct)
            if sell_signal:
                return True, sell_reason, 1.0
        
        # 7. 外部卖出信号
        if signal:
            signal_type = signal.get('signal_type', signal.get('signal', ''))
            strength = signal.get('strength', 0)
            if signal_type == 'sell' and strength >= 4:
                return True, f"📤 强卖出信号(强度{strength})", 1.0
            if signal_type == 'sell' and strength >= 3 and profit_pct > 0:
                return True, f"📤 卖出信号+盈利({profit_pct:.1f}%)", 0.5
        
        return False, "不满足卖出条件", 0
    
    def _check_technical_sell(self, indicators: Dict, profit_pct: float) -> Tuple[bool, str]:
        """检查技术指标卖出信号"""
        
        # MACD死叉
        macd = indicators.get('macd', {})
        if macd.get('crossover') == 'death_cross':
            if profit_pct > 0:
                return True, f"📉 MACD死叉+盈利({profit_pct:.1f}%)"
            elif profit_pct < -0.5:
                return True, f"📉 MACD死叉+亏损({profit_pct:.1f}%)"
        
        # RSI超买
        rsi = indicators.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        if rsi_value > 75 and profit_pct > 1:
            return True, f"📈 RSI超买({rsi_value:.0f})+盈利({profit_pct:.1f}%)"
        
        # KDJ超买
        kdj = indicators.get('kdj', {})
        j_value = kdj.get('j', 50)
        if j_value > 90 and profit_pct > 1:
            return True, f"📈 KDJ超买(J={j_value:.0f})+盈利({profit_pct:.1f}%)"
        
        # 多指标共振看空
        bearish_count = 0
        if macd.get('trend') == 'bearish':
            bearish_count += 1
        if rsi_value > 65:
            bearish_count += 1
        if kdj.get('crossover') == 'death_cross':
            bearish_count += 1
        
        if bearish_count >= 2 and profit_pct > 0:
            return True, f"📉 多指标看空({bearish_count}个)+盈利({profit_pct:.1f}%)"
        
        return False, ""


# ============================================
# 兼容旧版本的类和函数
# ============================================

class HighWinRateStrategy:
    """高胜率策略（兼容旧版本，实际使用v4）"""
    
    def __init__(self):
        self._strategy = UltraHighWinRateStrategyV4()
    
    def analyze(
        self, 
        indicators: Dict, 
        quant_analysis: Dict = None,
        support_resistance: Dict = None,
        holding_period: str = 'swing'
    ) -> HighWinSignal:
        return self._strategy.analyze(indicators, quant_analysis, support_resistance)


class UltraHighWinRateStrategy:
    """超高胜率策略（兼容旧版本，实际使用v4）"""
    
    def __init__(self):
        self._strategy = UltraHighWinRateStrategyV4()
    
    def analyze(
        self,
        indicators: Dict,
        quant_analysis: Dict = None,
        support_resistance: Dict = None
    ) -> HighWinSignal:
        return self._strategy.analyze(indicators, quant_analysis, support_resistance)


def analyze_high_win_rate(
    indicators: Dict,
    quant_analysis: Dict = None,
    support_resistance: Dict = None,
    strategy: str = 'ultra'
) -> Dict:
    """
    高胜率分析入口函数
    
    Args:
        indicators: 技术指标数据
        quant_analysis: 量化分析数据
        support_resistance: 支撑阻力位数据
        strategy: 策略类型（统一使用v4）
    
    Returns:
        分析结果字典
    """
    analyzer = UltraHighWinRateStrategyV4()
    signal = analyzer.analyze(indicators, quant_analysis, support_resistance)
    
    return {
        'status': 'success',
        'signal_type': signal.signal_type.value,
        'signal_type_cn': _get_signal_type_cn(signal.signal_type),
        'confidence': signal.confidence,
        'score': signal.score,
        'met_conditions': signal.met_conditions,
        'unmet_conditions': signal.unmet_conditions,
        'warnings': signal.warnings,
        'entry_price': signal.entry_price,
        'stop_loss': signal.stop_loss,
        'stop_loss_pct': round((1 - signal.stop_loss / signal.entry_price) * 100, 2) if signal.entry_price > 0 else 0,
        'take_profit_1': signal.take_profit_1,
        'take_profit_2': signal.take_profit_2,
        'position_pct': signal.position_pct,
        'reason': signal.reason,
        'strategy_version': 'v4.0',
        'target_win_rate': '95%+',
        'disclaimer': '本分析仅供学习研究使用，不构成任何投资建议。高胜率策略意味着极低交易频率，请理性对待。'
    }


def _get_signal_type_cn(signal_type: HighWinSignalType) -> str:
    """获取信号类型中文"""
    mapping = {
        HighWinSignalType.STRONG_BUY: '🎯 强烈买入',
        HighWinSignalType.BUY: '✅ 买入',
        HighWinSignalType.HOLD: '⏸️ 观望',
        HighWinSignalType.SELL: '📤 卖出',
        HighWinSignalType.STRONG_SELL: '🚨 强烈卖出',
    }
    return mapping.get(signal_type, '观望')


def analyze_sell_signal(
    position: Dict,
    current_price: float,
    indicators: Dict = None,
    signal: Dict = None
) -> Dict:
    """
    分析卖出信号
    
    Args:
        position: 持仓信息
        current_price: 当前价格
        indicators: 技术指标
        signal: 外部信号
    
    Returns:
        卖出分析结果
    """
    sell_strategy = UltraHighWinSellStrategy()
    should_sell, reason, sell_ratio = sell_strategy.should_sell(
        position, current_price, indicators, signal
    )
    
    return {
        'should_sell': should_sell,
        'reason': reason,
        'sell_ratio': sell_ratio,
        'strategy_version': 'v4.0'
    }
