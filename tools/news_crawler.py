"""
============================================
新闻爬虫工具模块
获取权威财经新闻和舆情信息
============================================
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import re
from urllib.parse import urlparse, quote_plus
import time

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# 权威来源配置
AUTHORITATIVE_DOMAINS = {
    # 官方机构
    "sec.gov": {"name": "SEC", "trust_level": "official", "priority": 1},
    "federalreserve.gov": {"name": "美联储", "trust_level": "official", "priority": 1},
    
    # 一级权威媒体
    "bloomberg.com": {"name": "Bloomberg", "trust_level": "tier1", "priority": 2},
    "reuters.com": {"name": "Reuters", "trust_level": "tier1", "priority": 2},
    "wsj.com": {"name": "Wall Street Journal", "trust_level": "tier1", "priority": 2},
    "ft.com": {"name": "Financial Times", "trust_level": "tier1", "priority": 2},
    "cnbc.com": {"name": "CNBC", "trust_level": "tier1", "priority": 2},
    "marketwatch.com": {"name": "MarketWatch", "trust_level": "tier1", "priority": 2},
    
    # 二级专业来源
    "finance.yahoo.com": {"name": "Yahoo Finance", "trust_level": "tier2", "priority": 3},
    "seekingalpha.com": {"name": "Seeking Alpha", "trust_level": "tier2", "priority": 3},
    "investing.com": {"name": "Investing.com", "trust_level": "tier2", "priority": 3},
    "barrons.com": {"name": "Barron's", "trust_level": "tier2", "priority": 3},
}

# 不可信来源
BLACKLISTED_DOMAINS = [
    "reddit.com", "twitter.com", "x.com", "facebook.com",
    "tiktok.com", "weibo.com", "zhihu.com", "medium.com"
]


def _extract_domain(url: str) -> str:
    """从 URL 中提取主域名"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除 www 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def _check_source_authority(url: str) -> Dict:
    """
    检查新闻来源的权威性
    
    返回:
        {
            "is_authoritative": bool,
            "is_blacklisted": bool,
            "source_info": {...} or None,
            "trust_level": str
        }
    """
    domain = _extract_domain(url)
    
    # 检查黑名单
    for blacklisted in BLACKLISTED_DOMAINS:
        if blacklisted in domain:
            return {
                "is_authoritative": False,
                "is_blacklisted": True,
                "source_info": None,
                "trust_level": "untrusted",
                "domain": domain
            }
    
    # 检查权威来源
    for auth_domain, info in AUTHORITATIVE_DOMAINS.items():
        if auth_domain in domain:
            return {
                "is_authoritative": True,
                "is_blacklisted": False,
                "source_info": info,
                "trust_level": info["trust_level"],
                "domain": domain
            }
    
    # 未知来源
    return {
        "is_authoritative": False,
        "is_blacklisted": False,
        "source_info": None,
        "trust_level": "unknown",
        "domain": domain
    }


def search_financial_news(
    query: str,
    max_results: int = 10,
    days_back: int = 7,
    require_authoritative: bool = True
) -> str:
    """
    搜索财经新闻 (使用 Google 搜索模拟)
    
    Args:
        query: 搜索关键词 (如: "AAPL earnings" 或 "苹果公司财报")
        max_results: 最大返回结果数
        days_back: 搜索多少天内的新闻
        require_authoritative: 是否只返回权威来源
    
    Returns:
        JSON 格式的新闻列表
    """
    try:
        # 构建搜索 URL (使用 Google News)
        # 添加权威来源限定
        site_filters = " OR ".join([f"site:{d}" for d in list(AUTHORITATIVE_DOMAINS.keys())[:5]])
        search_query = f"{query} ({site_filters})"
        
        # 使用 DuckDuckGo HTML 搜索 (无需 API Key)
        encoded_query = quote_plus(search_query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        results = []
        
        # 解析搜索结果
        for result in soup.select(".result"):
            try:
                title_elem = result.select_one(".result__title a")
                snippet_elem = result.select_one(".result__snippet")
                
                if not title_elem:
                    continue
                
                url = title_elem.get("href", "")
                title = title_elem.get_text(strip=True)
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # 检查来源权威性
                authority_check = _check_source_authority(url)
                
                # 如果要求权威来源,过滤掉非权威和黑名单
                if require_authoritative:
                    if not authority_check["is_authoritative"]:
                        continue
                
                if authority_check["is_blacklisted"]:
                    continue
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source": authority_check.get("source_info", {}).get("name", authority_check["domain"]),
                    "trust_level": authority_check["trust_level"],
                    "domain": authority_check["domain"],
                })
                
                if len(results) >= max_results:
                    break
                    
            except Exception as e:
                continue
        
        # 按权威性排序
        priority_map = {"official": 1, "tier1": 2, "tier2": 3, "unknown": 4}
        results.sort(key=lambda x: priority_map.get(x["trust_level"], 5))
        
        return json.dumps({
            "status": "success",
            "query": query,
            "results_count": len(results),
            "authoritative_only": require_authoritative,
            "news": results,
            "search_timestamp": datetime.now().isoformat(),
            "note": "新闻结果需要经过 Data_Verifier_Agent 审核验证"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"搜索失败: {str(e)}",
            "suggestion": "请检查网络连接或稍后重试"
        }, ensure_ascii=False)


def parse_news_content(url: str) -> str:
    """
    解析新闻页面内容
    
    Args:
        url: 新闻页面 URL
    
    Returns:
        JSON 格式的新闻内容
    """
    try:
        # 先检查来源权威性
        authority_check = _check_source_authority(url)
        
        if authority_check["is_blacklisted"]:
            return json.dumps({
                "status": "rejected",
                "url": url,
                "reason": "来源在黑名单中,不予采信",
                "domain": authority_check["domain"]
            }, ensure_ascii=False)
        
        # 获取页面内容
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # 尝试提取标题
        title = ""
        for selector in ["h1", "title", ".headline", ".article-title"]:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # 尝试提取正文
        content = ""
        for selector in ["article", ".article-body", ".story-body", "main", ".content"]:
            elem = soup.select_one(selector)
            if elem:
                paragraphs = elem.find_all("p")
                content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
                break
        
        if not content:
            # 回退到所有段落
            paragraphs = soup.find_all("p")
            content = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:20]])
        
        # 提取发布日期
        publish_date = None
        for selector in ["time", ".date", ".publish-date", "[datetime]"]:
            elem = soup.select_one(selector)
            if elem:
                publish_date = elem.get("datetime") or elem.get_text(strip=True)
                break
        
        return json.dumps({
            "status": "success",
            "url": url,
            "title": title[:200] if title else "未能提取标题",
            "content": content[:3000] if content else "未能提取内容",
            "publish_date": publish_date,
            "source_authority": authority_check,
            "content_length": len(content),
            "parse_timestamp": datetime.now().isoformat(),
            "verification_required": True
        }, ensure_ascii=False)
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": "请求超时"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": str(e)
        }, ensure_ascii=False)


def verify_data_freshness(timestamp_str: str, data_type: str = "news") -> str:
    """
    验证数据时效性
    
    Args:
        timestamp_str: 数据时间戳字符串
        data_type: 数据类型 (news, price_data, financial_report, macro_policy)
    
    Returns:
        JSON 格式的验证结果
    """
    freshness_limits = {
        "price_data": 1,      # 价格数据必须当天
        "news": 7,            # 新闻7天内
        "financial_report": 365,  # 财报1年内
        "macro_policy": 30,   # 宏观政策30天内
    }
    
    try:
        # 尝试解析时间
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%B %d, %Y"]:
            try:
                data_date = datetime.strptime(timestamp_str[:19], fmt)
                break
            except:
                continue
        else:
            return json.dumps({
                "is_fresh": False,
                "reason": "无法解析日期格式",
                "timestamp": timestamp_str
            }, ensure_ascii=False)
        
        days_old = (datetime.now() - data_date).days
        limit = freshness_limits.get(data_type, 7)
        
        return json.dumps({
            "is_fresh": days_old <= limit,
            "data_type": data_type,
            "days_old": days_old,
            "freshness_limit": limit,
            "timestamp": timestamp_str,
            "verdict": "数据新鲜度合格" if days_old <= limit else f"数据已过期 ({days_old} 天前)"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "is_fresh": False,
            "error": str(e),
            "timestamp": timestamp_str
        }, ensure_ascii=False)
