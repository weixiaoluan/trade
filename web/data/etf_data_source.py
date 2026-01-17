"""
============================================
ETF数据源接入模块
ETF Data Source Integration
============================================

支持多数据源:
- tushare (需要token)
- akshare (免费)
- 本地缓存

提供统一的数据接口
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
import json
import time

logger = logging.getLogger(__name__)


class DataSourceBase(ABC):
    """数据源基类"""
    
    @abstractmethod
    def get_etf_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF日线数据"""
        pass
    
    @abstractmethod
    def get_etf_realtime(self, symbol: str) -> Dict:
        """获取ETF实时行情"""
        pass
    
    @abstractmethod
    def get_etf_premium(self, symbol: str, date: str = None) -> float:
        """获取ETF溢价率"""
        pass
    
    @abstractmethod
    def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        pass


class AkShareDataSource(DataSourceBase):
    """
    AkShare数据源 (免费)
    
    安装: pip install akshare
    """
    
    def __init__(self):
        self._ak = None
        self._init_akshare()
    
    def _init_akshare(self):
        """初始化akshare"""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("AkShare数据源初始化成功")
        except ImportError:
            logger.warning("AkShare未安装，请运行: pip install akshare")
            self._ak = None
    
    def _normalize_symbol(self, symbol: str) -> Tuple[str, str]:
        """
        标准化代码格式
        
        输入: 513100.SH / 510300.SH
        输出: (sz513100, sz) 或 (sh510300, sh)
        """
        code = symbol.split('.')[0]
        market = symbol.split('.')[1].lower() if '.' in symbol else ''
        
        if market == 'sh':
            return f"sh{code}", 'sh'
        elif market == 'sz':
            return f"sz{code}", 'sz'
        else:
            # 根据代码判断市场
            if code.startswith('5'):
                return f"sh{code}", 'sh'
            elif code.startswith('1'):
                return f"sz{code}", 'sz'
            else:
                return f"sh{code}", 'sh'
    
    def get_etf_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF日线数据
        
        Args:
            symbol: ETF代码 (如 513100.SH)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 包含 date, open, high, low, close, volume, amount
        """
        if self._ak is None:
            logger.error("AkShare未初始化")
            return pd.DataFrame()
        
        try:
            ak_symbol, market = self._normalize_symbol(symbol)
            code = symbol.split('.')[0]
            
            # 使用fund_etf_hist_em获取ETF历史数据
            df = self._ak.fund_etf_hist_em(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="hfq"  # 后复权
            )
            
            if df.empty:
                logger.warning(f"未获取到{symbol}的数据")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            # 确保日期格式
            df['date'] = pd.to_datetime(df['date'])
            df['symbol'] = symbol
            
            # 选择需要的列
            columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'amount']
            available_cols = [c for c in columns if c in df.columns]
            
            return df[available_cols].sort_values('date')
            
        except Exception as e:
            logger.error(f"获取{symbol}日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_realtime(self, symbol: str) -> Dict:
        """
        获取ETF实时行情
        
        Returns:
            Dict: 包含 current_price, open, high, low, volume, change_pct
        """
        if self._ak is None:
            return {}
        
        try:
            code = symbol.split('.')[0]
            
            # 获取ETF实时行情
            df = self._ak.fund_etf_spot_em()
            
            if df.empty:
                return {}
            
            # 查找对应的ETF
            row = df[df['代码'] == code]
            if row.empty:
                return {}
            
            row = row.iloc[0]
            
            return {
                'symbol': symbol,
                'name': row.get('名称', ''),
                'current_price': float(row.get('最新价', 0)),
                'open': float(row.get('开盘价', 0)),
                'high': float(row.get('最高价', 0)),
                'low': float(row.get('最低价', 0)),
                'pre_close': float(row.get('昨收', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取{symbol}实时行情失败: {e}")
            return {}
    
    def get_etf_premium(self, symbol: str, date: str = None) -> float:
        """
        获取ETF溢价率
        
        溢价率 = (市价 - 净值) / 净值
        
        Returns:
            float: 溢价率 (0.01 表示 1%)
        """
        if self._ak is None:
            return 0.0
        
        try:
            code = symbol.split('.')[0]
            
            # 获取ETF实时估值数据
            df = self._ak.fund_etf_spot_em()
            
            if df.empty:
                return 0.0
            
            row = df[df['代码'] == code]
            if row.empty:
                return 0.0
            
            row = row.iloc[0]
            
            # 计算溢价率
            price = float(row.get('最新价', 0))
            nav = float(row.get('基金净值', 0))  # 可能需要调整列名
            
            if nav > 0 and price > 0:
                premium = (price - nav) / nav
                return premium
            
            return 0.0
            
        except Exception as e:
            logger.error(f"获取{symbol}溢价率失败: {e}")
            return 0.0
    
    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF列表
        
        Returns:
            DataFrame: 包含 symbol, name, fund_type
        """
        if self._ak is None:
            return pd.DataFrame()
        
        try:
            df = self._ak.fund_etf_spot_em()
            
            if df.empty:
                return pd.DataFrame()
            
            # 标准化格式
            result = pd.DataFrame({
                'symbol': df['代码'].apply(lambda x: f"{x}.SH" if x.startswith('5') else f"{x}.SZ"),
                'name': df['名称'],
                'current_price': df['最新价'],
                'change_pct': df['涨跌幅']
            })
            
            return result
            
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return pd.DataFrame()
    
    def get_index_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数日线数据 (用于计算基准)
        
        Args:
            symbol: 指数代码 (如 000300 沪深300)
        """
        if self._ak is None:
            return pd.DataFrame()
        
        try:
            df = self._ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            return df.sort_values('date')
            
        except Exception as e:
            logger.error(f"获取指数{symbol}数据失败: {e}")
            return pd.DataFrame()


class TushareDataSource(DataSourceBase):
    """
    Tushare数据源 (需要token)
    
    注册获取token: https://tushare.pro/register
    安装: pip install tushare
    """
    
    def __init__(self, token: str = None):
        self._pro = None
        self._token = token
        self._init_tushare()
    
    def _init_tushare(self):
        """初始化tushare"""
        if not self._token:
            # 尝试从环境变量或配置获取
            import os
            self._token = os.environ.get('TUSHARE_TOKEN', '')
        
        if not self._token:
            logger.warning("Tushare token未配置")
            return
        
        try:
            import tushare as ts
            ts.set_token(self._token)
            self._pro = ts.pro_api()
            logger.info("Tushare数据源初始化成功")
        except ImportError:
            logger.warning("Tushare未安装，请运行: pip install tushare")
        except Exception as e:
            logger.error(f"Tushare初始化失败: {e}")
    
    def get_etf_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF日线数据"""
        if self._pro is None:
            return pd.DataFrame()
        
        try:
            # tushare格式: 510300.SH
            ts_symbol = symbol.replace('.SH', '.SH').replace('.SZ', '.SZ')
            
            df = self._pro.fund_daily(
                ts_code=ts_symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                'trade_date': 'date',
                'ts_code': 'symbol',
                'pre_close': 'pre_close',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
            
        except Exception as e:
            logger.error(f"Tushare获取{symbol}数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_realtime(self, symbol: str) -> Dict:
        """获取实时行情 (tushare实时数据需要更高权限)"""
        # 降级到akshare
        ak_source = AkShareDataSource()
        return ak_source.get_etf_realtime(symbol)
    
    def get_etf_premium(self, symbol: str, date: str = None) -> float:
        """获取溢价率"""
        if self._pro is None:
            return 0.0
        
        try:
            ts_symbol = symbol.replace('.SH', '.SH').replace('.SZ', '.SZ')
            
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            else:
                date = date.replace('-', '')
            
            # 获取ETF净值
            df = self._pro.fund_nav(ts_code=ts_symbol, end_date=date)
            
            if df.empty:
                return 0.0
            
            nav = df.iloc[0]['unit_nav']  # 单位净值
            
            # 获取当日收盘价
            price_df = self._pro.fund_daily(ts_code=ts_symbol, trade_date=date)
            if price_df.empty:
                return 0.0
            
            price = price_df.iloc[0]['close']
            
            if nav > 0:
                return (price - nav) / nav
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Tushare获取{symbol}溢价率失败: {e}")
            return 0.0
    
    def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        if self._pro is None:
            return pd.DataFrame()
        
        try:
            df = self._pro.fund_basic(market='E')  # E表示场内基金
            
            if df.empty:
                return pd.DataFrame()
            
            # 筛选ETF
            df = df[df['fund_type'].str.contains('ETF', na=False)]
            
            return df[['ts_code', 'name', 'fund_type']].rename(columns={
                'ts_code': 'symbol'
            })
            
        except Exception as e:
            logger.error(f"Tushare获取ETF列表失败: {e}")
            return pd.DataFrame()


class ETFDataManager:
    """
    ETF数据管理器
    
    统一管理多数据源，提供缓存和降级机制
    """
    
    def __init__(self, primary_source: str = 'akshare', tushare_token: str = None):
        """
        初始化数据管理器
        
        Args:
            primary_source: 主数据源 ('akshare' 或 'tushare')
            tushare_token: tushare token
        """
        self.sources: Dict[str, DataSourceBase] = {}
        self.primary_source = primary_source
        
        # 初始化数据源
        self.sources['akshare'] = AkShareDataSource()
        
        if tushare_token:
            self.sources['tushare'] = TushareDataSource(tushare_token)
        
        logger.info(f"ETF数据管理器初始化完成，主数据源: {primary_source}")
    
    def _get_source(self) -> DataSourceBase:
        """获取可用的数据源"""
        if self.primary_source in self.sources:
            return self.sources[self.primary_source]
        
        # 降级到其他可用数据源
        for name, source in self.sources.items():
            return source
        
        raise RuntimeError("没有可用的数据源")
    
    def get_etf_daily(self, symbol: str, start_date: str = None, 
                      end_date: str = None, days: int = 252) -> pd.DataFrame:
        """
        获取ETF日线数据
        
        Args:
            symbol: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            days: 如果未指定日期，获取最近N个交易日
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=int(days * 1.5))).strftime('%Y-%m-%d')
        
        source = self._get_source()
        return source.get_etf_daily(symbol, start_date, end_date)
    
    def get_etf_realtime(self, symbol: str) -> Dict:
        """获取实时行情"""
        source = self._get_source()
        return source.get_etf_realtime(symbol)
    
    def get_etf_premium(self, symbol: str) -> float:
        """获取溢价率"""
        source = self._get_source()
        return source.get_etf_premium(symbol)
    
    def get_multiple_etf_daily(self, symbols: List[str], 
                                start_date: str = None,
                                end_date: str = None) -> pd.DataFrame:
        """
        获取多个ETF的日线数据，合并为宽表格式
        
        Returns:
            DataFrame: 索引为日期，列为各ETF收盘价
        """
        all_data = {}
        
        for symbol in symbols:
            df = self.get_etf_daily(symbol, start_date, end_date)
            if not df.empty:
                df = df.set_index('date')
                all_data[symbol] = df['close']
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.DataFrame(all_data)
        result = result.sort_index()
        result = result.ffill()  # 前向填充缺失值
        
        return result
    
    def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        source = self._get_source()
        return source.get_etf_list()
    
    def get_premium_data(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取多个ETF的溢价率
        
        Returns:
            DataFrame: 包含各ETF当前溢价率
        """
        data = []
        for symbol in symbols:
            premium = self.get_etf_premium(symbol)
            data.append({
                'symbol': symbol,
                'premium_rate': premium,
                'update_time': datetime.now()
            })
        
        return pd.DataFrame(data)


# 全局数据管理器实例
_etf_data_manager: Optional[ETFDataManager] = None


def get_etf_data_manager(primary_source: str = 'akshare', 
                          tushare_token: str = None) -> ETFDataManager:
    """
    获取ETF数据管理器单例
    """
    global _etf_data_manager
    
    if _etf_data_manager is None:
        _etf_data_manager = ETFDataManager(primary_source, tushare_token)
    
    return _etf_data_manager


# ============================================
# 便捷函数
# ============================================

def fetch_etf_daily(symbol: str, days: int = 252) -> pd.DataFrame:
    """快捷获取ETF日线数据"""
    manager = get_etf_data_manager()
    return manager.get_etf_daily(symbol, days=days)


def fetch_etf_realtime(symbol: str) -> Dict:
    """快捷获取ETF实时行情"""
    manager = get_etf_data_manager()
    return manager.get_etf_realtime(symbol)


def fetch_multiple_etf(symbols: List[str], days: int = 252) -> pd.DataFrame:
    """快捷获取多个ETF日线数据"""
    manager = get_etf_data_manager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=int(days * 1.5))).strftime('%Y-%m-%d')
    return manager.get_multiple_etf_daily(symbols, start_date, end_date)
