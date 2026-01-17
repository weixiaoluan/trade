"""
============================================
策略交易集成模块
Strategy Trading Integration
============================================

将策略信号转化为模拟交易系统的实际交易:
- 加载用户策略配置
- 生成交易信号
- 执行买入/卖出操作
- 同步持仓状态
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .etf_rotation import (
    ETFMomentumRotationStrategy, BinaryRotationStrategy, IndustryMomentumStrategy,
    TICKER_POOL, BINARY_ROTATION_POOL, ETFInfo
)
from .registry import StrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class TradeOrder:
    """交易订单"""
    symbol: str
    name: str
    action: str  # 'buy' or 'sell'
    quantity: int
    price: float
    reason: str
    strategy_id: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class StrategyTrader:
    """
    策略交易执行器
    
    连接策略信号和模拟交易系统
    """
    
    def __init__(self, username: str):
        self.username = username
        self.strategies: Dict[str, object] = {}
        self._init_strategies()
    
    def _init_strategies(self):
        """初始化策略实例"""
        self.strategies = {
            'etf_momentum_rotation': ETFMomentumRotationStrategy(),
            'binary_rotation': BinaryRotationStrategy(),
            'industry_momentum': IndustryMomentumStrategy(),
        }
    
    def get_strategy_data(self, strategy_id: str) -> Tuple[object, Dict[str, ETFInfo]]:
        """
        获取策略实例和对应的ETF池
        """
        if strategy_id == 'etf_momentum_rotation':
            return self.strategies[strategy_id], TICKER_POOL
        elif strategy_id == 'binary_rotation':
            return self.strategies[strategy_id], self.strategies[strategy_id].ticker_pool
        elif strategy_id == 'industry_momentum':
            return self.strategies[strategy_id], self.strategies[strategy_id].ticker_pool
        else:
            return None, {}
    
    def generate_signal(self, strategy_id: str, 
                        price_data, premium_data=None) -> Optional[str]:
        """
        生成策略信号
        
        Args:
            strategy_id: 策略ID
            price_data: 价格数据DataFrame
            premium_data: 溢价率数据DataFrame
            
        Returns:
            目标持仓代码
        """
        strategy, _ = self.get_strategy_data(strategy_id)
        
        if strategy is None:
            logger.error(f"未找到策略: {strategy_id}")
            return None
        
        try:
            signals = strategy.generate_signals(price_data, premium_data)
            
            if signals.empty:
                return None
            
            # 获取最新信号
            latest = signals.iloc[-1]
            
            if 'target_symbol' in latest:
                return latest['target_symbol']
            elif 'target_symbols' in latest:
                # 行业轮动返回多个标的
                return latest['target_symbols']
            
            return None
            
        except Exception as e:
            logger.error(f"生成{strategy_id}信号失败: {e}")
            return None
    
    def calculate_trade_orders(self, 
                                strategy_id: str,
                                target_symbol: str,
                                current_positions: List[Dict],
                                available_capital: float,
                                current_prices: Dict[str, float]) -> List[TradeOrder]:
        """
        计算需要执行的交易订单
        
        Args:
            strategy_id: 策略ID
            target_symbol: 目标持仓代码
            current_positions: 当前持仓列表
            available_capital: 可用资金
            current_prices: 当前价格字典
            
        Returns:
            交易订单列表
        """
        orders = []
        strategy, ticker_pool = self.get_strategy_data(strategy_id)
        
        if strategy is None:
            return orders
        
        # 获取当前策略相关的持仓
        strategy_symbols = [etf.symbol for etf in ticker_pool.values()]
        current_holdings = {
            p['symbol']: p for p in current_positions 
            if p['symbol'] in strategy_symbols
        }
        
        # 处理多标的情况（行业轮动）
        if ',' in str(target_symbol):
            target_symbols = [s.strip() for s in target_symbol.split(',')]
        else:
            target_symbols = [target_symbol] if target_symbol else []
        
        # 过滤掉现金标的（如 511880.SH 货币ETF 作为现金等价物时不买入）
        cash_symbols = ['511880.SH', '511010.SH', '511990.SH']  # 常见货币基金
        is_cash_only = all(t in cash_symbols for t in target_symbols if t)
        
        # 1. 卖出不在目标中的持仓
        for symbol, position in current_holdings.items():
            if symbol not in target_symbols:
                etf_info = next((e for e in ticker_pool.values() if e.symbol == symbol), None)
                name = etf_info.name if etf_info else symbol
                
                price = current_prices.get(symbol, position.get('current_price', 0))
                
                orders.append(TradeOrder(
                    symbol=symbol,
                    name=name,
                    action='sell',
                    quantity=position.get('quantity', 0),
                    price=price,
                    reason=f'策略信号换仓',
                    strategy_id=strategy_id
                ))
        
        # 2. 买入目标标的（如果目标是现金则不买入）
        if is_cash_only:
            logger.info(f"策略{strategy_id}信号为持有现金，不执行买入")
            return orders
        
        for target in target_symbols:
            # 跳过现金标的
            if target in cash_symbols:
                continue
                
            if target and target not in current_holdings:
                etf_info = next((e for e in ticker_pool.values() if e.symbol == target), None)
                
                if etf_info is None:
                    continue
                
                price = current_prices.get(target, 0)
                
                if price <= 0:
                    logger.warning(f"无法获取{target}的价格")
                    continue
                
                # 计算可买数量
                # 考虑滑点和手续费
                slippage_rate = strategy.config.slippage_rate if hasattr(strategy, 'config') else 0.002
                effective_capital = available_capital * (1 - slippage_rate)
                
                # 平均分配资金给多个目标（排除现金标的）
                non_cash_targets = [t for t in target_symbols if t not in cash_symbols]
                capital_per_target = effective_capital / len(non_cash_targets) if non_cash_targets else 0
                
                # ETF 100股为一手
                quantity = int(capital_per_target / price / 100) * 100
                
                if quantity > 0:
                    orders.append(TradeOrder(
                        symbol=target,
                        name=etf_info.name,
                        action='buy',
                        quantity=quantity,
                        price=price,
                        reason=f'策略信号买入',
                        strategy_id=strategy_id
                    ))
        
        return orders
    
    def execute_orders(self, orders: List[TradeOrder]) -> List[Dict]:
        """
        执行交易订单（调用模拟交易系统）
        
        Returns:
            执行结果列表
        """
        from ..database import (
            db_get_sim_account, db_update_sim_account,
            db_add_sim_position, db_update_sim_position,
            db_get_sim_positions, db_remove_sim_position,
            db_add_sim_trade_record
        )
        
        results = []
        
        for order in orders:
            try:
                # 获取账户
                account = db_get_sim_account(self.username)
                if not account:
                    results.append({
                        'order': order,
                        'success': False,
                        'error': '账户不存在'
                    })
                    continue
                
                if order.action == 'sell':
                    result = self._execute_sell(order, account)
                else:
                    result = self._execute_buy(order, account)
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"执行订单失败: {e}")
                results.append({
                    'order': order,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _execute_buy(self, order: TradeOrder, account: Dict) -> Dict:
        """执行买入"""
        from ..database import (
            db_update_sim_account, db_add_sim_position,
            db_get_sim_position, db_update_sim_position,
            db_add_sim_trade_record, get_trade_rule
        )
        
        total_cost = order.quantity * order.price
        
        # 检查资金 - 使用 current_capital 字段
        available_cash = account.get('current_capital', account.get('cash', 0))
        if available_cash < total_cost:
            return {
                'order': order,
                'success': False,
                'error': f'资金不足: 需要{total_cost:.2f}, 可用{available_cash:.2f}'
            }
        
        # 扣除资金
        new_capital = available_cash - total_cost
        db_update_sim_account(self.username, current_capital=new_capital)
        
        # 添加/更新持仓
        existing = db_get_sim_position(self.username, order.symbol)
        
        if existing:
            # 更新持仓 - 使用正确的字段名 cost_price
            new_quantity = existing['quantity'] + order.quantity
            old_cost = existing.get('cost_price', 0) * existing['quantity']
            new_total_cost = old_cost + total_cost
            new_avg_price = new_total_cost / new_quantity
            
            db_update_sim_position(
                self.username, order.symbol,
                quantity=new_quantity,
                cost_price=new_avg_price
            )
        else:
            # 新建持仓 - 使用正确的参数
            trade_rule = 'T+0' if 'ETF' in order.name else 'T+1'
            db_add_sim_position(
                username=self.username,
                symbol=order.symbol,
                name=order.name,
                type_='ETF',
                quantity=order.quantity,
                cost_price=order.price,
                buy_signal=order.reason,
                holding_period='swing',
                trade_rule=trade_rule
            )
        
        # 记录交易 - 使用正确的参数名 trade_type
        db_add_sim_trade_record(
            username=self.username,
            symbol=order.symbol,
            name=order.name,
            trade_type='buy',
            quantity=order.quantity,
            price=order.price,
            signal_type=order.strategy_id,
            signal_strength=3
        )
        
        logger.info(f"[{self.username}] 买入 {order.symbol} {order.quantity}股 @ {order.price}")
        
        return {
            'order': order,
            'success': True,
            'message': f'买入成功: {order.quantity}股 @ {order.price}'
        }
    
    def _execute_sell(self, order: TradeOrder, account: Dict) -> Dict:
        """执行卖出"""
        from ..database import (
            db_update_sim_account, db_get_sim_position,
            db_update_sim_position, db_remove_sim_position,
            db_add_sim_trade_record
        )
        from datetime import datetime
        
        # 检查持仓
        position = db_get_sim_position(self.username, order.symbol)
        
        if not position:
            return {
                'order': order,
                'success': False,
                'error': f'没有{order.symbol}的持仓'
            }
        
        if position['quantity'] < order.quantity:
            order.quantity = position['quantity']  # 卖出全部
        
        # 计算收益 - 使用正确的字段名 cost_price
        sell_amount = order.quantity * order.price
        cost_per_share = position.get('cost_price', 0)
        if cost_per_share <= 0:
            cost_per_share = order.price  # 防止除零错误
        profit = (order.price - cost_per_share) * order.quantity
        profit_pct = ((order.price / cost_per_share) - 1) * 100 if cost_per_share > 0 else 0
        
        # 计算持有天数
        buy_date_str = position.get('buy_date', '')
        holding_days = 0
        if buy_date_str:
            try:
                buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
                holding_days = (datetime.now() - buy_date).days
            except:
                pass
        
        # 获取当前资金
        available_cash = account.get('current_capital', account.get('cash', 0))
        new_capital = available_cash + sell_amount
        
        # 更新账户统计 - 一次性更新所有字段避免多次调用
        new_total_profit = account.get('total_profit', 0) + profit
        if profit > 0:
            new_win_count = account.get('win_count', 0) + 1
            new_loss_count = account.get('loss_count', 0)
        else:
            new_win_count = account.get('win_count', 0)
            new_loss_count = account.get('loss_count', 0) + 1
        
        total_trades = new_win_count + new_loss_count
        new_win_rate = (new_win_count / total_trades * 100) if total_trades > 0 else 0
        initial_capital = account.get('initial_capital', 1000000)
        new_total_profit_pct = (new_total_profit / initial_capital) * 100
        
        db_update_sim_account(
            self.username,
            current_capital=new_capital,
            total_profit=new_total_profit,
            total_profit_pct=new_total_profit_pct,
            win_count=new_win_count,
            loss_count=new_loss_count,
            win_rate=new_win_rate
        )
        
        # 更新持仓
        remaining = position['quantity'] - order.quantity
        
        if remaining <= 0:
            db_remove_sim_position(self.username, order.symbol)
        else:
            db_update_sim_position(
                self.username, order.symbol,
                quantity=remaining
            )
        
        # 记录交易 - 使用正确的参数名
        db_add_sim_trade_record(
            username=self.username,
            symbol=order.symbol,
            name=position.get('name', order.name),
            trade_type='sell',
            quantity=order.quantity,
            price=order.price,
            signal_type=order.strategy_id,
            signal_strength=3,
            profit=profit,
            profit_pct=profit_pct,
            holding_days=holding_days
        )
        
        logger.info(f"[{self.username}] 卖出 {order.symbol} {order.quantity}股 @ {order.price}, 盈亏: {profit:.2f}")
        
        return {
            'order': order,
            'success': True,
            'message': f'卖出成功: {order.quantity}股 @ {order.price}, 盈亏: {profit:.2f}'
        }


def execute_etf_strategy(username: str, strategy_id: str, 
                          allocated_capital: float = None) -> Dict:
    """
    执行ETF策略的便捷函数
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        allocated_capital: 分配资金（可选）
        
    Returns:
        执行结果
    """
    from ..database import db_get_sim_account, db_get_sim_positions
    from ..data import (
        get_sync_service, db_get_multiple_etf_daily,
        db_get_multiple_etf_premium, db_get_etf_realtime
    )
    
    try:
        trader = StrategyTrader(username)
        strategy, ticker_pool = trader.get_strategy_data(strategy_id)
        
        if strategy is None:
            return {'success': False, 'error': f'未知策略: {strategy_id}'}
        
        # 获取账户信息
        account = db_get_sim_account(username)
        if not account:
            return {'success': False, 'error': '账户不存在'}
        
        # 获取当前持仓
        positions = db_get_sim_positions(username)
        
        # 获取策略所需的ETF代码
        symbols = [etf.symbol for etf in ticker_pool.values()]
        
        # 获取价格数据
        sync_service = get_sync_service()
        data = sync_service.get_strategy_data(symbols, days=60)
        
        price_data = data['prices']
        premium_data = data['premium']
        
        if price_data.empty:
            return {'success': False, 'error': '无法获取价格数据'}
        
        # 生成信号
        target_symbol = trader.generate_signal(strategy_id, price_data, premium_data)
        
        if not target_symbol:
            return {'success': True, 'message': '无交易信号', 'target': None}
        
        # 获取实时价格
        current_prices = {}
        for symbol in symbols:
            realtime = db_get_etf_realtime(symbol)
            if realtime and realtime.get('current_price'):
                current_prices[symbol] = realtime['current_price']
            elif not price_data.empty and symbol in price_data.columns:
                current_prices[symbol] = price_data[symbol].iloc[-1]
        
        # 计算可用资金 - 使用正确的字段名 current_capital
        available_cash = account.get('current_capital', account.get('cash', 0))
        if allocated_capital:
            available = min(allocated_capital, available_cash)
        else:
            available = available_cash
        
        # 计算交易订单
        orders = trader.calculate_trade_orders(
            strategy_id, target_symbol, positions,
            available, current_prices
        )
        
        if not orders:
            return {
                'success': True, 
                'message': '持仓已是目标状态，无需交易',
                'target': target_symbol
            }
        
        # 执行订单
        results = trader.execute_orders(orders)
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return {
            'success': True,
            'target': target_symbol,
            'orders': len(orders),
            'executed': success_count,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"执行ETF策略失败: {e}")
        return {'success': False, 'error': str(e)}


def execute_strategy_signal(username: str, signal, allocated_capital: float = None) -> Dict:
    """
    执行策略信号（通用，适用于所有策略）
    
    Args:
        username: 用户名
        signal: Signal对象，包含symbol, signal_type, strategy_id等
        allocated_capital: 分配资金
        
    Returns:
        执行结果
    """
    from ..database import (
        db_get_sim_account, db_get_sim_positions, db_get_sim_position,
        db_add_monitor_log
    )
    from ..stock import get_stock_info
    
    try:
        trader = StrategyTrader(username)
        
        # 获取账户信息
        account = db_get_sim_account(username)
        if not account:
            return {'success': False, 'error': '账户不存在'}
        
        # 获取当前持仓
        positions = db_get_sim_positions(username)
        
        symbol = signal.symbol
        signal_type = signal.signal_type
        strategy_id = signal.strategy_id or 'unknown'
        
        # 获取实时价格
        stock_info = get_stock_info(symbol)
        if not stock_info:
            return {'success': False, 'error': f'无法获取{symbol}行情'}
        
        price_info = stock_info.get('price_info', {})
        current_price = price_info.get('current_price', 0)
        
        if current_price <= 0:
            return {'success': False, 'error': f'无效价格: {current_price}'}
        
        stock_name = stock_info.get('basic_info', {}).get('name', symbol)
        
        orders = []
        
        if signal_type == 'buy':
            # 检查是否已有持仓
            existing = db_get_sim_position(username, symbol)
            if existing and existing.get('quantity', 0) > 0:
                return {'success': True, 'message': f'{symbol}已有持仓，跳过买入'}
            
            # 计算可买数量
            available_cash = account.get('current_capital', 0)
            capital_to_use = min(allocated_capital or available_cash, available_cash)
            
            # 考虑手续费，留一点余量
            effective_capital = capital_to_use * 0.998
            
            # 计算买入数量（100股为一手）
            quantity = int(effective_capital / current_price / 100) * 100
            
            if quantity >= 100:
                orders.append(TradeOrder(
                    symbol=symbol,
                    name=stock_name,
                    action='buy',
                    quantity=quantity,
                    price=current_price,
                    reason=signal.reason or f'{strategy_id}买入信号',
                    strategy_id=strategy_id
                ))
                
                # 记录监控日志
                db_add_monitor_log(
                    username, 'signal',
                    f'策略{strategy_id}触发买入信号: {stock_name}({symbol})',
                    symbol=symbol,
                    details=f'信号强度: {signal.strength}, 置信度: {signal.confidence}%'
                )
        
        elif signal_type == 'sell':
            # 检查持仓
            existing = db_get_sim_position(username, symbol)
            if not existing or existing.get('quantity', 0) <= 0:
                return {'success': True, 'message': f'{symbol}无持仓，跳过卖出'}
            
            quantity = existing.get('quantity', 0)
            
            orders.append(TradeOrder(
                symbol=symbol,
                name=existing.get('name', stock_name),
                action='sell',
                quantity=quantity,
                price=current_price,
                reason=signal.reason or f'{strategy_id}卖出信号',
                strategy_id=strategy_id
            ))
            
            # 记录监控日志
            db_add_monitor_log(
                username, 'signal',
                f'策略{strategy_id}触发卖出信号: {stock_name}({symbol})',
                symbol=symbol,
                details=f'信号强度: {signal.strength}, 置信度: {signal.confidence}%'
            )
        
        if not orders:
            return {'success': True, 'message': '无需执行交易', 'signal_type': signal_type}
        
        # 执行订单
        results = trader.execute_orders(orders)
        
        success_count = sum(1 for r in results if r.get('success'))
        
        # 记录交易执行日志
        for result in results:
            if result.get('success'):
                order = result.get('order')
                db_add_monitor_log(
                    username, 'trade',
                    f'策略{strategy_id}执行{order.action}: {order.name}({order.symbol}) {order.quantity}股 @ ¥{order.price:.3f}',
                    symbol=order.symbol,
                    details=f'原因: {order.reason}'
                )
        
        return {
            'success': True,
            'strategy_id': strategy_id,
            'signal_type': signal_type,
            'orders': len(orders),
            'executed': success_count,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"执行策略信号失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def get_etf_strategy_status(username: str, strategy_id: str) -> Dict:
    """
    获取ETF策略状态
    
    Returns:
        策略当前状态信息
    """
    from ..database import db_get_sim_positions
    from ..data import get_sync_service, db_get_etf_realtime
    
    try:
        trader = StrategyTrader(username)
        strategy, ticker_pool = trader.get_strategy_data(strategy_id)
        
        if strategy is None:
            return {'error': f'未知策略: {strategy_id}'}
        
        # 获取当前持仓
        positions = db_get_sim_positions(username)
        strategy_symbols = [etf.symbol for etf in ticker_pool.values()]
        
        # 过滤策略相关持仓
        strategy_positions = [
            p for p in positions if p['symbol'] in strategy_symbols
        ]
        
        # 获取价格数据
        sync_service = get_sync_service()
        data = sync_service.get_strategy_data(strategy_symbols, days=60)
        
        # 生成当前信号
        target = trader.generate_signal(
            strategy_id, data['prices'], data['premium']
        )
        
        # 获取实时行情
        realtime_data = {}
        for symbol in strategy_symbols:
            rt = db_get_etf_realtime(symbol)
            if rt:
                realtime_data[symbol] = rt
        
        return {
            'strategy_id': strategy_id,
            'current_positions': strategy_positions,
            'current_target': target,
            'etf_pool': [
                {
                    'symbol': etf.symbol,
                    'name': etf.name,
                    'is_qdii': etf.is_qdii,
                    'trading_rule': etf.trading_rule.value,
                    'realtime': realtime_data.get(etf.symbol)
                }
                for etf in ticker_pool.values()
            ],
            'last_update': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        return {'error': str(e)}
