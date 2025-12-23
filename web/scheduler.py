"""
============================================
定时任务调度器
Price Alert Scheduler
============================================
"""

import asyncio
import json
import logging
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional
from pathlib import Path
import threading
import schedule
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入必要模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.auth import (
    get_reminders, save_reminders, get_user_reminders,
    update_reminder, get_user_report
)
from tools.data_fetcher import get_stock_info
from config import APIConfig


# ============================================
# 短信发送功能
# ============================================

def send_sms_alert(phone: str, symbol: str, alert_type: str, 
                   current_price: float, target_price: float, name: str = "") -> bool:
    """
    发送短信提醒
    注意：这里需要集成实际的短信服务商 API
    常用服务商：阿里云短信、腾讯云短信、云片等
    """
    try:
        # TODO: 集成实际的短信服务
        # 示例：使用阿里云短信
        # from aliyunsdkcore.client import AcsClient
        # from aliyunsdkdysmsapi.request.v20170525.SendSmsRequest import SendSmsRequest
        
        action = "买入" if alert_type == "buy" else "卖出"
        message = f"【AI智能投研】{name or symbol} 已触发{action}价格提醒！当前价格：{current_price}，目标{action}价：{target_price}"
        
        logger.info(f"发送短信到 {phone}: {message}")
        
        # 实际发送短信的代码
        # client = AcsClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, 'cn-hangzhou')
        # request = SendSmsRequest()
        # request.set_PhoneNumbers(phone)
        # request.set_SignName("AI智能投研")
        # request.set_TemplateCode("SMS_XXXXX")
        # request.set_TemplateParam(json.dumps({
        #     "symbol": symbol,
        #     "name": name,
        #     "action": action,
        #     "current_price": str(current_price),
        #     "target_price": str(target_price)
        # }))
        # response = client.do_action_with_exception(request)
        
        return True
    except Exception as e:
        logger.error(f"发送短信失败: {e}")
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
    """从AI报告中获取买入卖出目标价"""
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
        ai_summary = report_data.get('ai_summary', {})
        if 'buy_price' in ai_summary:
            buy_price = ai_summary['buy_price']
        if 'sell_price' in ai_summary:
            sell_price = ai_summary['sell_price']
        
        return {
            'buy_price': buy_price,
            'sell_price': sell_price
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
    
    triggered = False
    name = reminder.get('name', symbol)
    
    # 检查买入信号
    if reminder_type in ['buy', 'both'] and buy_price:
        if current_price <= buy_price:
            send_sms_alert(phone, symbol, 'buy', current_price, buy_price, name)
            triggered = True
            logger.info(f"{symbol} 触发买入提醒: 当前价 {current_price} <= 目标价 {buy_price}")
    
    # 检查卖出信号
    if reminder_type in ['sell', 'both'] and sell_price:
        if current_price >= sell_price:
            send_sms_alert(phone, symbol, 'sell', current_price, sell_price, name)
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


# ============================================
# 调度器主逻辑
# ============================================

def run_scheduled_checks():
    """运行所有定时提醒检查"""
    logger.info("开始执行定时提醒检查...")
    
    try:
        # 获取所有提醒
        all_reminders = get_reminders()
        
        for username, user_reminders in all_reminders.items():
            # 获取用户手机号
            from web.auth import get_user_by_username
            user = get_user_by_username(username)
            if not user:
                continue
            
            phone = user.get('phone')
            if not phone:
                continue
            
            for reminder in user_reminders:
                if should_run_reminder(reminder):
                    logger.info(f"执行提醒: {username} - {reminder.get('symbol')}")
                    
                    triggered = check_price_alert(username, phone, reminder)
                    
                    # 更新最后触发时间
                    if triggered:
                        update_reminder(username, reminder.get('id'), {
                            'last_triggered': datetime.now().isoformat()
                        })
    
    except Exception as e:
        logger.error(f"执行定时检查失败: {e}")


def start_scheduler():
    """启动调度器"""
    logger.info("启动定时任务调度器...")
    
    # 每分钟检查一次
    schedule.every(1).minutes.do(run_scheduled_checks)
    
    # 在后台线程运行
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(30)
    
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()
    
    logger.info("定时任务调度器已启动")


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
