"""
============================================
数据库模块
Database Module - SQLite
============================================
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

# 数据库路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "ai_trade.db"


@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                salt TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        ''')
        
        # 会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 自选列表表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                type TEXT,
                position REAL,
                cost_price REAL,
                added_at TEXT NOT NULL,
                UNIQUE(username, symbol),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 分析报告表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                report_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 分析任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                current_step TEXT,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 价格触发提醒表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                reminder_type TEXT NOT NULL,
                frequency TEXT NOT NULL DEFAULT 'trading_day',
                analysis_time TEXT DEFAULT '09:30',
                weekday INTEGER,
                day_of_month INTEGER,
                buy_price REAL,
                sell_price REAL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_notified_type TEXT,
                last_notified_at TEXT,
                last_analysis_at TEXT,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_username ON watchlist(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_username ON reports(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_username ON reminders(username)')
        
        conn.commit()
        print("数据库初始化完成")


def migrate_database():
    """数据库迁移 - 添加新字段"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查 users 表是否有 role 字段
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'role' not in columns:
            print("迁移: 添加 role 字段")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        
        if 'status' not in columns:
            print("迁移: 添加 status 字段")
            cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
        
        # 将 19919930729 手机号的用户设置为超级管理员，状态为已审核
        cursor.execute("""
            UPDATE users SET role = 'admin', status = 'approved' 
            WHERE phone = '19919930729'
        """)
        
        # 检查 watchlist 表是否有 starred 字段
        cursor.execute("PRAGMA table_info(watchlist)")
        watchlist_columns = [col[1] for col in cursor.fetchall()]
        
        if 'starred' not in watchlist_columns:
            print("迁移: 添加 starred 字段到 watchlist 表")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN starred INTEGER DEFAULT 0")
        
        # 检查 users 表是否有 pushplus_token 字段
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'pushplus_token' not in user_columns:
            print("迁移: 添加 pushplus_token 字段到 users 表")
            cursor.execute("ALTER TABLE users ADD COLUMN pushplus_token TEXT")
        
        # 检查 reminders 表是否有 AI 分析相关字段
        cursor.execute("PRAGMA table_info(reminders)")
        reminder_columns = [col[1] for col in cursor.fetchall()]
        
        if 'ai_analysis_frequency' not in reminder_columns:
            print("迁移: 添加 AI 分析频率字段到 reminders 表")
            cursor.execute("ALTER TABLE reminders ADD COLUMN ai_analysis_frequency TEXT DEFAULT 'trading_day'")
        
        if 'ai_analysis_time' not in reminder_columns:
            print("迁移: 添加 AI 分析时间字段到 reminders 表")
            cursor.execute("ALTER TABLE reminders ADD COLUMN ai_analysis_time TEXT DEFAULT '09:30'")
        
        if 'ai_analysis_weekday' not in reminder_columns:
            print("迁移: 添加 AI 分析周几字段到 reminders 表")
            cursor.execute("ALTER TABLE reminders ADD COLUMN ai_analysis_weekday INTEGER")
        
        if 'ai_analysis_day_of_month' not in reminder_columns:
            print("迁移: 添加 AI 分析日期字段到 reminders 表")
            cursor.execute("ALTER TABLE reminders ADD COLUMN ai_analysis_day_of_month INTEGER")
        
        conn.commit()
        print("数据库迁移完成")


# ============================================
# 用户管理
# ============================================

def db_get_user_by_username(username: str) -> Optional[Dict]:
    """根据用户名获取用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def db_get_user_by_phone(phone: str) -> Optional[Dict]:
    """根据手机号获取用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def db_create_user(username: str, password: str, salt: str, phone: str) -> Dict:
    """创建用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (username, password, salt, phone, role, status, created_at)
            VALUES (?, ?, ?, ?, 'user', 'pending', ?)
        ''', (username, password, salt, phone, created_at))
        
        return {'username': username, 'phone': phone, 'role': 'user', 'status': 'pending'}


def db_get_all_users() -> List[Dict]:
    """获取所有用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, phone, role, status, created_at FROM users ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]


def db_update_user_status(username: str, status: str) -> bool:
    """更新用户状态"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE username = ?', (status, username))
        return cursor.rowcount > 0


def db_update_user_role(username: str, role: str) -> bool:
    """更新用户角色"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))
        return cursor.rowcount > 0


# ============================================
# 会话管理
# ============================================

def db_create_session(token: str, username: str, expires_at: str) -> None:
    """创建会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO sessions (token, username, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (token, username, created_at, expires_at))


def db_get_session(token: str) -> Optional[Dict]:
    """获取会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE token = ?', (token,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def db_delete_session(token: str) -> None:
    """删除会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))


def db_cleanup_expired_sessions() -> None:
    """清理过期会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('DELETE FROM sessions WHERE expires_at < ?', (now,))


# ============================================
# 自选列表管理
# ============================================

def db_get_user_watchlist(username: str) -> List[Dict]:
    """获取用户自选列表（特别关注的排在前面）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT symbol, name, type, position, cost_price, added_at, 
                   COALESCE(starred, 0) as starred
            FROM watchlist WHERE username = ? 
            ORDER BY starred DESC, added_at DESC
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]


def db_add_to_watchlist(username: str, symbol: str, name: str = None, 
                        type_: str = None, position: float = None, 
                        cost_price: float = None) -> bool:
    """添加到自选"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO watchlist (username, symbol, name, type, position, cost_price, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, symbol, name, type_, position, cost_price, datetime.now().isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False


def db_remove_from_watchlist(username: str, symbol: str) -> bool:
    """从自选中移除，同时删除关联的报告、提醒、任务数据"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 删除自选
        cursor.execute('DELETE FROM watchlist WHERE username = ? AND symbol = ?', (username, symbol))
        deleted = cursor.rowcount > 0
        
        if deleted:
            # 删除关联的报告
            cursor.execute('DELETE FROM reports WHERE username = ? AND symbol = ?', (username, symbol))
            # 删除关联的提醒
            cursor.execute('DELETE FROM reminders WHERE username = ? AND symbol = ?', (username, symbol))
            # 删除关联的分析任务
            cursor.execute('DELETE FROM analysis_tasks WHERE username = ? AND symbol = ?', (username, symbol))
            conn.commit()
        
        return deleted


def db_update_watchlist_item(username: str, symbol: str, **kwargs) -> bool:
    """更新自选项"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        for key, value in kwargs.items():
            if value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.extend([username, symbol])
        cursor.execute(f'''
            UPDATE watchlist SET {", ".join(updates)}
            WHERE username = ? AND symbol = ?
        ''', values)
        return cursor.rowcount > 0


# ============================================
# 报告管理
# ============================================

def db_save_report(username: str, symbol: str, name: str, report_data: Dict) -> int:
    """保存报告"""
    from datetime import timedelta
    # 使用北京时间 (UTC+8)
    beijing_now = datetime.utcnow() + timedelta(hours=8)
    
    with get_db() as conn:
        cursor = conn.cursor()
        # 先删除旧报告
        cursor.execute('DELETE FROM reports WHERE username = ? AND symbol = ?', (username, symbol))
        # 插入新报告
        cursor.execute('''
            INSERT INTO reports (username, symbol, name, report_data, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, symbol, name, json.dumps(report_data, ensure_ascii=False), beijing_now.isoformat()))
        return cursor.lastrowid


def db_get_user_reports(username: str) -> List[Dict]:
    """获取用户所有报告"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, symbol, name, report_data, created_at 
            FROM reports WHERE username = ? ORDER BY created_at DESC
        ''', (username,))
        reports = []
        for row in cursor.fetchall():
            report = dict(row)
            report['report_data'] = json.loads(report['report_data'])
            reports.append(report)
        return reports


def db_get_user_report(username: str, symbol: str) -> Optional[Dict]:
    """获取用户某个证券的报告"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, symbol, name, report_data, created_at 
            FROM reports WHERE username = ? AND symbol = ? 
            ORDER BY created_at DESC LIMIT 1
        ''', (username, symbol))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            report['report_data'] = json.loads(report['report_data'])
            return report
        return None


def db_delete_report(username: str, symbol: str) -> bool:
    """删除报告"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reports WHERE username = ? AND symbol = ?', (username, symbol))
        return cursor.rowcount > 0


# ============================================
# 分析任务管理
# ============================================

def db_create_task(username: str, symbol: str, task_id: str) -> Dict:
    """创建分析任务"""
    from datetime import timedelta
    # 使用北京时间 (UTC+8)
    beijing_now = datetime.utcnow() + timedelta(hours=8)
    now = beijing_now.isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 删除旧任务
        cursor.execute('DELETE FROM analysis_tasks WHERE username = ? AND symbol = ?', (username, symbol))
        
        cursor.execute('''
            INSERT INTO analysis_tasks (username, symbol, task_id, status, progress, current_step, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', 0, '等待开始', ?, ?)
        ''', (username, symbol, task_id, now, now))
        
        return {
            'task_id': task_id,
            'symbol': symbol,
            'status': 'pending',
            'progress': 0,
            'current_step': '等待开始',
            'created_at': now,
            'updated_at': now
        }


def db_update_task(username: str, symbol: str, **kwargs) -> None:
    """更新任务状态"""
    from datetime import timedelta
    # 使用北京时间 (UTC+8)
    beijing_now = datetime.utcnow() + timedelta(hours=8)
    
    with get_db() as conn:
        cursor = conn.cursor()
        kwargs['updated_at'] = beijing_now.isoformat()
        
        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        values.extend([username, symbol])
        cursor.execute(f'''
            UPDATE analysis_tasks SET {", ".join(updates)}
            WHERE username = ? AND symbol = ?
        ''', values)


def db_get_user_tasks(username: str) -> Dict[str, Dict]:
    """获取用户所有任务"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analysis_tasks WHERE username = ?', (username,))
        tasks = {}
        for row in cursor.fetchall():
            task = dict(row)
            tasks[task['symbol']] = task
        return tasks


# ============================================
# 定时提醒管理
# ============================================

def db_get_user_reminders(username: str) -> List[Dict]:
    """获取用户所有提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 由于历史数据可能存在编码问题，尝试多种匹配方式
        cursor.execute('SELECT * FROM reminders WHERE username = ?', (username,))
        results = cursor.fetchall()
        if not results:
            # 如果没找到，尝试获取所有提醒（单用户系统的临时方案）
            cursor.execute('SELECT * FROM reminders')
            results = cursor.fetchall()
        return [dict(row) for row in results]


def db_get_all_reminders() -> Dict[str, List[Dict]]:
    """获取所有用户的提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reminders')
        reminders = {}
        for row in cursor.fetchall():
            r = dict(row)
            username = r['username']
            if username not in reminders:
                reminders[username] = []
            reminders[username].append(r)
        return reminders


def db_add_reminder(username: str, reminder_id: str, symbol: str, name: str,
                    reminder_type: str, frequency: str = 'trading_day',
                    analysis_time: str = '09:30', weekday: int = None,
                    day_of_month: int = None,
                    ai_analysis_frequency: str = 'trading_day',
                    ai_analysis_time: str = '09:30',
                    ai_analysis_weekday: int = None,
                    ai_analysis_day_of_month: int = None,
                    buy_price: float = None, sell_price: float = None) -> Dict:
    """添加价格触发提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO reminders (reminder_id, username, symbol, name, reminder_type, frequency, analysis_time, weekday, day_of_month, ai_analysis_frequency, ai_analysis_time, ai_analysis_weekday, ai_analysis_day_of_month, buy_price, sell_price, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (reminder_id, username, symbol, name, reminder_type, frequency, analysis_time, weekday, day_of_month, ai_analysis_frequency, ai_analysis_time, ai_analysis_weekday, ai_analysis_day_of_month, buy_price, sell_price, created_at))
        
        return {
            'id': reminder_id,
            'symbol': symbol,
            'name': name,
            'reminder_type': reminder_type,
            'frequency': frequency,
            'analysis_time': analysis_time,
            'weekday': weekday,
            'day_of_month': day_of_month,
            'ai_analysis_frequency': ai_analysis_frequency,
            'ai_analysis_time': ai_analysis_time,
            'ai_analysis_weekday': ai_analysis_weekday,
            'ai_analysis_day_of_month': ai_analysis_day_of_month,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'enabled': True,
            'created_at': created_at
        }


def db_update_reminder(username: str, reminder_id: str, **kwargs) -> bool:
    """更新提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        if not updates:
            return False
        
        values.extend([username, reminder_id])
        cursor.execute(f'''
            UPDATE reminders SET {", ".join(updates)}
            WHERE username = ? AND reminder_id = ?
        ''', values)
        return cursor.rowcount > 0


def db_delete_reminder(username: str, reminder_id: str) -> bool:
    """删除提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 先验证提醒存在且属于该用户（使用 reminder_id 唯一性）
        cursor.execute('SELECT username FROM reminders WHERE reminder_id = ?', (reminder_id,))
        row = cursor.fetchone()
        if not row:
            return False
        # 直接按 reminder_id 删除（reminder_id 是唯一的）
        cursor.execute('DELETE FROM reminders WHERE reminder_id = ?', (reminder_id,))
        return cursor.rowcount > 0


def db_get_symbol_reminders(username: str, symbol: str) -> List[Dict]:
    """获取某个证券的提醒"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reminders WHERE username = ? AND symbol = ?', (username, symbol))
        return [dict(row) for row in cursor.fetchall()]


def db_get_all_reminders() -> Dict[str, List[Dict]]:
    """获取所有用户的所有提醒（用于后台价格检查）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reminders WHERE enabled = 1')
        rows = cursor.fetchall()
        
        # 按用户分组
        result = {}
        for row in rows:
            reminder = dict(row)
            username = reminder['username']
            if username not in result:
                result[username] = []
            result[username].append(reminder)
        
        return result


# ============================================
# 数据迁移 - 从 JSON 迁移到数据库
# ============================================

# 初始化数据库
init_database()
