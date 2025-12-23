"""
============================================
用户认证模块
User Authentication Module
============================================
"""

import json
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, validator

# 数据存储路径
DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)


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


def load_json_file(file_path: Path) -> Dict:
    """加载 JSON 文件"""
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding='utf-8'))
        except:
            return {}
    return {}


def save_json_file(file_path: Path, data: Dict):
    """保存 JSON 文件"""
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


# ============================================
# 用户管理
# ============================================

def get_users() -> Dict:
    """获取所有用户"""
    return load_json_file(USERS_FILE)


def save_users(users: Dict):
    """保存用户数据"""
    save_json_file(USERS_FILE, users)


def get_user_by_username(username: str) -> Optional[Dict]:
    """根据用户名获取用户"""
    users = get_users()
    return users.get(username)


def get_user_by_phone(phone: str) -> Optional[Dict]:
    """根据手机号获取用户"""
    users = get_users()
    for user in users.values():
        if user.get('phone') == phone:
            return user
    return None


def create_user(username: str, password: str, phone: str) -> Dict:
    """创建用户"""
    users = get_users()
    
    hashed_password, salt = hash_password(password)
    
    user = {
        'username': username,
        'password': hashed_password,
        'salt': salt,
        'phone': phone,
        'created_at': datetime.now().isoformat(),
        'watchlist': []
    }
    
    users[username] = user
    save_users(users)
    
    return {'username': username, 'phone': phone}


# ============================================
# 会话管理
# ============================================

def get_sessions() -> Dict:
    """获取所有会话"""
    return load_json_file(SESSIONS_FILE)


def save_sessions(sessions: Dict):
    """保存会话数据"""
    save_json_file(SESSIONS_FILE, sessions)


def create_session(username: str) -> str:
    """创建会话"""
    sessions = get_sessions()
    token = generate_token()
    
    sessions[token] = {
        'username': username,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    save_sessions(sessions)
    return token


def get_session(token: str) -> Optional[Dict]:
    """获取会话"""
    sessions = get_sessions()
    session = sessions.get(token)
    
    if session:
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() < expires_at:
            return session
        else:
            # 会话过期，删除
            del sessions[token]
            save_sessions(sessions)
    
    return None


def delete_session(token: str):
    """删除会话"""
    sessions = get_sessions()
    if token in sessions:
        del sessions[token]
        save_sessions(sessions)


def get_current_user(token: str) -> Optional[Dict]:
    """根据 token 获取当前用户"""
    session = get_session(token)
    if session:
        user = get_user_by_username(session['username'])
        if user:
            return {
                'username': user['username'],
                'phone': user['phone'],
                'created_at': user['created_at']
            }
    return None


# ============================================
# 自选列表管理
# ============================================

def get_user_watchlist(username: str) -> list:
    """获取用户自选列表"""
    users = get_users()
    user = users.get(username)
    if user:
        return user.get('watchlist', [])
    return []


def add_to_watchlist(username: str, item: Dict) -> bool:
    """添加到自选列表"""
    users = get_users()
    user = users.get(username)
    
    if not user:
        return False
    
    watchlist = user.get('watchlist', [])
    
    # 检查是否已存在
    for existing in watchlist:
        if existing.get('symbol') == item.get('symbol'):
            return False  # 已存在
    
    item['added_at'] = datetime.now().isoformat()
    watchlist.append(item)
    user['watchlist'] = watchlist
    
    save_users(users)
    return True


def remove_from_watchlist(username: str, symbol: str) -> bool:
    """从自选列表移除"""
    users = get_users()
    user = users.get(username)
    
    if not user:
        return False
    
    watchlist = user.get('watchlist', [])
    new_watchlist = [item for item in watchlist if item.get('symbol') != symbol]
    
    if len(new_watchlist) == len(watchlist):
        return False  # 未找到
    
    user['watchlist'] = new_watchlist
    save_users(users)
    return True


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
# 分析报告管理
# ============================================

REPORTS_FILE = DATA_DIR / "reports.json"


def get_reports() -> Dict:
    """获取所有报告"""
    return load_json_file(REPORTS_FILE)


def save_reports(reports: Dict):
    """保存报告数据"""
    save_json_file(REPORTS_FILE, reports)


def save_user_report(username: str, symbol: str, report_data: Dict) -> str:
    """保存用户的分析报告"""
    reports = get_reports()
    
    if username not in reports:
        reports[username] = {}
    
    report_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    report = {
        'id': report_id,
        'symbol': symbol,
        'created_at': datetime.now().isoformat(),
        'status': report_data.get('status', 'completed'),
        'data': report_data
    }
    
    # 按 symbol 存储，只保留最新的报告
    reports[username][symbol] = report
    
    save_reports(reports)
    return report_id


def get_user_reports(username: str) -> list:
    """获取用户的所有报告"""
    reports = get_reports()
    user_reports = reports.get(username, {})
    
    # 转换为列表并按时间排序
    report_list = list(user_reports.values())
    report_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return report_list


def get_user_report(username: str, symbol: str) -> Optional[Dict]:
    """获取用户某个标的的报告"""
    reports = get_reports()
    user_reports = reports.get(username, {})
    return user_reports.get(symbol)


def delete_user_report(username: str, symbol: str) -> bool:
    """删除用户的报告"""
    reports = get_reports()
    
    if username not in reports:
        return False
    
    if symbol not in reports[username]:
        return False
    
    del reports[username][symbol]
    save_reports(reports)
    return True


# ============================================
# 分析任务管理
# ============================================

TASKS_FILE = DATA_DIR / "analysis_tasks.json"


def get_analysis_tasks() -> Dict:
    """获取所有分析任务"""
    return load_json_file(TASKS_FILE)


def save_analysis_tasks(tasks: Dict):
    """保存分析任务"""
    save_json_file(TASKS_FILE, tasks)


def create_analysis_task(username: str, symbol: str, task_id: str) -> Dict:
    """创建分析任务"""
    tasks = get_analysis_tasks()
    
    if username not in tasks:
        tasks[username] = {}
    
    task = {
        'task_id': task_id,
        'symbol': symbol,
        'status': 'pending',  # pending, running, completed, failed
        'progress': 0,
        'current_step': '等待开始',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'result': None,
        'error': None
    }
    
    tasks[username][symbol] = task
    save_analysis_tasks(tasks)
    return task


def update_analysis_task(username: str, symbol: str, updates: Dict):
    """更新分析任务状态"""
    tasks = get_analysis_tasks()
    
    if username not in tasks or symbol not in tasks[username]:
        return
    
    task = tasks[username][symbol]
    task.update(updates)
    task['updated_at'] = datetime.now().isoformat()
    
    save_analysis_tasks(tasks)


def get_user_analysis_tasks(username: str) -> Dict:
    """获取用户的所有分析任务"""
    tasks = get_analysis_tasks()
    return tasks.get(username, {})
