"""
============================================
ETF数据同步服务
ETF Data Sync Service
============================================

负责:
- 定时同步ETF日线数据
- 更新溢价率数据
- 刷新实时行情缓存
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

from .etf_data_source import get_etf_data_manager, ETFDataManager
from .etf_database import (
    db_save_etf_info, db_save_etf_daily, db_get_latest_etf_date,
    db_save_etf_premium, db_update_etf_realtime, db_get_all_etf_info
)

logger = logging.getLogger(__name__)


# 默认ETF池 - 策略需要的标的
DEFAULT_ETF_POOL = [
    # 全球ETF动量轮动
    {'symbol': '513100.SH', 'name': '纳指ETF', 'is_qdii': True, 'trading_rule': 'T+0'},
    {'symbol': '510300.SH', 'name': '沪深300ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '518880.SH', 'name': '黄金ETF', 'is_qdii': False, 'trading_rule': 'T+0'},
    {'symbol': '511880.SH', 'name': '货币ETF', 'is_qdii': False, 'trading_rule': 'T+0'},
    
    # 二八轮动
    {'symbol': '510500.SH', 'name': '中证500ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    
    # 行业动量轮动
    {'symbol': '512760.SH', 'name': '芯片ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '159928.SZ', 'name': '消费ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '512010.SH', 'name': '医药ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '512070.SH', 'name': '证券ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '516160.SH', 'name': '新能源ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '512660.SH', 'name': '军工ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    
    # 其他常用ETF
    {'symbol': '159915.SZ', 'name': '创业板ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '510050.SH', 'name': '上证50ETF', 'is_qdii': False, 'trading_rule': 'T+1'},
    {'symbol': '513050.SH', 'name': '中概互联ETF', 'is_qdii': True, 'trading_rule': 'T+0'},
    {'symbol': '513060.SH', 'name': '恒生科技ETF', 'is_qdii': True, 'trading_rule': 'T+0'},
]


class ETFSyncService:
    """ETF数据同步服务"""
    
    def __init__(self, data_manager: ETFDataManager = None):
        self.data_manager = data_manager or get_etf_data_manager()
        self.etf_pool = DEFAULT_ETF_POOL
    
    def init_etf_pool(self) -> int:
        """
        初始化ETF池信息到数据库
        
        Returns:
            成功保存的数量
        """
        saved = 0
        for etf in self.etf_pool:
            success = db_save_etf_info(
                symbol=etf['symbol'],
                name=etf['name'],
                is_qdii=etf.get('is_qdii', False),
                trading_rule=etf.get('trading_rule', 'T+1'),
                max_premium_rate=0.05 if etf.get('is_qdii') else 0.03
            )
            if success:
                saved += 1
        
        logger.info(f"初始化ETF池完成，保存{saved}个ETF信息")
        return saved
    
    def sync_etf_daily(self, symbol: str, days: int = 252, 
                        force: bool = False) -> int:
        """
        同步单个ETF的日线数据
        
        Args:
            symbol: ETF代码
            days: 同步天数
            force: 是否强制全量同步
            
        Returns:
            同步的记录数
        """
        try:
            # 获取最新数据日期
            latest_date = db_get_latest_etf_date(symbol)
            
            if latest_date and not force:
                # 增量同步
                start_date = latest_date
                logger.info(f"增量同步{symbol}，从{start_date}开始")
            else:
                # 全量同步
                start_date = (datetime.now() - timedelta(days=int(days * 1.5))).strftime('%Y-%m-%d')
                logger.info(f"全量同步{symbol}，从{start_date}开始")
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 获取数据
            df = self.data_manager.get_etf_daily(symbol, start_date, end_date)
            
            if df.empty:
                logger.warning(f"未获取到{symbol}的数据")
                return 0
            
            # 保存到数据库
            saved = db_save_etf_daily(symbol, df)
            return saved
            
        except Exception as e:
            logger.error(f"同步{symbol}日线数据失败: {e}")
            return 0
    
    def sync_all_etf_daily(self, days: int = 252, force: bool = False) -> Dict[str, int]:
        """
        同步所有ETF的日线数据
        
        Returns:
            {symbol: 同步记录数}
        """
        results = {}
        
        for etf in self.etf_pool:
            symbol = etf['symbol']
            count = self.sync_etf_daily(symbol, days, force)
            results[symbol] = count
            
            # 避免请求过快
            time.sleep(0.5)
        
        total = sum(results.values())
        logger.info(f"同步完成，共更新{total}条记录")
        return results
    
    def sync_etf_premium(self, symbol: str) -> bool:
        """同步单个ETF的溢价率"""
        try:
            premium = self.data_manager.get_etf_premium(symbol)
            date = datetime.now().strftime('%Y-%m-%d')
            
            # 获取实时行情用于市价
            realtime = self.data_manager.get_etf_realtime(symbol)
            market_price = realtime.get('current_price', 0) if realtime else 0
            
            success = db_save_etf_premium(
                symbol=symbol,
                date=date,
                premium_rate=premium,
                market_price=market_price
            )
            
            return success
            
        except Exception as e:
            logger.error(f"同步{symbol}溢价率失败: {e}")
            return False
    
    def sync_all_etf_premium(self) -> Dict[str, bool]:
        """同步所有ETF的溢价率"""
        results = {}
        
        for etf in self.etf_pool:
            symbol = etf['symbol']
            success = self.sync_etf_premium(symbol)
            results[symbol] = success
            time.sleep(0.3)
        
        return results
    
    def update_realtime_cache(self, symbol: str) -> bool:
        """更新单个ETF的实时行情缓存"""
        try:
            data = self.data_manager.get_etf_realtime(symbol)
            
            if not data:
                return False
            
            # 添加溢价率
            data['premium_rate'] = self.data_manager.get_etf_premium(symbol)
            
            return db_update_etf_realtime(symbol, data)
            
        except Exception as e:
            logger.error(f"更新{symbol}实时行情失败: {e}")
            return False
    
    def update_all_realtime_cache(self) -> Dict[str, bool]:
        """更新所有ETF的实时行情缓存"""
        results = {}
        
        for etf in self.etf_pool:
            symbol = etf['symbol']
            success = self.update_realtime_cache(symbol)
            results[symbol] = success
            time.sleep(0.2)
        
        return results
    
    def get_strategy_data(self, symbols: List[str], days: int = 60) -> Dict:
        """
        获取策略所需的数据
        
        Args:
            symbols: ETF代码列表
            days: 获取的天数
            
        Returns:
            包含价格数据和溢价率数据的字典
        """
        from .etf_database import db_get_multiple_etf_daily, db_get_multiple_etf_premium
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=int(days * 1.5))).strftime('%Y-%m-%d')
        
        # 获取价格数据
        price_data = db_get_multiple_etf_daily(symbols, start_date, end_date)
        
        # 获取溢价率数据
        premium_data = db_get_multiple_etf_premium(symbols, start_date, end_date)
        
        return {
            'prices': price_data,
            'premium': premium_data
        }


# 全局同步服务实例
_sync_service: Optional[ETFSyncService] = None


def get_sync_service() -> ETFSyncService:
    """获取同步服务单例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = ETFSyncService()
    return _sync_service


def sync_etf_data_task():
    """
    定时任务：同步ETF数据
    
    在scheduler中调用
    """
    try:
        service = get_sync_service()
        
        # 同步日线数据（增量）
        logger.info("[ETF同步] 开始同步日线数据...")
        service.sync_all_etf_daily(days=60, force=False)
        
        # 同步溢价率
        logger.info("[ETF同步] 开始同步溢价率...")
        service.sync_all_etf_premium()
        
        # 更新实时行情缓存
        logger.info("[ETF同步] 开始更新实时行情...")
        service.update_all_realtime_cache()
        
        logger.info("[ETF同步] 同步完成")
        
    except Exception as e:
        logger.error(f"[ETF同步] 同步失败: {e}")


def init_etf_data():
    """
    初始化ETF数据
    
    首次运行时调用，下载历史数据
    """
    try:
        service = get_sync_service()
        
        # 初始化ETF池信息
        logger.info("[ETF初始化] 初始化ETF池...")
        service.init_etf_pool()
        
        # 全量同步日线数据
        logger.info("[ETF初始化] 开始全量同步日线数据...")
        service.sync_all_etf_daily(days=756, force=True)  # 约3年
        
        logger.info("[ETF初始化] 初始化完成")
        
    except Exception as e:
        logger.error(f"[ETF初始化] 初始化失败: {e}")
