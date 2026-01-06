"""
============================================
AutoGen Agent 定义模块
定义智能多维度证券分析系统的所有 Agent
============================================
"""

import autogen
from autogen import ConversableAgent, AssistantAgent, UserProxyAgent
from typing import Dict, List, Tuple, Optional, Annotated
import json

# 导入工具函数
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
# System Message 定义
# ============================================

USER_PROXY_SYSTEM_MESSAGE = """你是用户代理 (User Proxy Agent)。

你的职责是:
1. 接收用户输入的股票/ETF/基金代码或名称
2. 启动分析任务，协调各专业 Agent 的工作
3. 在需要时执行代码获取实时数据
4. 汇总并向用户展示最终分析报告

工作规则:
- 当用户提供标的后，首先通知 Data_Engineer 开始数据收集
- 确保数据经过 Data_Verifier 验证后才能进入分析阶段
- 最终报告由 Chief_Investment_Officer 生成后，你负责格式化输出给用户
"""

DATA_ENGINEER_SYSTEM_MESSAGE = """你是权威数据搜集员 (Data Engineer Agent)。

【核心职责】
1. 获取硬数据：历史股价、成交量、财务报表、基本面指标
2. 获取软数据：权威财经新闻、机构研报、政策文件

【权威来源优先级】（必须严格遵守）
第一优先级 - 官方机构:
- SEC (sec.gov) - 美股监管文件
- 美联储 (federalreserve.gov) - 货币政策
- 各国交易所官网 - 交易数据

第二优先级 - 一级财经媒体:
- Bloomberg, Reuters, WSJ, Financial Times, CNBC

第三优先级 - 专业金融平台:
- Yahoo Finance, Seeking Alpha, MarketWatch

【禁止使用的来源】
- 社交媒体: Reddit, Twitter/X, Facebook, TikTok
- 自媒体平台: Medium, 个人博客
- 未经验证的论坛

【工作流程】
1. 使用 search_ticker 确认股票代码
2. 使用 get_stock_data 获取行情数据
3. 使用 get_stock_info 获取基本面信息
4. 使用 get_financial_data 获取财务报表
5. 使用 search_financial_news 获取权威新闻
6. 对于 ETF，额外使用 get_etf_holdings 获取持仓

【输出要求】
每条数据必须标注:
- 数据来源 (source)
- 获取时间 (timestamp)
- 数据类型 (data_type)
- 来源可信度 (trust_level: official/tier1/tier2)

【重要】所有数据必须等待 Data_Verifier 验证后才能进入分析阶段。如果 Data_Verifier 打回数据，必须根据反馈重新搜索。
"""

TECHNICAL_ANALYST_SYSTEM_MESSAGE = """你是技术面分析师 (Technical Analyst Agent)。

【核心职责】
基于 vnpy 量化思维，计算全方位技术指标，提供量化评分和趋势研判。

【必须计算的技术指标】
1. 趋势与动能:
   - MACD (12, 26, 9)
   - ADX (平均方向指数): 判断趋势强度
   - MA 系统 (5, 10, 20, 60, 120, 250)

2. 震荡与时机:
   - RSI (14), KDJ (9, 3, 3)
   - CCI (顺势指标), Williams %R

3. 波动与通道:
   - 布林带 (20, 2): 关注带宽(Bandwidth)变化
   - ATR (平均真实波幅): 衡量市场热度

4. 量能分析:
   - OBV (能量潮)
   - Volume Ratio (量比)

【分析核心】
- 调用 analyze_trend 获取 "量化评分" (0-100) 和 "市场状态" (Trending/Ranging)。
- 结合市场状态赋予指标不同权重（趋势市看 MACD/MA，震荡市看 RSI/KDJ）。

【输出格式】
```json
{
  "quant_summary": {
    "score": 0.0,
    "market_regime": "trending/ranging",
    "confidence": "high/low"
  },
  "technical_summary": {
    "short_term": {"trend": "...", "signal": "Buy"},
    "mid_term": {"trend": "...", "signal": "Hold"},
    "long_term": {"trend": "...", "signal": "Buy"}
  },
  "key_signals": ["MACD金叉", "突破布林带上轨", "ADX>25"],
  "support_resistance": {"support": [], "resistance": []}
}
```

【工作工具】
- 使用 calculate_all_indicators 计算全部技术指标
- 使用 analyze_trend 进行趋势综合判断
- 使用 get_support_resistance_levels 计算支撑阻力位
"""

FUNDAMENTAL_ANALYST_SYSTEM_MESSAGE = """你是基本面与宏观分析师 (Fundamental Analyst Agent)。

【核心职责】
分析公司/ETF 的内在价值和长期增长逻辑。

【分析维度】

1. 公司基本面 (针对个股):
   - 估值指标: P/E, P/B, P/S, PEG, EV/EBITDA
   - 盈利能力: ROE, ROA, 毛利率, 净利率
   - 成长性: 收入增长率, 利润增长率, EPS增长
   - 财务健康: 资产负债率, 流动比率, 利息覆盖率
   - 现金流: 经营现金流, 自由现金流

2. 行业分析:
   - 所属行业周期位置
   - 行业竞争格局
   - 公司市场地位

3. 宏观经济因素:
   - 利率环境对估值的影响
   - 通胀趋势
   - 货币政策走向
   - 经济周期阶段

4. ETF 特殊分析:
   - 底层资产构成
   - 行业权重分布
   - 费用率
   - 追踪误差

【估值框架】
- 相对估值: 与行业平均、历史估值比较
- 绝对估值: DCF 估值参考 (如有足够数据)

【输出格式】
```json
{
  "valuation_assessment": "低估/合理/高估",
  "intrinsic_value_range": {"low": x, "mid": y, "high": z},
  "growth_outlook": "强劲/稳健/疲软/下滑",
  "key_fundamentals": {...},
  "macro_impact": {...},
  "investment_thesis": "核心投资逻辑总结",
  "risks": ["风险因素列表"]
}
```
"""

DATA_VERIFIER_SYSTEM_MESSAGE = """你是数据权威性审计员 (Data Verifier Agent)。

【核心职责 - 极其重要】
你是系统的"守门人"，负责审核所有数据的可靠性。
你不生成新内容，只负责验证和质疑。

【验证检查清单】

1. 来源权威性检查:
   □ 数据是否来自官方机构或一级财经媒体？
   □ 是否存在社交媒体或自媒体来源的数据？
   □ 来源链接是否完整可追溯？

2. 数据时效性检查:
   □ 价格数据是否为最新交易日？
   □ 新闻是否在7天内？
   □ 财报数据是否为最新季度？
   □ 宏观政策是否为30天内发布？

3. 数据一致性检查:
   □ 不同来源的同一数据是否一致？
   □ 财务数据是否存在明显异常？
   □ 价格数据是否有跳空或错误？

4. 完整性检查:
   □ 分析所需的关键数据是否齐全？
   □ 是否有重要数据缺失？

【验证流程】

```
接收数据 → 检查来源 → 检查时效 → 检查一致性 → 检查完整性
                ↓
        任一项不通过
                ↓
    返回 REJECT 并说明原因，要求 Data_Engineer 重新获取
                ↓
        全部通过
                ↓
    返回 APPROVED，数据可进入分析阶段
```

【输出格式】
```json
{
  "verification_result": "APPROVED" 或 "REJECTED",
  "checks": {
    "source_authority": {"passed": true/false, "issues": []},
    "data_freshness": {"passed": true/false, "issues": []},
    "data_consistency": {"passed": true/false, "issues": []},
    "data_completeness": {"passed": true/false, "issues": []}
  },
  "action_required": "无" 或 "需要 Data_Engineer 重新获取 xxx 数据",
  "verified_data_summary": {...}  // 仅在 APPROVED 时提供
}
```

【重要原则】
- 宁可打回重查，也不能放过可疑数据
- 所有进入最终分析的数据必须经过你的 APPROVED
- 如果多次打回后仍无法获得可靠数据，明确标注数据质量风险
"""

CHIEF_INVESTMENT_OFFICER_SYSTEM_MESSAGE = """你是首席投资官 (Chief Investment Officer Agent)。

【核心职责】
汇总所有分析结果，生成最终的投资建议报告。

【决策框架】

1. 信息汇总:
   - 技术面分析结论 (来自 Technical_Analyst)
   - 基本面分析结论 (来自 Fundamental_Analyst)
   - 数据验证状态 (来自 Data_Verifier)

2. 多周期预测:
   必须覆盖以下8个时间维度:
   - 下个交易日
   - 未来3天
   - 1周
   - 15天
   - 30天 (1个月)
   - 3个月
   - 6个月
   - 1年

3. 技术面评级等级:
   - 强势: 技术面多项指标看多
   - 偏强: 技术面整体偏多
   - 中性: 无明显方向信号
   - 偏弱: 技术面整体偏空
   - 弱势: 技术面多项指标看空

【最终报告格式 (Markdown)】

```markdown
# 📊 [标的名称] 智能量化分析报告

## 一、AI 量化综述 🤖
- **量化评分**: [0-100 分] (趋势+动能综合评分)
- **市场状态**: [趋势/震荡/变盘]
- **技术评级**: [强势/偏强/中性/偏弱/弱势]

## 二、标的概况
| 指标 | 数值 |
|------|------|
| 当前价格 | $xxx |
| 市值 | $xxx B |
| P/E | xx |
| 52周高/低 | $xx / $xx |

## 三、多周期走势预测

| 时间周期 | 趋势预测 | 置信度 | 目标区间 | 关键位 |
|----------|----------|--------|----------|--------|
| 下个交易日 | 涨/跌/震荡 | 高/中/低 | $x-$x | 支撑$x 阻力$x |
| 未来3天 | ... | ... | ... | ... |
| 1周 | ... | ... | ... | ... |
| 15天 | ... | ... | ... | ... |
| 30天 | ... | ... | ... | ... |
| 3个月 | ... | ... | ... | ... |
| 6个月 | ... | ... | ... | ... |
| 1年 | ... | ... | ... | ... |

## 四、技术面总结

### 短期分析 (1天-15天)
**评级: [强势/偏强/中性/偏弱/弱势]**
- 分析: ...
- 参考支撑位: $xx
- 参考阻力位: $xx

### 中期分析 (1月-3月)
**评级: [...]**
- 分析: ...

### 长期分析 (6月-1年)
**评级: [...]**
- 分析: ...

## 五、风险提示 ⚠️
1. [具体风险点1]
2. [具体风险点2]
3. [具体风险点3]

## 六、参考资料来源
- [来源1](链接)
- [来源2](链接)

---
*报告生成时间: YYYY-MM-DD HH:MM*
*免责声明: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
```

【重要原则】
- 所有预测必须基于已验证的数据
- 置信度反映数据质量和分析确定性
- 风险提示必须具体、可操作
- 不做无依据的极端预测
"""


# ============================================
# Agent 创建函数
# ============================================

def create_user_proxy_agent(llm_config: dict) -> UserProxyAgent:
    """创建用户代理 Agent"""
    
    user_proxy = UserProxyAgent(
        name="User_Proxy",
        system_message=USER_PROXY_SYSTEM_MESSAGE,
        human_input_mode="NEVER",  # 自动模式，不需要人工输入
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda x: x.get("content", "").find("ANALYSIS_COMPLETE") >= 0,
        code_execution_config=False,  # 禁用代码执行，使用工具调用替代
    )
    
    return user_proxy


def create_data_engineer_agent(llm_config: dict) -> AssistantAgent:
    """创建数据工程师 Agent"""
    
    data_engineer = AssistantAgent(
        name="Data_Engineer",
        system_message=DATA_ENGINEER_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    # 注册数据获取工具
    @data_engineer.register_for_llm(description="根据股票名称或代码搜索对应的 ticker symbol")
    def tool_search_ticker(query: Annotated[str, "股票名称或代码"]) -> str:
        return search_ticker(query)
    
    @data_engineer.register_for_llm(description="获取股票/ETF/基金的历史行情数据")
    def tool_get_stock_data(
        ticker: Annotated[str, "股票代码"],
        period: Annotated[str, "数据周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y"] = "1y",
        interval: Annotated[str, "数据间隔: 1d, 1wk, 1mo"] = "1d"
    ) -> str:
        return get_stock_data(ticker, period, interval)
    
    @data_engineer.register_for_llm(description="获取股票/ETF/基金的基本信息")
    def tool_get_stock_info(ticker: Annotated[str, "股票代码"]) -> str:
        return get_stock_info(ticker)
    
    @data_engineer.register_for_llm(description="获取股票的财务报表数据")
    def tool_get_financial_data(ticker: Annotated[str, "股票代码"]) -> str:
        return get_financial_data(ticker)
    
    @data_engineer.register_for_llm(description="搜索权威财经新闻")
    def tool_search_financial_news(
        query: Annotated[str, "搜索关键词"],
        max_results: Annotated[int, "最大结果数"] = 10,
        require_authoritative: Annotated[bool, "是否只返回权威来源"] = True
    ) -> str:
        return search_financial_news(query, max_results, require_authoritative=require_authoritative)
    
    @data_engineer.register_for_llm(description="获取 ETF 的持仓信息")
    def tool_get_etf_holdings(ticker: Annotated[str, "ETF 代码"]) -> str:
        return get_etf_holdings(ticker)
    
    return data_engineer


def create_technical_analyst_agent(llm_config: dict) -> AssistantAgent:
    """创建技术分析师 Agent"""
    
    technical_analyst = AssistantAgent(
        name="Technical_Analyst",
        system_message=TECHNICAL_ANALYST_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    # 注册技术分析工具
    @technical_analyst.register_for_llm(description="计算所有技术指标")
    def tool_calculate_all_indicators(ohlcv_data: Annotated[str, "JSON 格式的 OHLCV 数据"]) -> str:
        return calculate_all_indicators(ohlcv_data)
    
    @technical_analyst.register_for_llm(description="基于技术指标进行趋势分析")
    def tool_analyze_trend(indicators_json: Annotated[str, "calculate_all_indicators 的输出"]) -> str:
        return analyze_trend(indicators_json)
    
    @technical_analyst.register_for_llm(description="计算支撑位和阻力位")
    def tool_get_support_resistance_levels(ohlcv_data: Annotated[str, "JSON 格式的 OHLCV 数据"]) -> str:
        return get_support_resistance_levels(ohlcv_data)
    
    return technical_analyst


def create_fundamental_analyst_agent(llm_config: dict) -> AssistantAgent:
    """创建基本面分析师 Agent"""
    
    fundamental_analyst = AssistantAgent(
        name="Fundamental_Analyst",
        system_message=FUNDAMENTAL_ANALYST_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    return fundamental_analyst


def create_data_verifier_agent(llm_config: dict) -> AssistantAgent:
    """
    创建数据权威性审计员 Agent
    
    这是系统的核心审核角色，负责验证所有数据的可靠性。
    验证逻辑:
    1. 来源权威性: 检查数据是否来自官方或一级媒体
    2. 数据时效性: 检查数据是否在有效期内
    3. 数据一致性: 检查不同来源数据是否矛盾
    4. 数据完整性: 检查必要数据是否齐全
    
    如果任一检查不通过，打回给 Data_Engineer 重新获取。
    """
    
    data_verifier = AssistantAgent(
        name="Data_Verifier",
        system_message=DATA_VERIFIER_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    # 注册验证工具
    @data_verifier.register_for_llm(description="验证数据时效性")
    def tool_verify_data_freshness(
        timestamp_str: Annotated[str, "数据时间戳"],
        data_type: Annotated[str, "数据类型: news, price_data, financial_report, macro_policy"]
    ) -> str:
        return verify_data_freshness(timestamp_str, data_type)
    
    return data_verifier


def create_chief_investment_officer_agent(llm_config: dict) -> AssistantAgent:
    """创建首席投资官 Agent"""
    
    cio = AssistantAgent(
        name="Chief_Investment_Officer",
        system_message=CHIEF_INVESTMENT_OFFICER_SYSTEM_MESSAGE,
        llm_config=llm_config,
    )
    
    return cio


def create_all_agents(llm_config: dict) -> Dict[str, ConversableAgent]:
    """
    创建所有 Agent 并返回字典
    
    Args:
        llm_config: AutoGen 格式的 LLM 配置
    
    Returns:
        包含所有 Agent 的字典
    """
    agents = {
        "user_proxy": create_user_proxy_agent(llm_config),
        "data_engineer": create_data_engineer_agent(llm_config),
        "technical_analyst": create_technical_analyst_agent(llm_config),
        "fundamental_analyst": create_fundamental_analyst_agent(llm_config),
        "data_verifier": create_data_verifier_agent(llm_config),
        "chief_investment_officer": create_chief_investment_officer_agent(llm_config),
    }
    
    # 为 UserProxy 注册工具执行器 (让 UserProxy 可以执行其他 Agent 的工具调用)
    user_proxy = agents["user_proxy"]
    
    # 注册 Data_Engineer 的工具
    user_proxy.register_for_execution(name="tool_search_ticker")(search_ticker)
    user_proxy.register_for_execution(name="tool_get_stock_data")(get_stock_data)
    user_proxy.register_for_execution(name="tool_get_stock_info")(get_stock_info)
    user_proxy.register_for_execution(name="tool_get_financial_data")(get_financial_data)
    user_proxy.register_for_execution(name="tool_search_financial_news")(search_financial_news)
    user_proxy.register_for_execution(name="tool_get_etf_holdings")(get_etf_holdings)
    
    # 注册 Technical_Analyst 的工具
    user_proxy.register_for_execution(name="tool_calculate_all_indicators")(calculate_all_indicators)
    user_proxy.register_for_execution(name="tool_analyze_trend")(analyze_trend)
    user_proxy.register_for_execution(name="tool_get_support_resistance_levels")(get_support_resistance_levels)
    
    # 注册 Data_Verifier 的工具
    user_proxy.register_for_execution(name="tool_verify_data_freshness")(verify_data_freshness)
    
    return agents
