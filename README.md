# 🤖 智能多维度证券分析系统

**Smart Multi-Dimensional Securities Analysis System**

基于 Microsoft AutoGen 框架的多智能体协同证券分析系统，支持 **硅基流动 DeepSeek-R1** 和 **Google Gemini Pro** 双 LLM 接入。

## ✨ 功能特点

- **多智能体协作**: 6个专业 Agent 各司其职，协同完成分析任务
- **数据权威性验证**: 专门的审计 Agent 确保数据来源可靠
- **多周期预测**: 覆盖从下个交易日到1年的8个时间维度
- **技术+基本面双维度**: 综合技术指标和财务分析
- **结构化报告**: 生成专业的 Markdown 格式投资报告

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      User Proxy Agent                        │
│                   (用户交互 & 工具执行)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    GroupChat Manager                         │
│                    (工作流协调器)                             │
└───┬─────────┬─────────┬─────────┬─────────┬─────────────────┘
    │         │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ Data  │ │ Data  │ │ Tech  │ │ Fund  │ │  CIO  │
│Engine │→│Verify │→│Analyst│→│Analyst│→│       │
│       │ │       │ │       │ │       │ │       │
└───────┘ └───┬───┘ └───────┘ └───────┘ └───────┘
              │
              ▼ (如验证失败)
        返回 Data Engine 重新获取
```

## 📦 技术栈

| 组件 | 技术 |
|------|------|
| 多智能体框架 | Microsoft AutoGen |
| LLM (默认) | 硅基流动 DeepSeek-R1 |
| LLM (备用) | Google Gemini Pro API |
| 行情数据 | yfinance |
| 新闻爬虫 | BeautifulSoup + Requests |
| 技术分析 | pandas + ta |
| 语言 | Python 3.10+ |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，配置 LLM API Key:

```bash
# 默认使用硅基流动 DeepSeek-R1
DEFAULT_LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=your_siliconflow_api_key

# 或者使用 Google Gemini
# DEFAULT_LLM_PROVIDER=gemini
# GOOGLE_API_KEY=your_gemini_api_key
```

**获取 API Key:**
- 硅基流动: https://cloud.siliconflow.cn/
- Google Gemini: https://aistudio.google.com/app/apikey

### 3. 运行系统

```bash
# 交互模式
python main.py

# 直接分析指定标的
python main.py --analyze AAPL
python main.py --analyze 600519
python main.py --analyze SPY
```

## 🤖 Agent 角色说明

### 1. User Proxy Agent (用户代理)
- 接收用户输入
- 执行工具调用
- 输出最终报告

### 2. Data Engineer Agent (数据工程师)
- 获取行情数据 (yfinance)
- 获取财务报表
- 搜索权威财经新闻
- **优先使用权威来源**: SEC, Bloomberg, Reuters, WSJ

### 3. Data Verifier Agent (数据审计员) ⭐
- **核心角色**: 验证所有数据的权威性
- 检查数据来源是否可信
- 检查数据时效性
- 不通过则打回重新获取

### 4. Technical Analyst Agent (技术分析师)
- 计算技术指标: MACD, KDJ, RSI, 布林带
- 分析均线系统
- 标注支撑位/阻力位
- 短线/中线/长线趋势判断

### 5. Fundamental Analyst Agent (基本面分析师)
- 估值分析: P/E, P/B, PEG
- 财务健康度评估
- 行业分析
- 宏观经济影响

### 6. Chief Investment Officer Agent (首席投资官)
- 汇总所有分析结论
- 生成8个时间周期预测
- 给出操作建议
- 列出风险提示

## 📊 输出报告示例

```markdown
# 📊 AAPL 投资分析报告

## 一、标的概况
| 指标 | 数值 |
|------|------|
| 当前价格 | $195.50 |
| 市值 | $3.01T |
| P/E | 31.2 |

## 二、多周期走势预测
| 时间周期 | 趋势预测 | 置信度 | 目标区间 |
|----------|----------|--------|----------|
| 下个交易日 | 震荡 | 中 | $193-$198 |
| 未来3天 | 偏多 | 中 | $194-$200 |
| 1周 | 看涨 | 高 | $195-$205 |
...

## 三、操作建议
### 短期策略 (1天-15天)
**建议: 持有**
- 理由: RSI 中性，等待突破确认

## 四、风险提示 ⚠️
1. 宏观利率风险
2. 手机销量不及预期
```

## 📁 项目结构

```
Ai-trade/
├── main.py                 # 主入口
├── config.py               # 配置管理
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量模板
├── README.md              # 项目说明
│
├── agents/                 # Agent 定义
│   ├── __init__.py
│   └── agent_definitions.py
│
├── tools/                  # 工具函数
│   ├── __init__.py
│   ├── data_fetcher.py    # 数据获取
│   ├── news_crawler.py    # 新闻爬虫
│   └── technical_analysis.py  # 技术分析
│
├── workflow/               # 工作流编排
│   ├── __init__.py
│   └── group_chat.py
│
├── reports/               # 生成的报告
│   └── *.md
│
└── logs/                  # 日志目录
```

## ⚙️ 配置说明

### 权威来源配置 (config.py)

```python
AUTHORITATIVE_SOURCES = [
    # 官方机构 (最高优先级)
    {"name": "SEC", "domain": "sec.gov", "trust_level": "official"},
    
    # 一级财经媒体
    {"name": "Bloomberg", "domain": "bloomberg.com", "trust_level": "tier1"},
    {"name": "Reuters", "domain": "reuters.com", "trust_level": "tier1"},
    
    # 二级专业平台
    {"name": "Yahoo Finance", "domain": "finance.yahoo.com", "trust_level": "tier2"},
]
```

### 数据新鲜度要求

| 数据类型 | 有效期 |
|----------|--------|
| 价格数据 | 当天 |
| 新闻 | 7天内 |
| 财报 | 1年内 |
| 宏观政策 | 30天内 |

## 🔧 常见问题

### Q: API Key 配置后仍报错？
确保 `.env` 文件在项目根目录，且格式正确:
```
GOOGLE_API_KEY=AIza...
```

### Q: 如何分析 A 股？
直接输入股票代码或名称:
```bash
python main.py --analyze 600519
python main.py --analyze 贵州茅台
```

### Q: 报告保存在哪里？
默认保存在 `reports/` 目录下，文件名格式: `{标的}_{时间戳}.md`

## ⚠️ 免责声明

本系统生成的分析报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。请在做出任何投资决策前咨询专业的金融顾问。

## 📄 许可证

MIT License

---

Made with ❤️ by AI-Trade Team
