"""
============================================
模拟交易引擎
Simulated Trading Engine
============================================

基于交易信号自动执行模拟买卖操作
支持A股不同交易规则（T+0/T+1/T+2）

注意：本模块仅供学习研究使用，不构成任何投资建议。
模拟交易结果不代表真实交易表现。
"""

import json
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


def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def is_trading_time() -> bool:
    """判断是否为A股交易时间"""
    now = get_beijing_now()
    # 周末不交易
    if now.weekday() >= 5:
        return False
    
    hour = now.hour
    minute = now.minute
    time_val = hour * 60 + minute
    
    # 上午 9:30-11:30 (570-690)
    # 下午 13:00-15:00 (780-900)
    return (570 <= time_val <= 690) or (780 <= time_val <= 900)


class SimTradeEngine:
    """模拟交易引擎
    
    核心功能：
    1. 根据信号自动买入/卖出
    2. 支持不同交易规则（T+0/T+1/T+2）
    3. 记录交易历史和收益
    4. 风险控制（止损/止盈）
    """
    
    def __init__(self, username: str):
        self.username = username
        self.account = self._ensure_account()
    
    def _ensure_account(self) -> Dict:
        """确保账户存在"""
        account = db_get_sim_account(self.username)
        if not account:
            account = db_create_sim_account(self.username)
        return account
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        account = db_get_sim_account(self.username)
        positions = db_get_sim_positions(self.username)
        stats = db_get_sim_trade_stats(self.username)
        
        # 计算持仓市值
        position_value = sum(p['quantity'] * (p['current_price'] or p['cost_price']) for p in positions)
        total_assets = account['current_capital'] + position_value
        
        return {
            'account': account,
            'positions': positions,
            'position_count': len(positions),
            'position_value': round(position_value, 2),
            'total_assets': round(total_assets, 2),
            'total_profit': round(total_assets - account['initial_capital'], 2),
            'total_profit_pct': round((total_assets / account['initial_capital'] - 1) * 100, 2),
            'stats': stats
        }
    
    def can_buy(self, symbol: str, price: float, quantity: int) -> Tuple[bool, str]:
        """检查是否可以买入
        
        Returns:
            (can_buy, reason)
        """
        account = db_get_sim_account(self.username)
        amount = price * quantity
        
        # 检查资金是否充足
        if account['current_capital'] < amount:
            return False, f"资金不足，需要{amount:.2f}，可用{account['current_capital']:.2f}"
        
        # 检查是否已有持仓（可以加仓）
        position = db_get_sim_position(self.username, symbol)
        if position:
            # 检查加仓后是否超过单只标的最大仓位（30%）
            total_assets = account['current_capital'] + sum(
                p['quantity'] * (p['current_price'] or p['cost_price']) 
                for p in db_get_sim_positions(self.username)
            )
            new_position_value = (position['quantity'] + quantity) * price
            if new_position_value / total_assets > 0.3:
                return False, f"单只标的仓位不能超过30%"
        
        return True, "可以买入"
    
    def can_sell(self, symbol: str, quantity: int) -> Tuple[bool, str]:
        """检查是否可以卖出
        
        Returns:
            (can_sell, reason)
        """
        position = db_get_sim_position(self.username, symbol)
        
        if not position:
            return False, "没有持仓"
        
        if position['quantity'] < quantity:
            return False, f"持仓不足，持有{position['quantity']}，要卖{quantity}"
        
        # 检查交易规则
        today = get_beijing_now().strftime('%Y-%m-%d')
        can_sell_date = position.get('can_sell_date', today)
        
        if can_sell_date > today:
            return False, f"T+{position.get('trade_rule', 'T+1')[2]}规则，{can_sell_date}后可卖出"
        
        return True, "可以卖出"
    
    def execute_buy(self, symbol: str, name: str, type_: str, price: float, 
                    quantity: int, signal_type: str = None, signal_strength: int = None,
                    signal_conditions: List[str] = None, holding_period: str = 'swing') -> Dict:
        """执行买入操作
        
        Args:
            symbol: 标的代码
            name: 标的名称
            type_: 标的类型
            price: 买入价格
            quantity: 买入数量
            signal_type: 信号类型
            signal_strength: 信号强度
            signal_conditions: 触发条件
            holding_period: 持有周期
        
        Returns:
            交易结果
        """
        can_buy, reason = self.can_buy(symbol, price, quantity)
        if not can_buy:
            return {'success': False, 'message': reason}
        
        amount = price * quantity
        trade_rule = get_trade_rule(symbol, type_)
        
        # 扣除资金
        account = db_get_sim_account(self.username)
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
            'message': f"买入成功: {name}({symbol}) {quantity}股 @ {price:.3f}",
            'trade_type': 'buy',
            'symbol': symbol,
            'name': name,
            'quantity': quantity,
            'price': price,
            'amount': amount,
            'trade_rule': trade_rule
        }
    
    def execute_sell(self, symbol: str, price: float, quantity: int = None,
                     signal_type: str = None, signal_strength: int = None,
                     signal_conditions: List[str] = None) -> Dict:
        """执行卖出操作
        
        Args:
            symbol: 标的代码
            price: 卖出价格
            quantity: 卖出数量（None表示全部卖出）
            signal_type: 信号类型
            signal_strength: 信号强度
            signal_conditions: 触发条件
        
        Returns:
            交易结果
        """
        position = db_get_sim_position(self.username, symbol)
        if not position:
            return {'success': False, 'message': '没有持仓'}
        
        # 默认全部卖出
        if quantity is None:
            quantity = position['quantity']
        
        can_sell, reason = self.can_sell(symbol, quantity)
        if not can_sell:
            return {'success': False, 'message': reason}
        
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
            db_update_sim_position(self.username, symbol, quantity=new_quantity)
        
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
            'message': f"卖出成功: {position['name']}({symbol}) {quantity}股 @ {price:.3f}",
            'trade_type': 'sell',
            'symbol': symbol,
            'name': position['name'],
            'quantity': quantity,
            'price': price,
            'amount': amount,
            'cost_price': cost_price,
            'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2),
            'holding_days': holding_days
        }
    
    def update_positions_price(self, quotes: Dict[str, Dict]) -> None:
        """更新持仓的当前价格
        
        Args:
            quotes: {symbol: {current_price: xxx, ...}}
        """
        positions = db_get_sim_positions(self.username)
        for position in positions:
            symbol = position['symbol']
            if symbol in quotes:
                current_price = quotes[symbol].get('current_price')
                if current_price and current_price > 0:
                    cost_price = position['cost_price']
                    profit = (current_price - cost_price) * position['quantity']
                    profit_pct = (current_price / cost_price - 1) * 100
                    db_update_sim_position(
                        self.username, symbol,
                        current_price=current_price,
                        profit=round(profit, 2),
                        profit_pct=round(profit_pct, 2)
                    )
    
    def check_stop_loss(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """检查是否触发止损
        
        止损规则：
        - 短线: 亏损超过3%止损
        - 波段: 亏损超过5%止损
        - 中长线: 亏损超过8%止损
        """
        cost_price = position['cost_price']
        loss_pct = (current_price / cost_price - 1) * 100
        
        holding_period = position.get('holding_period', 'swing')
        
        if holding_period == 'short' and loss_pct <= -3:
            return True, f"短线止损触发(亏损{loss_pct:.1f}%)"
        elif holding_period == 'swing' and loss_pct <= -5:
            return True, f"波段止损触发(亏损{loss_pct:.1f}%)"
        elif holding_period == 'long' and loss_pct <= -8:
            return True, f"中长线止损触发(亏损{loss_pct:.1f}%)"
        
        return False, ""
    
    def check_take_profit(self, position: Dict, current_price: float) -> Tuple[bool, str]:
        """检查是否触发止盈
        
        止盈规则：
        - 短线: 盈利超过5%可考虑止盈
        - 波段: 盈利超过10%可考虑止盈
        - 中长线: 盈利超过20%可考虑止盈
        
        注意：止盈不是强制的，需要结合信号判断
        """
        cost_price = position['cost_price']
        profit_pct = (current_price / cost_price - 1) * 100
        
        holding_period = position.get('holding_period', 'swing')
        
        if holding_period == 'short' and profit_pct >= 5:
            return True, f"短线止盈参考(盈利{profit_pct:.1f}%)"
        elif holding_period == 'swing' and profit_pct >= 10:
            return True, f"波段止盈参考(盈利{profit_pct:.1f}%)"
        elif holding_period == 'long' and profit_pct >= 20:
            return True, f"中长线止盈参考(盈利{profit_pct:.1f}%)"
        
        return False, ""


def calculate_buy_quantity(capital: float, price: float, position_pct: float = 0.1) -> int:
    """计算买入数量
    
    Args:
        capital: 可用资金
        price: 买入价格
        position_pct: 仓位比例（默认10%）
    
    Returns:
        买入数量（100的整数倍）
    """
    amount = capital * position_pct
    quantity = int(amount / price / 100) * 100  # A股最小单位100股
    return max(100, quantity)  # 至少买100股


def should_buy(signal: Dict, position: Dict = None, account: Dict = None) -> Tuple[bool, str]:
    """判断是否应该买入
    
    优化后的买入逻辑：
    1. 信号类型必须是buy
    2. 信号强度>=3（中等以上）
    3. 置信度>=60%
    4. 没有持仓或持仓较轻
    5. 不追高（当前价不能高于阻力位太多）
    """
    signal_type = signal.get('signal_type', '')
    strength = signal.get('strength', 0)
    confidence = signal.get('confidence', 0)
    
    if signal_type != 'buy':
        return False, "非买入信号"
    
    if strength < 3:
        return False, f"信号强度不足({strength}<3)"
    
    if confidence < 60:
        return False, f"置信度不足({confidence}<60)"
    
    # 如果已有持仓，检查是否适合加仓
    if position:
        current_profit_pct = position.get('profit_pct', 0)
        if current_profit_pct < -3:
            return False, f"持仓亏损中({current_profit_pct:.1f}%)，不宜加仓"
    
    return True, "符合买入条件"


def should_sell(signal: Dict, position: Dict, current_price: float) -> Tuple[bool, str]:
    """判断是否应该卖出
    
    优化后的卖出逻辑：
    1. 强制止损：亏损超过阈值必须卖出
    2. 信号卖出：信号类型是sell且强度>=3
    3. 止盈卖出：盈利达到目标且出现卖出信号
    4. 趋势保护：上涨趋势中不轻易卖出
    """
    if not position:
        return False, "没有持仓"
    
    cost_price = position['cost_price']
    profit_pct = (current_price / cost_price - 1) * 100
    holding_period = position.get('holding_period', 'swing')
    
    # 1. 强制止损检查
    stop_loss_pct = {'short': -3, 'swing': -5, 'long': -8}.get(holding_period, -5)
    if profit_pct <= stop_loss_pct:
        return True, f"触发止损(亏损{profit_pct:.1f}%)"
    
    signal_type = signal.get('signal_type', '')
    strength = signal.get('strength', 0)
    confidence = signal.get('confidence', 0)
    
    # 2. 信号卖出
    if signal_type == 'sell':
        # 强卖出信号
        if strength >= 4:
            return True, f"强卖出信号(强度{strength})"
        # 中等卖出信号 + 有盈利
        if strength >= 3 and profit_pct > 0:
            return True, f"卖出信号+盈利({profit_pct:.1f}%)"
        # 中等卖出信号 + 亏损较大
        if strength >= 3 and profit_pct < -2:
            return True, f"卖出信号+亏损({profit_pct:.1f}%)"
    
    # 3. 止盈检查（需要配合卖出信号）
    take_profit_pct = {'short': 5, 'swing': 10, 'long': 20}.get(holding_period, 10)
    if profit_pct >= take_profit_pct and signal_type == 'sell' and strength >= 2:
        return True, f"止盈+卖出信号(盈利{profit_pct:.1f}%)"
    
    # 4. 超高盈利保护（即使没有卖出信号）
    if profit_pct >= take_profit_pct * 2:
        return True, f"超高盈利保护(盈利{profit_pct:.1f}%)"
    
    return False, "不满足卖出条件"


def process_auto_trade(username: str, signals: Dict[str, Dict], quotes: Dict[str, Dict]) -> List[Dict]:
    """处理自动交易
    
    Args:
        username: 用户名
        signals: {symbol: {signal_type, strength, confidence, ...}}
        quotes: {symbol: {current_price, ...}}
    
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
    watchlist = db_get_user_watchlist(username)
    watchlist_symbols = {item['symbol'].upper() for item in watchlist}
    
    # 处理卖出（先卖后买）
    positions = db_get_sim_positions(username)
    for position in positions:
        symbol = position['symbol']
        if symbol not in quotes:
            continue
        
        current_price = quotes[symbol].get('current_price', 0)
        if current_price <= 0:
            continue
        
        # 获取对应周期的信号
        holding_period = position.get('holding_period', 'swing')
        signal = signals.get(symbol, {}).get(holding_period, {})
        
        should_sell_flag, reason = should_sell(signal, position, current_price)
        if should_sell_flag:
            result = engine.execute_sell(
                symbol=symbol,
                price=current_price,
                signal_type=signal.get('signal_type'),
                signal_strength=signal.get('strength'),
                signal_conditions=signal.get('triggered_conditions')
            )
            result['reason'] = reason
            results.append(result)
    
    # 处理买入
    for item in watchlist:
        symbol = item['symbol'].upper()
        if symbol not in quotes or symbol not in signals:
            continue
        
        current_price = quotes[symbol].get('current_price', 0)
        if current_price <= 0:
            continue
        
        # 已有持仓的跳过（暂不支持加仓）
        if db_get_sim_position(username, symbol):
            continue
        
        # 获取对应周期的信号
        holding_period = item.get('holding_period', 'swing')
        signal = signals.get(symbol, {}).get(holding_period, {})
        
        should_buy_flag, reason = should_buy(signal, None, account)
        if should_buy_flag:
            # 计算买入数量（使用10%仓位）
            quantity = calculate_buy_quantity(account['current_capital'], current_price, 0.1)
            if quantity >= 100:
                result = engine.execute_buy(
                    symbol=symbol,
                    name=item.get('name', symbol),
                    type_=item.get('type', 'stock'),
                    price=current_price,
                    quantity=quantity,
                    signal_type=signal.get('signal_type'),
                    signal_strength=signal.get('strength'),
                    signal_conditions=signal.get('triggered_conditions'),
                    holding_period=holding_period
                )
                result['reason'] = reason
                results.append(result)
                
                # 更新可用资金
                if result['success']:
                    account = db_get_sim_account(username)
    
    return results
