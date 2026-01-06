"""
============================================
简化版 Agent 定义模块
兼容 pyautogen >= 0.2.0
============================================
"""

import autogen
from autogen import AssistantAgent, UserProxyAgent
from typing import Dict, Any
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from tools.data_fetcher import (
    search_ticker,
    get_stock_data,
    get_stock_info,
    get_financial_data,
    get_etf_holdings,
)
from tools.news_crawler import (
    search_financial_news,
    parse_news_content,
    verify_data_freshness,
)
from tools.technical_analysis import (
    calculate_all_indicators,
    analyze_trend,
    get_support_resistance_levels,
)


# ============================================
# 工具函数定义 (用于 Function Calling)
# ============================================

TOOL_FUNCTIONS = {
    "search_ticker": search_ticker,
    "get_stock_data": get_stock_data,
    "get_stock_info": get_stock_info,
    "get_financial_data": get_financial_data,
    "get_etf_holdings": get_etf_holdings,
    "search_financial_news": search_financial_news,
    "parse_news_content": parse_news_content,
    "verify_data_freshness": verify_data_freshness,
    "calculate_all_indicators": calculate_all_indicators,
    "analyze_trend": analyze_trend,
    "get_support_resistance_levels": get_support_resistance_levels,
}


# 工具描述 (OpenAI Function Calling 格式)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_ticker",
            "description": "根据股票名称或代码搜索对应的 ticker symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "股票名称或代码，如 AAPL, 苹果, 600519, 贵州茅台"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_data",
            "description": "获取股票/ETF/基金的历史行情数据（OHLCV）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码，如 AAPL, 600519.SS"
                    },
                    "period": {
                        "type": "string",
                        "description": "数据周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
                        "default": "1y"
                    },
                    "interval": {
                        "type": "string",
                        "description": "数据间隔: 1d, 1wk, 1mo",
                        "default": "1d"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": "获取股票/ETF/基金的基本信息，包括市值、PE、行业等",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_data",
            "description": "获取股票的财务报表数据（损益表、资产负债表、现金流）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_financial_news",
            "description": "搜索权威财经新闻，优先返回 Bloomberg, Reuters 等来源",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_all_indicators",
            "description": "计算所有技术指标（MACD, RSI, KDJ, 布林带, 均线等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ohlcv_data": {
                        "type": "string",
                        "description": "JSON 格式的 OHLCV 数据（来自 get_stock_data 的输出）"
                    }
                },
                "required": ["ohlcv_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_trend",
            "description": "基于技术指标进行趋势分析，判断多空信号",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicators_json": {
                        "type": "string",
                        "description": "calculate_all_indicators 的输出"
                    }
                },
                "required": ["indicators_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_support_resistance_levels",
            "description": "计算支撑位和阻力位",
            "parameters": {
                "type": "object",
                "properties": {
                    "ohlcv_data": {
                        "type": "string",
                        "description": "JSON 格式的 OHLCV 数据"
                    }
                },
                "required": ["ohlcv_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_data_freshness",
            "description": "验证数据时效性",
            "parameters": {
                "type": "object",
                "properties": {
                    "timestamp_str": {
                        "type": "string",
                        "description": "数据时间戳"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "数据类型: news, price_data, financial_report, macro_policy"
                    }
                },
                "required": ["timestamp_str", "data_type"]
            }
        }
    }
]


# ============================================
# System Messages
# ============================================

DATA_ENGINEER_MSG = """你是权威数据搜集员 (Data Engineer Agent)。

【职责】
1. 使用工具获取股票行情、基本信息、财务数据
2. 搜索权威财经新闻

【工作流程】
1. 先用 search_ticker 确认股票代码
2. 用 get_stock_data 获取至少1年的行情数据
3. 用 get_stock_info 获取基本面信息
4. 用 get_financial_data 获取财务报表
5. 用 search_financial_news 搜索相关新闻

【权威来源优先】
优先使用: SEC, Bloomberg, Reuters, WSJ, CNBC
禁止使用: 社交媒体、自媒体

收集完数据后，汇总给 Data_Verifier 进行验证。
"""

DATA_VERIFIER_MSG = """你是数据权威性审计员 (Data Verifier Agent)。

【核心职责】
你是"守门人"，负责审核所有数据的可靠性。

【验证清单】
1. 来源权威性: 是否来自官方或一级财经媒体？
2. 数据时效性: 价格数据是否当天？新闻是否7天内？
3. 数据一致性: 不同来源数据是否矛盾？
4. 数据完整性: 分析所需数据是否齐全？

【验证结果】
- APPROVED: 数据可信，允许进入分析阶段
- REJECTED: 数据有问题，说明原因，要求 Data_Engineer 重新获取

使用 verify_data_freshness 工具检查时效性。
"""

TECHNICAL_ANALYST_MSG = """你是技术面分析师 (Technical Analyst Agent)。

【职责】
基于行情数据进行技术分析。

【必须分析的指标】
- 趋势: MACD, 均线系统 (MA5/10/20/50/120/250)
- 动量: RSI, KDJ
- 波动: 布林带

【时间框架】
- 短线 (1天-15天): 关注 RSI, KDJ 金叉死叉
- 中线 (1月-3月): 关注 MACD 趋势
- 长线 (6月-1年): 关注长期均线

【工具使用】
1. 用 calculate_all_indicators 计算指标
2. 用 analyze_trend 进行趋势判断
3. 用 get_support_resistance_levels 计算支撑阻力

输出短线、中线、长线的趋势判断和置信度。
"""

FUNDAMENTAL_ANALYST_MSG = """你是基本面与宏观分析师 (Fundamental Analyst Agent)。

【职责】
分析公司/ETF 的内在价值。

【分析维度】
1. 估值: P/E, P/B, P/S, PEG
2. 盈利能力: ROE, ROA, 利润率
3. 成长性: 收入增长、利润增长
4. 财务健康: 负债率、现金流
5. 行业地位和竞争格局
6. 宏观经济影响: 利率、通胀

【输出】
- 估值评估: 低估/合理/高估
- 成长前景: 强劲/稳健/疲软
- 主要风险因素
"""

CIO_MSG = """你是首席投资官 (Chief Investment Officer Agent)。

【职责】
汇总所有分析，生成最终投资报告。

【必须覆盖的8个时间周期】
1. 下个交易日
2. 未来3天
3. 1周
4. 15天
5. 30天
6. 3个月
7. 6个月
8. 1年

【技术面评级等级】
- 强势 / 偏强 / 中性 / 偏弱 / 弱势

【报告格式 (Markdown)】
```
# 📊 [标的] 技术分析报告

## 一、标的概况
| 指标 | 数值 |
|------|------|
| 当前价格 | $xxx |
| 市值 | $xxx |
| P/E | xx |

## 二、多周期走势预测
| 时间周期 | 趋势 | 置信度 | 目标区间 | 支撑/阻力 |
|----------|------|--------|----------|-----------|
| 下个交易日 | ... | ... | ... | ... |
...

## 三、技术面总结
### 短期 (1天-15天): [评级]
### 中期 (1月-3月): [评级]
### 长期 (6月-1年): [评级]

## 四、风险提示 ⚠️
1. ...

## 五、数据来源
- ...

---
*报告时间: xxx*
*免责声明: 本报告仅供参考，不构成投资建议*
```

生成报告后，在末尾加上 "ANALYSIS_COMPLETE" 标记结束。
"""


def create_simple_agents(llm_config: dict) -> Dict[str, Any]:
    """
    创建简化版 Agent (兼容 AutoGen 0.2+)
    
    Args:
        llm_config: LLM 配置
    
    Returns:
        Agent 字典
    """
    # 添加工具定义到 llm_config
    llm_config_with_tools = llm_config.copy()
    llm_config_with_tools["tools"] = TOOL_DEFINITIONS
    
    # UserProxyAgent - 负责执行工具
    user_proxy = UserProxyAgent(
        name="User_Proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=15,
        is_termination_msg=lambda x: "ANALYSIS_COMPLETE" in str(x.get("content", "")),
        code_execution_config=False,
        system_message="你是用户代理，负责执行工具调用并协调分析流程。",
    )
    
    # 注册工具执行函数
    for func_name, func in TOOL_FUNCTIONS.items():
        user_proxy.register_function(
            function_map={func_name: func}
        )
    
    # Data Engineer Agent
    data_engineer = AssistantAgent(
        name="Data_Engineer",
        system_message=DATA_ENGINEER_MSG,
        llm_config=llm_config_with_tools,
    )
    
    # Data Verifier Agent
    data_verifier = AssistantAgent(
        name="Data_Verifier",
        system_message=DATA_VERIFIER_MSG,
        llm_config=llm_config_with_tools,
    )
    
    # Technical Analyst Agent
    technical_analyst = AssistantAgent(
        name="Technical_Analyst",
        system_message=TECHNICAL_ANALYST_MSG,
        llm_config=llm_config_with_tools,
    )
    
    # Fundamental Analyst Agent
    fundamental_analyst = AssistantAgent(
        name="Fundamental_Analyst",
        system_message=FUNDAMENTAL_ANALYST_MSG,
        llm_config=llm_config,  # 不需要工具
    )
    
    # Chief Investment Officer Agent
    cio = AssistantAgent(
        name="Chief_Investment_Officer",
        system_message=CIO_MSG,
        llm_config=llm_config,  # 不需要工具
    )
    
    return {
        "user_proxy": user_proxy,
        "data_engineer": data_engineer,
        "data_verifier": data_verifier,
        "technical_analyst": technical_analyst,
        "fundamental_analyst": fundamental_analyst,
        "chief_investment_officer": cio,
    }
