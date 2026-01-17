"""
============================================
定时任务调度器
Price Alert Scheduler + AI Analysis Scheduler + Auto Trade Scheduler
============================================
"""

import asyncio
import json
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import threading
import schedule
import time
import requests

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入必要模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.auth import (
    get_user_report
)
from tools.data_fetcher import get_stock_info
from config import APIConfig


# ============================================
# 交易时间判断
# ============================================

def is_trading_time() -> bool:
    """判断当前是否为交易时间（A股: 9:30-11:30, 13:00-15:00）"""
    now = datetime.now()
    current_time = now.time()
    
    # 周末不交易
    if now.weekday() >= 5:
        return False
    
    # 上午交易时段: 9:30 - 11:30
    morning_start = dt_time(9, 30)
    morning_end = dt_time(11, 30)
    
    # 下午交易时段: 13:00 - 15:00
    afternoon_start = dt_time(13, 0)
    afternoon_end = dt_time(15, 0)
    
    if (morning_start <= current_time <= morning_end) or \
       (afternoon_start <= current_time <= afternoon_end):
        return True
    
    return False


def is_near_trading_time() -> bool:
    """判断是否接近交易时间（提前5分钟开始准备）"""
    now = datetime.now()
    current_time = now.time()
    
    # 周末不交易
    if now.weekday() >= 5:
        return False
    
    # 上午交易时段前5分钟: 9:25 - 9:30
    morning_prep_start = dt_time(9, 25)
    morning_prep_end = dt_time(9, 30)
    
    # 下午交易时段前5分钟: 12:55 - 13:00
    afternoon_prep_start = dt_time(12, 55)
    afternoon_prep_end = dt_time(13, 0)
    
    if (morning_prep_start <= current_time <= morning_prep_end) or \
       (afternoon_prep_start <= current_time <= afternoon_prep_end):
        return True
    
    return False


# ============================================
# 短信发送功能
# ============================================

def send_sms_alert(phone: str, symbol: str, alert_type: str, 
                   current_price: float, target_price: float, name: str = "",
                   username: str = "", ai_summary: str = "") -> bool:
    """
    发送价格提醒通知
    使用微信公众号模板消息推送
    """
    try:
        from web.api import send_price_alert_notification
        
        action = "触及支撑位" if alert_type == "buy" else "触及阻力位"
        
        # 如果没有 AI 分析内容，生成默认内容
        if not ai_summary:
            if alert_type == "buy":
                ai_summary = f"根据AI技术分析，{name or symbol}当前价格已触及支撑位。技术指标显示该价位附近存在支撑，仅供学习研究参考，不构成任何投资建议。"
            else:
                ai_summary = f"根据AI技术分析，{name or symbol}当前价格已触及阻力位。技术指标显示该价位附近存在阻力，仅供学习研究参考，不构成任何投资建议。"
        
        logger.info(f"发送价格提醒: {username} - {name or symbol} - {action} - 当前价格: {current_price}, 目标价: {target_price}")
        
        # 调用微信推送
        if username:
            result = send_price_alert_notification(
                username=username,
                symbol=symbol,
                name=name or symbol,
                alert_type=alert_type,
                current_price=current_price,
                target_price=target_price,
                ai_summary=ai_summary
            )
            if result:
                logger.info(f"价格提醒推送成功: {username} - {symbol}")
                return True
            else:
                logger.warning(f"价格提醒推送失败: {username} - {symbol}")
                return False
        else:
            logger.warning(f"未提供用户名，无法发送推送")
            return False
        
    except Exception as e:
        logger.error(f"发送价格提醒失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 价格检查功能
# ============================================

def get_real_time_price(symbol: str) -> Optional[float]:
    """获取证券实时价格"""
    try:
        stock_info = get_stock_info(symbol)
        if stock_info and 'price_info' in stock_info:
            return stock_info['price_info'].get('current_price')
        return None
    except Exception as e:
        logger.error(f"获取 {symbol} 价格失败: {e}")
        return None


def get_ai_price_targets(username: str, symbol: str) -> Dict:
    """从AI报告中获取买入卖出目标价和AI分析摘要"""
    try:
        report = get_user_report(username, symbol)
        if not report:
            return {}
        
        report_data = report.get('report_data', {})
        
        # 从量化分析中提取目标价
        quant = report_data.get('quant_analysis', {})
        support_resistance = quant.get('support_resistance', {})
        
        # 支撑位和阻力位
        buy_price = None
        sell_price = None
        
        supports = support_resistance.get('supports', [])
        resistances = support_resistance.get('resistances', [])
        
        if supports:
            buy_price = supports[0] if isinstance(supports[0], (int, float)) else None
        if resistances:
            sell_price = resistances[0] if isinstance(resistances[0], (int, float)) else None
        
        # 也可以从 AI 摘要中解析
        ai_summary_data = report_data.get('ai_summary', {})
        if 'buy_price' in ai_summary_data:
            buy_price = ai_summary_data['buy_price']
        if 'sell_price' in ai_summary_data:
            sell_price = ai_summary_data['sell_price']
        
        # 获取 AI 分析摘要文本
        ai_summary_text = ""
        if isinstance(ai_summary_data, dict):
            ai_summary_text = ai_summary_data.get('summary', '') or ai_summary_data.get('analysis', '')
        elif isinstance(ai_summary_data, str):
            ai_summary_text = ai_summary_data
        
        # 如果没有摘要，尝试从其他字段获取
        if not ai_summary_text:
            ai_analysis = report_data.get('ai_analysis', {})
            if isinstance(ai_analysis, dict):
                ai_summary_text = ai_analysis.get('summary', '') or ai_analysis.get('recommendation', '')
            elif isinstance(ai_analysis, str):
                ai_summary_text = ai_analysis
        
        return {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'ai_summary': ai_summary_text
        }
    except Exception as e:
        logger.error(f"获取 {symbol} 目标价失败: {e}")
        return {}


# ============================================
# 自选列表AI建议价格实时监控
# ============================================

def check_watchlist_price_alerts():
    """检查自选列表中的AI建议价格触发情况（交易时间内运行）"""
    if not is_trading_time():
        return
    
    logger.info("开始检查自选列表AI建议价格...")
    
    try:
        from web.database import db_get_all_watchlist_with_ai_prices, db_update_watchlist_last_alert
        from web.api import send_price_alert_notification
        
        # 获取所有设置了AI建议价格的自选项
        watchlist_items = db_get_all_watchlist_with_ai_prices()
        
        if not watchlist_items:
            return
        
        logger.info(f"共有 {len(watchlist_items)} 个自选项需要监控")
        
        for item in watchlist_items:
            username = item.get('username')
            symbol = item.get('symbol')
            name = item.get('name', symbol)
            ai_buy_price = item.get('ai_buy_price')
            ai_sell_price = item.get('ai_sell_price')
            ai_buy_quantity = item.get('ai_buy_quantity')
            ai_sell_quantity = item.get('ai_sell_quantity')
            last_alert_at = item.get('last_alert_at')
            wechat_openid = item.get('wechat_openid')
            pushplus_token = item.get('pushplus_token')
            
            # 检查是否有推送配置
            if not wechat_openid and not pushplus_token:
                continue
            
            # 检查是否在冷却期内（同一标的30分钟内不重复提醒）
            if last_alert_at:
                try:
                    last_time = datetime.fromisoformat(last_alert_at)
                    if datetime.now() - last_time < timedelta(minutes=30):
                        continue
                except:
                    pass
            
            # 获取实时价格
            current_price = get_real_time_price(symbol)
            if current_price is None:
                continue
            
            triggered = False
            alert_type = None
            target_price = None
            
            # 检查是否触及支撑位（当前价格 <= 技术支撑位）
            # 注意：这仅是价格到达技术分析参考位置的通知，不构成任何买入建议
            if ai_buy_price and current_price <= ai_buy_price:
                triggered = True
                alert_type = 'buy'
                target_price = ai_buy_price
                logger.info(f"[自选监控] {symbol} 触及支撑位: 当前价 {current_price} <= 技术支撑位 {ai_buy_price}")
            
            # 检查是否触及阻力位（当前价格 >= 技术阻力位）
            # 注意：这仅是价格到达技术分析参考位置的通知，不构成任何卖出建议
            elif ai_sell_price and current_price >= ai_sell_price:
                triggered = True
                alert_type = 'sell'
                target_price = ai_sell_price
                logger.info(f"[自选监控] {symbol} 触及阻力位: 当前价 {current_price} >= 技术阻力位 {ai_sell_price}")
            
            # 发送提醒
            if triggered:
                # 获取技术分析摘要
                ai_summary = ""
                try:
                    targets = get_ai_price_targets(username, symbol)
                    ai_summary = targets.get('ai_summary', '')
                except:
                    pass
                
                # 发送推送（包含参考价位信息）
                result = send_price_alert_notification(
                    username=username,
                    symbol=symbol,
                    name=name,
                    alert_type=alert_type,
                    current_price=current_price,
                    target_price=target_price,
                    ai_summary=ai_summary,
                    ai_buy_price=ai_buy_price,
                    ai_sell_price=ai_sell_price,
                    ai_buy_quantity=ai_buy_quantity,
                    ai_sell_quantity=ai_sell_quantity
                )
                
                if result:
                    # 更新最后提醒时间
                    db_update_watchlist_last_alert(username, symbol)
                    logger.info(f"[自选监控] {username} - {symbol} 推送成功")
                else:
                    logger.warning(f"[自选监控] {username} - {symbol} 推送失败")
    
    except Exception as e:
        logger.error(f"检查自选列表价格失败: {e}")
        import traceback
        traceback.print_exc()


# ============================================
# 自动交易调度
# ============================================

def process_auto_trades():
    """处理所有开启自动交易的用户（交易时间内每分钟执行）
    
    核心逻辑：
    1. 获取所有开启自动交易的用户
    2. 对每个用户：获取自选列表、实时行情、生成信号
    3. 调用 SimTradeEngine 执行自动买卖
    
    注意：本功能仅供学习研究使用，不构成任何投资建议。
    """
    if not is_trading_time():
        return
    
    try:
        from web.database import (
            db_get_all_auto_trade_users, 
            db_get_user_watchlist,
            db_get_auto_trade_user_count,
            db_add_monitor_log
        )
        from web.sim_trade import process_auto_trade
        from tools.data_fetcher import get_batch_quotes
        
        # 获取开启自动交易的用户数量
        user_count = db_get_auto_trade_user_count()
        if user_count == 0:
            return
        
        logger.info(f"[自动交易] 开始处理，共 {user_count} 个用户开启了自动交易")
        
        # 获取所有开启自动交易的用户
        auto_trade_users = db_get_all_auto_trade_users()
        
        total_trades = 0
        
        for user_account in auto_trade_users:
            username = user_account['username']
            
            try:
                # 获取用户自选列表
                watchlist = db_get_user_watchlist(username)
                if not watchlist:
                    continue
                
                symbols = [item['symbol'] for item in watchlist]
                
                # 记录扫描开始日志
                db_add_monitor_log(
                    username, 'scan', 
                    f'开始扫描 {len(symbols)} 个标的',
                    details=f'标的列表: {", ".join(symbols[:10])}{"..." if len(symbols) > 10 else ""}'
                )
                
                # 批量获取实时行情
                quotes_result = get_batch_quotes(symbols)
                quotes = {}
                if quotes_result.get('status') == 'success':
                    for q in quotes_result.get('quotes', []):
                        quotes[q['symbol'].upper()] = q
                
                if not quotes:
                    logger.warning(f"[自动交易] {username} 获取行情失败，跳过")
                    db_add_monitor_log(username, 'error', '获取行情数据失败，跳过本轮扫描')
                    continue
                
                # 记录行情获取成功
                db_add_monitor_log(
                    username, 'info', 
                    f'获取到 {len(quotes)} 个标的的实时行情'
                )
                
                # 生成量化信号
                signals = {}
                signal_summary = {'buy': [], 'sell': [], 'hold': []}
                
                for item in watchlist:
                    symbol = item['symbol']
                    try:
                        signal = generate_quant_signal_for_auto_trade(
                            symbol, item, quotes.get(symbol.upper(), {})
                        )
                        signals[symbol.upper()] = {
                            'short': signal,
                            'swing': signal,
                            'long': signal
                        }
                        
                        # 记录信号
                        signal_type = signal.get('signal_type', 'hold')
                        if signal_type == 'buy':
                            signal_summary['buy'].append(symbol)
                            db_add_monitor_log(
                                username, 'signal',
                                f'{item.get("name", symbol)}({symbol}) 触发买入信号',
                                symbol=symbol,
                                details=f'信号强度: {signal.get("strength", 0)}, 置信度: {signal.get("confidence", 0)}%, 原因: {signal.get("reason", "")}'
                            )
                        elif signal_type == 'sell':
                            signal_summary['sell'].append(symbol)
                            db_add_monitor_log(
                                username, 'signal',
                                f'{item.get("name", symbol)}({symbol}) 触发卖出信号',
                                symbol=symbol,
                                details=f'信号强度: {signal.get("strength", 0)}, 置信度: {signal.get("confidence", 0)}%, 原因: {signal.get("reason", "")}'
                            )
                        else:
                            signal_summary['hold'].append(symbol)
                            
                    except Exception as e:
                        logger.error(f"[自动交易] {username} - {symbol} 信号生成失败: {e}")
                        db_add_monitor_log(username, 'error', f'{symbol} 信号生成失败: {str(e)}', symbol=symbol)
                
                # 记录信号汇总
                db_add_monitor_log(
                    username, 'info',
                    f'信号扫描完成: 买入{len(signal_summary["buy"])}个, 卖出{len(signal_summary["sell"])}个, 持有{len(signal_summary["hold"])}个'
                )
                
                # 执行自动交易
                results = process_auto_trade(username, signals, quotes, watchlist)
                
                if results:
                    total_trades += len(results)
                    for result in results:
                        trade_type = result.get('trade_type', '')
                        symbol = result.get('symbol', '')
                        name = result.get('name', symbol)
                        quantity = result.get('quantity', 0)
                        price = result.get('price', 0)
                        reason = result.get('reason', '')
                        
                        if trade_type == 'buy':
                            logger.info(f"[自动交易] {username} 买入 {name}({symbol}) {quantity}股 @ ¥{price:.3f} - {reason}")
                            db_add_monitor_log(
                                username, 'trade',
                                f'买入 {name}({symbol}) {quantity}股 @ ¥{price:.3f}',
                                symbol=symbol,
                                details=f'原因: {reason}'
                            )
                        else:
                            profit = result.get('profit', 0)
                            profit_pct = result.get('profit_pct', 0)
                            logger.info(f"[自动交易] {username} 卖出 {name}({symbol}) {quantity}股 @ ¥{price:.3f}, 盈亏: {profit:.2f}({profit_pct:.2f}%) - {reason}")
                            db_add_monitor_log(
                                username, 'trade',
                                f'卖出 {name}({symbol}) {quantity}股 @ ¥{price:.3f}, 盈亏: {"+" if profit >= 0 else ""}¥{profit:.2f}({profit_pct:.2f}%)',
                                symbol=symbol,
                                details=f'原因: {reason}'
                            )
                else:
                    db_add_monitor_log(username, 'info', '本轮扫描无交易执行')
                
            except Exception as e:
                logger.error(f"[自动交易] 处理用户 {username} 失败: {e}")
                db_add_monitor_log(username, 'error', f'自动交易处理失败: {str(e)}')
                import traceback
                traceback.print_exc()
        
        if total_trades > 0:
            logger.info(f"[自动交易] 本轮处理完成，共执行 {total_trades} 笔交易")
    
    except Exception as e:
        logger.error(f"[自动交易] 调度任务执行失败: {e}")
        import traceback
        traceback.print_exc()


def generate_quant_signal_for_auto_trade(symbol: str, watchlist_item: Dict, quote: Dict) -> Dict:
    """
    为自动交易生成量化信号（纯量化指标，不使用AI）
    
    核心逻辑：
    1. 基于价格与支撑位/阻力位的关系
    2. 基于涨跌幅和成交量
    3. 高胜率策略：严格的入场条件
    """
    current_price = quote.get('current_price', 0)
    if current_price <= 0:
        return {'signal_type': 'hold', 'signal': 'hold', 'strength': 0, 'confidence': 0}
    
    # 获取支撑位和阻力位
    holding_period = watchlist_item.get('holding_period', 'swing')
    support_price = watchlist_item.get(f'{holding_period}_support') or watchlist_item.get('ai_buy_price', 0)
    resistance_price = watchlist_item.get(f'{holding_period}_resistance') or watchlist_item.get('ai_sell_price', 0)
    
    # 获取涨跌幅
    change_pct = quote.get('change_percent', 0)
    
    # 初始化信号
    buy_score = 0
    sell_score = 0
    conditions = []
    
    # ========== 一票否决条件（高胜率核心）==========
    # 大跌超过5%不买
    if change_pct <= -5:
        return {
            'signal_type': 'hold', 'signal': 'hold', 
            'strength': 0, 'confidence': 0,
            'reason': '大跌超过5%，不追跌'
        }
    
    # 大涨超过7%不买（追高风险）
    if change_pct >= 7:
        return {
            'signal_type': 'hold', 'signal': 'hold',
            'strength': 0, 'confidence': 0,
            'reason': '大涨超过7%，不追高'
        }
    
    # ========== 买入信号评分 ==========
    if support_price and support_price > 0:
        dist_to_support = ((current_price - support_price) / support_price) * 100
        
        # 非常接近支撑位（1%以内）
        if 0 <= dist_to_support <= 1:
            buy_score += 3
            conditions.append(f'接近支撑位({dist_to_support:.1f}%)')
        # 接近支撑位（1-2%）
        elif 1 < dist_to_support <= 2:
            buy_score += 2
            conditions.append(f'较接近支撑位({dist_to_support:.1f}%)')
        # 跌破支撑位（可能是假突破）
        elif dist_to_support < 0 and dist_to_support >= -2:
            buy_score += 1
            conditions.append(f'跌破支撑位({abs(dist_to_support):.1f}%)')
    
    # ========== 卖出信号评分 ==========
    if resistance_price and resistance_price > 0:
        dist_to_resistance = ((resistance_price - current_price) / current_price) * 100
        
        # 非常接近阻力位（1%以内）
        if 0 <= dist_to_resistance <= 1:
            sell_score += 3
            conditions.append(f'接近阻力位({dist_to_resistance:.1f}%)')
        # 接近阻力位（1-2%）
        elif 1 < dist_to_resistance <= 2:
            sell_score += 2
            conditions.append(f'较接近阻力位({dist_to_resistance:.1f}%)')
        # 突破阻力位
        elif dist_to_resistance < 0:
            sell_score += 1
            conditions.append(f'突破阻力位({abs(dist_to_resistance):.1f}%)')
    
    # ========== 涨跌幅信号 ==========
    if -2 <= change_pct <= -0.5:
        buy_score += 1
        conditions.append(f'小幅回调({change_pct:.1f}%)')
    elif 0.5 <= change_pct <= 2:
        sell_score += 1
        conditions.append(f'小幅上涨({change_pct:.1f}%)')
    
    # ========== 生成最终信号 ==========
    if buy_score >= 3 and buy_score > sell_score:
        confidence = min(95, 70 + buy_score * 5)
        return {
            'signal_type': 'buy',
            'signal': 'buy',
            'strength': min(5, buy_score),
            'confidence': confidence,
            'triggered_conditions': conditions
        }
    elif sell_score >= 3 and sell_score > buy_score:
        confidence = min(95, 70 + sell_score * 5)
        return {
            'signal_type': 'sell',
            'signal': 'sell',
            'strength': min(5, sell_score),
            'confidence': confidence,
            'triggered_conditions': conditions
        }
    else:
        return {
            'signal_type': 'hold',
            'signal': 'hold',
            'strength': 0,
            'confidence': 50,
            'triggered_conditions': conditions
        }


def execute_strategy_signals():
    """执行策略池信号（交易时间内）"""
    if not is_trading_time():
        return
    
    try:
        from web.database import (
            db_get_all_auto_trade_users, db_get_enabled_strategy_configs,
            db_save_strategy_performance
        )
        from web.strategies import StrategyExecutor, UserStrategyConfig
        
        # 获取开启自动交易的用户
        auto_trade_users = db_get_all_auto_trade_users()
        
        for user in auto_trade_users:
            username = user.get('username')
            if not username:
                continue
            
            # 获取用户启用的策略配置
            strategy_configs = db_get_enabled_strategy_configs(username)
            if not strategy_configs:
                continue
            
            # 转换为 UserStrategyConfig 对象
            configs = []
            for cfg in strategy_configs:
                configs.append(UserStrategyConfig(
                    strategy_id=cfg['strategy_id'],
                    enabled=bool(cfg.get('enabled', True)),
                    allocated_capital=cfg.get('allocated_capital', 10000),
                    params=cfg.get('params', {})
                ))
            
            # 创建执行器并加载策略
            executor = StrategyExecutor()
            loaded, errors = executor.load_user_strategies(configs)
            
            if errors:
                for err in errors:
                    logger.warning(f"[策略池] 用户 {username} 策略加载警告: {err}")
            
            if loaded == 0:
                continue
            
            # 获取市场数据（简化版，实际需要更完整的数据）
            market_data = get_market_data_for_strategies(executor.get_all_applicable_symbols())
            
            # 执行所有策略
            signals, results = executor.execute_all(market_data)
            
            # 记录执行结果
            for result in results:
                if result.errors:
                    for err in result.errors:
                        logger.error(f"[策略池] 用户 {username} 策略 {result.strategy_id} 执行错误: {err}")
                
                if result.resolved_signals:
                    logger.info(
                        f"[策略池] 用户 {username} 策略 {result.strategy_id} "
                        f"生成 {len(result.resolved_signals)} 个信号"
                    )
            
            # TODO: 将信号传递给交易执行模块
            # 这里需要与现有的自动交易逻辑集成
            
    except Exception as e:
        logger.error(f"[策略池] 执行策略信号失败: {e}")
        import traceback
        traceback.print_exc()


def get_market_data_for_strategies(symbols: List[str]) -> Dict:
    """获取策略所需的市场数据"""
    market_data = {}
    
    for symbol in symbols:
        try:
            stock_info = get_stock_info(symbol)
            if not stock_info:
                continue
            
            price_info = stock_info.get('price_info', {})
            
            market_data[symbol] = {
                'close': price_info.get('current_price'),
                'open': price_info.get('open'),
                'high': price_info.get('high'),
                'low': price_info.get('low'),
                'volume': price_info.get('volume'),
                'change_pct': price_info.get('change_pct'),
            }
        except Exception as e:
            logger.warning(f"[策略池] 获取 {symbol} 市场数据失败: {e}")
    
    return market_data


def execute_etf_strategy_signals():
    """执行ETF轮动策略信号"""
    if not is_trading_time():
        return
    
    try:
        from web.database import db_get_all_auto_trade_users, db_get_enabled_strategy_configs
        from web.strategies import execute_etf_strategy
        
        # ETF策略ID列表
        etf_strategies = ['etf_momentum_rotation', 'binary_rotation', 'industry_momentum']
        
        # 获取开启自动交易的用户
        auto_trade_users = db_get_all_auto_trade_users()
        
        for user in auto_trade_users:
            username = user.get('username')
            if not username:
                continue
            
            # 获取用户启用的策略配置
            strategy_configs = db_get_enabled_strategy_configs(username)
            if not strategy_configs:
                continue
            
            # 过滤出ETF策略
            for cfg in strategy_configs:
                strategy_id = cfg.get('strategy_id')
                if strategy_id not in etf_strategies:
                    continue
                
                if not cfg.get('enabled', True):
                    continue
                
                allocated_capital = cfg.get('allocated_capital', 50000)
                
                # 执行ETF策略
                result = execute_etf_strategy(username, strategy_id, allocated_capital)
                
                if result.get('success'):
                    if result.get('orders', 0) > 0:
                        logger.info(
                            f"[ETF策略] 用户 {username} 策略 {strategy_id} "
                            f"执行 {result.get('executed', 0)}/{result.get('orders', 0)} 笔交易, "
                            f"目标: {result.get('target')}"
                        )
                else:
                    logger.warning(
                        f"[ETF策略] 用户 {username} 策略 {strategy_id} "
                        f"执行失败: {result.get('error')}"
                    )
                    
    except Exception as e:
        logger.error(f"[ETF策略] 执行失败: {e}")
        import traceback
        traceback.print_exc()


def sync_etf_data():
    """同步ETF数据（盘后执行）"""
    try:
        from web.data import sync_etf_data_task
        sync_etf_data_task()
    except Exception as e:
        logger.error(f"[ETF数据同步] 失败: {e}")


def start_scheduler():
    """启动调度器"""
    logger.info("启动定时任务调度器...")
    
    # 每30秒检查一次自选列表AI建议价格（交易时间内）
    schedule.every(30).seconds.do(check_watchlist_price_alerts)
    
    # 每60秒执行一次自动交易（交易时间内）
    # 自动交易会检查所有开启自动交易的用户，执行买卖操作
    schedule.every(60).seconds.do(process_auto_trades)
    
    # 每2分钟执行一次策略池信号（交易时间内）
    schedule.every(2).minutes.do(execute_strategy_signals)
    
    # 每5分钟执行一次ETF轮动策略（交易时间内）
    schedule.every(5).minutes.do(execute_etf_strategy_signals)
    
    # 每天16:00同步ETF数据（收盘后）
    schedule.every().day.at("16:00").do(sync_etf_data)
    
    # 每天23:59清空研究列表（保留当天的）
    schedule.every().day.at("23:59").do(clear_ai_picks_daily)
    
    # 在后台线程运行
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(10)
    
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()
    
    logger.info("定时任务调度器已启动（包含自选列表实时监控 + 自动交易）")


def clear_ai_picks_daily():
    """每日清空研究列表（保留当天添加的）"""
    try:
        from web.database import db_clear_ai_picks_daily
        deleted_count = db_clear_ai_picks_daily()
        logger.info(f"[研究列表] 每日清理完成，删除 {deleted_count} 条非今日数据")
    except Exception as e:
        logger.error(f"[研究列表] 每日清理失败: {e}")


if __name__ == "__main__":
    # 测试运行
    start_scheduler()
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("调度器已停止")
