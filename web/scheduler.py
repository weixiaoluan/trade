"""
============================================
定时任务调度器
Price Alert Scheduler + AI Analysis Scheduler
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
    get_reminders, get_user_reminders,
    update_reminder, get_user_report
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
        
        action = "买入" if alert_type == "buy" else "卖出"
        
        # 如果没有 AI 分析内容，生成默认内容
        if not ai_summary:
            if alert_type == "buy":
                ai_summary = f"根据AI智能分析，{name or symbol}当前价格已触及设定的买入价位。技术指标显示短期存在反弹机会，建议关注成交量变化，把握买入时机。请结合自身风险承受能力，谨慎决策。"
            else:
                ai_summary = f"根据AI智能分析，{name or symbol}当前价格已触及设定的卖出价位。技术指标显示短期可能面临回调压力，建议适时获利了结，注意控制风险。请结合自身风险承受能力，谨慎决策。"
        
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
        
        # 支撑位作为买入价，阻力位作为卖出价
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


def check_price_alert(username: str, phone: str, reminder: Dict) -> bool:
    """检查价格是否触发提醒"""
    symbol = reminder.get('symbol')
    reminder_type = reminder.get('reminder_type')  # buy, sell, both
    
    # 获取实时价格
    current_price = get_real_time_price(symbol)
    if current_price is None:
        logger.warning(f"无法获取 {symbol} 的实时价格")
        return False
    
    # 获取目标价
    targets = get_ai_price_targets(username, symbol)
    buy_price = targets.get('buy_price')
    sell_price = targets.get('sell_price')
    ai_summary = targets.get('ai_summary', '')
    
    triggered = False
    name = reminder.get('name', symbol)
    
    # 检查买入信号
    if reminder_type in ['buy', 'both'] and buy_price:
        if current_price <= buy_price:
            send_sms_alert(phone, symbol, 'buy', current_price, buy_price, name, username, ai_summary)
            triggered = True
            logger.info(f"{symbol} 触发买入提醒: 当前价 {current_price} <= 目标价 {buy_price}")
    
    # 检查卖出信号
    if reminder_type in ['sell', 'both'] and sell_price:
        if current_price >= sell_price:
            send_sms_alert(phone, symbol, 'sell', current_price, sell_price, name, username, ai_summary)
            triggered = True
            logger.info(f"{symbol} 触发卖出提醒: 当前价 {current_price} >= 目标价 {sell_price}")
    
    return triggered


# ============================================
# 交易日判断
# ============================================

def is_trading_day() -> bool:
    """判断今天是否为交易日（简化版，仅排除周末）"""
    today = datetime.now()
    # 周六(5)和周日(6)不是交易日
    if today.weekday() >= 5:
        return False
    
    # TODO: 可以添加节假日判断
    # 可以调用交易所日历API或维护本地节假日列表
    
    return True


def should_run_reminder(reminder: Dict) -> bool:
    """判断提醒是否应该在当前时间运行"""
    if not reminder.get('enabled', True):
        return False
    
    frequency = reminder.get('frequency')
    now = datetime.now()
    
    # 检查时间
    reminder_time = reminder.get('time', '09:00')
    try:
        hour, minute = map(int, reminder_time.split(':'))
        target_time = dt_time(hour, minute)
        current_time = now.time()
        
        # 允许5分钟的时间窗口
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) - 
            (target_time.hour * 60 + target_time.minute)
        )
        if time_diff > 5:
            return False
    except:
        return False
    
    # 检查频率
    if frequency == 'trading_day':
        return is_trading_day()
    elif frequency == 'daily':
        return True
    elif frequency == 'weekly':
        target_weekday = reminder.get('weekday', 0)
        return now.weekday() == target_weekday
    elif frequency == 'monthly':
        target_day = reminder.get('day_of_month', 1)
        return now.day == target_day
    
    return False


def should_run_ai_analysis(reminder: Dict) -> bool:
    """判断是否应该触发AI分析"""
    if not reminder.get('enabled', True):
        return False
    
    # 获取AI分析设置
    ai_frequency = reminder.get('ai_analysis_frequency', 'trading_day')
    ai_time = reminder.get('ai_analysis_time', '09:30')
    
    now = datetime.now()
    
    # 检查时间
    try:
        hour, minute = map(int, ai_time.split(':'))
        target_time = dt_time(hour, minute)
        current_time = now.time()
        
        # 允许2分钟的时间窗口
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) - 
            (target_time.hour * 60 + target_time.minute)
        )
        if time_diff > 2:
            return False
    except:
        return False
    
    # 检查频率
    if ai_frequency == 'trading_day':
        return is_trading_day()
    elif ai_frequency == 'daily':
        return True
    elif ai_frequency == 'weekly':
        target_weekday = reminder.get('ai_analysis_weekday', 1)
        return now.weekday() == target_weekday
    elif ai_frequency == 'monthly':
        target_day = reminder.get('ai_analysis_day_of_month', 1)
        return now.day == target_day
    
    return False


def trigger_ai_analysis(username: str, symbol: str) -> bool:
    """触发AI分析任务"""
    try:
        # 获取用户token（从数据库获取）
        from web.auth import get_user_by_username, generate_token
        user = get_user_by_username(username)
        if not user:
            logger.error(f"用户 {username} 不存在")
            return False
        
        # 生成临时token
        token = generate_token(username)
        
        # 调用后台分析API
        response = requests.post(
            "http://localhost:8000/api/analyze/background",
            json={"ticker": symbol},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"成功触发 {username} 的 {symbol} AI分析")
            return True
        else:
            logger.error(f"触发AI分析失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"触发AI分析异常: {e}")
        return False


# ============================================
# 调度器主逻辑
# ============================================

def run_scheduled_checks():
    """运行所有定时提醒检查（包括AI分析触发）"""
    logger.info("开始执行定时提醒检查...")
    
    try:
        # 获取所有提醒
        all_reminders = get_reminders()
        
        for username, user_reminders in all_reminders.items():
            # 获取用户信息
            from web.auth import get_user_by_username
            user = get_user_by_username(username)
            if not user:
                continue
            
            phone = user.get('phone')
            
            for reminder in user_reminders:
                symbol = reminder.get('symbol')
                
                # 检查是否需要触发AI分析
                if should_run_ai_analysis(reminder):
                    # 检查今天是否已经分析过（避免重复触发）
                    last_analysis = reminder.get('last_analysis_at')
                    today = datetime.now().date().isoformat()
                    
                    if not last_analysis or not last_analysis.startswith(today):
                        logger.info(f"触发AI分析: {username} - {symbol}")
                        if trigger_ai_analysis(username, symbol):
                            # 更新最后分析时间
                            update_reminder(username, reminder.get('id'), {
                                'last_analysis_at': datetime.now().isoformat()
                            })
                
                # 检查价格提醒（需要手机号）
                if phone and should_run_reminder(reminder):
                    logger.info(f"执行价格提醒: {username} - {symbol}")
                    
                    triggered = check_price_alert(username, phone, reminder)
                    
                    # 更新最后触发时间
                    if triggered:
                        update_reminder(username, reminder.get('id'), {
                            'last_triggered': datetime.now().isoformat()
                        })
    
    except Exception as e:
        logger.error(f"执行定时检查失败: {e}")


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
            
            # 检查买入信号（当前价格 <= AI建议买入价）
            if ai_buy_price and current_price <= ai_buy_price:
                triggered = True
                alert_type = 'buy'
                target_price = ai_buy_price
                logger.info(f"[自选监控] {symbol} 触发买入: 当前价 {current_price} <= AI建议买入价 {ai_buy_price}")
            
            # 检查卖出信号（当前价格 >= AI建议卖出价）
            elif ai_sell_price and current_price >= ai_sell_price:
                triggered = True
                alert_type = 'sell'
                target_price = ai_sell_price
                logger.info(f"[自选监控] {symbol} 触发卖出: 当前价 {current_price} >= AI建议卖出价 {ai_sell_price}")
            
            # 发送提醒
            if triggered:
                # 获取AI分析摘要
                ai_summary = ""
                try:
                    targets = get_ai_price_targets(username, symbol)
                    ai_summary = targets.get('ai_summary', '')
                except:
                    pass
                
                # 发送推送（包含建议价格和数量）
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


def start_scheduler():
    """启动调度器"""
    logger.info("启动定时任务调度器...")
    
    # 每分钟检查一次定时提醒
    schedule.every(1).minutes.do(run_scheduled_checks)
    
    # 每30秒检查一次自选列表AI建议价格（交易时间内）
    schedule.every(30).seconds.do(check_watchlist_price_alerts)
    
    # 在后台线程运行
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(10)
    
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()
    
    logger.info("定时任务调度器已启动（包含自选列表实时监控）")


# ============================================
# 手动触发检查（用于测试）
# ============================================

def manual_check_all():
    """手动触发所有提醒检查（忽略时间条件）"""
    logger.info("手动执行所有提醒检查...")
    
    all_reminders = get_reminders()
    
    for username, user_reminders in all_reminders.items():
        from web.auth import get_user_by_username
        user = get_user_by_username(username)
        if not user:
            continue
        
        phone = user.get('phone')
        if not phone:
            continue
        
        for reminder in user_reminders:
            if reminder.get('enabled', True):
                logger.info(f"检查: {username} - {reminder.get('symbol')}")
                check_price_alert(username, phone, reminder)


if __name__ == "__main__":
    # 测试运行
    start_scheduler()
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("调度器已停止")
