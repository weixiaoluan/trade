"""
============================================
用户认证模块
User Authentication Module
============================================
"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, validator

# 导入数据库模块
from web.database import (
    db_get_user_by_username, db_get_user_by_phone, db_create_user,
    db_create_session, db_get_session, db_delete_session,
    db_get_user_watchlist, db_add_to_watchlist, db_remove_from_watchlist, db_update_watchlist_item,
    db_save_report, db_get_user_reports, db_get_user_report, db_delete_report,
    db_create_task, db_update_task, db_get_user_tasks,
    db_get_user_reminders, db_add_reminder, db_update_reminder, db_delete_reminder, 
    db_get_symbol_reminders, db_get_all_reminders,
    db_get_all_users, db_update_user_status, db_update_user_role
)


# ============================================
# 数据模型
# ============================================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    confirm_password: str
    phone: str
    
    @validator('username')
    def validate_username(cls, v):
        # 用户名必须是中文或英文，长度2-20
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]{2,20}$', v):
            raise ValueError('用户名必须为2-20位中文或英文字母')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6 or len(v) > 20:
            raise ValueError('密码长度必须为6-20位')
        return v
    
    @validator('confirm_password')
    def validate_confirm_password(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        # 中国手机号验证
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('请输入有效的手机号码')
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class WatchlistItem(BaseModel):
    """自选项"""
    symbol: str
    name: Optional[str] = None
    type: Optional[str] = None  # stock, etf, fund
    added_at: Optional[str] = None
    position: Optional[float] = None  # 持仓数量
    cost_price: Optional[float] = None  # 持仓成本价
    from_ai_pick: Optional[int] = 0  # 是否来自研究列表


class ReminderItem(BaseModel):
    """价格触发提醒项"""
    id: Optional[str] = None
    symbol: str
    name: Optional[str] = None
    reminder_type: str  # buy, sell, both
    frequency: str = "trading_day"  # trading_day, weekly, monthly
    analysis_time: str = "09:30"  # 提醒时间 HH:MM
    weekday: Optional[int] = None  # 1-7 (周一-周日)，仅 weekly 时使用
    day_of_month: Optional[int] = None  # 1-31，仅 monthly 时使用
    # AI 自动分析设置
    ai_analysis_frequency: str = "trading_day"  # AI分析频率
    ai_analysis_time: str = "09:30"  # AI分析时间 HH:MM
    ai_analysis_weekday: Optional[int] = None  # AI分析周几
    ai_analysis_day_of_month: Optional[int] = None  # AI分析日期
    buy_price: Optional[float] = None  # AI分析的支撑位
    sell_price: Optional[float] = None  # AI分析的阻力位
    enabled: bool = True
    created_at: Optional[str] = None
    last_notified_type: Optional[str] = None  # 最后触发类型
    last_notified_at: Optional[str] = None  # 最后触发时间
    last_analysis_at: Optional[str] = None  # 最后分析时间


# ============================================
# 工具函数
# ============================================

def hash_password(password: str, salt: str = None) -> tuple:
    """密码哈希"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码"""
    new_hash, _ = hash_password(password, salt)
    return new_hash == hashed


def generate_token() -> str:
    """生成会话 token"""
    return secrets.token_hex(32)


# ============================================
# 用户管理 (使用数据库)
# ============================================

def get_user_by_username(username: str) -> Optional[Dict]:
    """根据用户名获取用户"""
    return db_get_user_by_username(username)


def get_user_by_phone(phone: str) -> Optional[Dict]:
    """根据手机号获取用户"""
    return db_get_user_by_phone(phone)


def create_user(username: str, password: str, phone: str) -> Dict:
    """创建用户"""
    hashed_password, salt = hash_password(password)
    return db_create_user(username, hashed_password, salt, phone)


def get_all_users() -> list:
    """获取所有用户（管理员功能）"""
    return db_get_all_users()


def update_user_status(username: str, status: str) -> bool:
    """更新用户状态"""
    return db_update_user_status(username, status)


def update_user_role(username: str, role: str) -> bool:
    """更新用户角色"""
    return db_update_user_role(username, role)


def is_admin(user: Dict) -> bool:
    """检查用户是否是管理员"""
    return user.get('role') == 'admin'


def is_approved(user: Dict) -> bool:
    """检查用户是否已审核"""
    return user.get('status') == 'approved'


# ============================================
# 会话管理 (使用数据库)
# ============================================

def create_session(username: str) -> str:
    """创建会话"""
    token = generate_token()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db_create_session(token, username, expires_at)
    return token


def get_session(token: str) -> Optional[Dict]:
    """获取会话"""
    session = db_get_session(token)
    if session:
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() < expires_at:
            return session
        else:
            db_delete_session(token)
    return None


def delete_session(token: str):
    """删除会话"""
    db_delete_session(token)


def get_current_user(token: str) -> Optional[Dict]:
    """根据 token 获取当前用户"""
    session = get_session(token)
    if session:
        user = get_user_by_username(session['username'])
        if user:
            return {
                'username': user['username'],
                'phone': user['phone'],
                'role': user.get('role', 'user'),
                'status': user.get('status', 'pending'),
                'created_at': user['created_at']
            }
    return None


# ============================================
# 自选列表管理 (使用数据库)
# ============================================

def get_user_watchlist(username: str) -> list:
    """获取用户自选列表"""
    return db_get_user_watchlist(username)


def add_to_watchlist(username: str, item: Dict) -> bool:
    """添加到自选列表"""
    return db_add_to_watchlist(
        username, 
        item.get('symbol'),
        item.get('name'),
        item.get('type'),
        item.get('position'),
        item.get('cost_price'),
        item.get('from_ai_pick', 0)
    )


def remove_from_watchlist(username: str, symbol: str) -> bool:
    """从自选列表移除"""
    return db_remove_from_watchlist(username, symbol)


def update_watchlist_item(username: str, symbol: str, **kwargs) -> bool:
    """更新自选项信息"""
    return db_update_watchlist_item(username, symbol, **kwargs)


def batch_add_to_watchlist(username: str, items: list) -> Dict:
    """批量添加到自选列表"""
    added = []
    skipped = []
    
    for item in items:
        if add_to_watchlist(username, item):
            added.append(item.get('symbol'))
        else:
            skipped.append(item.get('symbol'))
    
    return {'added': added, 'skipped': skipped}


def batch_remove_from_watchlist(username: str, symbols: list) -> Dict:
    """批量从自选列表移除"""
    removed = []
    not_found = []
    
    for symbol in symbols:
        if remove_from_watchlist(username, symbol):
            removed.append(symbol)
        else:
            not_found.append(symbol)
    
    return {'removed': removed, 'not_found': not_found}


# ============================================
# 分析报告管理 (使用数据库)
# ============================================

def save_user_report(username: str, symbol: str, report_data: Dict) -> str:
    """保存用户的分析报告"""
    name = report_data.get('name', symbol)
    report_id = db_save_report(username, symbol, name, report_data)
    return f"{symbol}_{report_id}"


def get_user_reports(username: str) -> list:
    """获取用户的所有报告"""
    reports = db_get_user_reports(username)
    # 转换为旧格式以兼容
    result = []
    for r in reports:
        result.append({
            'id': r['id'],
            'symbol': r['symbol'],
            'name': r.get('name', r['symbol']),
            'created_at': r['created_at'],
            'status': 'completed',
            'data': r['report_data']
        })
    return result


def clean_nan_values(obj):
    """递归清理数据中的 NaN 和 Infinity 值，替换为 None"""
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(v) for v in obj]
    else:
        return obj


def get_user_report(username: str, symbol: str) -> Optional[Dict]:
    """获取用户某个标的的报告"""
    report = db_get_user_report(username, symbol)
    if report:
        # 清理报告数据中的 NaN 值，避免 JSON 序列化错误
        report_data = clean_nan_values(report['report_data'])
        return {
            'id': report['id'],
            'symbol': report['symbol'],
            'name': report.get('name', report['symbol']),
            'created_at': report['created_at'],
            'status': 'completed',
            'data': report_data
        }
    return None


def delete_user_report(username: str, symbol: str) -> bool:
    """删除用户的报告"""
    return db_delete_report(username, symbol)


# ============================================
# 分析任务管理 (使用数据库)
# ============================================

def create_analysis_task(username: str, symbol: str, task_id: str) -> Dict:
    """创建分析任务"""
    return db_create_task(username, symbol, task_id)


def update_analysis_task(username: str, symbol: str, updates: Dict):
    """更新分析任务状态"""
    db_update_task(username, symbol, **updates)


def get_user_analysis_tasks(username: str) -> Dict:
    """获取用户的所有分析任务"""
    return db_get_user_tasks(username)


# ============================================
# 定时提醒相关函数 (使用数据库)
# ============================================

def get_reminders() -> Dict:
    """获取所有提醒"""
    return db_get_all_reminders()


def get_user_reminders(username: str) -> list:
    """获取用户的所有提醒"""
    reminders = db_get_user_reminders(username)
    # 转换 reminder_id 为 id 以兼容前端（排除数据库自增主键 id）
    result = []
    for r in reminders:
        item = {k: v for k, v in r.items() if k not in ('id', 'reminder_id')}
        item['id'] = r.get('reminder_id')  # 使用 reminder_id 作为前端的 id
        result.append(item)
    return result


def add_reminder(username: str, reminder: Dict) -> Dict:
    """添加价格触发提醒"""
    reminder_id = secrets.token_hex(8)
    return db_add_reminder(
        username,
        reminder_id,
        reminder['symbol'],
        reminder.get('name'),
        reminder['reminder_type'],
        reminder.get('frequency', 'trading_day'),
        reminder.get('analysis_time', '09:30'),
        reminder.get('weekday'),
        reminder.get('day_of_month'),
        reminder.get('ai_analysis_frequency', 'trading_day'),
        reminder.get('ai_analysis_time', '09:30'),
        reminder.get('ai_analysis_weekday'),
        reminder.get('ai_analysis_day_of_month'),
        reminder.get('buy_price'),
        reminder.get('sell_price')
    )


def update_reminder(username: str, reminder_id: str, updates: Dict) -> bool:
    """更新提醒"""
    return db_update_reminder(username, reminder_id, **updates)


def delete_reminder(username: str, reminder_id: str) -> bool:
    """删除提醒"""
    return db_delete_reminder(username, reminder_id)


def get_symbol_reminders(username: str, symbol: str) -> list:
    """获取某个证券的所有提醒"""
    reminders = db_get_symbol_reminders(username, symbol)
    return [{'id': r.get('reminder_id', r.get('id')), **{k: v for k, v in r.items() if k != 'reminder_id'}} for r in reminders]


def batch_add_reminders(username: str, symbols: list, reminder_config: Dict) -> Dict:
    """批量添加提醒"""
    added = []
    for symbol in symbols:
        reminder = reminder_config.copy()
        reminder['symbol'] = symbol
        result = add_reminder(username, reminder)
        added.append(result)
    return {'added': added, 'count': len(added)}
