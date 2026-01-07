"""
============================================
数据库模块
Database Module - SQLite
============================================
"""

import sqlite3
import json
from datetime import datetime, timedelta
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
        
        # 提醒历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                reminder_type TEXT NOT NULL,
                buy_price REAL,
                buy_quantity INTEGER,
                sell_price REAL,
                sell_quantity INTEGER,
                current_price REAL,
                message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_username ON watchlist(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_username ON reports(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_username ON reminders(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_logs_username ON reminder_logs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_logs_symbol ON reminder_logs(username, symbol)')
        
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
        
        # 检查 watchlist 表是否有技术分析参考价位字段（仅供学习研究参考，不构成投资建议）
        if 'ai_buy_price' not in watchlist_columns:
            print("迁移: 添加 ai_buy_price 字段到 watchlist 表（技术分析参考低位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_buy_price REAL")
        
        if 'ai_sell_price' not in watchlist_columns:
            print("迁移: 添加 ai_sell_price 字段到 watchlist 表（技术分析参考高位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_sell_price REAL")
        
        if 'ai_price_updated_at' not in watchlist_columns:
            print("迁移: 添加 ai_price_updated_at 字段到 watchlist 表")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_price_updated_at TEXT")
        
        if 'last_alert_at' not in watchlist_columns:
            print("迁移: 添加 last_alert_at 字段到 watchlist 表")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN last_alert_at TEXT")
        
        # 检查 watchlist 表是否有持有周期字段
        if 'holding_period' not in watchlist_columns:
            print("迁移: 添加 holding_period 字段到 watchlist 表")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN holding_period TEXT DEFAULT 'swing'")
        
        # 检查 watchlist 表是否有参考数量字段（仅供学习研究参考）
        if 'ai_buy_quantity' not in watchlist_columns:
            print("迁移: 添加 ai_buy_quantity 字段到 watchlist 表（参考数量）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_buy_quantity INTEGER")
        
        if 'ai_sell_quantity' not in watchlist_columns:
            print("迁移: 添加 ai_sell_quantity 字段到 watchlist 表（参考数量）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_sell_quantity INTEGER")
        
        # 检查 watchlist 表是否有技术面评级字段（强势/偏强/中性/偏弱/弱势）
        if 'ai_recommendation' not in watchlist_columns:
            print("迁移: 添加 ai_recommendation 字段到 watchlist 表（技术面评级）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_recommendation TEXT")
        
        # 检查 watchlist 表是否有 from_ai_pick 字段（标记是否来自研究列表）
        if 'from_ai_pick' not in watchlist_columns:
            print("迁移: 添加 from_ai_pick 字段到 watchlist 表")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN from_ai_pick INTEGER DEFAULT 0")
        
        # 检查 users 表是否有 pushplus_token 字段
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'pushplus_token' not in user_columns:
            print("迁移: 添加 pushplus_token 字段到 users 表")
            cursor.execute("ALTER TABLE users ADD COLUMN pushplus_token TEXT")
        
        # 检查 users 表是否有 wechat_openid 字段 (微信公众号推送)
        if 'wechat_openid' not in user_columns:
            print("迁移: 添加 wechat_openid 字段到 users 表")
            cursor.execute("ALTER TABLE users ADD COLUMN wechat_openid TEXT")
        
        # 检查 users 表是否有 can_view_ai_picks 字段 (研究列表查看权限)
        if 'can_view_ai_picks' not in user_columns:
            print("迁移: 添加 can_view_ai_picks 字段到 users 表")
            cursor.execute("ALTER TABLE users ADD COLUMN can_view_ai_picks INTEGER DEFAULT 0")
        
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
        
        # 检查 reminders 表是否有持有周期字段
        if 'holding_period' not in reminder_columns:
            print("迁移: 添加 holding_period 字段到 reminders 表")
            cursor.execute("ALTER TABLE reminders ADD COLUMN holding_period TEXT DEFAULT 'swing'")
        
        # 创建研究列表表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT,
                type TEXT,
                added_by TEXT NOT NULL,
                added_at TEXT NOT NULL,
                FOREIGN KEY (added_by) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_picks_symbol ON ai_picks(symbol)')
        print("迁移: 研究列表表已创建/检查完成")
        
        # 创建用户已处理的研究列表表（用户添加到自选或手动删除的标的）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_dismissed_ai_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                dismissed_at TEXT NOT NULL,
                UNIQUE(username, symbol),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_dismissed_ai_picks ON user_dismissed_ai_picks(username, symbol)')
        print("迁移: 用户已处理研究列表表已创建/检查完成")
        
        # 创建用户操作记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_detail TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_username ON user_activity_logs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_created_at ON user_activity_logs(created_at)')
        print("迁移: 用户操作记录表已创建/检查完成")
        
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
                   COALESCE(starred, 0) as starred,
                   ai_buy_price, ai_sell_price, ai_price_updated_at, last_alert_at,
                   COALESCE(holding_period, 'swing') as holding_period,
                   ai_buy_quantity, ai_sell_quantity, ai_recommendation,
                   COALESCE(from_ai_pick, 0) as from_ai_pick
            FROM watchlist WHERE username = ? 
            ORDER BY starred DESC, added_at DESC
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]


def db_add_to_watchlist(username: str, symbol: str, name: str = None, 
                        type_: str = None, position: float = None, 
                        cost_price: float = None, from_ai_pick: int = 0) -> bool:
    """添加到自选"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO watchlist (username, symbol, name, type, position, cost_price, from_ai_pick, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, symbol, name, type_, position, cost_price, from_ai_pick, datetime.now().isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False


def db_remove_from_watchlist(username: str, symbol: str) -> bool:
    """从自选中移除，同时删除关联的报告、提醒、任务数据"""
    symbol = symbol.upper()  # 统一转大写
    with get_db() as conn:
        cursor = conn.cursor()
        # 删除自选（同时匹配大小写变体）
        cursor.execute('DELETE FROM watchlist WHERE username = ? AND UPPER(symbol) = ?', (username, symbol))
        deleted = cursor.rowcount > 0
        
        # 无论是否删除成功，都尝试清理关联数据（处理历史遗留数据）
        # 删除关联的报告（匹配多种格式：纯代码、带后缀的代码）
        cursor.execute('DELETE FROM reports WHERE username = ? AND (UPPER(symbol) = ? OR UPPER(symbol) LIKE ? OR UPPER(symbol) LIKE ?)', 
                      (username, symbol, f"{symbol}.%", f"%.{symbol}"))
        # 删除关联的提醒
        cursor.execute('DELETE FROM reminders WHERE username = ? AND (UPPER(symbol) = ? OR UPPER(symbol) LIKE ? OR UPPER(symbol) LIKE ?)', 
                      (username, symbol, f"{symbol}.%", f"%.{symbol}"))
        # 删除关联的分析任务
        cursor.execute('DELETE FROM analysis_tasks WHERE username = ? AND (UPPER(symbol) = ? OR UPPER(symbol) LIKE ? OR UPPER(symbol) LIKE ?)', 
                      (username, symbol, f"{symbol}.%", f"%.{symbol}"))
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


def db_update_watchlist_ai_prices(username: str, symbol: str, 
                                   ai_buy_price: float = None, 
                                   ai_sell_price: float = None,
                                   ai_buy_quantity: int = None,
                                   ai_sell_quantity: int = None,
                                   ai_recommendation: str = None) -> bool:
    """更新自选项的技术分析参考价位（参考低位/参考高位）和技术面评级
    
    注意：这些数据仅供个人学习研究参考，不构成任何投资建议。
    - ai_buy_price: 技术分析参考低位（支撑位）
    - ai_sell_price: 技术分析参考高位（阻力位）
    - ai_recommendation: 技术面评级（强势/偏强/中性/偏弱/弱势）
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE watchlist 
            SET ai_buy_price = ?, ai_sell_price = ?, 
                ai_buy_quantity = ?, ai_sell_quantity = ?,
                ai_recommendation = ?,
                ai_price_updated_at = ?
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', (ai_buy_price, ai_sell_price, ai_buy_quantity, ai_sell_quantity, 
              ai_recommendation, datetime.now().isoformat(), username, symbol))
        return cursor.rowcount > 0


def db_get_all_watchlist_with_ai_prices() -> List[Dict]:
    """获取所有设置了技术分析参考价位的自选项（用于价格变动提醒）
    
    注意：价格提醒仅用于通知用户价格已到达技术分析的参考位置，
    不构成任何买入或卖出建议。用户应自行判断是否进行任何操作。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.username, w.symbol, w.name, w.type, 
                   w.ai_buy_price, w.ai_sell_price, w.last_alert_at,
                   w.ai_buy_quantity, w.ai_sell_quantity,
                   u.wechat_openid, u.pushplus_token
            FROM watchlist w
            JOIN users u ON w.username = u.username
            WHERE (w.ai_buy_price IS NOT NULL OR w.ai_sell_price IS NOT NULL)
              AND u.status = 'approved'
        ''')
        return [dict(row) for row in cursor.fetchall()]


def db_update_watchlist_last_alert(username: str, symbol: str) -> bool:
    """更新自选项的最后提醒时间"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE watchlist 
            SET last_alert_at = ?
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', (datetime.now().isoformat(), username, symbol))
        return cursor.rowcount > 0


# ============================================
# 报告管理
# ============================================

def db_save_report(username: str, symbol: str, name: str, report_data: Dict) -> int:
    """保存报告"""
    from datetime import timedelta
    # 使用北京时间 (UTC+8)
    beijing_now = datetime.utcnow() + timedelta(hours=8)
    
    print(f"[DB报告保存] username={username}, symbol={symbol}, name={name}")
    
    with get_db() as conn:
        cursor = conn.cursor()
        # 先删除旧报告（同时删除点号和下划线格式）
        symbol_with_dot = symbol.replace('_', '.')
        symbol_with_underscore = symbol.replace('.', '_')
        cursor.execute('''
            DELETE FROM reports WHERE username = ? AND (
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?)
            )
        ''', (username, symbol, symbol_with_dot, symbol_with_underscore))
        deleted = cursor.rowcount
        print(f"[DB报告保存] 删除旧报告: {deleted} 条")
        
        # 插入新报告
        cursor.execute('''
            INSERT INTO reports (username, symbol, name, report_data, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, symbol, name, json.dumps(report_data, ensure_ascii=False), beijing_now.isoformat()))
        report_id = cursor.lastrowid
        print(f"[DB报告保存] 新报告ID: {report_id}")
        return report_id


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


def db_get_user_reports_summary(username: str) -> List[Dict]:
    """获取用户所有报告的摘要信息（不加载完整report_data，提升性能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, symbol, name, 
                   json_extract(report_data, '$.recommendation') as recommendation,
                   json_extract(report_data, '$.quant_score') as quant_score,
                   json_extract(report_data, '$.price') as price,
                   json_extract(report_data, '$.change_percent') as change_percent,
                   created_at 
            FROM reports WHERE username = ? ORDER BY created_at DESC
        ''', (username,))
        reports = []
        for row in cursor.fetchall():
            reports.append({
                'id': row['id'],
                'symbol': row['symbol'],
                'name': row['name'],
                'recommendation': row['recommendation'],
                'quant_score': row['quant_score'],
                'price': row['price'],
                'change_percent': row['change_percent'],
                'created_at': row['created_at'],
                'status': 'completed'
            })
        return reports


def db_get_user_report(username: str, symbol: str) -> Optional[Dict]:
    """获取用户某个证券的报告"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 同时查询下划线格式和点号格式（兼容新旧数据）
        # 例如：SPAX_PVT 和 SPAX.PVT
        symbol_with_dot = symbol.replace('_', '.')
        symbol_with_underscore = symbol.replace('.', '_')
        print(f"[DB报告查询] username={username}, symbol={symbol}, dot={symbol_with_dot}, underscore={symbol_with_underscore}")
        cursor.execute('''
            SELECT id, symbol, name, report_data, created_at 
            FROM reports 
            WHERE username = ? AND (
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?)
            )
            ORDER BY created_at DESC LIMIT 1
        ''', (username, symbol, symbol_with_dot, symbol_with_underscore))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            print(f"[DB报告查询] 找到报告: id={report['id']}, symbol={report['symbol']}")
            report['report_data'] = json.loads(report['report_data'])
            return report
        print(f"[DB报告查询] 未找到报告")
        return None


def db_delete_report(username: str, symbol: str) -> bool:
    """删除报告"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 同时删除下划线格式和点号格式（兼容新旧数据）
        symbol_with_dot = symbol.replace('_', '.')
        symbol_with_underscore = symbol.replace('.', '_')
        cursor.execute('''
            DELETE FROM reports 
            WHERE username = ? AND (
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?) OR 
                UPPER(symbol) = UPPER(?)
            )
        ''', (username, symbol, symbol_with_dot, symbol_with_underscore))
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
        cursor.execute('SELECT * FROM reminders WHERE username = ?', (username,))
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
    """添加价格触发提醒（24小时内相同字段去重）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查24小时内是否已存在相同配置的提醒（不比较 analysis_time）
        time_24h_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute('''
            SELECT reminder_id FROM reminders 
            WHERE username = ? AND symbol = ? AND reminder_type = ? 
            AND frequency = ?
            AND (weekday IS ? OR (weekday IS NULL AND ? IS NULL))
            AND (day_of_month IS ? OR (day_of_month IS NULL AND ? IS NULL))
            AND created_at > ?
        ''', (username, symbol, reminder_type, frequency,
              weekday, weekday, day_of_month, day_of_month, time_24h_ago))
        
        existing = cursor.fetchone()
        if existing:
            # 24小时内已存在相同配置的提醒，返回 None 表示重复
            return None
        
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


# ============================================
# 提醒历史记录
# ============================================

def db_add_reminder_log(username: str, symbol: str, name: str, reminder_type: str,
                        buy_price: float = None, buy_quantity: int = None,
                        sell_price: float = None, sell_quantity: int = None,
                        current_price: float = None, message: str = None) -> bool:
    """添加提醒历史记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO reminder_logs (username, symbol, name, reminder_type, 
                buy_price, buy_quantity, sell_price, sell_quantity, current_price, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, symbol, name, reminder_type, buy_price, buy_quantity, 
              sell_price, sell_quantity, current_price, message, created_at))
        return cursor.rowcount > 0


def db_get_reminder_logs(username: str, symbol: str = None, limit: int = 50) -> List[Dict]:
    """获取提醒历史记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        if symbol:
            cursor.execute('''
                SELECT * FROM reminder_logs 
                WHERE username = ? AND symbol = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM reminder_logs 
                WHERE username = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, limit))
        return [dict(row) for row in cursor.fetchall()]


def db_delete_user(username: str) -> bool:
    """删除用户及其所有数据"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 删除用户的所有关联数据
        cursor.execute('DELETE FROM watchlist WHERE username = ?', (username,))
        cursor.execute('DELETE FROM reports WHERE username = ?', (username,))
        cursor.execute('DELETE FROM reminders WHERE username = ?', (username,))
        cursor.execute('DELETE FROM analysis_tasks WHERE username = ?', (username,))
        cursor.execute('DELETE FROM sessions WHERE username = ?', (username,))
        # 删除用户
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        return cursor.rowcount > 0


def db_update_user_info(username: str, new_username: str = None, phone: str = None) -> bool:
    """更新用户信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        
        if new_username and new_username != username:
            updates.append("username = ?")
            values.append(new_username)
        if phone:
            updates.append("phone = ?")
            values.append(phone)
        
        if not updates:
            return False
        
        values.append(username)
        cursor.execute(f'''
            UPDATE users SET {", ".join(updates)}
            WHERE username = ?
        ''', values)
        
        # 如果用户名变更，需要更新所有关联表
        if new_username and new_username != username:
            cursor.execute('UPDATE watchlist SET username = ? WHERE username = ?', (new_username, username))
            cursor.execute('UPDATE reports SET username = ? WHERE username = ?', (new_username, username))
            cursor.execute('UPDATE reminders SET username = ? WHERE username = ?', (new_username, username))
            cursor.execute('UPDATE analysis_tasks SET username = ? WHERE username = ?', (new_username, username))
            cursor.execute('UPDATE sessions SET username = ? WHERE username = ?', (new_username, username))
        
        return True


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
# 研究列表管理
# ============================================

def db_get_ai_picks() -> List[Dict]:
    """获取所有研究列表标的"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT symbol, name, type, added_by, added_at 
            FROM ai_picks 
            ORDER BY added_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def db_add_ai_pick(symbol: str, name: str, type_: str, added_by: str) -> bool:
    """添加研究列表标的"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ai_picks (symbol, name, type, added_by, added_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol.upper(), name, type_, added_by, datetime.now().isoformat()))
            return True
        except sqlite3.IntegrityError:
            # 已存在，更新信息
            cursor.execute('''
                UPDATE ai_picks SET name = ?, type = ?, added_by = ?, added_at = ?
                WHERE symbol = ?
            ''', (name, type_, added_by, datetime.now().isoformat(), symbol.upper()))
            return True


def db_remove_ai_pick(symbol: str) -> bool:
    """移除研究列表标的"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ai_picks WHERE symbol = ?', (symbol.upper(),))
        return cursor.rowcount > 0


def db_update_ai_pick(symbol: str, name: str = None, type_: str = None) -> bool:
    """更新研究列表标的的名称和类型"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if type_:
            updates.append("type = ?")
            params.append(type_)
        
        if not updates:
            return False
        
        params.append(symbol.upper())
        cursor.execute(f'''
            UPDATE ai_picks SET {", ".join(updates)}
            WHERE symbol = ?
        ''', params)
        return cursor.rowcount > 0


def db_is_ai_pick(symbol: str) -> bool:
    """检查是否是研究列表标的"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM ai_picks WHERE symbol = ?', (symbol.upper(),))
        return cursor.fetchone() is not None


def db_get_ai_picks_for_user(username: str) -> List[Dict]:
    """获取用户可见的研究列表标的（排除已处理的）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ap.symbol, ap.name, ap.type, ap.added_by, ap.added_at 
            FROM ai_picks ap
            WHERE ap.symbol NOT IN (
                SELECT symbol FROM user_dismissed_ai_picks WHERE username = ?
            )
            ORDER BY ap.added_at DESC
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]


def db_dismiss_ai_pick(username: str, symbol: str) -> bool:
    """用户标记研究列表标的为已处理（添加到自选或手动删除）"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_dismissed_ai_picks (username, symbol, dismissed_at)
                VALUES (?, ?, ?)
            ''', (username, symbol.upper(), datetime.now().isoformat()))
            return True
        except sqlite3.IntegrityError:
            # 已存在
            return True


def db_dismiss_ai_picks_batch(username: str, symbols: List[str]) -> int:
    """批量标记研究列表标的为已处理"""
    with get_db() as conn:
        cursor = conn.cursor()
        count = 0
        for symbol in symbols:
            try:
                cursor.execute('''
                    INSERT INTO user_dismissed_ai_picks (username, symbol, dismissed_at)
                    VALUES (?, ?, ?)
                ''', (username, symbol.upper(), datetime.now().isoformat()))
                count += 1
            except sqlite3.IntegrityError:
                pass
        return count


def db_dismiss_all_ai_picks(username: str) -> int:
    """用户清空所有研究列表（标记所有当前的为已处理）"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 获取所有当前的研究列表
        cursor.execute('SELECT symbol FROM ai_picks')
        symbols = [row['symbol'] for row in cursor.fetchall()]
        
        count = 0
        for symbol in symbols:
            try:
                cursor.execute('''
                    INSERT INTO user_dismissed_ai_picks (username, symbol, dismissed_at)
                    VALUES (?, ?, ?)
                ''', (username, symbol, datetime.now().isoformat()))
                count += 1
            except sqlite3.IntegrityError:
                pass
        return count


def db_clear_ai_picks_daily():
    """每日清空研究列表（保留当天添加的）"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 获取今天的日期（北京时间）
        from datetime import timezone, timedelta
        beijing_tz = timezone(timedelta(hours=8))
        today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        
        # 删除非今天添加的研究列表标的
        cursor.execute('''
            DELETE FROM ai_picks 
            WHERE date(added_at) < date(?)
        ''', (today,))
        deleted_count = cursor.rowcount
        
        # 同时清空用户已处理记录（因为原始数据已删除）
        cursor.execute('''
            DELETE FROM user_dismissed_ai_picks 
            WHERE symbol NOT IN (SELECT symbol FROM ai_picks)
        ''')
        
        print(f"[研究列表清理] 已删除 {deleted_count} 条非今日数据")
        return deleted_count


def db_get_user_ai_picks_permission(username: str) -> bool:
    """检查用户是否有研究列表查看权限"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT can_view_ai_picks, role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            # 管理员始终有权限
            if row['role'] == 'admin':
                return True
            return row['can_view_ai_picks'] == 1
        return False


def db_set_user_ai_picks_permission(username: str, can_view: bool) -> bool:
    """设置用户研究列表查看权限"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET can_view_ai_picks = ? WHERE username = ?
        ''', (1 if can_view else 0, username))
        return cursor.rowcount > 0


# ============================================
# 用户操作记录
# ============================================

def db_add_user_activity(username: str, action_type: str, action_detail: str = None,
                         ip_address: str = None, user_agent: str = None) -> int:
    """添加用户操作记录"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    created_at = datetime.now(beijing_tz).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_activity_logs (username, action_type, action_detail, ip_address, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, action_type, action_detail, ip_address, user_agent, created_at))
        return cursor.lastrowid


def db_get_user_activities(username: str, limit: int = 50) -> List[Dict]:
    """获取用户操作记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, action_type, action_detail, ip_address, created_at
            FROM user_activity_logs 
            WHERE username = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (username, limit))
        return [dict(row) for row in cursor.fetchall()]


# ============================================
# 数据迁移 - 从 JSON 迁移到数据库
# ============================================

# 初始化数据库
init_database()
