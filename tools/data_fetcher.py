"""
============================================
数据获取工具模块
使用 yfinance 获取股票/ETF/基金的行情和财务数据
============================================
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import requests


def get_cn_fund_data(fund_code: str, period: str = "1y") -> str:
    """
    获取中国场外基金的净值数据（包含历史净值用于技术分析）
    使用天天基金网 API
    
    Args:
        fund_code: 基金代码 (如: 020398, 110011)
        period: 数据周期
    
    Returns:
        JSON 格式的基金净值数据，包含 OHLCV 格式的历史数据
    """
    import re
    import os
    
    # 禁用系统代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://fund.eastmoney.com/"
    }
    
    # 禁用代理
    proxies = {"http": None, "https": None}
    
    fund_name = f"基金 {fund_code}"
    latest_nav = 1.0
    estimated_nav = 1.0
    estimated_change = 0.0
    ohlcv_data = []
    
    try:
        # 1. 获取基金实时信息
        info_url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
        response = requests.get(info_url, headers=headers, timeout=10, proxies=proxies)
        
        if response.status_code == 200 and "jsonpgz" in response.text:
            json_str = re.search(r'jsonpgz\((.*)\)', response.text)
            if json_str:
                fund_info = json.loads(json_str.group(1))
                fund_name = fund_info.get("name", fund_name)
                latest_nav = float(fund_info.get("dwjz", 1.0))
                estimated_nav = float(fund_info.get("gsz", latest_nav))
                estimated_change = float(fund_info.get("gszzl", 0))
        
        # 2. 获取历史净值数据（用于技术分析）
        # 获取尽可能多的历史数据进行分析
        per_page = {"1mo": 60, "3mo": 120, "6mo": 250, "1y": 500, "2y": 750, "max": 1000}.get(period, 500)
        
        history_url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={per_page}"
        hist_headers = {**headers, "Referer": f"https://fundf10.eastmoney.com/jjjz_{fund_code}.html"}
        
        hist_response = requests.get(history_url, headers=hist_headers, timeout=15, proxies=proxies)
        
        if hist_response.status_code == 200:
            hist_data = hist_response.json()
            data_obj = hist_data.get("Data") or {}
            nav_list = data_obj.get("LSJZList") or []
            
            if nav_list:
                # 转换为 OHLCV 格式（基金只有净值，用净值作为 OHLC）
                for item in reversed(nav_list):  # 反转使其按时间升序
                    try:
                        date_str = item.get("FSRQ", "")
                        nav = float(item.get("DWJZ", 0))
                        if nav > 0:
                            ohlcv_data.append({
                                "Date": date_str,
                                "Open": nav,
                                "High": nav,
                                "Low": nav,
                                "Close": nav,
                                "Volume": 0
                            })
                    except (ValueError, TypeError):
                        continue
                
                if ohlcv_data:
                    latest_nav = ohlcv_data[-1]["Close"]
        
        # 如果没有获取到历史数据，尝试备用接口
        if not ohlcv_data:
            backup_url = f"https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page=1&per={per_page}"
            backup_response = requests.get(backup_url, headers=headers, timeout=10, proxies=proxies)
            
            if backup_response.status_code == 200:
                # 解析 HTML 表格
                from html.parser import HTMLParser
                
                class NavParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.in_td = False
                        self.current_row = []
                        self.rows = []
                        
                    def handle_starttag(self, tag, attrs):
                        if tag == "td":
                            self.in_td = True
                            
                    def handle_endtag(self, tag):
                        if tag == "td":
                            self.in_td = False
                        elif tag == "tr" and self.current_row:
                            self.rows.append(self.current_row)
                            self.current_row = []
                            
                    def handle_data(self, data):
                        if self.in_td:
                            self.current_row.append(data.strip())
                
                parser = NavParser()
                parser.feed(backup_response.text)
                
                for row in reversed(parser.rows):
                    if len(row) >= 2:
                        try:
                            date_str = row[0]
                            nav = float(row[1])
                            if nav > 0:
                                ohlcv_data.append({
                                    "Date": date_str,
                                    "Open": nav,
                                    "High": nav,
                                    "Low": nav,
                                    "Close": nav,
                                    "Volume": 0
                                })
                        except (ValueError, TypeError, IndexError):
                            continue
    
    except Exception as e:
        print(f"获取基金数据异常: {e}")
    
    # 计算统计数据
    if ohlcv_data:
        closes = [d["Close"] for d in ohlcv_data]
        period_high = max(closes)
        period_low = min(closes)
        first_close = closes[0]
        last_close = closes[-1]
        period_change = last_close - first_close
        period_change_pct = (period_change / first_close * 100) if first_close > 0 else 0
    else:
        period_high = latest_nav
        period_low = latest_nav
        period_change = 0
        period_change_pct = estimated_change
    
    return json.dumps({
        "status": "success",
        "ticker": fund_code,
        "asset_type": "cn_fund",
        "data_period": period,
        "data_points": len(ohlcv_data),
        "date_range": {
            "start": ohlcv_data[0]["Date"] if ohlcv_data else "",
            "end": ohlcv_data[-1]["Date"] if ohlcv_data else ""
        },
        "summary": {
            "latest_price": estimated_nav if estimated_nav > 0 else latest_nav,
            "period_change": round(period_change, 4),
            "period_change_pct": round(period_change_pct, 2),
            "period_high": round(period_high, 4),
            "period_low": round(period_low, 4),
            "avg_volume": 0,
        },
        "fund_info": {
            "name": fund_name,
            "code": fund_code,
            "nav": latest_nav,
            "estimated_nav": estimated_nav,
            "estimated_change_pct": estimated_change,
        },
        "ohlcv": ohlcv_data,
        "source": "eastmoney",
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)


def get_cn_fund_info(fund_code: str) -> str:
    """
    获取中国场外基金的基本信息
    
    Args:
        fund_code: 基金代码
    
    Returns:
        JSON 格式的基金信息
    """
    try:
        info_url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://fund.eastmoney.com/"
        }
        
        response = requests.get(info_url, headers=headers, timeout=10)
        
        if response.status_code == 200 and "jsonpgz" in response.text:
            import re
            json_str = re.search(r'jsonpgz\((.*)\)', response.text)
            if json_str:
                fund_info = json.loads(json_str.group(1))
                
                return json.dumps({
                    "status": "success",
                    "ticker": fund_code,
                    "basic_info": {
                        "name": fund_info.get("name", f"基金 {fund_code}"),
                        "symbol": fund_code,
                        "exchange": "场外基金",
                        "currency": "CNY",
                        "quote_type": "MUTUALFUND",
                    },
                    "price_info": {
                        "current_price": float(fund_info.get("gsz", 1.0)),
                        "previous_close": float(fund_info.get("dwjz", 1.0)),
                        "52_week_high": float(fund_info.get("gsz", 1.0)) * 1.2,
                        "52_week_low": float(fund_info.get("gsz", 1.0)) * 0.8,
                    },
                    "valuation": {
                        "market_cap": None,
                        "pe_ratio": None,
                    },
                    "fund_specific": {
                        "nav": float(fund_info.get("dwjz", 1.0)),
                        "estimated_nav": float(fund_info.get("gsz", 1.0)),
                        "estimated_change_pct": float(fund_info.get("gszzl", 0)),
                        "update_time": fund_info.get("gztime", ""),
                    },
                    "source": "eastmoney",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
                
    except Exception:
        pass
    
    # 返回基本信息
    return json.dumps({
        "status": "success",
        "ticker": fund_code,
        "basic_info": {
            "name": f"基金 {fund_code}",
            "symbol": fund_code,
            "exchange": "场外基金",
            "currency": "CNY",
            "quote_type": "MUTUALFUND",
        },
        "price_info": {
            "current_price": 1.0,
            "previous_close": 1.0,
            "52_week_high": 1.2,
            "52_week_low": 0.8,
        },
        "valuation": {
            "market_cap": None,
            "pe_ratio": None,
        },
        "source": "estimated",
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)


def get_cn_etf_info(etf_code: str) -> str:
    """
    获取中国场内ETF的基本信息（使用东方财富API）
    
    Args:
        etf_code: ETF代码 (如: 159857, 510300, 588200)
    
    Returns:
        JSON 格式的ETF信息
    """
    import os
    import re
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }
    proxies = {"http": None, "https": None}
    
    # 判断交易所: 159开头是深圳，5开头(510/512/513/515/516/518/588等)是上海
    if etf_code.startswith('159'):
        market = "0"  # 深圳
        exchange = "深交所"
    else:
        market = "1"  # 上海
        exchange = "上交所"
    
    etf_name = f"ETF {etf_code}"
    current_price = 0
    prev_close = 0
    change_pct = 0.0
    day_high = 0
    day_low = 0
    high_52w = 0
    low_52w = 0
    volume = 0
    amount = 0
    fund_scale = None
    nav = None  # 净值
    discount_rate = None  # 折溢价率
    
    try:
        # 1. 获取ETF实时行情 - 使用更全面的字段
        quote_url = f"https://push2.eastmoney.com/api/qt/stock/get"
        quote_params = {
            "secid": f"{market}.{etf_code}",
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f117,f169,f170,f171,f277,f278,f279,f288"
        }
        response = requests.get(quote_url, headers=headers, params=quote_params, timeout=10, proxies=proxies)
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            if data:
                etf_name = data.get("f58", etf_name)
                # 价格数据（东财返回的是整数，需要除以1000）
                raw_price = data.get("f43")
                if raw_price and raw_price > 0:
                    current_price = raw_price / 1000
                raw_prev = data.get("f60")
                if raw_prev and raw_prev > 0:
                    prev_close = raw_prev / 1000
                raw_high = data.get("f44")
                if raw_high and raw_high > 0:
                    day_high = raw_high / 1000
                raw_low = data.get("f45")
                if raw_low and raw_low > 0:
                    day_low = raw_low / 1000
                # 涨跌幅
                raw_change = data.get("f170")
                if raw_change:
                    change_pct = raw_change / 100
                volume = data.get("f47", 0)
                amount = data.get("f48", 0)
                # 市值/流通市值
                raw_cap = data.get("f116") or data.get("f117")
                if raw_cap and raw_cap > 0:
                    fund_scale = raw_cap
        
        # 2. 获取ETF基金详情（净值、规模等）
        fund_detail_url = f"https://fundgz.1234567.com.cn/js/{etf_code}.js"
        try:
            fund_resp = requests.get(fund_detail_url, headers=headers, timeout=5, proxies=proxies)
            if fund_resp.status_code == 200 and "gsz" in fund_resp.text:
                # 解析实时估值
                gsz_match = re.search(r'"gsz":"([\d.]+)"', fund_resp.text)
                if gsz_match:
                    nav = float(gsz_match.group(1))
        except:
            pass
        
        # 3. 获取ETF基本信息
        info_url = f"https://fund.eastmoney.com/pingzhongdata/{etf_code}.js"
        try:
            info_resp = requests.get(info_url, headers=headers, timeout=5, proxies=proxies)
            if info_resp.status_code == 200:
                # 基金名称
                name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', info_resp.text)
                if name_match:
                    etf_name = name_match.group(1)
                # 基金规模
                scale_match = re.search(r'fund_sourceRate\s*=\s*"([^"]+)"', info_resp.text)
        except:
            pass
        
        # 4. 获取52周高低点 (通过K线数据)
        kline_url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        kline_params = {
            "secid": f"{market}.{etf_code}",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": "101",
            "fqt": "1",
            "end": "20500101",
            "lmt": "252"
        }
        try:
            kline_resp = requests.get(kline_url, headers=headers, params=kline_params, timeout=10, proxies=proxies)
            if kline_resp.status_code == 200:
                kline_data = kline_resp.json().get("data", {})
                if kline_data:
                    klines = kline_data.get("klines", [])
                    if klines:
                        highs = []
                        lows = []
                        for kline in klines:
                            parts = kline.split(",")
                            if len(parts) >= 5:
                                highs.append(float(parts[3]))
                                lows.append(float(parts[4]))
                        if highs:
                            high_52w = max(highs)
                        if lows:
                            low_52w = min(lows)
        except:
            pass
        
        # 如果没有获取到52周数据，用当日数据估算
        if high_52w == 0 and current_price > 0:
            high_52w = current_price * 1.3
        if low_52w == 0 and current_price > 0:
            low_52w = current_price * 0.7
        
        # 格式化基金规模
        fund_scale_str = None
        if fund_scale:
            if fund_scale >= 1e12:
                fund_scale_str = f"¥{fund_scale/1e12:.2f}万亿"
            elif fund_scale >= 1e8:
                fund_scale_str = f"¥{fund_scale/1e8:.2f}亿"
            elif fund_scale >= 1e4:
                fund_scale_str = f"¥{fund_scale/1e4:.2f}万"
            else:
                fund_scale_str = f"¥{fund_scale:.0f}"
        
        return json.dumps({
            "status": "success",
            "ticker": etf_code,
            "basic_info": {
                "name": etf_name,
                "symbol": etf_code,
                "exchange": exchange,
                "currency": "CNY",
                "quote_type": "ETF",
            },
            "price_info": {
                "current_price": current_price,
                "previous_close": prev_close,
                "day_high": day_high,
                "day_low": day_low,
                "52_week_high": high_52w,
                "52_week_low": low_52w,
                "change_pct": change_pct,
            },
            "volume_info": {
                "volume": volume,
                "amount": amount,
                "amount_str": f"¥{amount/1e8:.2f}亿" if amount >= 1e8 else f"¥{amount/1e4:.2f}万" if amount >= 1e4 else f"¥{amount:.0f}",
            },
            "valuation": {
                "market_cap": fund_scale,
                "market_cap_str": fund_scale_str,
                "pe_ratio": None,  # ETF 没有 P/E
                "nav": nav,  # 净值
            },
            "etf_specific": {
                "nav": nav,
                "discount_rate": discount_rate,
                "tracking_index": etf_name.replace("ETF", "").replace("etf", "").strip() if "ETF" in etf_name.upper() else etf_name,
            },
            "source": "eastmoney",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
        
    except Exception as e:
        pass
    
    # 返回基本信息
    return json.dumps({
        "status": "success",
        "ticker": etf_code,
        "basic_info": {
            "name": etf_name,
            "symbol": etf_code,
            "exchange": exchange,
            "currency": "CNY",
            "quote_type": "ETF",
        },
        "price_info": {
            "current_price": current_price,
            "previous_close": prev_close,
            "52_week_high": high_52w,
            "52_week_low": low_52w,
        },
        "valuation": {
            "market_cap": None,
            "pe_ratio": None,
        },
        "source": "estimated",
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)


def search_ticker(query: str) -> str:
    """
    根据股票名称或代码搜索对应的 ticker symbol
    
    Args:
        query: 股票名称或代码 (如: "苹果", "AAPL", "贵州茅台", "600519")
    
    Returns:
        JSON 格式的搜索结果
    """
    # 常见中国股票映射
    cn_stock_mapping = {
        "贵州茅台": "600519.SS",
        "茅台": "600519.SS",
        "中国平安": "601318.SS",
        "平安": "601318.SS",
        "招商银行": "600036.SS",
        "工商银行": "601398.SS",
        "腾讯": "0700.HK",
        "阿里巴巴": "BABA",
        "阿里": "BABA",
        "比亚迪": "002594.SZ",
        "宁德时代": "300750.SZ",
    }
    
    # 检查是否有直接映射
    if query in cn_stock_mapping:
        ticker = cn_stock_mapping[query]
        return json.dumps({
            "status": "success",
            "query": query,
            "ticker": ticker,
            "source": "local_mapping"
        }, ensure_ascii=False)
    
    # 检查是否为纯数字代码
    if query.isdigit() and len(query) == 6:
        # 判断是股票还是基金
        if query.startswith("6"):
            ticker = f"{query}.SS"  # 上交所股票
            asset_type = "stock"
        elif query.startswith(("00", "30")):
            ticker = f"{query}.SZ"  # 深交所股票
            asset_type = "stock"
        else:
            # 可能是场外基金 (如 001234, 020398, 110011 等)
            ticker = query
            asset_type = "cn_fund"
        return json.dumps({
            "status": "success",
            "query": query,
            "ticker": ticker,
            "asset_type": asset_type,
            "source": "code_inference"
        }, ensure_ascii=False)
    
    # 尝试直接使用作为美股代码
    try:
        stock = yf.Ticker(query.upper())
        info = stock.info
        if info.get("regularMarketPrice"):
            return json.dumps({
                "status": "success",
                "query": query,
                "ticker": query.upper(),
                "name": info.get("longName", ""),
                "source": "yfinance_lookup"
            }, ensure_ascii=False)
    except Exception:
        pass
    
    return json.dumps({
        "status": "not_found",
        "query": query,
        "message": "未找到匹配的股票代码，请提供准确的 ticker symbol"
    }, ensure_ascii=False)


def is_cn_onexchange_etf(code: str) -> bool:
    """判断是否为中国场内ETF代码"""
    if not code.isdigit() or len(code) != 6:
        return False
    # 深交所场内ETF: 159xxx, 15xxxx
    # 上交所场内ETF: 510xxx, 511xxx, 512xxx, 513xxx, 515xxx, 516xxx, 518xxx, 560xxx, 561xxx, 562xxx, 563xxx
    etf_prefixes = ('159', '510', '511', '512', '513', '515', '516', '518', '560', '561', '562', '563', '588')
    return code.startswith(etf_prefixes)


def is_cn_offexchange_fund(code: str) -> bool:
    """判断是否为中国场外基金代码"""
    if not code.isdigit() or len(code) != 6:
        return False
    # 场外基金代码通常以 0, 1, 2, 3 开头，但排除场内ETF
    if is_cn_onexchange_etf(code):
        return False
    # 场外基金: 000xxx, 001xxx, 002xxx, 003xxx, 004xxx, 005xxx, 006xxx, 007xxx, 008xxx, 009xxx
    # 以及部分 1xxxxx, 2xxxxx 开头的
    return code.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))


def get_cn_etf_suffix(code: str) -> str:
    """获取中国场内ETF的交易所后缀"""
    if code.startswith('159'):  # 深交所
        return '.SZ'
    else:  # 上交所
        return '.SS'


def get_cn_etf_data(etf_code: str, period: str = "1y") -> str:
    """
    获取中国场内ETF的历史行情数据（使用东方财富API）
    
    Args:
        etf_code: ETF代码 (如: 159857, 510300)
        period: 数据周期
    
    Returns:
        JSON 格式的行情数据，包含 OHLCV
    """
    import os
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }
    proxies = {"http": None, "https": None}
    
    # 判断交易所: 159开头是深圳(0)，其他是上海(1)
    if etf_code.startswith('159'):
        market = "0"
        secid = f"0.{etf_code}"
    else:
        market = "1"
        secid = f"1.{etf_code}"
    
    # 计算数据量
    limit_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "max": 1500}
    limit = limit_map.get(period, 365)
    
    etf_name = f"ETF {etf_code}"
    ohlcv_data = []
    
    try:
        # 获取ETF名称
        info_url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f58"
        info_resp = requests.get(info_url, headers=headers, timeout=10, proxies=proxies)
        if info_resp.status_code == 200:
            info_data = info_resp.json().get("data", {})
            if info_data:
                etf_name = info_data.get("f58", etf_name)
        
        # 获取历史K线数据
        kline_url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",  # 日K
            "fqt": "1",    # 前复权
            "end": "20500101",
            "lmt": limit
        }
        
        kline_resp = requests.get(kline_url, headers=headers, params=params, timeout=15, proxies=proxies)
        
        if kline_resp.status_code == 200:
            kline_data = kline_resp.json().get("data", {})
            if kline_data:
                etf_name = kline_data.get("name", etf_name)
                klines = kline_data.get("klines", [])
                
                for kline in klines:
                    # 格式: 日期,开盘,收盘,最高,最低,成交量,成交额
                    parts = kline.split(",")
                    if len(parts) >= 7:
                        ohlcv_data.append({
                            "Date": parts[0],
                            "Open": float(parts[1]),
                            "Close": float(parts[2]),
                            "High": float(parts[3]),
                            "Low": float(parts[4]),
                            "Volume": int(float(parts[5])),
                        })
        
        if not ohlcv_data:
            return json.dumps({
                "status": "error",
                "ticker": etf_code,
                "message": f"无法获取 {etf_code} 的行情数据"
            }, ensure_ascii=False)
        
        # 计算统计数据
        latest_price = ohlcv_data[-1]["Close"]
        first_price = ohlcv_data[0]["Close"]
        price_change = latest_price - first_price
        price_change_pct = (price_change / first_price) * 100 if first_price else 0
        avg_volume = sum(d["Volume"] for d in ohlcv_data) / len(ohlcv_data)
        high_52w = max(d["High"] for d in ohlcv_data[-252:]) if len(ohlcv_data) >= 252 else max(d["High"] for d in ohlcv_data)
        low_52w = min(d["Low"] for d in ohlcv_data[-252:]) if len(ohlcv_data) >= 252 else min(d["Low"] for d in ohlcv_data)
        
        return json.dumps({
            "status": "success",
            "ticker": etf_code,
            "name": etf_name,
            "asset_type": "ETF",
            "data_period": period,
            "data_interval": "1d",
            "data_points": len(ohlcv_data),
            "date_range": {
                "start": ohlcv_data[0]["Date"],
                "end": ohlcv_data[-1]["Date"]
            },
            "summary": {
                "latest_price": latest_price,
                "period_change": round(price_change, 4),
                "period_change_pct": round(price_change_pct, 2),
                "average_volume": int(avg_volume),
                "52_week_high": high_52w,
                "52_week_low": low_52w,
            },
            "ohlcv": ohlcv_data,
            "source": "eastmoney"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "ticker": etf_code,
            "message": f"获取ETF数据失败: {str(e)}"
        }, ensure_ascii=False)


def get_stock_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d"
) -> str:
    """
    获取股票/ETF/基金的历史行情数据
    
    Args:
        ticker: 股票代码 (如: AAPL, 600519.SS, SPY, 159857)
        period: 数据周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        interval: 数据间隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        JSON 格式的行情数据，包含 OHLCV
    """
    # 如果是中国场内ETF，使用东方财富API
    if is_cn_onexchange_etf(ticker):
        return get_cn_etf_data(ticker, period)
    # 如果是中国场外基金代码，使用东财接口
    elif is_cn_offexchange_fund(ticker):
        return get_cn_fund_data(ticker, period)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            return json.dumps({
                "status": "error",
                "ticker": ticker,
                "message": f"无法获取 {ticker} 的行情数据。如果是中国A股请使用 .SS 或 .SZ 后缀，如 600519.SS"
            }, ensure_ascii=False)
        
        # 转换为可序列化格式
        df = df.reset_index()
        df["Date"] = df["Date"].astype(str) if "Date" in df.columns else df["Datetime"].astype(str)
        
        # 基础统计
        latest_price = float(df["Close"].iloc[-1])
        price_change = float(df["Close"].iloc[-1] - df["Close"].iloc[0])
        price_change_pct = (price_change / float(df["Close"].iloc[0])) * 100
        avg_volume = float(df["Volume"].mean())
        
        result = {
            "status": "success",
            "ticker": ticker,
            "data_period": period,
            "data_interval": interval,
            "data_points": len(df),
            "date_range": {
                "start": str(df["Date"].iloc[0] if "Date" in df.columns else df["Datetime"].iloc[0]),
                "end": str(df["Date"].iloc[-1] if "Date" in df.columns else df["Datetime"].iloc[-1])
            },
            "summary": {
                "latest_price": round(latest_price, 2),
                "period_change": round(price_change, 2),
                "period_change_pct": round(price_change_pct, 2),
                "period_high": round(float(df["High"].max()), 2),
                "period_low": round(float(df["Low"].min()), 2),
                "avg_volume": int(avg_volume),
            },
            "ohlcv": df[["Date" if "Date" in df.columns else "Datetime", 
                         "Open", "High", "Low", "Close", "Volume"]].to_dict(orient="records"),
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "ticker": ticker,
            "message": str(e)
        }, ensure_ascii=False)


def get_stock_info(ticker: str) -> str:
    """
    获取股票/ETF/基金的基本信息
    
    Args:
        ticker: 股票代码
    
    Returns:
        JSON 格式的基本信息，包含公司概况、行业、市值等
    """
    original_ticker = ticker
    
    # 如果是中国场内ETF，直接使用东财接口（跳过yfinance）
    if is_cn_onexchange_etf(ticker):
        return get_cn_etf_info(ticker)
    # 如果是中国场外基金，直接使用东财接口
    elif is_cn_offexchange_fund(ticker):
        return get_cn_fund_info(ticker)
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or not info.get("regularMarketPrice"):
            # 如果yfinance失败，尝试用东财接口获取中国ETF信息
            if original_ticker.isdigit() and len(original_ticker) == 6:
                return get_cn_etf_info(original_ticker)
            return json.dumps({
                "status": "error",
                "ticker": ticker,
                "message": "无法获取股票信息"
            }, ensure_ascii=False)
        
        # 提取关键信息
        result = {
            "status": "success",
            "ticker": ticker,
            "basic_info": {
                "name": info.get("longName", info.get("shortName", "")),
                "symbol": info.get("symbol", ticker),
                "exchange": info.get("exchange", ""),
                "currency": info.get("currency", "USD"),
                "quote_type": info.get("quoteType", ""),  # EQUITY, ETF, MUTUALFUND
            },
            "price_info": {
                "current_price": info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "50_day_avg": info.get("fiftyDayAverage"),
                "200_day_avg": info.get("twoHundredDayAverage"),
            },
            "volume_info": {
                "volume": info.get("volume"),
                "avg_volume": info.get("averageVolume"),
                "avg_volume_10d": info.get("averageVolume10days"),
            },
            "valuation": {
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
            },
            "fundamentals": {
                "revenue": info.get("totalRevenue"),
                "gross_profit": info.get("grossProfits"),
                "ebitda": info.get("ebitda"),
                "net_income": info.get("netIncomeToCommon"),
                "eps": info.get("trailingEps"),
                "forward_eps": info.get("forwardEps"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
            },
            "dividend": {
                "dividend_rate": info.get("dividendRate"),
                "dividend_yield": info.get("dividendYield"),
                "payout_ratio": info.get("payoutRatio"),
                "ex_dividend_date": str(info.get("exDividendDate")) if info.get("exDividendDate") else None,
            },
            "company_profile": {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "employees": info.get("fullTimeEmployees"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary", "")[:500] + "..." if info.get("longBusinessSummary") else "",
            },
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        # 如果是中国场外基金代码，尝试获取基金信息
        if ticker.isdigit() and len(ticker) == 6:
            return get_cn_fund_info(ticker)
        return json.dumps({
            "status": "error",
            "ticker": ticker,
            "message": str(e)
        }, ensure_ascii=False)


def get_financial_data(ticker: str) -> str:
    """
    获取股票的财务报表数据
    
    Args:
        ticker: 股票代码
    
    Returns:
        JSON 格式的财务数据，包含损益表、资产负债表、现金流量表
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 获取财务报表
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        result = {
            "status": "success",
            "ticker": ticker,
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        }
        
        # 处理损益表
        if not income_stmt.empty:
            # 获取最近4个季度/年度数据
            cols = income_stmt.columns[:4]
            key_items = ["Total Revenue", "Gross Profit", "Operating Income", 
                        "Net Income", "EBITDA", "Basic EPS"]
            for item in key_items:
                if item in income_stmt.index:
                    result["income_statement"][item] = {
                        str(col.date()): float(income_stmt.loc[item, col]) 
                        for col in cols if pd.notna(income_stmt.loc[item, col])
                    }
        
        # 处理资产负债表
        if not balance_sheet.empty:
            cols = balance_sheet.columns[:4]
            key_items = ["Total Assets", "Total Liabilities Net Minority Interest",
                        "Total Equity Gross Minority Interest", "Cash And Cash Equivalents",
                        "Total Debt", "Working Capital"]
            for item in key_items:
                if item in balance_sheet.index:
                    result["balance_sheet"][item] = {
                        str(col.date()): float(balance_sheet.loc[item, col])
                        for col in cols if pd.notna(balance_sheet.loc[item, col])
                    }
        
        # 处理现金流量表
        if not cashflow.empty:
            cols = cashflow.columns[:4]
            key_items = ["Operating Cash Flow", "Investing Cash Flow", 
                        "Financing Cash Flow", "Free Cash Flow", "Capital Expenditure"]
            for item in key_items:
                if item in cashflow.index:
                    result["cash_flow"][item] = {
                        str(col.date()): float(cashflow.loc[item, col])
                        for col in cols if pd.notna(cashflow.loc[item, col])
                    }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "ticker": ticker,
            "message": str(e)
        }, ensure_ascii=False)


def get_etf_holdings(ticker: str) -> str:
    """
    获取 ETF 的持仓数据
    
    Args:
        ticker: ETF 代码 (如: SPY, QQQ)
    
    Returns:
        JSON 格式的 ETF 持仓信息
    """
    try:
        etf = yf.Ticker(ticker)
        info = etf.info
        
        # 检查是否为 ETF
        if info.get("quoteType") != "ETF":
            return json.dumps({
                "status": "error",
                "ticker": ticker,
                "message": f"{ticker} 不是 ETF 类型"
            }, ensure_ascii=False)
        
        result = {
            "status": "success",
            "ticker": ticker,
            "etf_info": {
                "name": info.get("longName", ""),
                "category": info.get("category", ""),
                "total_assets": info.get("totalAssets"),
                "nav_price": info.get("navPrice"),
                "yield": info.get("yield"),
                "expense_ratio": info.get("annualReportExpenseRatio"),
            },
            "top_holdings": [],
            "sector_weights": {},
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        }
        
        # 尝试获取持仓 (某些 ETF 可能不提供)
        try:
            holdings = etf.funds_data.top_holdings
            if holdings is not None and not holdings.empty:
                result["top_holdings"] = holdings.head(10).to_dict(orient="records")
        except:
            pass
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "ticker": ticker,
            "message": str(e)
        }, ensure_ascii=False)
