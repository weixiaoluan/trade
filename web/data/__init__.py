"""
ETF数据模块
"""

from .etf_data_source import (
    ETFDataManager,
    AkShareDataSource,
    TushareDataSource,
    get_etf_data_manager,
    fetch_etf_daily,
    fetch_etf_realtime,
    fetch_multiple_etf,
)

from .etf_database import (
    init_etf_tables,
    db_save_etf_info,
    db_get_etf_info,
    db_get_all_etf_info,
    db_save_etf_daily,
    db_get_etf_daily,
    db_get_multiple_etf_daily,
    db_get_latest_etf_date,
    db_save_etf_premium,
    db_get_etf_premium,
    db_get_latest_premium,
    db_get_multiple_etf_premium,
    db_update_etf_realtime,
    db_get_etf_realtime,
    db_save_strategy_signal,
    db_get_latest_strategy_signal,
    db_mark_signal_executed,
    db_get_pending_signals,
)

from .etf_sync_service import (
    ETFSyncService,
    get_sync_service,
    sync_etf_data_task,
    init_etf_data,
    DEFAULT_ETF_POOL,
)

__all__ = [
    # Data Source
    'ETFDataManager',
    'AkShareDataSource',
    'TushareDataSource',
    'get_etf_data_manager',
    'fetch_etf_daily',
    'fetch_etf_realtime',
    'fetch_multiple_etf',
    # Database
    'init_etf_tables',
    'db_save_etf_info',
    'db_get_etf_info',
    'db_get_all_etf_info',
    'db_save_etf_daily',
    'db_get_etf_daily',
    'db_get_multiple_etf_daily',
    'db_get_latest_etf_date',
    'db_save_etf_premium',
    'db_get_etf_premium',
    'db_get_latest_premium',
    'db_get_multiple_etf_premium',
    'db_update_etf_realtime',
    'db_get_etf_realtime',
    'db_save_strategy_signal',
    'db_get_latest_strategy_signal',
    'db_mark_signal_executed',
    'db_get_pending_signals',
    # Sync Service
    'ETFSyncService',
    'get_sync_service',
    'sync_etf_data_task',
    'init_etf_data',
    'DEFAULT_ETF_POOL',
]
