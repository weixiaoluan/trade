"""
============================================
动态风控模块 v5.0
Dynamic Risk Control Module
============================================

核心优化：
1. ATR 动态风控 - 根据市场波动率自适应调整止损止盈
2. 金字塔式分仓策略 - 分批建仓，降低成本，提高胜率
3. 移动止盈 (Trailing Stop) - 让利润奔跑，锁定收益

原理：
- 止损位：Price - (n × ATR)，市场安静时缩小止损，市场狂躁时扩大止损
- 支撑位判断：使用 ≤ 0.5 × ATR 替代固定百分比
- 移动止盈：利润达到阈值后，从最高点回撤一定比例时卖出

注意：本模块仅供学习研究使用，不构成任何投资建议。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import math


class PositionPhase(Enum):
    """仓位阶段"""
    INITIAL = "initial"           # 初始建仓（底仓）
    PULLBACK_ADD = "pullback_add" # 回调加仓
    BREAKOUT_ADD = "breakout_add" # 突破加仓
    FULL = "full"                 # 满仓


class ExitReason(Enum):
    """退出原因"""
    STOP_LOSS = "stop_loss"                   # 固定止损
    TRAILING_STOP = "trailing_stop"           # 移动止损
    TAKE_PROFIT_PARTIAL = "take_profit_partial"  # 部分止盈
    TAKE_PROFIT_FULL = "take_profit_full"     # 全部止盈
    TIME_STOP = "time_stop"                   # 时间止损
    PROFIT_PROTECTION = "profit_protection"   # 利润回吐保护
    SIGNAL_EXIT = "signal_exit"               # 信号退出


@dataclass
class ATRConfig:
    """ATR 动态风控配置"""
    # ATR 倍数配置（按持有周期）
    stop_loss_atr_multiplier: Dict[str, float] = field(default_factory=lambda: {
        'short': 1.5,   # 短线止损：1.5倍ATR
        'swing': 2.0,   # 波段止损：2倍ATR
        'long': 2.5,    # 中长线止损：2.5倍ATR
    })
    
    # 移动止盈配置
    trailing_activation_atr: float = 3.0    # 利润达到3倍ATR时激活移动止盈
    trailing_stop_atr: float = 1.0          # 从最高点回撤1倍ATR时止盈
    
    # 支撑位判断配置
    support_distance_atr: float = 0.5       # 距离支撑位 ≤ 0.5倍ATR 视为接近支撑
    resistance_distance_atr: float = 1.0    # 距离阻力位 < 1倍ATR 视为接近阻力
    
    # 最大最小止损限制（防止极端情况）
    min_stop_loss_pct: float = 1.0          # 最小止损1%
    max_stop_loss_pct: float = 8.0          # 最大止损8%


@dataclass
class PyramidConfig:
    """金字塔式分仓配置"""
    # 分仓比例配置
    initial_position_pct: float = 5.0       # 初始建仓：5%仓位（底仓）
    pullback_add_pct: float = 10.0          # 回调加仓：10%仓位
    breakout_add_pct: float = 5.0           # 突破加仓：5%仓位（剩余）
    
    # 触发条件
    initial_min_score: int = 75             # 初始建仓最低评分
    pullback_add_min_score: int = 90        # 回调加仓最低评分
    
    # 加仓条件
    pullback_not_broken: bool = True        # 回调未破位才加仓
    breakout_confirmed: bool = True         # 突破确认后加仓
    
    # 最大仓位限制
    max_single_position_pct: float = 20.0   # 单只标的最大仓位20%
    max_total_position_pct: float = 60.0    # 总仓位最大60%


@dataclass
class TrailingStopConfig:
    """移动止盈配置"""
    # 激活阈值（使用ATR倍数或固定百分比）
    activation_profit_pct: float = 3.0      # 利润达到3%时激活
    activation_profit_atr: float = 3.0      # 或利润达到3倍ATR时激活
    
    # 回撤卖出阈值
    trailing_drawdown_pct: float = 1.0      # 从最高点回撤1%时卖出
    trailing_drawdown_atr: float = 0.5      # 或从最高点回撤0.5倍ATR时卖出
    
    # 使用ATR还是固定百分比
    use_atr: bool = True                    # 默认使用ATR动态计算


class DynamicRiskManager:
    """
    动态风控管理器 v5.0
    
    核心功能：
    1. ATR 动态止损止盈计算
    2. 金字塔式分仓策略
    3. 移动止盈机制
    4. 动态支撑阻力位判断
    """
    
    def __init__(self, atr_config: ATRConfig = None, 
                 pyramid_config: PyramidConfig = None,
                 trailing_config: TrailingStopConfig = None):
        self.atr_config = atr_config or ATRConfig()
        self.pyramid_config = pyramid_config or PyramidConfig()
        self.trailing_config = trailing_config or TrailingStopConfig()
    
    def calculate_dynamic_stop_loss(
        self,
        entry_price: float,
        atr_value: float,
        holding_period: str = 'swing',
        support_price: float = None
    ) -> Tuple[float, float]:
        """
        计算动态止损位
        
        Args:
            entry_price: 入场价格
            atr_value: ATR值
            holding_period: 持有周期 (short/swing/long)
            support_price: 支撑位价格（可选）
        
        Returns:
            (止损价格, 止损百分比)
        """
        # 获取ATR倍数
        atr_multiplier = self.atr_config.stop_loss_atr_multiplier.get(
            holding_period, 2.0
        )
        
        # 基于ATR计算止损
        atr_stop_loss = entry_price - (atr_multiplier * atr_value)
        
        # 如果有支撑位，取支撑位下方一定距离
        if support_price and support_price > 0:
            support_stop_loss = support_price - (0.5 * atr_value)
            # 取较高的止损位（更保守）
            atr_stop_loss = max(atr_stop_loss, support_stop_loss)
        
        # 计算止损百分比
        stop_loss_pct = (entry_price - atr_stop_loss) / entry_price * 100
        
        # 限制在合理范围内
        min_pct = self.atr_config.min_stop_loss_pct
        max_pct = self.atr_config.max_stop_loss_pct
        
        if stop_loss_pct < min_pct:
            stop_loss_pct = min_pct
            atr_stop_loss = entry_price * (1 - min_pct / 100)
        elif stop_loss_pct > max_pct:
            stop_loss_pct = max_pct
            atr_stop_loss = entry_price * (1 - max_pct / 100)
        
        return round(atr_stop_loss, 4), round(stop_loss_pct, 2)

    
    def check_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,
        atr_value: float
    ) -> Tuple[bool, str, float]:
        """
        检查移动止盈
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            highest_price: 持仓期间最高价
            atr_value: ATR值
        
        Returns:
            (是否触发, 原因, 卖出比例)
        """
        if highest_price <= entry_price:
            return False, "", 0
        
        profit_pct = (current_price / entry_price - 1) * 100
        max_profit_pct = (highest_price / entry_price - 1) * 100
        
        # 计算激活阈值
        if self.trailing_config.use_atr and atr_value > 0:
            activation_threshold = (self.trailing_config.activation_profit_atr * atr_value / entry_price) * 100
            drawdown_threshold = (self.trailing_config.trailing_drawdown_atr * atr_value / highest_price) * 100
        else:
            activation_threshold = self.trailing_config.activation_profit_pct
            drawdown_threshold = self.trailing_config.trailing_drawdown_pct
        
        # 检查是否激活移动止盈
        if max_profit_pct < activation_threshold:
            return False, "", 0
        
        # 计算从最高点的回撤
        drawdown_from_high = (highest_price - current_price) / highest_price * 100
        
        # 触发移动止盈
        if drawdown_from_high >= drawdown_threshold:
            return True, f"🎯 移动止盈触发(最高盈利{max_profit_pct:.1f}%，回撤{drawdown_from_high:.1f}%)", 1.0
        
        return False, "", 0
    
    def check_exit_conditions(
        self,
        position: Dict,
        current_price: float,
        atr_value: float,
        holding_period: str = 'swing',
        signal: Dict = None
    ) -> Tuple[bool, ExitReason, str, float]:
        """
        综合检查所有退出条件
        
        Args:
            position: 持仓信息
            current_price: 当前价格
            atr_value: ATR值
            holding_period: 持有周期
            signal: 交易信号（可选）
        
        Returns:
            (是否退出, 退出原因枚举, 原因描述, 卖出比例)
        """
        entry_price = position.get('cost_price', 0)
        highest_price = position.get('highest_price', entry_price)
        sold_ratio = position.get('sold_ratio', 0)
        
        if entry_price <= 0:
            return False, None, "", 0
        
        profit_pct = (current_price / entry_price - 1) * 100
        
        # 1. 动态止损检查
        stop_loss_price, stop_loss_pct = self.calculate_dynamic_stop_loss(
            entry_price, atr_value, holding_period
        )
        
        if current_price <= stop_loss_price:
            return True, ExitReason.STOP_LOSS, f"🚨 动态止损(亏损{abs(profit_pct):.1f}%，ATR止损位{stop_loss_price:.3f})", 1.0
        
        # 2. 移动止盈检查
        trailing_triggered, trailing_reason, trailing_ratio = self.check_trailing_stop(
            entry_price, current_price, highest_price, atr_value
        )
        if trailing_triggered:
            return True, ExitReason.TRAILING_STOP, trailing_reason, trailing_ratio
        
        # 3. 利润回吐保护
        max_profit_pct = (highest_price / entry_price - 1) * 100
        if max_profit_pct >= 2 and profit_pct <= 0.5:
            return True, ExitReason.PROFIT_PROTECTION, f"🚨 利润回吐保护(曾盈利{max_profit_pct:.1f}%，现{profit_pct:.1f}%)", 1.0
        
        # 4. 时间止损
        buy_date_str = position.get('buy_date', '')
        if buy_date_str:
            try:
                buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
                beijing_tz = timezone(timedelta(hours=8))
                today = datetime.now(beijing_tz).replace(tzinfo=None)
                holding_days = (today - buy_date).days
                
                max_days = {'short': 3, 'swing': 7, 'long': 15}.get(holding_period, 7)
                if holding_days >= max_days and profit_pct <= 0:
                    return True, ExitReason.TIME_STOP, f"⏰ 时间止损(持有{holding_days}天未盈利)", 1.0
            except:
                pass
        
        # 5. 信号退出
        if signal:
            signal_type = signal.get('signal_type', signal.get('signal', ''))
            strength = signal.get('strength', 0)
            if signal_type == 'sell' and strength >= 4:
                return True, ExitReason.SIGNAL_EXIT, f"📤 强卖出信号(强度{strength})", 1.0
            if signal_type == 'sell' and strength >= 3 and profit_pct > 0:
                return True, ExitReason.SIGNAL_EXIT, f"📤 卖出信号+盈利({profit_pct:.1f}%)", 0.5
        
        return False, None, "", 0

    
    def is_near_support(
        self,
        current_price: float,
        support_price: float,
        atr_value: float
    ) -> Tuple[bool, float]:
        """
        判断是否接近支撑位（使用ATR动态判断）
        
        Args:
            current_price: 当前价格
            support_price: 支撑位价格
            atr_value: ATR值
        
        Returns:
            (是否接近支撑, 距离ATR倍数)
        """
        if support_price <= 0 or atr_value <= 0:
            return False, float('inf')
        
        distance = current_price - support_price
        distance_atr = distance / atr_value
        
        threshold = self.atr_config.support_distance_atr
        return distance_atr <= threshold, round(distance_atr, 2)
    
    def is_near_resistance(
        self,
        current_price: float,
        resistance_price: float,
        atr_value: float
    ) -> Tuple[bool, float]:
        """
        判断是否接近阻力位（使用ATR动态判断）
        
        Args:
            current_price: 当前价格
            resistance_price: 阻力位价格
            atr_value: ATR值
        
        Returns:
            (是否接近阻力, 距离ATR倍数)
        """
        if resistance_price <= 0 or atr_value <= 0:
            return False, float('inf')
        
        distance = resistance_price - current_price
        distance_atr = distance / atr_value
        
        threshold = self.atr_config.resistance_distance_atr
        return distance_atr < threshold, round(distance_atr, 2)


class PyramidPositionManager:
    """
    金字塔式分仓管理器
    
    策略：
    1. 信号触发（Score 75+）：先买入 5% 仓位（底仓）
    2. 价格回撤但未破位（Score 90+）：再买入 10% 仓位（拉低均价）
    3. 价格确认上涨（突破）：最后买入剩余仓位
    """
    
    def __init__(self, config: PyramidConfig = None):
        self.config = config or PyramidConfig()
    
    def calculate_initial_position(
        self,
        total_assets: float,
        available_capital: float,
        price: float,
        score: int,
        confidence: float
    ) -> Tuple[int, float, str]:
        """
        计算初始建仓数量（底仓）
        
        Args:
            total_assets: 总资产
            available_capital: 可用资金
            price: 当前价格
            score: 信号评分
            confidence: 置信度
        
        Returns:
            (买入数量, 仓位占比, 建仓阶段说明)
        """
        # 检查评分门槛
        if score < self.config.initial_min_score:
            return 0, 0, f"评分不足({score}<{self.config.initial_min_score})，暂不建仓"
        
        # 计算初始仓位
        position_pct = self.config.initial_position_pct
        
        # 根据置信度微调
        if confidence >= 90:
            position_pct *= 1.2
        elif confidence < 80:
            position_pct *= 0.8
        
        # 计算买入金额
        buy_amount = total_assets * (position_pct / 100)
        buy_amount = min(buy_amount, available_capital)
        
        # 计算买入数量（A股最小单位100股）
        quantity = int(buy_amount / price / 100) * 100
        
        if quantity < 100:
            return 0, 0, "资金不足建仓"
        
        actual_pct = (quantity * price) / total_assets * 100
        return quantity, round(actual_pct, 2), f"初始建仓(底仓{actual_pct:.1f}%)"

    
    def calculate_pullback_add(
        self,
        position: Dict,
        total_assets: float,
        available_capital: float,
        current_price: float,
        score: int,
        atr_value: float,
        support_price: float = None
    ) -> Tuple[int, float, str]:
        """
        计算回调加仓数量
        
        条件：
        1. 价格回撤但未破位
        2. 评分达到90+
        3. 当前仓位未达上限
        
        Args:
            position: 当前持仓信息
            total_assets: 总资产
            available_capital: 可用资金
            current_price: 当前价格
            score: 信号评分
            atr_value: ATR值
            support_price: 支撑位价格
        
        Returns:
            (加仓数量, 仓位占比, 加仓说明)
        """
        cost_price = position.get('cost_price', 0)
        current_quantity = position.get('quantity', 0)
        add_count = position.get('add_count', 0)
        
        # 检查评分门槛
        if score < self.config.pullback_add_min_score:
            return 0, 0, f"评分不足({score}<{self.config.pullback_add_min_score})，暂不加仓"
        
        # 检查是否已加仓过
        if add_count >= 1:
            return 0, 0, "已完成回调加仓，不再加仓"
        
        # 检查是否回调（当前价格低于成本价）
        if current_price >= cost_price:
            return 0, 0, "价格未回调，等待回调机会"
        
        # 检查是否破位（跌破支撑位）
        if support_price and support_price > 0:
            if current_price < support_price - (0.5 * atr_value):
                return 0, 0, "价格已破位，不宜加仓"
        
        # 检查当前仓位
        current_position_value = current_quantity * current_price
        current_position_pct = current_position_value / total_assets * 100
        
        if current_position_pct >= self.config.max_single_position_pct:
            return 0, 0, f"仓位已达上限({current_position_pct:.1f}%)"
        
        # 计算加仓数量
        add_pct = self.config.pullback_add_pct
        remaining_pct = self.config.max_single_position_pct - current_position_pct
        add_pct = min(add_pct, remaining_pct)
        
        add_amount = total_assets * (add_pct / 100)
        add_amount = min(add_amount, available_capital)
        
        add_quantity = int(add_amount / current_price / 100) * 100
        
        if add_quantity < 100:
            return 0, 0, "资金不足加仓"
        
        actual_pct = (add_quantity * current_price) / total_assets * 100
        
        # 计算加仓后的新均价
        new_total_cost = (cost_price * current_quantity) + (current_price * add_quantity)
        new_total_quantity = current_quantity + add_quantity
        new_avg_price = new_total_cost / new_total_quantity
        
        return add_quantity, round(actual_pct, 2), f"回调加仓(+{actual_pct:.1f}%，均价从{cost_price:.3f}降至{new_avg_price:.3f})"
    
    def calculate_breakout_add(
        self,
        position: Dict,
        total_assets: float,
        available_capital: float,
        current_price: float,
        resistance_price: float,
        atr_value: float
    ) -> Tuple[int, float, str]:
        """
        计算突破加仓数量
        
        条件：
        1. 价格突破阻力位
        2. 当前仓位未达上限
        
        Args:
            position: 当前持仓信息
            total_assets: 总资产
            available_capital: 可用资金
            current_price: 当前价格
            resistance_price: 阻力位价格
            atr_value: ATR值
        
        Returns:
            (加仓数量, 仓位占比, 加仓说明)
        """
        current_quantity = position.get('quantity', 0)
        add_count = position.get('add_count', 0)
        
        # 检查是否已加仓两次
        if add_count >= 2:
            return 0, 0, "已完成所有加仓"
        
        # 检查是否突破阻力位
        if resistance_price and resistance_price > 0:
            breakout_threshold = resistance_price + (0.3 * atr_value)
            if current_price < breakout_threshold:
                return 0, 0, "尚未确认突破阻力位"
        else:
            return 0, 0, "缺少阻力位数据"
        
        # 检查当前仓位
        current_position_value = current_quantity * current_price
        current_position_pct = current_position_value / total_assets * 100
        
        if current_position_pct >= self.config.max_single_position_pct:
            return 0, 0, f"仓位已达上限({current_position_pct:.1f}%)"
        
        # 计算加仓数量
        add_pct = self.config.breakout_add_pct
        remaining_pct = self.config.max_single_position_pct - current_position_pct
        add_pct = min(add_pct, remaining_pct)
        
        add_amount = total_assets * (add_pct / 100)
        add_amount = min(add_amount, available_capital)
        
        add_quantity = int(add_amount / current_price / 100) * 100
        
        if add_quantity < 100:
            return 0, 0, "资金不足加仓"
        
        actual_pct = (add_quantity * current_price) / total_assets * 100
        return add_quantity, round(actual_pct, 2), f"突破加仓(+{actual_pct:.1f}%，确认突破{resistance_price:.3f})"


class DynamicSignalScorer:
    """
    动态信号评分器
    
    使用ATR标准化距离计算，替代固定百分比
    """
    
    def __init__(self, risk_manager: DynamicRiskManager = None):
        self.risk_manager = risk_manager or DynamicRiskManager()
    
    def calculate_score(
        self,
        current_price: float,
        support_price: float,
        resistance_price: float,
        atr_value: float,
        indicators: Dict = None,
        quant_analysis: Dict = None
    ) -> Tuple[int, float, List[str]]:
        """
        计算综合评分（使用ATR动态标准化）
        
        Args:
            current_price: 当前价格
            support_price: 支撑位价格
            resistance_price: 阻力位价格
            atr_value: ATR值
            indicators: 技术指标数据
            quant_analysis: 量化分析数据
        
        Returns:
            (评分0-100, 置信度0-100, 评分条件列表)
        """
        score = 0
        conditions = []
        
        if atr_value <= 0:
            atr_value = current_price * 0.02  # 默认2%波动率
        
        # 1. 距离支撑位评分（使用ATR倍数）
        if support_price and support_price > 0:
            dist_to_support = (current_price - support_price) / atr_value
            
            if dist_to_support <= 0.5:
                # 非常接近支撑位（0.5倍ATR内）
                score += 25
                conditions.append(f"✅ 极接近支撑位({dist_to_support:.1f}倍ATR)(+25)")
            elif dist_to_support <= 1.0:
                # 接近支撑位（1倍ATR内）
                score += 15
                conditions.append(f"✅ 接近支撑位({dist_to_support:.1f}倍ATR)(+15)")
            elif dist_to_support <= 2.0:
                # 较接近支撑位（2倍ATR内）
                score += 8
                conditions.append(f"⚠️ 距支撑位较近({dist_to_support:.1f}倍ATR)(+8)")
            else:
                # 远离支撑位
                conditions.append(f"❌ 远离支撑位({dist_to_support:.1f}倍ATR)")
        
        # 2. 距离阻力位评分（使用ATR倍数）
        if resistance_price and resistance_price > 0:
            dist_to_resistance = (resistance_price - current_price) / atr_value
            
            if dist_to_resistance < 1.0:
                # 太接近阻力位，扣分
                score -= 15
                conditions.append(f"❌ 太接近阻力位({dist_to_resistance:.1f}倍ATR)(-15)")
            elif dist_to_resistance >= 3.0:
                # 远离阻力位，加分
                score += 10
                conditions.append(f"✅ 远离阻力位({dist_to_resistance:.1f}倍ATR)(+10)")
            elif dist_to_resistance >= 2.0:
                score += 5
                conditions.append(f"✅ 阻力位较远({dist_to_resistance:.1f}倍ATR)(+5)")
        
        # 3. 技术指标评分
        if indicators:
            indicator_score, indicator_conditions = self._score_indicators(indicators)
            score += indicator_score
            conditions.extend(indicator_conditions)
        
        # 4. 量化评分
        if quant_analysis:
            quant_score = quant_analysis.get('quant_score', 50)
            if quant_score >= 70:
                score += 15
                conditions.append(f"✅ 量化评分优秀({quant_score:.0f})(+15)")
            elif quant_score >= 60:
                score += 10
                conditions.append(f"✅ 量化评分良好({quant_score:.0f})(+10)")
            elif quant_score >= 50:
                score += 5
                conditions.append(f"⚠️ 量化评分中等({quant_score:.0f})(+5)")
            elif quant_score < 40:
                score -= 10
                conditions.append(f"❌ 量化评分较低({quant_score:.0f})(-10)")
        
        # 5. 量价配合评分
        if indicators:
            volume_score, volume_conditions = self._score_volume(indicators, current_price)
            score += volume_score
            conditions.extend(volume_conditions)
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        # 计算置信度
        confidence = self._calculate_confidence(score, len(conditions))
        
        return score, confidence, conditions

    
    def _score_indicators(self, indicators: Dict) -> Tuple[int, List[str]]:
        """评分技术指标"""
        score = 0
        conditions = []
        
        # 均线系统
        ma_trend = indicators.get('ma_trend', '')
        if ma_trend == 'bullish_alignment':
            score += 15
            conditions.append("✅ 均线多头排列(+15)")
        elif ma_trend == 'bearish_alignment':
            score -= 15
            conditions.append("❌ 均线空头排列(-15)")
        
        # MACD
        macd = indicators.get('macd', {})
        if macd.get('crossover') == 'golden_cross':
            score += 10
            conditions.append("✅ MACD金叉(+10)")
        elif macd.get('crossover') == 'death_cross':
            score -= 10
            conditions.append("❌ MACD死叉(-10)")
        elif macd.get('trend') == 'bullish':
            score += 5
            conditions.append("✅ MACD多头(+5)")
        
        # RSI
        rsi = indicators.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        if rsi.get('status') == 'oversold' or rsi_value < 35:
            score += 10
            conditions.append(f"✅ RSI超卖({rsi_value:.0f})(+10)")
        elif rsi.get('status') == 'overbought' or rsi_value > 70:
            score -= 10
            conditions.append(f"❌ RSI超买({rsi_value:.0f})(-10)")
        elif 35 <= rsi_value <= 50:
            score += 5
            conditions.append(f"✅ RSI回调区间({rsi_value:.0f})(+5)")
        
        # KDJ
        kdj = indicators.get('kdj', {})
        if kdj.get('crossover') == 'golden_cross':
            score += 8
            conditions.append("✅ KDJ金叉(+8)")
        elif kdj.get('crossover') == 'death_cross':
            score -= 8
            conditions.append("❌ KDJ死叉(-8)")
        if kdj.get('status') == 'oversold':
            score += 5
            conditions.append("✅ KDJ超卖(+5)")
        
        # ADX趋势强度
        adx = indicators.get('adx', {})
        if adx.get('trend_strength') == 'strong' and adx.get('trend_direction') == 'bullish':
            score += 10
            conditions.append(f"✅ ADX强势上涨({adx.get('adx', 0):.0f})(+10)")
        
        return score, conditions
    
    def _score_volume(self, indicators: Dict, current_price: float) -> Tuple[int, List[str]]:
        """评分量价配合"""
        score = 0
        conditions = []
        
        vol = indicators.get('volume_analysis', {})
        vol_ratio = vol.get('volume_ratio', 1)
        vol_status = vol.get('status', 'normal')
        price_change = indicators.get('price_change_pct', 0)
        
        # 放量上涨
        if vol_status == 'high_volume' and vol_ratio > 1.5 and price_change > 0:
            score += 10
            conditions.append(f"✅ 放量上涨({vol_ratio:.1f}倍)(+10)")
        # 缩量回调（健康回调）
        elif vol_status == 'low_volume' and price_change < 0:
            score += 5
            conditions.append(f"✅ 缩量回调({vol_ratio:.1f}倍)(+5)")
        # 放量下跌（危险信号）
        elif vol_status == 'high_volume' and vol_ratio > 1.5 and price_change < -1.5:
            score -= 15
            conditions.append(f"❌ 放量下跌({vol_ratio:.1f}倍)(-15)")
        
        return score, conditions
    
    def _calculate_confidence(self, score: int, conditions_count: int) -> float:
        """计算置信度"""
        # 基础置信度 = 分数
        confidence = score
        
        # 条件数量加成
        if conditions_count >= 8:
            confidence += 5
        elif conditions_count >= 6:
            confidence += 3
        
        return min(99, max(0, confidence))


# ============================================
# 便捷函数
# ============================================

def calculate_dynamic_stop_loss(
    entry_price: float,
    atr_value: float,
    holding_period: str = 'swing',
    support_price: float = None
) -> Tuple[float, float]:
    """计算动态止损位（便捷函数）"""
    manager = DynamicRiskManager()
    return manager.calculate_dynamic_stop_loss(entry_price, atr_value, holding_period, support_price)


def check_trailing_stop(
    entry_price: float,
    current_price: float,
    highest_price: float,
    atr_value: float
) -> Tuple[bool, str, float]:
    """检查移动止盈（便捷函数）"""
    manager = DynamicRiskManager()
    return manager.check_trailing_stop(entry_price, current_price, highest_price, atr_value)


def calculate_pyramid_position(
    total_assets: float,
    available_capital: float,
    price: float,
    score: int,
    confidence: float,
    position: Dict = None,
    atr_value: float = None,
    support_price: float = None,
    resistance_price: float = None
) -> Tuple[int, float, str, str]:
    """
    计算金字塔式建仓数量（便捷函数）
    
    Returns:
        (买入数量, 仓位占比, 建仓阶段, 说明)
    """
    manager = PyramidPositionManager()
    
    if position is None:
        # 初始建仓
        quantity, pct, reason = manager.calculate_initial_position(
            total_assets, available_capital, price, score, confidence
        )
        return quantity, pct, PositionPhase.INITIAL.value, reason
    
    # 检查加仓条件
    add_count = position.get('add_count', 0)
    
    if add_count == 0 and atr_value:
        # 尝试回调加仓
        quantity, pct, reason = manager.calculate_pullback_add(
            position, total_assets, available_capital, price, score, atr_value, support_price
        )
        if quantity > 0:
            return quantity, pct, PositionPhase.PULLBACK_ADD.value, reason
    
    if add_count <= 1 and atr_value and resistance_price:
        # 尝试突破加仓
        quantity, pct, reason = manager.calculate_breakout_add(
            position, total_assets, available_capital, price, resistance_price, atr_value
        )
        if quantity > 0:
            return quantity, pct, PositionPhase.BREAKOUT_ADD.value, reason
    
    return 0, 0, PositionPhase.FULL.value, "不满足加仓条件"


def calculate_dynamic_score(
    current_price: float,
    support_price: float,
    resistance_price: float,
    atr_value: float,
    indicators: Dict = None,
    quant_analysis: Dict = None
) -> Tuple[int, float, List[str]]:
    """计算动态评分（便捷函数）"""
    scorer = DynamicSignalScorer()
    return scorer.calculate_score(
        current_price, support_price, resistance_price, atr_value, indicators, quant_analysis
    )


# ============================================
# 导出
# ============================================

__all__ = [
    'ATRConfig',
    'PyramidConfig', 
    'TrailingStopConfig',
    'PositionPhase',
    'ExitReason',
    'DynamicRiskManager',
    'PyramidPositionManager',
    'DynamicSignalScorer',
    'calculate_dynamic_stop_loss',
    'check_trailing_stop',
    'calculate_pyramid_position',
    'calculate_dynamic_score',
]
