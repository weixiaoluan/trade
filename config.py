"""
============================================
配置管理模块
Smart Multi-Dimensional Securities Analysis System
============================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================
# API 配置
# ============================================

class APIConfig:
    """API 密钥和端点配置"""
    
    # Google Gemini API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = "gemini-1.5-pro"  # Gemini 3.0 Pro 对应最新版本
    
    # 硅基流动 (SiliconFlow) API - DeepSeek
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "sk-muoigvectooargythxattxwslxhcvuvhyujbnbshlifrqsal")
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "deepseek-ai/DeepSeek-R1"  # DeepSeek-R1 模型
    
    # 默认使用的 LLM 提供商: "gemini" 或 "siliconflow"
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "siliconflow")
    
    # 验证 Gemini API Key
    @classmethod
    def validate_gemini(cls) -> bool:
        if not cls.GOOGLE_API_KEY:
            raise ValueError(
                "❌ GOOGLE_API_KEY 未配置!\n"
                "请在 .env 文件中设置 GOOGLE_API_KEY=your_api_key\n"
                "获取地址: https://aistudio.google.com/app/apikey"
            )
        return True
    
    # 验证硅基流动 API Key
    @classmethod
    def validate_siliconflow(cls) -> bool:
        if not cls.SILICONFLOW_API_KEY:
            raise ValueError(
                "❌ SILICONFLOW_API_KEY 未配置!\n"
                "请在 .env 文件中设置 SILICONFLOW_API_KEY=your_api_key\n"
                "获取地址: https://cloud.siliconflow.cn/"
            )
        return True
    
    # 验证当前选择的 API Key
    @classmethod
    def validate(cls) -> bool:
        if cls.DEFAULT_LLM_PROVIDER == "siliconflow":
            return cls.validate_siliconflow()
        else:
            return cls.validate_gemini()


# ============================================
# LLM 配置 (AutoGen 格式)
# ============================================

def get_llm_config(provider: str = None) -> dict:
    """
    获取 AutoGen 兼容的 LLM 配置
    
    Args:
        provider: LLM 提供商，可选 "gemini" 或 "siliconflow"
                  默认使用 DEFAULT_LLM_PROVIDER 环境变量配置
    
    Returns:
        AutoGen 格式的 LLM 配置字典
    """
    if provider is None:
        provider = APIConfig.DEFAULT_LLM_PROVIDER
    
    if provider == "siliconflow":
        return get_siliconflow_config()
    else:
        return get_gemini_config()


def get_gemini_config() -> dict:
    """
    获取 Google Gemini API 配置
    """
    APIConfig.validate_gemini()
    
    return {
        "config_list": [
            {
                "model": APIConfig.GEMINI_MODEL,
                "api_key": APIConfig.GOOGLE_API_KEY,
                "api_type": "google",
            }
        ],
        "temperature": 0.3,  # 金融分析需要较低的创造性
        "timeout": 120,
        "cache_seed": None,  # 禁用缓存以获取最新数据
    }


def get_siliconflow_config() -> dict:
    """
    获取硅基流动 (SiliconFlow) API 配置
    使用 DeepSeek-R1 模型
    
    硅基流动 API 兼容 OpenAI 格式
    """
    APIConfig.validate_siliconflow()
    
    return {
        "config_list": [
            {
                "model": APIConfig.SILICONFLOW_MODEL,
                "api_key": APIConfig.SILICONFLOW_API_KEY,
                "base_url": APIConfig.SILICONFLOW_BASE_URL,
                "api_type": "openai",  # 硅基流动兼容 OpenAI 格式
            }
        ],
        "temperature": 0.3,  # 金融分析需要较低的创造性
        "timeout": 180,  # DeepSeek-R1 推理较慢，增加超时时间
        "cache_seed": None,  # 禁用缓存以获取最新数据
    }


# ============================================
# 数据源配置
# ============================================

class DataSourceConfig:
    """数据源优先级和可信度配置"""
    
    # 权威财经数据来源 (按优先级排序)
    AUTHORITATIVE_SOURCES = [
        # 官方监管机构
        {"name": "SEC", "domain": "sec.gov", "trust_level": "official"},
        {"name": "美联储", "domain": "federalreserve.gov", "trust_level": "official"},
        {"name": "中国证监会", "domain": "csrc.gov.cn", "trust_level": "official"},
        {"name": "上交所", "domain": "sse.com.cn", "trust_level": "official"},
        {"name": "深交所", "domain": "szse.cn", "trust_level": "official"},
        
        # 权威财经媒体
        {"name": "Bloomberg", "domain": "bloomberg.com", "trust_level": "tier1"},
        {"name": "Reuters", "domain": "reuters.com", "trust_level": "tier1"},
        {"name": "WSJ", "domain": "wsj.com", "trust_level": "tier1"},
        {"name": "Financial Times", "domain": "ft.com", "trust_level": "tier1"},
        {"name": "CNBC", "domain": "cnbc.com", "trust_level": "tier1"},
        
        # 专业金融数据平台
        {"name": "Yahoo Finance", "domain": "finance.yahoo.com", "trust_level": "tier2"},
        {"name": "Seeking Alpha", "domain": "seekingalpha.com", "trust_level": "tier2"},
        {"name": "东方财富", "domain": "eastmoney.com", "trust_level": "tier2"},
        {"name": "同花顺", "domain": "10jqka.com.cn", "trust_level": "tier2"},
    ]
    
    # 不可信来源黑名单
    BLACKLISTED_SOURCES = [
        "reddit.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "tiktok.com",
        "weibo.com",
    ]
    
    # 数据新鲜度要求 (天)
    FRESHNESS_REQUIREMENTS = {
        "price_data": 1,      # 价格数据必须当天
        "news": 7,            # 新闻7天内
        "financial_report": 365,  # 财报1年内
        "macro_policy": 30,   # 宏观政策30天内
    }


# ============================================
# 分析周期配置
# ============================================

class AnalysisPeriodConfig:
    """分析时间周期配置"""
    
    PERIODS = [
        {"name": "next_day", "label": "下个交易日", "days": 1, "category": "短线"},
        {"name": "3_days", "label": "未来3天", "days": 3, "category": "短线"},
        {"name": "1_week", "label": "1周", "days": 7, "category": "短线"},
        {"name": "15_days", "label": "15天", "days": 15, "category": "短线"},
        {"name": "1_month", "label": "30天", "days": 30, "category": "中线"},
        {"name": "3_months", "label": "3个月", "days": 90, "category": "中线"},
        {"name": "6_months", "label": "6个月", "days": 180, "category": "长线"},
        {"name": "1_year", "label": "1年", "days": 365, "category": "长线"},
    ]
    
    # 技术指标时间框架
    TECHNICAL_TIMEFRAMES = {
        "短线": {"ma_periods": [5, 10, 20], "rsi_period": 14},
        "中线": {"ma_periods": [20, 50, 60], "rsi_period": 14},
        "长线": {"ma_periods": [60, 120, 250], "rsi_period": 14},
    }


# ============================================
# 系统配置
# ============================================

class SystemConfig:
    """系统运行配置"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent
    
    # 日志目录
    LOG_DIR = PROJECT_ROOT / "logs"
    
    # 报告输出目录
    REPORT_DIR = PROJECT_ROOT / "reports"
    
    # GroupChat 配置
    MAX_ROUNDS = 20  # 最大对话轮次
    
    # Agent 超时配置 (秒)
    AGENT_TIMEOUT = 300
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        cls.LOG_DIR.mkdir(exist_ok=True)
        cls.REPORT_DIR.mkdir(exist_ok=True)


# 初始化目录
SystemConfig.init_directories()
