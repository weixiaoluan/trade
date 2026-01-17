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
        
        # 用户操作记录表
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
            print("迁移: 添加 ai_buy_price 字段到 watchlist 表（技术分析支撑位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_buy_price REAL")
        
        if 'ai_sell_price' not in watchlist_columns:
            print("迁移: 添加 ai_sell_price 字段到 watchlist 表（技术分析阻力位）")
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
        
        # 检查 watchlist 表是否有多周期价位字段
        # 短线价位
        if 'short_support' not in watchlist_columns:
            print("迁移: 添加 short_support 字段到 watchlist 表（短线支撑位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN short_support REAL")
        if 'short_resistance' not in watchlist_columns:
            print("迁移: 添加 short_resistance 字段到 watchlist 表（短线阻力位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN short_resistance REAL")
        if 'short_risk' not in watchlist_columns:
            print("迁移: 添加 short_risk 字段到 watchlist 表（短线风险位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN short_risk REAL")
        
        # 波段价位
        if 'swing_support' not in watchlist_columns:
            print("迁移: 添加 swing_support 字段到 watchlist 表（波段支撑位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN swing_support REAL")
        if 'swing_resistance' not in watchlist_columns:
            print("迁移: 添加 swing_resistance 字段到 watchlist 表（波段阻力位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN swing_resistance REAL")
        if 'swing_risk' not in watchlist_columns:
            print("迁移: 添加 swing_risk 字段到 watchlist 表（波段风险位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN swing_risk REAL")
        
        # 中长线价位
        if 'long_support' not in watchlist_columns:
            print("迁移: 添加 long_support 字段到 watchlist 表（中长线支撑位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN long_support REAL")
        if 'long_resistance' not in watchlist_columns:
            print("迁移: 添加 long_resistance 字段到 watchlist 表（中长线阻力位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN long_resistance REAL")
        if 'long_risk' not in watchlist_columns:
            print("迁移: 添加 long_risk 字段到 watchlist 表（中长线风险位）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN long_risk REAL")
        
        # 检查 watchlist 表是否有技术面评级字段（强势/偏强/中性/偏弱/弱势）
        if 'ai_recommendation' not in watchlist_columns:
            print("迁移: 添加 ai_recommendation 字段到 watchlist 表（技术面评级）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN ai_recommendation TEXT")
        
        # 检查 watchlist 表是否有多周期信号类型字段（buy/sell/hold）
        if 'short_signal' not in watchlist_columns:
            print("迁移: 添加 short_signal 字段到 watchlist 表（短线信号类型）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN short_signal TEXT")
        if 'swing_signal' not in watchlist_columns:
            print("迁移: 添加 swing_signal 字段到 watchlist 表（波段信号类型）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN swing_signal TEXT")
        if 'long_signal' not in watchlist_columns:
            print("迁移: 添加 long_signal 字段到 watchlist 表（中长线信号类型）")
            cursor.execute("ALTER TABLE watchlist ADD COLUMN long_signal TEXT")
        
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
        
        # 检查 sim_trade_positions 表是否有新字段
        cursor.execute("PRAGMA table_info(sim_trade_positions)")
        sim_pos_columns = [col[1] for col in cursor.fetchall()]
        
        if 'highest_price' not in sim_pos_columns:
            print("迁移: 添加 highest_price 字段到 sim_trade_positions 表（移动止损用）")
            cursor.execute("ALTER TABLE sim_trade_positions ADD COLUMN highest_price REAL")
        
        if 'sold_ratio' not in sim_pos_columns:
            print("迁移: 添加 sold_ratio 字段到 sim_trade_positions 表（分批卖出记录）")
            cursor.execute("ALTER TABLE sim_trade_positions ADD COLUMN sold_ratio REAL DEFAULT 0")
        
        if 'add_count' not in sim_pos_columns:
            print("迁移: 添加 add_count 字段到 sim_trade_positions 表（加仓次数）")
            cursor.execute("ALTER TABLE sim_trade_positions ADD COLUMN add_count INTEGER DEFAULT 0")
        
        # ============================================
        # 策略池相关表迁移
        # ============================================
        
        # 创建策略配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                allocated_capital REAL DEFAULT 100000,
                params TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, strategy_id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_configs_username ON strategy_configs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_configs_strategy_id ON strategy_configs(strategy_id)')
        print("迁移: 策略配置表已创建/检查完成")
        
        # 创建策略表现统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_return REAL DEFAULT 0,
                daily_return REAL DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                position_value REAL DEFAULT 0,
                UNIQUE(username, strategy_id, date),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_performance_username ON strategy_performance(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy_id ON strategy_performance(strategy_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_performance_date ON strategy_performance(date)')
        print("迁移: 策略表现统计表已创建/检查完成")
        
        # 添加 strategy_id 字段到 sim_trade_positions 表
        if 'strategy_id' not in sim_pos_columns:
            print("迁移: 添加 strategy_id 字段到 sim_trade_positions 表")
            cursor.execute("ALTER TABLE sim_trade_positions ADD COLUMN strategy_id TEXT")
        
        # 检查 sim_trade_records 表是否有 strategy_id 字段
        cursor.execute("PRAGMA table_info(sim_trade_records)")
        sim_rec_columns = [col[1] for col in cursor.fetchall()]
        
        if 'strategy_id' not in sim_rec_columns:
            print("迁移: 添加 strategy_id 字段到 sim_trade_records 表")
            cursor.execute("ALTER TABLE sim_trade_records ADD COLUMN strategy_id TEXT")
        
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
                   COALESCE(from_ai_pick, 0) as from_ai_pick,
                   short_support, short_resistance, short_risk,
                   swing_support, swing_resistance, swing_risk,
                   long_support, long_resistance, long_risk,
                   short_signal, swing_signal, long_signal
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
                                   ai_recommendation: str = None,
                                   multi_period_prices: dict = None,
                                   multi_period_signals: dict = None) -> bool:
    """更新自选项的技术分析参考价位（支撑位/阻力位）和技术面评级
    
    注意：这些数据仅供个人学习研究参考，不构成任何投资建议。
    - ai_buy_price: 技术分析支撑位（当前周期）
    - ai_sell_price: 技术分析阻力位（当前周期）
    - ai_recommendation: 技术面评级（强势/偏强/中性/偏弱/弱势）
    - multi_period_prices: 多周期价位数据 {
        'short': {'support': x, 'resistance': x, 'risk': x},
        'swing': {'support': x, 'resistance': x, 'risk': x},
        'long': {'support': x, 'resistance': x, 'risk': x}
      }
    - multi_period_signals: 多周期信号类型 {
        'short': 'buy'/'sell'/'hold',
        'swing': 'buy'/'sell'/'hold',
        'long': 'buy'/'sell'/'hold'
      }
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 基础更新
        updates = [
            'ai_buy_price = ?', 'ai_sell_price = ?',
            'ai_buy_quantity = ?', 'ai_sell_quantity = ?',
            'ai_recommendation = ?', 'ai_price_updated_at = ?'
        ]
        params = [ai_buy_price, ai_sell_price, ai_buy_quantity, ai_sell_quantity,
                  ai_recommendation, datetime.now().isoformat()]
        
        # 多周期价位更新
        if multi_period_prices:
            short = multi_period_prices.get('short', {})
            swing = multi_period_prices.get('swing', {})
            long = multi_period_prices.get('long', {})
            
            updates.extend([
                'short_support = ?', 'short_resistance = ?', 'short_risk = ?',
                'swing_support = ?', 'swing_resistance = ?', 'swing_risk = ?',
                'long_support = ?', 'long_resistance = ?', 'long_risk = ?'
            ])
            params.extend([
                short.get('support'), short.get('resistance'), short.get('risk'),
                swing.get('support'), swing.get('resistance'), swing.get('risk'),
                long.get('support'), long.get('resistance'), long.get('risk')
            ])
        
        # 多周期信号类型更新
        if multi_period_signals:
            updates.extend([
                'short_signal = ?', 'swing_signal = ?', 'long_signal = ?'
            ])
            params.extend([
                multi_period_signals.get('short'),
                multi_period_signals.get('swing'),
                multi_period_signals.get('long')
            ])
        
        params.extend([username, symbol])
        
        cursor.execute(f'''
            UPDATE watchlist 
            SET {', '.join(updates)}
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', params)
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
# 模拟交易系统
# ============================================

def init_sim_trade_tables():
    """初始化模拟交易相关表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 模拟交易账户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sim_trade_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                initial_capital REAL DEFAULT 1000000,
                current_capital REAL DEFAULT 1000000,
                total_profit REAL DEFAULT 0,
                total_profit_pct REAL DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                auto_trade_enabled INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 模拟持仓表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sim_trade_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                type TEXT,
                quantity INTEGER NOT NULL,
                cost_price REAL NOT NULL,
                current_price REAL,
                profit REAL DEFAULT 0,
                profit_pct REAL DEFAULT 0,
                buy_date TEXT NOT NULL,
                buy_signal TEXT,
                holding_period TEXT DEFAULT 'swing',
                trade_rule TEXT DEFAULT 'T+1',
                can_sell_date TEXT,
                highest_price REAL,
                sold_ratio REAL DEFAULT 0,
                UNIQUE(username, symbol),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 模拟交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sim_trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                signal_type TEXT,
                signal_strength INTEGER,
                signal_conditions TEXT,
                profit REAL,
                profit_pct REAL,
                holding_days INTEGER,
                trade_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sim_positions_username ON sim_trade_positions(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sim_records_username ON sim_trade_records(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sim_records_symbol ON sim_trade_records(username, symbol)')
        
        # 监控日志表（记录自动交易的监控活动）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sim_trade_monitor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                log_type TEXT NOT NULL,
                symbol TEXT,
                message TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monitor_logs_username ON sim_trade_monitor_logs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monitor_logs_created_at ON sim_trade_monitor_logs(created_at)')
        
        conn.commit()
        print("模拟交易表初始化完成")


def db_get_sim_account(username: str) -> Optional[Dict]:
    """获取用户模拟交易账户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sim_trade_accounts WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def db_create_sim_account(username: str, initial_capital: float = 1000000) -> Dict:
    """创建模拟交易账户"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO sim_trade_accounts 
                (username, initial_capital, current_capital, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, initial_capital, initial_capital, now, now))
            return {
                'username': username,
                'initial_capital': initial_capital,
                'current_capital': initial_capital,
                'total_profit': 0,
                'total_profit_pct': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'auto_trade_enabled': 0,
                'created_at': now,
                'updated_at': now
            }
        except sqlite3.IntegrityError:
            # 已存在，返回现有账户
            return db_get_sim_account(username)


def db_update_sim_account(username: str, **kwargs) -> bool:
    """更新模拟交易账户"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    kwargs['updated_at'] = datetime.now(beijing_tz).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        values.append(username)
        cursor.execute(f'''
            UPDATE sim_trade_accounts SET {", ".join(updates)}
            WHERE username = ?
        ''', values)
        return cursor.rowcount > 0


def db_get_sim_positions(username: str) -> List[Dict]:
    """获取用户模拟持仓"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sim_trade_positions 
            WHERE username = ? 
            ORDER BY buy_date DESC
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]


def db_get_sim_position(username: str, symbol: str) -> Optional[Dict]:
    """获取某个标的的持仓"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sim_trade_positions 
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', (username, symbol))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# 交易日历缓存
_trading_calendar_cache = {
    'data': None,
    'year': None
}


def get_trading_calendar(year: int = None) -> set:
    """
    获取交易日历（使用 akshare 接口）
    返回指定年份的所有交易日集合
    """
    from datetime import timezone, timedelta
    
    if year is None:
        beijing_tz = timezone(timedelta(hours=8))
        year = datetime.now(beijing_tz).year
    
    # 检查缓存
    if _trading_calendar_cache['data'] and _trading_calendar_cache['year'] == year:
        return _trading_calendar_cache['data']
    
    try:
        import akshare as ak
        # 获取交易日历
        df = ak.tool_trade_date_hist_sina()
        # 筛选指定年份的交易日
        trading_days = set()
        for _, row in df.iterrows():
            date_str = str(row['trade_date'])
            if date_str.startswith(str(year)):
                trading_days.add(date_str)
        
        # 也获取下一年的数据（用于跨年计算）
        next_year = year + 1
        for _, row in df.iterrows():
            date_str = str(row['trade_date'])
            if date_str.startswith(str(next_year)):
                trading_days.add(date_str)
        
        if trading_days:
            _trading_calendar_cache['data'] = trading_days
            _trading_calendar_cache['year'] = year
            print(f"[交易日历] 已加载 {year} 年交易日历，共 {len(trading_days)} 个交易日")
            return trading_days
    except Exception as e:
        print(f"[交易日历] 获取失败: {e}，使用简化判断")
    
    return None


def is_trading_day_real(date_str: str) -> bool:
    """
    判断指定日期是否为交易日（使用真实交易日历）
    date_str: 格式 'YYYY-MM-DD'
    """
    from datetime import timezone, timedelta
    
    # 尝试获取交易日历
    year = int(date_str[:4])
    calendar = get_trading_calendar(year)
    
    if calendar:
        # 转换格式 'YYYY-MM-DD' -> 'YYYYMMDD'
        date_compact = date_str.replace('-', '')
        return date_compact in calendar
    
    # 降级：简单判断周末
    from datetime import datetime as dt
    date_obj = dt.strptime(date_str, '%Y-%m-%d')
    return date_obj.weekday() < 5


def get_next_n_trading_day(start_date, n: int) -> str:
    """
    获取从start_date开始的第N个交易日
    T+0: n=0, T+1: n=1, T+2: n=2
    使用真实交易日历，跳过周末和节假日
    """
    from datetime import timedelta
    
    if n == 0:
        return start_date.strftime('%Y-%m-%d')
    
    # 尝试获取交易日历
    year = start_date.year
    calendar = get_trading_calendar(year)
    
    current = start_date
    trading_days_counted = 0
    
    while trading_days_counted < n:
        current = current + timedelta(days=1)
        date_str = current.strftime('%Y-%m-%d')
        
        if calendar:
            # 使用真实交易日历
            date_compact = date_str.replace('-', '')
            if date_compact in calendar:
                trading_days_counted += 1
        else:
            # 降级：只判断周末
            if current.weekday() < 5:
                trading_days_counted += 1
    
    return current.strftime('%Y-%m-%d')


def db_add_sim_position(username: str, symbol: str, name: str, type_: str,
                        quantity: int, cost_price: float, buy_signal: str = None,
                        holding_period: str = 'swing', trade_rule: str = 'T+1') -> bool:
    """添加模拟持仓"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    buy_date = now.strftime('%Y-%m-%d')
    
    # 根据交易规则计算可卖出日期（只算交易日）
    if trade_rule == 'T+0':
        can_sell_date = get_next_n_trading_day(now, 0)
    elif trade_rule == 'T+1':
        can_sell_date = get_next_n_trading_day(now, 1)
    elif trade_rule == 'T+2':
        can_sell_date = get_next_n_trading_day(now, 2)
    else:
        can_sell_date = get_next_n_trading_day(now, 1)
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO sim_trade_positions 
                (username, symbol, name, type, quantity, cost_price, current_price,
                 buy_date, buy_signal, holding_period, trade_rule, can_sell_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, symbol.upper(), name, type_, quantity, cost_price, cost_price,
                  buy_date, buy_signal, holding_period, trade_rule, can_sell_date))
            return True
        except sqlite3.IntegrityError:
            # 已有持仓，更新（加仓）
            cursor.execute('''
                UPDATE sim_trade_positions 
                SET quantity = quantity + ?,
                    cost_price = (cost_price * quantity + ? * ?) / (quantity + ?),
                    buy_signal = ?
                WHERE username = ? AND UPPER(symbol) = UPPER(?)
            ''', (quantity, cost_price, quantity, quantity, buy_signal, username, symbol))
            return cursor.rowcount > 0


def db_update_sim_position(username: str, symbol: str, **kwargs) -> bool:
    """更新模拟持仓"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        values.extend([username, symbol])
        cursor.execute(f'''
            UPDATE sim_trade_positions SET {", ".join(updates)}
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', values)
        return cursor.rowcount > 0


def db_remove_sim_position(username: str, symbol: str) -> bool:
    """删除模拟持仓"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM sim_trade_positions 
            WHERE username = ? AND UPPER(symbol) = UPPER(?)
        ''', (username, symbol))
        return cursor.rowcount > 0


def db_add_sim_trade_record(username: str, symbol: str, name: str, trade_type: str,
                            quantity: int, price: float, signal_type: str = None,
                            signal_strength: int = None, signal_conditions: str = None,
                            profit: float = None, profit_pct: float = None,
                            holding_days: int = None) -> int:
    """添加模拟交易记录"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    trade_date = now.strftime('%Y-%m-%d')
    created_at = now.isoformat()
    amount = quantity * price
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sim_trade_records 
            (username, symbol, name, trade_type, quantity, price, amount,
             signal_type, signal_strength, signal_conditions,
             profit, profit_pct, holding_days, trade_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, symbol.upper(), name, trade_type, quantity, price, amount,
              signal_type, signal_strength, signal_conditions,
              profit, profit_pct, holding_days, trade_date, created_at))
        return cursor.lastrowid


def db_get_sim_trade_records(username: str, symbol: str = None, limit: int = 100) -> List[Dict]:
    """获取模拟交易记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        if symbol:
            cursor.execute('''
                SELECT * FROM sim_trade_records 
                WHERE username = ? AND UPPER(symbol) = UPPER(?)
                ORDER BY created_at DESC LIMIT ?
            ''', (username, symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM sim_trade_records 
                WHERE username = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, limit))
        return [dict(row) for row in cursor.fetchall()]


def db_get_sim_trade_stats(username: str) -> Dict:
    """获取模拟交易统计"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 总交易次数
        cursor.execute('''
            SELECT COUNT(*) as total_trades,
                   SUM(CASE WHEN trade_type = 'buy' THEN 1 ELSE 0 END) as buy_count,
                   SUM(CASE WHEN trade_type = 'sell' THEN 1 ELSE 0 END) as sell_count
            FROM sim_trade_records WHERE username = ?
        ''', (username,))
        row = cursor.fetchone()
        total_trades = row['total_trades'] or 0
        buy_count = row['buy_count'] or 0
        sell_count = row['sell_count'] or 0
        
        # 盈亏统计（只统计卖出记录）
        cursor.execute('''
            SELECT SUM(profit) as total_profit,
                   SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as win_count,
                   SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as loss_count,
                   AVG(profit_pct) as avg_profit_pct,
                   MAX(profit_pct) as max_profit_pct,
                   MIN(profit_pct) as min_profit_pct,
                   AVG(holding_days) as avg_holding_days
            FROM sim_trade_records 
            WHERE username = ? AND trade_type = 'sell' AND profit IS NOT NULL
        ''', (username,))
        row = cursor.fetchone()
        
        total_profit = row['total_profit'] or 0
        win_count = row['win_count'] or 0
        loss_count = row['loss_count'] or 0
        avg_profit_pct = row['avg_profit_pct'] or 0
        max_profit_pct = row['max_profit_pct'] or 0
        min_profit_pct = row['min_profit_pct'] or 0
        avg_holding_days = row['avg_holding_days'] or 0
        
        win_rate = (win_count / (win_count + loss_count) * 100) if (win_count + loss_count) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'total_profit': round(total_profit, 2),
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': round(win_rate, 2),
            'avg_profit_pct': round(avg_profit_pct, 2),
            'max_profit_pct': round(max_profit_pct, 2),
            'min_profit_pct': round(min_profit_pct, 2),
            'avg_holding_days': round(avg_holding_days, 1)
        }


def get_trade_rule(symbol: str, type_: str = None) -> str:
    """根据标的类型获取交易规则
    
    A股交易规则：
    - 股票: T+1 (当天买入，次日才能卖出)
    - 境内ETF: T+1 (如沪深300ETF、中证500ETF等)
    - 跨境ETF/境外ETF: T+0 (如纳指ETF、标普ETF、恒生ETF、日经ETF等)
    - 货币ETF: T+0
    - 债券ETF: T+0
    - 黄金ETF: T+0
    - 场内基金LOF: T+1
    - 可转债: T+0
    - 港股通: T+0
    - 美股: T+0 (但有T+2结算)
    
    跨境ETF代码规则（T+0）：
    - 上证: 513xxx (跨境ETF), 518xxx (黄金ETF), 511xxx (货币/债券ETF)
    - 深证: 159941 (纳指ETF), 159920 (恒生ETF) 等特定代码
    """
    symbol = symbol.upper()
    
    # 根据代码判断类型
    if symbol.isdigit() and len(symbol) == 6:
        # 中国市场
        
        # 可转债: 11xxxx(上证), 12xxxx(深证) - T+0
        if symbol.startswith('11') or symbol.startswith('12'):
            return 'T+0'
        
        # 上证ETF
        if symbol.startswith('5'):
            # 跨境ETF: 513xxx (纳指、标普、日经、德国、法国、恒生科技等) - T+0
            if symbol.startswith('513'):
                return 'T+0'
            # 黄金ETF: 518xxx - T+0
            if symbol.startswith('518'):
                return 'T+0'
            # 货币ETF/债券ETF: 511xxx - T+0
            if symbol.startswith('511'):
                return 'T+0'
            # 其他上证ETF: 510xxx, 512xxx, 515xxx, 516xxx, 517xxx, 520xxx, 560xxx, 561xxx, 562xxx, 563xxx, 588xxx - T+1
            return 'T+1'
        
        # 深证ETF: 159xxx
        if symbol.startswith('159'):
            # 跨境ETF - T+0
            cross_border_etf_159 = [
                '159941',  # 纳指ETF
                '159920',  # 恒生ETF
                '159954',  # 港股通50ETF (部分券商支持T+0)
                '159934',  # 黄金ETF
                '159937',  # 黄金ETF博时
                '159812',  # 纳指科技ETF
                '159509',  # 纳指100ETF
                '159513',  # 纳斯达克ETF
                '159632',  # 标普500ETF
                '159655',  # 标普ETF
                '159866',  # 日经ETF
                '159506',  # 日经225ETF
                '159507',  # 德国ETF
                '159508',  # 法国ETF
                '159605',  # 恒生科技ETF
                '159740',  # 恒生科技30ETF
                '159742',  # 恒生互联网ETF
                '159892',  # 恒生医疗ETF
                '159847',  # 中概互联网ETF
                '159636',  # 越南ETF
                '159615',  # 东南亚科技ETF
                '159660',  # 亚太低碳ETF
                '159696',  # 印度基金ETF
            ]
            if symbol in cross_border_etf_159:
                return 'T+0'
            # 货币ETF - T+0
            if symbol.startswith('1599') and symbol in ['159001', '159003', '159005']:
                return 'T+0'
            # 其他深证ETF - T+1
            return 'T+1'
        
        # LOF: 16xxxx(深证) - T+1
        if symbol.startswith('16'):
            return 'T+1'
        
        # A股: 其他6位数字 - T+1
        return 'T+1'
    
    elif '.HK' in symbol or symbol.endswith('HK'):
        # 港股 - T+0
        return 'T+0'
    else:
        # 美股等 - T+0
        return 'T+0'



# ============================================
# 自动交易相关查询
# ============================================

def db_get_all_auto_trade_users() -> List[Dict]:
    """获取所有开启自动交易的用户账户
    
    用于后台调度器自动执行交易
    返回开启了自动交易的用户列表及其账户信息
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.username, a.initial_capital, a.current_capital, 
                   a.total_profit, a.total_profit_pct, a.win_count, 
                   a.loss_count, a.win_rate, a.auto_trade_enabled,
                   a.created_at, a.updated_at
            FROM sim_trade_accounts a
            JOIN users u ON a.username = u.username
            WHERE a.auto_trade_enabled = 1 AND u.status = 'approved'
        ''')
        return [dict(row) for row in cursor.fetchall()]


def db_get_auto_trade_user_count() -> int:
    """获取开启自动交易的用户数量"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM sim_trade_accounts a
            JOIN users u ON a.username = u.username
            WHERE a.auto_trade_enabled = 1 AND u.status = 'approved'
        ''')
        return cursor.fetchone()[0]


def db_add_monitor_log(username: str, log_type: str, message: str, 
                       symbol: str = None, details: str = None) -> bool:
    """添加监控日志
    
    log_type: 
        - 'scan': 扫描监控
        - 'signal': 信号触发
        - 'trade': 交易执行
        - 'risk': 风控触发
        - 'error': 错误
        - 'info': 信息
    """
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sim_trade_monitor_logs 
            (username, log_type, symbol, message, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, log_type, symbol, message, details, now))
        return True


def db_get_monitor_logs(username: str, limit: int = 100, log_type: str = None) -> List[Dict]:
    """获取监控日志"""
    with get_db() as conn:
        cursor = conn.cursor()
        if log_type:
            cursor.execute('''
                SELECT * FROM sim_trade_monitor_logs 
                WHERE username = ? AND log_type = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, log_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM sim_trade_monitor_logs 
                WHERE username = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, limit))
        return [dict(row) for row in cursor.fetchall()]


def db_clear_old_monitor_logs(days: int = 7) -> int:
    """清理旧的监控日志"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    cutoff = (datetime.now(beijing_tz) - timedelta(days=days)).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sim_trade_monitor_logs WHERE created_at < ?', (cutoff,))
        return cursor.rowcount


# 初始化模拟交易表
try:
    init_sim_trade_tables()
except Exception as e:
    print(f"初始化模拟交易表失败: {e}")


# ============================================
# 策略配置管理
# ============================================

def db_get_user_strategy_configs(username: str) -> List[Dict]:
    """获取用户的所有策略配置
    
    Args:
        username: 用户名
        
    Returns:
        策略配置列表
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, strategy_id, enabled, allocated_capital, 
                   params, created_at, updated_at
            FROM strategy_configs
            WHERE username = ?
            ORDER BY created_at DESC
        ''', (username,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            config = dict(row)
            # 解析 params JSON
            if config.get('params'):
                try:
                    config['params'] = json.loads(config['params'])
                except:
                    config['params'] = {}
            else:
                config['params'] = {}
            result.append(config)
        return result


def db_get_strategy_config(username: str, strategy_id: str) -> Optional[Dict]:
    """获取单个策略配置
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        
    Returns:
        策略配置，不存在返回None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, strategy_id, enabled, allocated_capital, 
                   params, created_at, updated_at
            FROM strategy_configs
            WHERE username = ? AND strategy_id = ?
        ''', (username, strategy_id))
        row = cursor.fetchone()
        if row:
            config = dict(row)
            if config.get('params'):
                try:
                    config['params'] = json.loads(config['params'])
                except:
                    config['params'] = {}
            else:
                config['params'] = {}
            return config
        return None


def db_save_user_strategy_config(username: str, strategy_id: str, 
                                  enabled: bool = True,
                                  allocated_capital: float = 10000.0,
                                  params: Dict = None) -> bool:
    """保存用户策略配置（新增或更新）
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        enabled: 是否启用
        allocated_capital: 分配资金
        params: 策略参数
        
    Returns:
        是否保存成功
    """
    now = datetime.now().isoformat()
    params_json = json.dumps(params) if params else None
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO strategy_configs 
                (username, strategy_id, enabled, allocated_capital, params, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username, strategy_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    allocated_capital = excluded.allocated_capital,
                    params = excluded.params,
                    updated_at = excluded.updated_at
            ''', (username, strategy_id, 1 if enabled else 0, allocated_capital, 
                  params_json, now, now))
            return True
        except Exception as e:
            print(f"保存策略配置失败: {e}")
            return False


def db_update_strategy_config(username: str, strategy_id: str, **kwargs) -> bool:
    """更新策略配置
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        **kwargs: 要更新的字段 (enabled, allocated_capital, params)
        
    Returns:
        是否更新成功
    """
    with get_db() as conn:
        cursor = conn.cursor()
        updates = ['updated_at = ?']
        values = [datetime.now().isoformat()]
        
        if 'enabled' in kwargs:
            updates.append('enabled = ?')
            values.append(1 if kwargs['enabled'] else 0)
        
        if 'allocated_capital' in kwargs:
            updates.append('allocated_capital = ?')
            values.append(kwargs['allocated_capital'])
        
        if 'params' in kwargs:
            updates.append('params = ?')
            values.append(json.dumps(kwargs['params']) if kwargs['params'] else None)
        
        values.extend([username, strategy_id])
        
        cursor.execute(f'''
            UPDATE strategy_configs 
            SET {', '.join(updates)}
            WHERE username = ? AND strategy_id = ?
        ''', values)
        return cursor.rowcount > 0


def db_delete_strategy_config(username: str, strategy_id: str) -> bool:
    """删除策略配置
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        
    Returns:
        是否删除成功
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM strategy_configs
            WHERE username = ? AND strategy_id = ?
        ''', (username, strategy_id))
        return cursor.rowcount > 0


def db_get_enabled_strategy_configs(username: str) -> List[Dict]:
    """获取用户启用的策略配置
    
    Args:
        username: 用户名
        
    Returns:
        启用的策略配置列表
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, strategy_id, enabled, allocated_capital, 
                   params, created_at, updated_at
            FROM strategy_configs
            WHERE username = ? AND enabled = 1
            ORDER BY created_at DESC
        ''', (username,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            config = dict(row)
            if config.get('params'):
                try:
                    config['params'] = json.loads(config['params'])
                except:
                    config['params'] = {}
            else:
                config['params'] = {}
            result.append(config)
        return result


def db_get_total_allocated_capital(username: str) -> float:
    """获取用户已分配的总资金
    
    Args:
        username: 用户名
        
    Returns:
        已分配总资金
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COALESCE(SUM(allocated_capital), 0)
            FROM strategy_configs
            WHERE username = ? AND enabled = 1
        ''', (username,))
        return cursor.fetchone()[0]


# ============================================
# 策略性能统计
# ============================================

def db_save_strategy_performance(username: str, strategy_id: str, date: str,
                                  total_return: float = 0, daily_return: float = 0,
                                  win_count: int = 0, loss_count: int = 0,
                                  win_rate: float = 0, max_drawdown: float = 0,
                                  sharpe_ratio: float = 0, trade_count: int = 0,
                                  position_value: float = 0) -> bool:
    """保存策略性能数据
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        date: 日期 (YYYY-MM-DD)
        其他: 性能指标
        
    Returns:
        是否保存成功
    """
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO strategy_performance 
                (username, strategy_id, date, total_return, daily_return,
                 win_count, loss_count, win_rate, max_drawdown, sharpe_ratio,
                 trade_count, position_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username, strategy_id, date) DO UPDATE SET
                    total_return = excluded.total_return,
                    daily_return = excluded.daily_return,
                    win_count = excluded.win_count,
                    loss_count = excluded.loss_count,
                    win_rate = excluded.win_rate,
                    max_drawdown = excluded.max_drawdown,
                    sharpe_ratio = excluded.sharpe_ratio,
                    trade_count = excluded.trade_count,
                    position_value = excluded.position_value
            ''', (username, strategy_id, date, total_return, daily_return,
                  win_count, loss_count, win_rate, max_drawdown, sharpe_ratio,
                  trade_count, position_value))
            return True
        except Exception as e:
            print(f"保存策略性能数据失败: {e}")
            return False


def db_get_strategy_performance(username: str, strategy_id: str, 
                                 start_date: str = None, end_date: str = None) -> List[Dict]:
    """获取策略性能数据
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)
        
    Returns:
        性能数据列表
    """
    with get_db() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT * FROM strategy_performance
            WHERE username = ? AND strategy_id = ?
        '''
        params = [username, strategy_id]
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY date DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def db_get_latest_strategy_performance(username: str, strategy_id: str) -> Optional[Dict]:
    """获取策略最新性能数据
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        
    Returns:
        最新性能数据
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM strategy_performance
            WHERE username = ? AND strategy_id = ?
            ORDER BY date DESC LIMIT 1
        ''', (username, strategy_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def db_get_all_strategies_performance(username: str, date: str = None) -> List[Dict]:
    """获取用户所有策略的性能数据
    
    Args:
        username: 用户名
        date: 指定日期 (可选，默认获取最新)
        
    Returns:
        所有策略的性能数据列表
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if date:
            cursor.execute('''
                SELECT * FROM strategy_performance
                WHERE username = ? AND date = ?
            ''', (username, date))
        else:
            # 获取每个策略的最新数据
            cursor.execute('''
                SELECT sp.* FROM strategy_performance sp
                INNER JOIN (
                    SELECT strategy_id, MAX(date) as max_date
                    FROM strategy_performance
                    WHERE username = ?
                    GROUP BY strategy_id
                ) latest ON sp.strategy_id = latest.strategy_id 
                       AND sp.date = latest.max_date
                WHERE sp.username = ?
            ''', (username, username))
        return [dict(row) for row in cursor.fetchall()]


def db_get_strategy_performance_summary(username: str, strategy_id: str) -> Optional[Dict]:
    """获取策略性能汇总
    
    Args:
        username: 用户名
        strategy_id: 策略ID
        
    Returns:
        性能汇总数据
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                strategy_id,
                COUNT(*) as days,
                MAX(total_return) as total_return,
                AVG(daily_return) as avg_daily_return,
                SUM(win_count) as total_wins,
                SUM(loss_count) as total_losses,
                SUM(trade_count) as total_trades,
                MAX(max_drawdown) as max_drawdown,
                AVG(sharpe_ratio) as avg_sharpe
            FROM strategy_performance
            WHERE username = ? AND strategy_id = ?
        ''', (username, strategy_id))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            total = result.get('total_wins', 0) + result.get('total_losses', 0)
            result['overall_win_rate'] = result.get('total_wins', 0) / total if total > 0 else 0
            return result
        return None


# ============================================
# 数据迁移 - 从 JSON 迁移到数据库
# ============================================

# 初始化数据库
init_database()
