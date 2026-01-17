"""
============================================
ETF数据库模块
ETF Database Module
============================================

SQLite存储:
- ETF日线行情数据
- ETF溢价率数据
- ETF基本信息
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "etf_data.db"


def get_etf_db():
    """获取ETF数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_etf_tables():
    """初始化ETF相关表"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        
        # ETF基本信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_info (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                fund_type TEXT,
                market TEXT,
                trading_rule TEXT DEFAULT 'T+1',
                is_qdii INTEGER DEFAULT 0,
                max_premium_rate REAL DEFAULT 0.03,
                min_capital REAL DEFAULT 10000,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # ETF日线行情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                adj_close REAL,
                created_at TEXT,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_etf_daily_symbol_date 
            ON etf_daily(symbol, date)
        ''')
        
        # ETF溢价率表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_premium (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                premium_rate REAL,
                market_price REAL,
                nav REAL,
                created_at TEXT,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_etf_premium_symbol_date 
            ON etf_premium(symbol, date)
        ''')
        
        # ETF实时行情缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_realtime (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                current_price REAL,
                open REAL,
                high REAL,
                low REAL,
                pre_close REAL,
                volume REAL,
                amount REAL,
                change_pct REAL,
                premium_rate REAL,
                updated_at TEXT
            )
        ''')
        
        # 策略信号历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                username TEXT NOT NULL,
                signal_date TEXT NOT NULL,
                target_symbol TEXT,
                signal_type TEXT,
                signal_strength REAL,
                confidence REAL,
                reason TEXT,
                executed INTEGER DEFAULT 0,
                created_at TEXT,
                UNIQUE(strategy_id, username, signal_date)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_strategy_signals_user 
            ON strategy_signals(username, strategy_id, signal_date)
        ''')
        
        conn.commit()
        logger.info("ETF数据库表初始化完成")


# ============================================
# ETF基本信息操作
# ============================================

def db_save_etf_info(symbol: str, name: str, fund_type: str = None,
                      market: str = None, trading_rule: str = 'T+1',
                      is_qdii: bool = False, max_premium_rate: float = 0.03) -> bool:
    """保存ETF基本信息"""
    now = datetime.now().isoformat()
    with get_etf_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO etf_info 
                (symbol, name, fund_type, market, trading_rule, is_qdii, 
                 max_premium_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    fund_type = excluded.fund_type,
                    market = excluded.market,
                    trading_rule = excluded.trading_rule,
                    is_qdii = excluded.is_qdii,
                    max_premium_rate = excluded.max_premium_rate,
                    updated_at = excluded.updated_at
            ''', (symbol, name, fund_type, market, trading_rule,
                  1 if is_qdii else 0, max_premium_rate, now, now))
            return True
        except Exception as e:
            logger.error(f"保存ETF信息失败: {e}")
            return False


def db_get_etf_info(symbol: str) -> Optional[Dict]:
    """获取ETF基本信息"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM etf_info WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


def db_get_all_etf_info() -> List[Dict]:
    """获取所有ETF信息"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM etf_info ORDER BY symbol')
        return [dict(row) for row in cursor.fetchall()]


# ============================================
# ETF日线数据操作
# ============================================

def db_save_etf_daily(symbol: str, data: pd.DataFrame) -> int:
    """
    批量保存ETF日线数据
    
    Args:
        symbol: ETF代码
        data: 包含 date, open, high, low, close, volume, amount 的DataFrame
        
    Returns:
        保存的记录数
    """
    if data.empty:
        return 0
    
    now = datetime.now().isoformat()
    saved = 0
    
    with get_etf_db() as conn:
        cursor = conn.cursor()
        
        for _, row in data.iterrows():
            try:
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
                
                cursor.execute('''
                    INSERT INTO etf_daily 
                    (symbol, date, open, high, low, close, volume, amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, date) DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume,
                        amount = excluded.amount
                ''', (symbol, date_str, 
                      row.get('open'), row.get('high'), row.get('low'), 
                      row.get('close'), row.get('volume'), row.get('amount'), now))
                saved += 1
            except Exception as e:
                logger.error(f"保存{symbol} {row.get('date')}数据失败: {e}")
        
        conn.commit()
    
    logger.info(f"保存{symbol}日线数据{saved}条")
    return saved


def db_get_etf_daily(symbol: str, start_date: str = None, 
                      end_date: str = None, limit: int = None) -> pd.DataFrame:
    """
    获取ETF日线数据
    
    Args:
        symbol: ETF代码
        start_date: 开始日期
        end_date: 结束日期
        limit: 限制返回条数
        
    Returns:
        DataFrame
    """
    with get_etf_db() as conn:
        query = 'SELECT * FROM etf_daily WHERE symbol = ?'
        params = [symbol]
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY date DESC'
        
        if limit:
            query += f' LIMIT {limit}'
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        return df


def db_get_multiple_etf_daily(symbols: List[str], start_date: str = None,
                               end_date: str = None) -> pd.DataFrame:
    """
    获取多个ETF的日线数据（宽表格式）
    
    Returns:
        DataFrame: 索引为日期，列为各ETF收盘价
    """
    all_data = {}
    
    for symbol in symbols:
        df = db_get_etf_daily(symbol, start_date, end_date)
        if not df.empty:
            df = df.set_index('date')
            all_data[symbol] = df['close']
    
    if not all_data:
        return pd.DataFrame()
    
    result = pd.DataFrame(all_data)
    result = result.sort_index()
    result = result.ffill()
    
    return result


def db_get_latest_etf_date(symbol: str) -> Optional[str]:
    """获取ETF最新数据日期"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(date) as latest_date FROM etf_daily WHERE symbol = ?
        ''', (symbol,))
        row = cursor.fetchone()
        return row['latest_date'] if row and row['latest_date'] else None


# ============================================
# ETF溢价率操作
# ============================================

def db_save_etf_premium(symbol: str, date: str, premium_rate: float,
                         market_price: float = None, nav: float = None) -> bool:
    """保存ETF溢价率"""
    now = datetime.now().isoformat()
    with get_etf_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO etf_premium 
                (symbol, date, premium_rate, market_price, nav, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, date) DO UPDATE SET
                    premium_rate = excluded.premium_rate,
                    market_price = excluded.market_price,
                    nav = excluded.nav
            ''', (symbol, date, premium_rate, market_price, nav, now))
            return True
        except Exception as e:
            logger.error(f"保存溢价率失败: {e}")
            return False


def db_get_etf_premium(symbol: str, start_date: str = None,
                        end_date: str = None) -> pd.DataFrame:
    """获取ETF溢价率数据"""
    with get_etf_db() as conn:
        query = 'SELECT * FROM etf_premium WHERE symbol = ?'
        params = [symbol]
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY date DESC'
        
        return pd.read_sql_query(query, conn, params=params)


def db_get_latest_premium(symbol: str) -> Optional[float]:
    """获取最新溢价率"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT premium_rate FROM etf_premium 
            WHERE symbol = ? ORDER BY date DESC LIMIT 1
        ''', (symbol,))
        row = cursor.fetchone()
        return row['premium_rate'] if row else None


def db_get_multiple_etf_premium(symbols: List[str], start_date: str = None,
                                 end_date: str = None) -> pd.DataFrame:
    """获取多个ETF的溢价率数据（宽表格式）"""
    all_data = {}
    
    for symbol in symbols:
        df = db_get_etf_premium(symbol, start_date, end_date)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            all_data[symbol] = df['premium_rate']
    
    if not all_data:
        return pd.DataFrame()
    
    result = pd.DataFrame(all_data)
    result = result.sort_index()
    
    return result


# ============================================
# 实时行情缓存操作
# ============================================

def db_update_etf_realtime(symbol: str, data: Dict) -> bool:
    """更新ETF实时行情缓存"""
    now = datetime.now().isoformat()
    with get_etf_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO etf_realtime 
                (symbol, name, current_price, open, high, low, pre_close,
                 volume, amount, change_pct, premium_rate, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    current_price = excluded.current_price,
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    pre_close = excluded.pre_close,
                    volume = excluded.volume,
                    amount = excluded.amount,
                    change_pct = excluded.change_pct,
                    premium_rate = excluded.premium_rate,
                    updated_at = excluded.updated_at
            ''', (symbol, data.get('name'), data.get('current_price'),
                  data.get('open'), data.get('high'), data.get('low'),
                  data.get('pre_close'), data.get('volume'), data.get('amount'),
                  data.get('change_pct'), data.get('premium_rate'), now))
            return True
        except Exception as e:
            logger.error(f"更新实时行情失败: {e}")
            return False


def db_get_etf_realtime(symbol: str) -> Optional[Dict]:
    """获取ETF实时行情缓存"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM etf_realtime WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ============================================
# 策略信号操作
# ============================================

def db_save_strategy_signal(strategy_id: str, username: str, signal_date: str,
                             target_symbol: str, signal_type: str,
                             signal_strength: float = None, confidence: float = None,
                             reason: str = None) -> bool:
    """保存策略信号"""
    now = datetime.now().isoformat()
    with get_etf_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO strategy_signals 
                (strategy_id, username, signal_date, target_symbol, signal_type,
                 signal_strength, confidence, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id, username, signal_date) DO UPDATE SET
                    target_symbol = excluded.target_symbol,
                    signal_type = excluded.signal_type,
                    signal_strength = excluded.signal_strength,
                    confidence = excluded.confidence,
                    reason = excluded.reason
            ''', (strategy_id, username, signal_date, target_symbol, signal_type,
                  signal_strength, confidence, reason, now))
            return True
        except Exception as e:
            logger.error(f"保存策略信号失败: {e}")
            return False


def db_get_latest_strategy_signal(strategy_id: str, username: str) -> Optional[Dict]:
    """获取最新策略信号"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM strategy_signals 
            WHERE strategy_id = ? AND username = ?
            ORDER BY signal_date DESC LIMIT 1
        ''', (strategy_id, username))
        row = cursor.fetchone()
        return dict(row) if row else None


def db_mark_signal_executed(signal_id: int) -> bool:
    """标记信号已执行"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE strategy_signals SET executed = 1 WHERE id = ?
        ''', (signal_id,))
        return cursor.rowcount > 0


def db_get_pending_signals(username: str) -> List[Dict]:
    """获取待执行的信号"""
    with get_etf_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM strategy_signals 
            WHERE username = ? AND executed = 0
            ORDER BY signal_date DESC
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]


# 初始化表
try:
    init_etf_tables()
except Exception as e:
    logger.error(f"初始化ETF数据库表失败: {e}")
