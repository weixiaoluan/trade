"""
============================================
模拟交易引擎 v5.0 - 动态风控版本
Simulated Trading Engine - Dynamic Risk Control
============================================

专业级模拟交易系统，目标95%+胜率

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

风控机制：
- 动态止损：基于ATR计算，短线1.5倍ATR，波段2倍ATR，中长线2.5倍ATR
- 移动止盈：利润达到3倍ATR后激活，从高点回撤0.5倍ATR时止盈
- 利润回吐保护：曾盈利2%以上，回到成本价附近止损
- 时间止损：持有超时且未盈利则平仓

注意：本模块仅供学习研究使用，不构成任何投资建议。
模拟交易结果不代表真实交易表现。
高胜率策略意味着极低交易频率，可能错过很多机会。
"""

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from web.database import (
    db_get_sim_account, db_create_sim_account, db_update_sim_account,
    db_get_sim_positions, db_get_sim_position, db_add_sim_position,
    db_update_sim_position, db_remove_sim_position,
    db_add_sim_trade_record, db_get_sim_trade_records, db_get_sim_trade_stats,
    get_trade_rule, db_get_user_watchlist
)

# 导入动态风控模块
from web.dynamic_risk_control import (
    DynamicRiskManager, PyramidPositionManager, DynamicSignalScorer,
    ATRConfig, PyramidConfig, TrailingStopConfig,
    PositionPhase, ExitReason,
    calculate_dynamic_stop_loss, check_trailing_stop, calculate_pyramid_position
)


# ============================================
# 常量配置
# ============================================

# 仓位管理配置 - v5.0 动态风控版本
# 核心理念：金字塔式分仓，动态调整
POSITION_CONFIG = {
    'max_single_position': 0.20,      # 单只标的最大仓位 20%（金字塔式分仓后提高）
    'max_total_position': 0.60,       # 最大总仓位 60%
    'min_position_size': 0.03,        # 最小仓位 3%
    'default_position_size': 0.05,    # 默认初始仓位 5%（底仓）
    'pyramid_ratio': 0.5,             # 金字塔加仓比例
    # 金字塔式分仓配置
    'initial_position': 0.05,         # 初始建仓 5%（底仓）
    'pullback_add': 0.10,             # 回调加仓 10%
    'breakout_add': 0.05,             # 突破加仓 5%
}

# 风控配置（按持有周期）- v5.0 动态风控版本
# 核心理念：ATR动态止损止盈
RISK_CONFIG = {
    'short': {
        'stop_loss_atr': 1.5,         # 止损 1.5倍ATR
        'trailing_activation_atr': 3.0,  # 移动止盈激活 3倍ATR
        'trailing_stop_atr': 0.5,     # 移动止损回撤 0.5倍ATR
        'max_holding_days': 5,        # 最大持有天数
        # 备用固定百分比（ATR数据缺失时使用）
        'stop_loss': -0.02,           # 止损 -2%
        'take_profit_1': 0.03,        # 第一止盈 3%
        'take_profit_2': 0.05,        # 第二止盈 5%
        'take_profit_3': 0.08,        # 第三止盈 8%
        'trailing_stop': 0.01,        # 移动止损回撤 1%
    },
    'swing': {
        'stop_loss_atr': 2.0,         # 止损 2倍ATR
        'trailing_activation_atr': 3.0,  # 移动止盈激活 3倍ATR
        'trailing_stop_atr': 0.5,     # 移动止损回撤 0.5倍ATR
        'max_holding_days': 10,       # 最大持有天数
        # 备用固定百分比
        'stop_loss': -0.03,           # 止损 -3%
        'take_profit_1': 0.05,        # 第一止盈 5%
        'take_profit_2': 0.08,        # 第二止盈 8%
        'take_profit_3': 0.12,        # 第三止盈 12%
        'trailing_stop': 0.015,       # 移动止损回撤 1.5%
    },
    'long': {
        'stop_loss_atr': 2.5,         # 止损 2.5倍ATR
        'trailing_activation_atr': 3.0,  # 移动止盈激活 3倍ATR
        'trailing_stop_atr': 1.0,     # 移动止损回撤 1倍ATR
        'max_holding_days': 20,       # 最大持有天数
        # 备用固定百分比
        'stop_loss': -0.05,           # 止损 -5%
        'take_profit_1': 0.08,        # 第一止盈 8%
        'take_profit_2': 0.12,        # 第二止盈 12%
        'take_profit_3': 0.20,        # 第三止盈 20%
        'trailing_stop': 0.02,        # 移动止损回撤 2%
    }
}

# 信号强度要求 - v5.0 动态风控版本
# 核心理念：金字塔式分仓，降低入场门槛
SIGNAL_CONFIG = {
    'min_buy_strength': 3,            # 最小买入信号强度（降低，因为分仓）
    'min_sell_strength': 3,           # 最小卖出信号强度
    'min_confidence': 75,             # 最小置信度（降低，因为分仓）
    'strong_signal_strength': 5,      # 强信号强度
    # 金字塔式分仓评分要求
    'initial_min_score': 75,          # 初始建仓最低评分
    'pullback_add_min_score': 90,     # 回调加仓最低评分
}


def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def is_trading_time() -> bool:
    """判断是否为A股交易时间"""
    now = get_beijing_now()
    if now.weekday() >= 5:
        return False
    
    time_val = now.hour * 60 + now.minute
    # 上午 9:30-11:30, 下午 13:00-15:00
    return (570 <= time_val <= 690) or (780 <= time_val <= 900)


def is_trading_day() -> bool:
    """判断是否为交易日（简化版，不考虑节假日）"""
    return get_beijing_now().weekday() < 5


# ============================================
# 仓位计算器
# ============================================

class PositionCalculator:
    """仓位计算器 - 智能计算买入数量"""
    
    @staticmethod
    def calculate_position_size(
        total_assets: float,
        available_capital: float,
        price: float,
        signal_strength: int = 3,
        volatility: float = None,
        existing_position_pct: float = 0
    ) -> Tuple[int, float]:
        """计算建议买入数量
        
        Args:
            total_assets: 总资产
            available_capital: 可用资金
            price: 当前价格
            signal_strength: 信号强度 (1-5)
            volatility: 波动率（可选，用于动态调整仓位）
            existing_position_pct: 已有仓位占比
        
        Returns:
            (买入数量, 仓位占比)
        """
        # 基础仓位比例（根据信号强度调整）
        base_pct = POSITION_CONFIG['default_position_size']
        if signal_strength >= 5:
            base_pct = 0.15  # 极强信号 15%
        elif signal_strength >= 4:
            base_pct = 0.12  # 强信号 12%
        elif signal_strength >= 3:
            base_pct = 0.10  # 中等信号 10%
        else:
            base_pct = 0.08  # 弱信号 8%
        
        # 波动率调整（高波动降低仓位）
        if volatility and volatility > 0:
            if volatility > 0.03:  # 日波动>3%
                base_pct *= 0.7
            elif volatility > 0.02:  # 日波动>2%
                base_pct *= 0.85
        
        # 检查单只标的最大仓位限制
        max_position_pct = POSITION_CONFIG['max_single_position'] - existing_position_pct
        position_pct = min(base_pct, max_position_pct)
        
        # 检查可用资金限制
        max_by_capital = available_capital / total_assets
        position_pct = min(position_pct, max_by_capital)
        
        # 计算买入金额和数量
        buy_amount = total_assets * position_pct
        buy_amount = min(buy_amount, available_capital)
        
        # A股最小单位100股
        quantity = int(buy_amount / price / 100) * 100
        
        # 确保至少买100股
        if quantity < 100 and available_capital >= price * 100:
            quantity = 100
        
        actual_pct = (quantity * price) / total_assets if total_assets > 0 else 0
        
        return quantity, round(actual_pct * 100, 2)
    
    @staticmethod
    def calculate_pyramid_add(
        existing_quantity: int,
        existing_cost: float,
        current_price: float,
        available_capital: float,
        profit_pct: float
    ) -> Tuple[int, str]:
        """计算金字塔加仓数量
        
        只有盈利时才加仓，且加仓数量递减
        
        Returns:
            (加仓数量, 原因)
        """
        # 亏损不加仓
        if profit_pct < 0:
            return 0, "亏损中不加仓"
        
        # 盈利不足不加仓
        if profit_pct < 2:
            return 0, "盈利不足2%，暂不加仓"
        
        # 金字塔加仓：每次加仓为上次的50%
        add_quantity = int(existing_quantity * POSITION_CONFIG['pyramid_ratio'] / 100) * 100
        
        # 检查资金是否足够
        if add_quantity * current_price > available_capital:
            add_quantity = int(available_capital / current_price / 100) * 100
        
        if add_quantity < 100:
            return 0, "资金不足加仓"
        
        return add_quantity, f"金字塔加仓(盈利{profit_pct:.1f}%)"


# ============================================
# 风控管理器 - v5.0 动态风控版本
# ============================================

class RiskManager:
    """风控管理器 - ATR动态止损止盈、移动止盈（v5.0动态风控版本）
    
    核心理念：
    1. ATR动态止损 - 根据市场波动率自适应调整止损位
    2. 移动止盈 - 让利润奔跑，从最高点回撤时止盈
    3. 利润回吐保护 - 曾盈利后回到成本价附近止损
    """
    
    def __init__(self):
        self.dynamic_manager = DynamicRiskManager()
    
    @staticmethod
    def check_stop_loss(
        position: Dict,
        current_price: float,
        holding_period: str = 'swing',
        atr_value: float = None
    ) -> Tuple[bool, str, float]:
        """检查是否触发止损（v5.0 ATR动态版本）
        
        Args:
            position: 持仓信息
            current_price: 当前价格
            holding_period: 持有周期
            atr_value: ATR值（可选，用于动态止损）
        
        Returns:
            (是否止损, 原因, 建议卖出比例)
        """
        cost_price = position['cost_price']
        profit_pct = (current_price / cost_price - 1)
        config = RISK_CONFIG.get(holding_period, RISK_CONFIG['swing'])
        
        # 优先使用ATR动态止损
        if atr_value and atr_value > 0:
            atr_multiplier = config.get('stop_loss_atr', 2.0)
            dynamic_stop_loss = cost_price - (atr_multiplier * atr_value)
            
            if current_price <= dynamic_stop_loss:
                return True, f"🚨 ATR动态止损(亏损{profit_pct*100:.1f}%，止损位{dynamic_stop_loss:.3f})", 1.0
        else:
            # 备用：固定百分比止损
            if profit_pct <= config['stop_loss']:
                return True, f"🚨 触发止损(亏损{profit_pct*100:.1f}%)", 1.0
        
        # 移动止损（只有盈利过才触发）
        highest_price = position.get('highest_price', cost_price)
        if highest_price > cost_price:
            # 优先使用ATR动态移动止损
            if atr_value and atr_value > 0:
                trailing_atr = config.get('trailing_stop_atr', 0.5)
                trailing_stop_price = highest_price - (trailing_atr * atr_value)
                
                if current_price <= trailing_stop_price:
                    from_high_pct = (current_price / highest_price - 1) * 100
                    return True, f"🚨 ATR移动止损(从高点回撤{abs(from_high_pct):.1f}%)", 1.0
            else:
                # 备用：固定百分比移动止损
                from_high_pct = (current_price / highest_price - 1)
                if from_high_pct <= -config['trailing_stop']:
                    return True, f"🚨 移动止损(从高点回撤{abs(from_high_pct)*100:.1f}%)", 1.0
            
            # 利润回吐保护：曾经盈利超过2%，现在回到成本价附近
            max_profit_pct = (highest_price / cost_price - 1) * 100
            if max_profit_pct >= 2 and profit_pct * 100 <= 0.5:
                return True, f"🚨 利润回吐保护(曾盈利{max_profit_pct:.1f}%，现{profit_pct*100:.1f}%)", 1.0
        
        return False, "", 0
    
    @staticmethod
    def check_take_profit(
        position: Dict,
        current_price: float,
        holding_period: str = 'swing',
        signal_type: str = None,
        atr_value: float = None
    ) -> Tuple[bool, str, float]:
        """检查是否触发止盈（v5.0 移动止盈版本）
        
        核心改进：移动止盈，让利润奔跑
        - 激活阈值：利润达到 3×ATR 时触发移动止盈
        - 回撤卖出：从最高点回撤 0.5×ATR 时全部卖出
        
        Returns:
            (是否止盈, 原因, 建议卖出比例)
        """
        cost_price = position['cost_price']
        profit_pct = (current_price / cost_price - 1)
        highest_price = position.get('highest_price', cost_price)
        sold_ratio = position.get('sold_ratio', 0)
        config = RISK_CONFIG.get(holding_period, RISK_CONFIG['swing'])
        
        # 优先使用ATR动态移动止盈
        if atr_value and atr_value > 0:
            activation_atr = config.get('trailing_activation_atr', 3.0)
            trailing_atr = config.get('trailing_stop_atr', 0.5)
            
            # 计算激活阈值（利润达到 n 倍 ATR）
            activation_profit = (activation_atr * atr_value) / cost_price
            
            # 检查是否激活移动止盈
            max_profit_pct = (highest_price / cost_price - 1)
            if max_profit_pct >= activation_profit:
                # 移动止盈已激活，检查是否触发
                trailing_stop_price = highest_price - (trailing_atr * atr_value)
                
                if current_price <= trailing_stop_price:
                    from_high_pct = (current_price / highest_price - 1) * 100
                    return True, f"🎯 移动止盈触发(最高盈利{max_profit_pct*100:.1f}%，回撤{abs(from_high_pct):.1f}%)", 1.0
        
        # 备用：固定百分比分级止盈
        # 第三止盈（卖出剩余全部）
        if profit_pct >= config['take_profit_3'] and sold_ratio < 0.7:
            return True, f"🎯 第三止盈(盈利{profit_pct*100:.1f}%)", 1.0
        
        # 第二止盈（卖出50%）
        if profit_pct >= config['take_profit_2'] and sold_ratio < 0.5:
            return True, f"✅ 第二止盈(盈利{profit_pct*100:.1f}%)", 0.5
        
        # 第一止盈（卖出30%）
        if profit_pct >= config['take_profit_1'] and sold_ratio < 0.3:
            return True, f"✅ 第一止盈(盈利{profit_pct*100:.1f}%)", 0.3
        
        # 有卖出信号时，降低止盈门槛
        if signal_type == 'sell':
            if profit_pct >= config['take_profit_1'] * 0.7 and sold_ratio < 0.5:
                return True, f"✅ 卖出信号+盈利({profit_pct*100:.1f}%)", 0.5
        
        return False, "", 0
    
    @staticmethod
    def check_time_stop(
        position: Dict,
        holding_period: str = 'swing'
    ) -> Tuple[bool, str]:
        """检查是否超过最大持有时间
        
        Returns:
            (是否超时, 原因)
        """
        config = RISK_CONFIG.get(holding_period, RISK_CONFIG['swing'])
        buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
        today = get_beijing_now().replace(tzinfo=None)
        holding_days = (today - buy_date).days
        
        if holding_days >= config['max_holding_days']:
            return True, f"持有超时({holding_days}天)"
        
        return False, ""
    
    @staticmethod
    def calculate_max_drawdown(trade_records: List[Dict]) -> float:
        """计算最大回撤"""
        if not trade_records:
            return 0
        
        # 按时间排序
        sorted_records = sorted(trade_records, key=lambda x: x.get('created_at', ''))
        
        cumulative_profit = 0
        peak = 0
        max_drawdown = 0
        
        for record in sorted_records:
            if record.get('trade_type') == 'sell' and record.get('profit'):
                cumulative_profit += record['profit']
                peak = max(peak, cumulative_profit)
                drawdown = (peak - cumulative_profit) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        return round(max_drawdown * 100, 2)


# ============================================
# 信号分析器 - v5.0 动态风控版本
# ============================================

class SignalAnalyzer:
    """信号分析器 - 判断买卖时机（v5.0 动态风控版本）
    
    核心理念：
    1. ATR动态评分 - 使用ATR标准化距离判断
    2. 金字塔式分仓 - 分批建仓，降低入场门槛
    3. 动态止损止盈 - 根据市场波动率调整
    """
    
    def __init__(self):
        self.scorer = DynamicSignalScorer()
    
    @staticmethod
    def should_buy(
        signal: Dict,
        position: Dict = None,
        account: Dict = None,
        current_price: float = None,
        support_price: float = None,
        resistance_price: float = None,
        atr_value: float = None
    ) -> Tuple[bool, str, int]:
        """判断是否应该买入（v5.0 动态风控版本）
        
        使用ATR动态判断距离支撑位/阻力位的远近
        
        Returns:
            (是否买入, 原因, 建议仓位等级1-3)
        """
        signal_type = signal.get('signal_type', signal.get('signal', ''))
        strength = signal.get('strength', 0)
        confidence = signal.get('confidence', 50)
        
        # 基本条件检查
        if signal_type != 'buy':
            return False, "非买入信号", 0
        
        # 信号强度检查（金字塔式分仓降低门槛）
        if strength < SIGNAL_CONFIG['min_buy_strength']:
            return False, f"信号强度不足({strength}<{SIGNAL_CONFIG['min_buy_strength']})", 0
        
        # 置信度检查
        if confidence < SIGNAL_CONFIG['min_confidence']:
            return False, f"置信度不足({confidence}<{SIGNAL_CONFIG['min_confidence']})", 0
        
        # 使用ATR动态判断价格位置
        if atr_value and atr_value > 0:
            # ATR动态判断距离阻力位
            if current_price and resistance_price and resistance_price > 0:
                dist_to_resistance = (resistance_price - current_price) / atr_value
                if dist_to_resistance < 1.0:  # 距离阻力位不足1倍ATR
                    return False, f"太接近阻力位({dist_to_resistance:.1f}倍ATR)，不追高", 0
            
            # ATR动态判断距离支撑位
            position_level = 0
            if current_price and support_price and support_price > 0:
                dist_to_support = (current_price - support_price) / atr_value
                if dist_to_support <= 0.5:  # 非常接近支撑位（0.5倍ATR内）
                    position_level = 3  # 重仓
                elif dist_to_support <= 1.0:  # 接近支撑位（1倍ATR内）
                    position_level = 2  # 中等仓位
                elif dist_to_support <= 2.0:  # 较接近支撑位（2倍ATR内）
                    position_level = 1  # 轻仓
                else:
                    return False, f"价格远离支撑位({dist_to_support:.1f}倍ATR)，等待回调", 0
            else:
                # 没有支撑位数据，使用信号强度判断
                if strength >= 5 and confidence >= 90:
                    position_level = 1
                else:
                    return False, "缺少支撑位数据，无法确认买点", 0
        else:
            # 备用：固定百分比判断
            if current_price and resistance_price and resistance_price > 0:
                above_resistance_pct = (current_price / resistance_price - 1) * 100
                if above_resistance_pct > 0:
                    return False, f"价格高于阻力位({above_resistance_pct:.1f}%)，不追高", 0
            
            position_level = 0
            if current_price and support_price and support_price > 0:
                above_support_pct = (current_price / support_price - 1) * 100
                if above_support_pct <= 1.5:
                    position_level = 2
                elif above_support_pct <= 3:
                    position_level = 1
                else:
                    return False, f"价格远离支撑位({above_support_pct:.1f}%)，等待回调", 0
            else:
                if strength >= 5 and confidence >= 90:
                    position_level = 1
                else:
                    return False, "缺少支撑位数据，无法确认买点", 0
        
        # 强信号加仓
        if strength >= SIGNAL_CONFIG['strong_signal_strength'] and confidence >= 90:
            position_level = min(3, position_level + 1)
        
        # 已有持仓检查
        if position:
            profit_pct = position.get('profit_pct', 0)
            add_count = position.get('add_count', 0)
            
            # 金字塔式加仓逻辑
            if add_count == 0:
                # 第一次加仓：回调未破位
                if profit_pct < -1:  # 亏损超过1%不加仓
                    return False, f"持仓亏损中({profit_pct:.1f}%)，不宜加仓", 0
                if profit_pct >= 0:  # 盈利中不加仓（等待回调）
                    return False, f"持仓盈利中({profit_pct:.1f}%)，等待回调加仓", 0
            elif add_count >= 2:
                return False, "已完成金字塔式建仓，不再加仓", 0
        
        return True, f"动态买入信号(强度{strength},置信度{confidence}%)", position_level
    
    @staticmethod
    def should_sell(
        signal: Dict,
        position: Dict,
        current_price: float,
        holding_period: str = 'swing',
        atr_value: float = None
    ) -> Tuple[bool, str, float]:
        """判断是否应该卖出（v5.0 动态风控版本）
        
        使用ATR动态止损止盈和移动止盈
        
        Returns:
            (是否卖出, 原因, 卖出比例)
        """
        if not position:
            return False, "没有持仓", 0
        
        cost_price = position['cost_price']
        profit_pct = (current_price / cost_price - 1) * 100
        
        # 1. 动态止损检查 - 最高优先级
        stop_loss, reason, ratio = RiskManager.check_stop_loss(
            position, current_price, holding_period, atr_value
        )
        if stop_loss:
            return True, reason, ratio
        
        # 2. 时间止损 - 持有超时且未盈利
        time_stop, reason = RiskManager.check_time_stop(position, holding_period)
        if time_stop:
            if profit_pct <= 0:
                return True, f"{reason}且未盈利", 1.0
            elif profit_pct < 1:
                return True, f"{reason}且盈利不足1%", 0.5
        
        signal_type = signal.get('signal_type', signal.get('signal', ''))
        strength = signal.get('strength', 0)
        
        # 3. 移动止盈检查（ATR动态）
        take_profit, reason, ratio = RiskManager.check_take_profit(
            position, current_price, holding_period, signal_type, atr_value
        )
        if take_profit:
            return True, reason, ratio
        
        # 4. 信号卖出
        if signal_type == 'sell':
            if strength >= SIGNAL_CONFIG['strong_signal_strength']:
                return True, f"强卖出信号(强度{strength})", 1.0
            if strength >= SIGNAL_CONFIG['min_sell_strength']:
                if profit_pct > 0.5:
                    return True, f"卖出信号+盈利({profit_pct:.1f}%)", 0.5
                if profit_pct < -0.5:
                    return True, f"卖出信号+亏损({profit_pct:.1f}%)", 1.0
        
        # 5. 盈利保护
        config = RISK_CONFIG.get(holding_period, RISK_CONFIG['swing'])
        if profit_pct >= config['take_profit_2'] * 100:
            return True, f"盈利保护({profit_pct:.1f}%)", 0.5
        
        return False, "不满足卖出条件", 0


# ============================================
# 模拟交易引擎 - v5.0 动态风控版本
# ============================================

class SimTradeEngine:
    """模拟交易引擎 v5.0 - 动态风控版本
    
    核心功能：
    1. ATR动态风控
    2. 金字塔式分仓
    3. 移动止盈
    4. 完整统计
    """
    
    def __init__(self, username: str):
        self.username = username
        self.account = self._ensure_account()
        self.position_calc = PositionCalculator()
        self.risk_manager = RiskManager()
        self.signal_analyzer = SignalAnalyzer()
        self.pyramid_manager = PyramidPositionManager()
        self.dynamic_risk = DynamicRiskManager()
    
    def _ensure_account(self) -> Dict:
        """确保账户存在"""
        account = db_get_sim_account(self.username)
        if not account:
            account = db_create_sim_account(self.username)
        return account
    
    def get_account_info(self) -> Dict:
        """获取账户完整信息"""
        account = db_get_sim_account(self.username)
        positions = db_get_sim_positions(self.username)
        stats = db_get_sim_trade_stats(self.username)
        records = db_get_sim_trade_records(self.username, limit=200)
        
        # 计算持仓市值
        position_value = sum(
            p['quantity'] * (p['current_price'] or p['cost_price']) 
            for p in positions
        )
        total_assets = account['current_capital'] + position_value
        
        # 计算浮动盈亏
        floating_profit = sum(p.get('profit', 0) for p in positions)
        
        # 计算最大回撤
        max_drawdown = RiskManager.calculate_max_drawdown(records)
        
        # 计算仓位占比
        position_ratio = position_value / total_assets * 100 if total_assets > 0 else 0
        
        return {
            'account': account,
            'positions': positions,
            'position_count': len(positions),
            'position_value': round(position_value, 2),
            'position_ratio': round(position_ratio, 2),
            'total_assets': round(total_assets, 2),
            'total_profit': round(total_assets - account['initial_capital'], 2),
            'total_profit_pct': round((total_assets / account['initial_capital'] - 1) * 100, 2),
            'floating_profit': round(floating_profit, 2),
            'max_drawdown': max_drawdown,
            'stats': stats
        }
    
    def can_buy(self, symbol: str, price: float, quantity: int) -> Tuple[bool, str]:
        """检查是否可以买入"""
        account = db_get_sim_account(self.username)
        amount = price * quantity
        
        if account['current_capital'] < amount:
            return False, f"资金不足，需要{amount:.2f}，可用{account['current_capital']:.2f}"
        
        # 检查总仓位限制
        positions = db_get_sim_positions(self.username)
        total_assets = account['current_capital'] + sum(
            p['quantity'] * (p['current_price'] or p['cost_price']) 
            for p in positions
        )
        current_position_ratio = sum(
            p['quantity'] * (p['current_price'] or p['cost_price']) 
            for p in positions
        ) / total_assets if total_assets > 0 else 0
        
        if current_position_ratio >= POSITION_CONFIG['max_total_position']:
            return False, f"总仓位已达上限({current_position_ratio*100:.1f}%)"
        
        # 检查单只标的仓位
        position = db_get_sim_position(self.username, symbol)
        if position:
            existing_value = position['quantity'] * (position['current_price'] or position['cost_price'])
            new_value = existing_value + amount
            if new_value / total_assets > POSITION_CONFIG['max_single_position']:
                return False, f"单只标的仓位不能超过{POSITION_CONFIG['max_single_position']*100:.0f}%"
        
        return True, "可以买入"
    
    def can_sell(self, symbol: str, quantity: int) -> Tuple[bool, str]:
        """检查是否可以卖出"""
        position = db_get_sim_position(self.username, symbol)
        
        if not position:
            return False, "没有持仓"
        
        if position['quantity'] < quantity:
            return False, f"持仓不足，持有{position['quantity']}，要卖{quantity}"
        
        # 检查交易规则
        today = get_beijing_now().strftime('%Y-%m-%d')
        can_sell_date = position.get('can_sell_date', today)
        
        if can_sell_date > today:
            trade_rule = position.get('trade_rule', 'T+1')
            return False, f"{trade_rule}规则，{can_sell_date}后可卖出"
        
        return True, "可以卖出"

    
    def execute_buy(
        self, 
        symbol: str, 
        name: str, 
        type_: str, 
        price: float, 
        quantity: int = None,
        signal_type: str = None, 
        signal_strength: int = None,
        signal_conditions: List[str] = None, 
        holding_period: str = 'swing',
        position_level: int = 1
    ) -> Dict:
        """执行买入操作
        
        Args:
            symbol: 标的代码
            name: 标的名称
            type_: 标的类型
            price: 买入价格
            quantity: 买入数量（None则自动计算）
            signal_type: 信号类型
            signal_strength: 信号强度
            signal_conditions: 触发条件
            holding_period: 持有周期
            position_level: 仓位等级 1-3
        
        Returns:
            交易结果
        """
        account = db_get_sim_account(self.username)
        positions = db_get_sim_positions(self.username)
        total_assets = account['current_capital'] + sum(
            p['quantity'] * (p['current_price'] or p['cost_price']) 
            for p in positions
        )
        
        # 检查是否已有持仓
        existing_position = db_get_sim_position(self.username, symbol)
        existing_pct = 0
        if existing_position:
            existing_value = existing_position['quantity'] * (existing_position['current_price'] or existing_position['cost_price'])
            existing_pct = existing_value / total_assets if total_assets > 0 else 0
        
        # 自动计算买入数量
        if quantity is None:
            # 根据仓位等级调整
            base_strength = signal_strength or 3
            if position_level == 3:
                base_strength = min(5, base_strength + 1)
            elif position_level == 1:
                base_strength = max(1, base_strength - 1)
            
            quantity, position_pct = self.position_calc.calculate_position_size(
                total_assets=total_assets,
                available_capital=account['current_capital'],
                price=price,
                signal_strength=base_strength,
                existing_position_pct=existing_pct
            )
        
        if quantity < 100:
            return {'success': False, 'message': '计算的买入数量不足100股'}
        
        can_buy, reason = self.can_buy(symbol, price, quantity)
        if not can_buy:
            return {'success': False, 'message': reason}
        
        amount = price * quantity
        trade_rule = get_trade_rule(symbol, type_)
        
        # 扣除资金
        new_capital = account['current_capital'] - amount
        db_update_sim_account(self.username, current_capital=new_capital)
        
        # 添加/更新持仓
        db_add_sim_position(
            username=self.username,
            symbol=symbol,
            name=name,
            type_=type_,
            quantity=quantity,
            cost_price=price,
            buy_signal=signal_type,
            holding_period=holding_period,
            trade_rule=trade_rule
        )
        
        # 记录交易
        conditions_str = json.dumps(signal_conditions, ensure_ascii=False) if signal_conditions else None
        db_add_sim_trade_record(
            username=self.username,
            symbol=symbol,
            name=name,
            trade_type='buy',
            quantity=quantity,
            price=price,
            signal_type=signal_type,
            signal_strength=signal_strength,
            signal_conditions=conditions_str
        )
        
        return {
            'success': True,
            'message': f"买入: {name}({symbol}) {quantity}股 @ ¥{price:.3f}",
            'trade_type': 'buy',
            'symbol': symbol,
            'name': name,
            'quantity': quantity,
            'price': price,
            'amount': round(amount, 2),
            'trade_rule': trade_rule,
            'position_pct': round((quantity * price) / total_assets * 100, 2) if total_assets > 0 else 0
        }

    
    def execute_sell(
        self, 
        symbol: str, 
        price: float, 
        quantity: int = None,
        sell_ratio: float = None,
        signal_type: str = None, 
        signal_strength: int = None,
        signal_conditions: List[str] = None,
        reason: str = None
    ) -> Dict:
        """执行卖出操作
        
        Args:
            symbol: 标的代码
            price: 卖出价格
            quantity: 卖出数量（None表示全部卖出）
            sell_ratio: 卖出比例（0-1，与quantity二选一）
            signal_type: 信号类型
            signal_strength: 信号强度
            signal_conditions: 触发条件
            reason: 卖出原因
        
        Returns:
            交易结果
        """
        position = db_get_sim_position(self.username, symbol)
        if not position:
            return {'success': False, 'message': '没有持仓'}
        
        # 计算卖出数量
        if quantity is None:
            if sell_ratio is not None:
                quantity = int(position['quantity'] * sell_ratio / 100) * 100
                if quantity < 100:
                    quantity = position['quantity']  # 剩余不足100股全部卖出
            else:
                quantity = position['quantity']
        
        can_sell, msg = self.can_sell(symbol, quantity)
        if not can_sell:
            return {'success': False, 'message': msg}
        
        amount = price * quantity
        cost_price = position['cost_price']
        profit = (price - cost_price) * quantity
        profit_pct = (price / cost_price - 1) * 100
        
        # 计算持有天数
        buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
        today = get_beijing_now().replace(tzinfo=None)
        holding_days = (today - buy_date).days
        
        # 增加资金
        account = db_get_sim_account(self.username)
        new_capital = account['current_capital'] + amount
        
        # 更新账户统计
        if profit > 0:
            new_win_count = account['win_count'] + 1
            new_loss_count = account['loss_count']
        else:
            new_win_count = account['win_count']
            new_loss_count = account['loss_count'] + 1
        
        total_trades = new_win_count + new_loss_count
        new_win_rate = (new_win_count / total_trades * 100) if total_trades > 0 else 0
        new_total_profit = account['total_profit'] + profit
        new_total_profit_pct = (new_total_profit / account['initial_capital']) * 100
        
        db_update_sim_account(
            self.username,
            current_capital=new_capital,
            total_profit=new_total_profit,
            total_profit_pct=new_total_profit_pct,
            win_count=new_win_count,
            loss_count=new_loss_count,
            win_rate=new_win_rate
        )
        
        # 更新或删除持仓
        if quantity >= position['quantity']:
            db_remove_sim_position(self.username, symbol)
        else:
            new_quantity = position['quantity'] - quantity
            # 记录已卖出比例
            sold_ratio = position.get('sold_ratio', 0) + (quantity / position['quantity'])
            db_update_sim_position(
                self.username, symbol, 
                quantity=new_quantity,
                sold_ratio=min(sold_ratio, 1.0)
            )
        
        # 记录交易
        conditions_str = json.dumps(signal_conditions, ensure_ascii=False) if signal_conditions else None
        db_add_sim_trade_record(
            username=self.username,
            symbol=symbol,
            name=position['name'],
            trade_type='sell',
            quantity=quantity,
            price=price,
            signal_type=signal_type,
            signal_strength=signal_strength,
            signal_conditions=conditions_str,
            profit=profit,
            profit_pct=profit_pct,
            holding_days=holding_days
        )
        
        return {
            'success': True,
            'message': f"卖出: {position['name']}({symbol}) {quantity}股 @ ¥{price:.3f}",
            'trade_type': 'sell',
            'symbol': symbol,
            'name': position['name'],
            'quantity': quantity,
            'price': price,
            'amount': round(amount, 2),
            'cost_price': cost_price,
            'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2),
            'holding_days': holding_days,
            'reason': reason or ''
        }
    
    def update_positions_price(self, quotes: Dict[str, Dict]) -> None:
        """更新持仓的当前价格和最高价"""
        positions = db_get_sim_positions(self.username)
        for position in positions:
            symbol = position['symbol'].upper()
            quote = quotes.get(symbol)
            if not quote:
                continue
            
            current_price = quote.get('current_price', 0)
            if current_price <= 0:
                continue
            
            cost_price = position['cost_price']
            profit = (current_price - cost_price) * position['quantity']
            profit_pct = (current_price / cost_price - 1) * 100
            
            # 更新最高价（用于移动止损）
            highest_price = max(
                position.get('highest_price', cost_price),
                current_price
            )
            
            db_update_sim_position(
                self.username, symbol,
                current_price=current_price,
                profit=round(profit, 2),
                profit_pct=round(profit_pct, 2),
                highest_price=highest_price
            )


# ============================================
# 自动交易处理
# ============================================

def process_auto_trade(
    username: str, 
    signals: Dict[str, Dict], 
    quotes: Dict[str, Dict],
    watchlist_data: List[Dict] = None
) -> List[Dict]:
    """处理自动交易
    
    Args:
        username: 用户名
        signals: {symbol: {period: {signal_type, strength, confidence, ...}}}
        quotes: {symbol: {current_price, change_percent, ...}}
        watchlist_data: 自选列表数据（可选，包含支撑位阻力位）
    
    Returns:
        交易结果列表
    """
    engine = SimTradeEngine(username)
    account_info = engine.get_account_info()
    account = account_info['account']
    
    # 检查是否开启自动交易
    if not account.get('auto_trade_enabled'):
        return []
    
    # 检查是否交易时间
    if not is_trading_time():
        return []
    
    results = []
    
    # 更新持仓价格
    engine.update_positions_price(quotes)
    
    # 获取自选列表
    if watchlist_data is None:
        watchlist_data = db_get_user_watchlist(username)
    
    watchlist_map = {item['symbol'].upper(): item for item in watchlist_data}
    
    # ========== 处理卖出（先卖后买）==========
    positions = db_get_sim_positions(username)
    for position in positions:
        symbol = position['symbol'].upper()
        quote = quotes.get(symbol)
        if not quote:
            continue
        
        current_price = quote.get('current_price', 0)
        if current_price <= 0:
            continue
        
        holding_period = position.get('holding_period', 'swing')
        signal = signals.get(symbol, {}).get(holding_period, {})
        
        # 检查是否应该卖出
        should_sell, reason, sell_ratio = engine.signal_analyzer.should_sell(
            signal, position, current_price, holding_period
        )
        
        if should_sell and sell_ratio > 0:
            result = engine.execute_sell(
                symbol=symbol,
                price=current_price,
                sell_ratio=sell_ratio,
                signal_type=signal.get('signal_type', signal.get('signal')),
                signal_strength=signal.get('strength'),
                signal_conditions=signal.get('triggered_conditions'),
                reason=reason
            )
            if result['success']:
                result['reason'] = reason
                results.append(result)
    
    # ========== 处理买入 ==========
    # 刷新账户信息
    account = db_get_sim_account(username)
    
    for item in watchlist_data:
        symbol = item['symbol'].upper()
        quote = quotes.get(symbol)
        if not quote:
            continue
        
        current_price = quote.get('current_price', 0)
        if current_price <= 0:
            continue
        
        # 已有持仓的跳过（暂不支持自动加仓）
        if db_get_sim_position(username, symbol):
            continue
        
        holding_period = item.get('holding_period', 'swing')
        signal = signals.get(symbol, {}).get(holding_period, {})
        
        # 获取支撑位阻力位
        support_price = item.get(f'{holding_period}_support') or item.get('ai_buy_price')
        resistance_price = item.get(f'{holding_period}_resistance') or item.get('ai_sell_price')
        
        # 检查是否应该买入
        should_buy, reason, position_level = engine.signal_analyzer.should_buy(
            signal=signal,
            position=None,
            account=account,
            current_price=current_price,
            support_price=support_price,
            resistance_price=resistance_price
        )
        
        if should_buy:
            result = engine.execute_buy(
                symbol=symbol,
                name=item.get('name', symbol),
                type_=item.get('type', 'stock'),
                price=current_price,
                signal_type=signal.get('signal_type', signal.get('signal')),
                signal_strength=signal.get('strength'),
                signal_conditions=signal.get('triggered_conditions'),
                holding_period=holding_period,
                position_level=position_level
            )
            if result['success']:
                result['reason'] = reason
                results.append(result)
                # 刷新账户
                account = db_get_sim_account(username)
    
    return results


# ============================================
# 辅助函数（兼容旧版本）
# ============================================

def calculate_buy_quantity(capital: float, price: float, position_pct: float = 0.1) -> int:
    """计算买入数量（兼容旧版本）"""
    quantity, _ = PositionCalculator.calculate_position_size(
        total_assets=capital,
        available_capital=capital,
        price=price,
        signal_strength=3
    )
    return quantity


def should_buy(signal: Dict, position: Dict = None, account: Dict = None) -> Tuple[bool, str]:
    """判断是否应该买入（兼容旧版本）"""
    result, reason, _ = SignalAnalyzer.should_buy(signal, position, account)
    return result, reason


def should_sell(signal: Dict, position: Dict, current_price: float) -> Tuple[bool, str]:
    """判断是否应该卖出（兼容旧版本）"""
    holding_period = position.get('holding_period', 'swing') if position else 'swing'
    result, reason, _ = SignalAnalyzer.should_sell(signal, position, current_price, holding_period)
    return result, reason
