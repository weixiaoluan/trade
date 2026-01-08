"""
============================================
简化版 Agent 定义模块
兼容 pyautogen 0.2.35
============================================
"""

import autogen
from autogen import AssistantAgent, UserProxyAgent
from typing import Dict, Any

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
    verify_data_freshness,
)
from tools.technical_analysis import (
    calculate_all_indicators,
    analyze_trend,
    get_support_resistance_levels,
)


# ============================================
# 工具函数映射 (用于 UserProxyAgent 执行)
# ============================================

FUNCTION_MAP = {
    "search_ticker": search_ticker,
    "get_stock_data": get_stock_data,
    "get_stock_info": get_stock_info,
    "get_financial_data": get_financial_data,
    "get_etf_holdings": get_etf_holdings,
    "search_financial_news": search_financial_news,
    "verify_data_freshness": verify_data_freshness,
    "calculate_all_indicators": calculate_all_indicators,
    "analyze_trend": analyze_trend,
    "get_support_resistance_levels": get_support_resistance_levels,
}


# ============================================
# System Messages (简化版)
# ============================================

ANALYST_SYSTEM_MESSAGE = """你是一个专业的证券技术分析研究员。

你的任务是分析用户提供的股票/ETF/基金，并生成技术分析研究报告。
你的分析应基于"vnpy"式的量化思维，结合多维度指标进行技术研判。

【重要声明】
本报告仅供个人学习研究参考，不构成任何投资建议。
- 禁止使用"建议买入"、"建议卖出"、"强力推荐"等引导性语言
- 使用"技术面评级"（强势/偏强/中性/偏弱/弱势）代替投资建议
- 使用"支撑位"、"阻力位"代替"买入价"、"卖出价"
- 所有分析仅基于历史数据的技术指标计算，不代表未来走势

【分析流程】
1. 首先确认股票代码
2. 获取行情数据和基本面信息
3. 进行全方位量化技术分析（调用 analyze_trend 获取量化评分和市场状态）
   - 趋势指标: MACD, MA, ADX (判断趋势强度)
   - 震荡指标: RSI, KDJ, CCI, Williams %R
   - 波动率指标: ATR, Bollinger Bands (判断变盘点)
   - 量能指标: OBV, Volume Ratio
4. 进行基本面分析（估值、财务、行业）
5. 综合生成"智能化、多维度"的技术分析研究报告

【报告要求】
生成包含以下内容的 Markdown 报告：

# 📊 [标的名称] 智能量化分析报告

## 一、AI 量化综述 🤖
- **量化评分**: [0-100分] (根据 analyze_trend 结果)
- **技术面评级**: [强势/偏强/中性/偏弱/弱势]
- **市场状态**: [趋势市/震荡市/变盘节点] (基于 ADX 和 布林带)
- **置信度**: [高/中/低]

## 二、多维技术面扫描
### 1. 趋势维度 (Trend)
- 长期趋势 (MA20/60/250): ...
- 动能状态 (MACD/ADX): ...
- **核心判断**: 当前是否处于强势主升浪？还是下跌中继？

### 2. 时机维度 (Timing)
- 超买超卖 (RSI/KDJ/CCI): ...
- 支撑压力 (布林带/历史高低点): ...
- **核心判断**: 当前技术面状态如何？是否存在背离信号？

### 3. 资金维度 (Flow)
- 量能分析 (Volume/OBV): ...
- 资金流向判断: ...

## 三、基本面体检
- 估值水平 (PE/PB vs 历史/行业): ...
- 财务健康度: ...
- 行业地位: ...

## 四、未来走势技术分析
| 时间周期 | 技术面状态 | 关键点位 | 置信度 |
|----------|----------|----------|------|
| 短期 (1-5天) | ... | ... | ... |
| 中期 (1-3月) | ... | ... | ... |
| 长期 (6月+) | ... | ... | ... |

## 五、技术参考价位
- **支撑位**: [技术支撑位] (仅供参考，不构成买入建议)
- **阻力位**: [技术阻力位] (仅供参考，不构成卖出建议)
- **止损参考**: [技术止损位]

## 六、风险提示 ⚠️
- 主要风险因素 (波动率风险、政策风险等)
- 本报告仅供学习研究参考，不构成任何投资建议

---
*报告生成时间: [当前时间]*
*重要声明: 本报告由AI基于公开数据和技术指标自动生成，仅供个人学习研究参考，不构成任何投资建议。投资有风险，任何投资决策请咨询持牌专业人士。*

完成分析后，在报告末尾加上 "ANALYSIS_COMPLETE" 标记。
"""


def create_simple_agents(llm_config: dict) -> Dict[str, Any]:
    """
    创建简化版 Agent
    
    Args:
        llm_config: LLM 配置
    
    Returns:
        Agent 字典
    """
    
    # 1. 创建 Assistant Agent (负责分析和推理)
    assistant = AssistantAgent(
        name="Securities_Analyst",
        system_message=ANALYST_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    # 2. 创建 UserProxy Agent (负责执行工具)
    user_proxy = UserProxyAgent(
        name="User_Proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=15,
        is_termination_msg=lambda x: "ANALYSIS_COMPLETE" in str(x.get("content", "")),
        code_execution_config={
            "work_dir": "workspace",
            "use_docker": False,
        },
        function_map=FUNCTION_MAP,  # 注册工具函数
    )
    
    return {
        "assistant": assistant,
        "user_proxy": user_proxy,
    }


def run_simple_analysis(ticker: str, llm_config: dict) -> str:
    """
    运行简化版分析
    
    Args:
        ticker: 股票代码
        llm_config: LLM 配置
    
    Returns:
        分析结果
    """
    agents = create_simple_agents(llm_config)
    
    # 构建分析任务
    task = f"""
请对以下标的进行"vnpy"式的智能量化证券分析：

标的: {ticker}

请严格按照以下步骤进行：
1. 数据获取: 使用 get_stock_data 获取1年数据，使用 get_stock_info 获取基本面。
2. 量化计算: 
   - 使用 calculate_all_indicators 计算全套指标 (MACD, RSI, KDJ, ADX, ATR, CCI, OBV等)。
   - 使用 analyze_trend 获取"量化评分"和"市场状态"。
   - 使用 get_support_resistance_levels 获取关键点位。
3. 智能研判: 结合量化评分、市场状态（趋势/震荡）和多维度指标，进行深度推演。
4. 报告生成: 输出一份包含"AI 量化综述"、"多维技术面扫描"、"未来走势 AI 推演"的专业分析报告。

请开始分析。
"""
    
    # 启动对话
    agents["user_proxy"].initiate_chat(
        agents["assistant"],
        message=task,
    )
    
    # 返回最后一条消息
    return "分析完成"
