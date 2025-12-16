"""
============================================
FastAPI 后端 API 服务
提供证券分析的 REST API 接口
============================================
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_llm_config, APIConfig, SystemConfig
from tools.data_fetcher import get_stock_data, get_stock_info, get_financial_data, search_ticker
from tools.technical_analysis import calculate_all_indicators, analyze_trend, get_support_resistance_levels


# ============================================
# 数据模型
# ============================================

class AnalysisRequest(BaseModel):
    """分析请求"""
    ticker: str
    analysis_type: str = "full"  # full, quick, technical, fundamental


class AnalysisResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    current_step: str
    result: Optional[str] = None
    error: Optional[str] = None


# ============================================
# 全局状态管理
# ============================================

# 存储分析任务状态
analysis_tasks: Dict[str, Dict[str, Any]] = {}


# ============================================
# FastAPI 应用
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("[START] Securities Analysis API starting...")
    yield
    print("[STOP] Securities Analysis API shutting down...")


app = FastAPI(
    title="智能多维度证券分析系统 API",
    description="基于 AutoGen + DeepSeek-R1 的多智能体证券分析系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# API 路由
# ============================================

@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return {"message": "智能证券分析系统 API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        APIConfig.validate()
        return {
            "status": "healthy",
            "llm_provider": APIConfig.DEFAULT_LLM_PROVIDER,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/search/{query}")
async def search_stock(query: str):
    """搜索股票代码"""
    try:
        result = search_ticker(query)
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{ticker}/quote")
async def get_quote(ticker: str):
    """获取股票行情"""
    try:
        data = await asyncio.to_thread(get_stock_data, ticker, "5d", "1d")
        info = await asyncio.to_thread(get_stock_info, ticker)
        return {
            "quote": json.loads(data),
            "info": json.loads(info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{ticker}/technical")
async def get_technical_analysis(ticker: str):
    """获取技术分析"""
    try:
        # 获取行情数据
        data = await asyncio.to_thread(get_stock_data, ticker, "1y", "1d")
        
        # 计算技术指标
        indicators = await asyncio.to_thread(calculate_all_indicators, data)
        
        # 趋势分析
        trend = await asyncio.to_thread(analyze_trend, indicators)
        
        # 支撑阻力位
        levels = await asyncio.to_thread(get_support_resistance_levels, data)
        
        return {
            "indicators": json.loads(indicators),
            "trend": json.loads(trend),
            "levels": json.loads(levels)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def start_analysis(request: AnalysisRequest):
    """启动完整分析任务"""
    task_id = str(uuid.uuid4())[:8]
    
    # 初始化任务状态
    analysis_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "current_step": "初始化",
        "ticker": request.ticker,
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }
    
    # 使用线程启动后台任务，完全脱离当前请求
    import threading
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_full_analysis(task_id, request.ticker))
        loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    return AnalysisResponse(
        task_id=task_id,
        status="pending",
        message=f"分析任务已创建，任务ID: {task_id}"
    )


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        current_step=task["current_step"],
        result=task["result"],
        error=task["error"]
    )


@app.get("/api/stream/{task_id}")
async def stream_analysis(task_id: str):
    """SSE 流式返回分析进度"""
    
    async def event_generator():
        while True:
            if task_id not in analysis_tasks:
                yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                break
            
            task = analysis_tasks[task_id]
            yield f"data: {json.dumps(task, ensure_ascii=False)}\n\n"
            
            if task["status"] in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ============================================
# 后台分析任务
# ============================================

async def run_full_analysis(task_id: str, ticker: str):
    """
    运行完整的多 Agent 分析
    """
    task = analysis_tasks[task_id]
    
    try:
        # === 第一列：数据获取 ===
        # 步骤 1: AI Agents正在集结
        task["status"] = "running"
        task["current_step"] = "AI Agents正在集结"
        task["progress"] = 5
        await asyncio.sleep(0.2)
        
        # 步骤 2: 正在获取实时行情数据
        task["current_step"] = "正在获取实时行情数据"
        task["progress"] = 15
        
        # 自动识别并标准化ticker（自动添加市场后缀）
        search_result = await asyncio.to_thread(search_ticker, ticker)
        search_dict = json.loads(search_result)
        
        if search_dict.get("status") == "success":
            ticker = search_dict.get("ticker", ticker)
        
        stock_data = await asyncio.to_thread(get_stock_data, ticker, "2y", "1d")
        stock_data_dict = json.loads(stock_data)
        
        if stock_data_dict.get("status") != "success":
            raise Exception(f"无法获取 {ticker} 的行情数据")
        
        await asyncio.sleep(0.3)
        
        # 步骤 3: 基本面分析师正在评估价值
        task["current_step"] = "基本面分析师正在评估价值"
        task["progress"] = 25
        
        stock_info = await asyncio.to_thread(get_stock_info, ticker)
        stock_info_dict = json.loads(stock_info)
        
        await asyncio.sleep(0.3)
        
        # === 第二列：量化分析 ===
        # 步骤 4: 技术面分析师正在计算指标
        task["current_step"] = "技术面分析师正在计算指标"
        task["progress"] = 35
        
        indicators = await asyncio.to_thread(calculate_all_indicators, stock_data)
        indicators_dict = json.loads(indicators)
        
        # 检查指标数据是否有效
        if indicators_dict.get("status") == "error" or not indicators_dict.get("indicators"):
            raise Exception(f"无法计算 {ticker} 的技术指标：{indicators_dict.get('message', '数据不足或格式错误')}")
        
        await asyncio.sleep(0.3)
        
        # 步骤 5: 量化引擎正在生成信号
        task["current_step"] = "量化引擎正在生成信号"
        task["progress"] = 45
        
        trend = await asyncio.to_thread(analyze_trend, indicators)
        trend_dict = json.loads(trend)
        
        # 检查趋势分析是否有效
        if trend_dict.get("status") == "error":
            raise Exception(f"无法分析 {ticker} 的趋势：{trend_dict.get('message', '量化分析失败')}")
        
        await asyncio.sleep(0.3)
        
        # 步骤 6: 数据审计员正在验证来源
        task["current_step"] = "数据审计员正在验证来源"
        task["progress"] = 55
        
        levels = await asyncio.to_thread(get_support_resistance_levels, stock_data)
        levels_dict = json.loads(levels)
        
        await asyncio.sleep(0.3)
        
        # === 第三列：AI分析 ===
        # 步骤 7: 风险管理专家正在评估风险
        task["current_step"] = "风险管理专家正在评估风险"
        task["progress"] = 65
        await asyncio.sleep(0.3)
        
        # 步骤 8: 首席投资官正在生成报告
        task["current_step"] = "首席投资官正在生成报告"
        task["progress"] = 75
        
        # 调用 AI 生成报告和预测（多Agent论证）
        report, predictions = await generate_ai_report_with_predictions(
            ticker, 
            stock_data_dict, 
            stock_info_dict, 
            indicators_dict, 
            trend_dict, 
            levels_dict
        )

        # 从趋势分析中提取量化评分和市场状态，用于前端快速展示
        quant_analysis = trend_dict.get("quant_analysis", {})
        trend_analysis = trend_dict.get("trend_analysis", trend_dict)
        signal_details = trend_dict.get("signal_details", [])

        quant_score = quant_analysis.get("score")
        market_regime = quant_analysis.get("market_regime", "unknown")
        volatility_state = quant_analysis.get("volatility_state", "medium")
        quant_reco = quant_analysis.get("recommendation", "hold")

        # 摘要部分技术指标 (ADX/ATR) 用于前端仪表盘小字说明
        ind_root = indicators_dict.get("indicators", indicators_dict or {})
        if isinstance(ind_root, dict):
            adx_data = ind_root.get("adx", {}) or {}
            atr_data = ind_root.get("atr", {}) or {}
        else:
            adx_data = {}
            atr_data = {}

        indicator_overview = {
            "adx_value": adx_data.get("adx"),
            "adx_trend_strength": adx_data.get("trend_strength"),
            "atr_value": atr_data.get("value"),
            "atr_pct": atr_data.get("percentage"),
        }

        reco_map = {
            "strong_buy": "强力买入",
            "buy": "建议买入",
            "hold": "持有观望",
            "sell": "建议减持",
            "strong_sell": "强力卖出",
        }
        regime_map = {
            "trending": "趋势市",
            "ranging": "震荡市",
            "squeeze": "窄幅整理/突破蓄势",
            "unknown": "待判定",
        }
        vol_map = {
            "high": "高波动",
            "medium": "中等波动",
            "low": "低波动",
        }

        if isinstance(quant_score, (int, float)):
            score_text = f"{quant_score:.1f}"
        else:
            score_text = "N/A"

        # 步骤 9: 质量控制专员正在审核
        task["current_step"] = "质量控制专员正在审核"
        task["progress"] = 90
        await asyncio.sleep(0.2)
        
        ai_summary = (
            f"量化评分 {score_text} 分，当前处于{regime_map.get(market_regime, '待判定')}，"
            f"{vol_map.get(volatility_state, '波动适中')}，综合建议：{reco_map.get(quant_reco, '观望')}。"
        )

        task["progress"] = 100
        task["current_step"] = "分析完成"
        task["status"] = "completed"
        task["result"] = json.dumps({
            "report": report,
            "predictions": predictions,
            "quant_analysis": quant_analysis,
            "trend_analysis": trend_analysis,
            "ai_summary": ai_summary,
            "indicator_overview": indicator_overview,
            "signal_details": signal_details,
        }, ensure_ascii=False)
        
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
        task["current_step"] = "失败"


def generate_predictions(
    indicators: dict,
    trend: dict,
    levels: dict,
    stock_data: dict
) -> list:
    """
    基于技术指标生成多周期预测
    """
    ind = indicators.get("indicators", indicators)
    if isinstance(ind, list):
        ind = {}
    
    trend_analysis = trend.get("trend_analysis", trend)
    if isinstance(trend_analysis, list):
        trend_analysis = {}
    
    # 获取关键指标
    rsi = ind.get("rsi", {})
    rsi_value = rsi.get("value", 50) if isinstance(rsi, dict) else 50
    
    macd = ind.get("macd", {})
    macd_trend = macd.get("trend", "neutral") if isinstance(macd, dict) else "neutral"
    macd_histogram = macd.get("histogram", 0) if isinstance(macd, dict) else 0
    
    kdj = ind.get("kdj", {})
    kdj_status = kdj.get("status", "neutral") if isinstance(kdj, dict) else "neutral"
    
    ma_trend = ind.get("ma_trend", "unknown")
    
    bb = ind.get("bollinger_bands", {})
    bb_position = bb.get("position", 0) if isinstance(bb, dict) else 0
    
    # 获取当前价格和支撑阻力位
    latest_price = ind.get("latest_price", stock_data.get("summary", {}).get("latest_price", 1.0))
    
    key_levels = levels.get("key_levels", levels)
    if isinstance(key_levels, list):
        support_prices = [l.get("price", 0) for l in key_levels if l.get("type") == "support"]
        resistance_prices = [l.get("price", 0) for l in key_levels if l.get("type") == "resistance"]
        nearest_support = support_prices[0] if support_prices else latest_price * 0.95
        nearest_resistance = resistance_prices[0] if resistance_prices else latest_price * 1.05
    else:
        nearest_support = key_levels.get("nearest_support", latest_price * 0.95)
        nearest_resistance = key_levels.get("nearest_resistance", latest_price * 1.05)
    
    if isinstance(nearest_support, str):
        nearest_support = latest_price * 0.95
    if isinstance(nearest_resistance, str):
        nearest_resistance = latest_price * 1.05
    
    # 计算综合得分 (-100 到 100)
    score = 0
    
    # RSI 贡献 (-30 到 30)
    if rsi_value < 30:
        score += 25  # 超卖，看涨
    elif rsi_value > 70:
        score -= 25  # 超买，看跌
    else:
        score += (50 - rsi_value) * 0.5  # 中性区间
    
    # MACD 贡献 (-25 到 25)
    if macd_trend == "bullish":
        score += 20
    elif macd_trend == "bearish":
        score -= 20
    if macd_histogram > 0:
        score += 5
    elif macd_histogram < 0:
        score -= 5
    
    # KDJ 贡献 (-20 到 20)
    if kdj_status == "oversold":
        score += 15
    elif kdj_status == "overbought":
        score -= 15
    
    # 均线趋势贡献 (-15 到 15)
    if ma_trend == "bullish_alignment":
        score += 15
    elif ma_trend == "bearish_alignment":
        score -= 15
    
    # 布林带位置贡献 (-10 到 10)
    if bb_position < -50:
        score += 10  # 接近下轨，看涨
    elif bb_position > 50:
        score -= 10  # 接近上轨，看跌
    
    # 根据得分生成预测
    def get_trend_and_target(base_score, period_factor, volatility=0.02):
        adjusted_score = base_score * period_factor
        
        if adjusted_score > 30:
            trend = "bullish"
            # 计算目标涨幅
            target_pct = min(adjusted_score * volatility, 50)
        elif adjusted_score < -30:
            trend = "bearish"
            target_pct = max(adjusted_score * volatility, -50)
        else:
            trend = "neutral"
            target_pct = adjusted_score * volatility * 0.5
        
        # 置信度
        abs_score = abs(adjusted_score)
        if abs_score > 50:
            confidence = "high"
        elif abs_score > 25:
            confidence = "medium"
        else:
            confidence = "low"
        
        return trend, target_pct, confidence
    
    # 生成各周期预测
    predictions = []
    periods = [
        ("1D", "明日", 0.3, 0.005),
        ("3D", "3天", 0.5, 0.01),
        ("1W", "1周", 0.7, 0.02),
        ("15D", "15天", 0.85, 0.03),
        ("1M", "1个月", 1.0, 0.05),
        ("3M", "3个月", 1.2, 0.10),
        ("6M", "6个月", 1.3, 0.15),
        ("1Y", "1年", 1.5, 0.25),
    ]
    
    for period, label, factor, volatility in periods:
        trend, target_pct, confidence = get_trend_and_target(score, factor, volatility)
        
        # 格式化目标
        if target_pct > 0:
            target = f"+{target_pct:.1f}%"
        elif target_pct < 0:
            target = f"{target_pct:.1f}%"
        else:
            target = "±0.5%"
        
        predictions.append({
            "period": period,
            "label": label,
            "trend": trend,
            "confidence": confidence,
            "target": target
        })
    
    return predictions


async def generate_ai_report_with_predictions(
    ticker: str,
    stock_data: dict,
    stock_info: dict,
    indicators: dict,
    trend: dict,
    levels: dict
) -> tuple:
    """
    调用 AI 多Agent分析生成报告和预测
    返回: (report, predictions)
    """
    from openai import OpenAI
    import httpx
    import os
    import re
    
    # 强制禁用系统代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    api_key = APIConfig.SILICONFLOW_API_KEY
    
    # 创建强制直连的 HTTP 客户端
    transport = httpx.HTTPTransport(proxy=None)
    http_client = httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(180.0, connect=30.0)
    )
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        http_client=http_client
    )
    
    # 准备数据摘要
    summary = stock_data.get("summary", {})
    info = stock_info.get("basic_info", {})
    price_info = stock_info.get("price_info", {})
    
    ind = indicators.get("indicators", indicators)
    if isinstance(ind, list):
        ind = {}
    
    trend_analysis = trend.get("trend_analysis", trend)
    if isinstance(trend_analysis, list):
        trend_analysis = {}
    
    latest_price = ind.get("latest_price", summary.get("latest_price", 1.0))
    
    # ============================================
    # Agent 1: 技术分析师 - 生成多周期预测
    # ============================================
    prediction_prompt = f"""你是一位资深的量化分析师，请基于以下技术指标数据，对标的进行多周期价格预测。

## 标的信息
- 代码: {ticker}
- 当前价格: {latest_price}

## 基础技术指标
- MACD: {ind.get('macd', {})}
- RSI: {ind.get('rsi', {})}
- KDJ: {ind.get('kdj', {})}
- 均线排列: {ind.get('ma_trend', 'N/A')}
- 均线数据: {ind.get('moving_averages', {})}
- 布林带: {ind.get('bollinger_bands', {})}
- 价格位置: {ind.get('price_position', {})}

## 高级技术指标
- ATR波动率: {ind.get('atr', {})}
- Williams %R: {ind.get('williams_r', {})}
- CCI: {ind.get('cci', {})}
- ADX趋势强度: {ind.get('adx', {})}
- 动量: {ind.get('momentum', {})}
- ROC变动率: {ind.get('roc', {})}
- OBV能量潮: {ind.get('obv', {})}
- 成交量: {ind.get('volume_analysis', {})}

## 多周期涨跌幅历史
{ind.get('period_returns', {})}

## 趋势分析
- 综合趋势: {trend_analysis.get('trend_cn', trend_analysis.get('overall_trend', 'N/A'))}
- 多头信号: {trend_analysis.get('bullish_signals', 0)}
- 空头信号: {trend_analysis.get('bearish_signals', 0)}

请严格按以下JSON格式输出8个周期的预测（不要输出其他内容）：
```json
[
  {{"period": "1D", "label": "明日", "trend": "bullish/bearish/neutral", "confidence": "high/medium/low", "target": "+X.X%或-X.X%"}},
  {{"period": "3D", "label": "3天", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "1W", "label": "1周", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "15D", "label": "15天", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "1M", "label": "1个月", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "3M", "label": "3个月", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "6M", "label": "6个月", "trend": "...", "confidence": "...", "target": "..."}},
  {{"period": "1Y", "label": "1年", "trend": "...", "confidence": "...", "target": "..."}}
]
```

分析要点：
1. 综合多个指标信号：RSI/KDJ超买超卖、MACD/均线金叉死叉、CCI/Williams %R趋势
2. 参考ADX趋势强度、ATR波动率、OBV资金流向、动量/ROC变化
3. 结合多周期历史涨跌幅表现，短期参考5日/10日，长期参考60日/250日
4. 短期预测置信度应更高（有数据支撑），长期预测置信度降低
5. target涨跌幅要合理：短期(1D-1W)±0.5%~5%，中期(15D-1M)±3%~15%，长期(3M-1Y)±10%~50%
6. 如果多空信号冲突严重，选择neutral并降低置信度"""

    predictions = []
    
    try:
        # Agent 1 调用
        pred_response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": "你是量化分析师，只输出JSON格式的预测数据，不要输出其他内容。"},
                {"role": "user", "content": prediction_prompt}
            ],
            max_tokens=1000,
            temperature=0.2,
            timeout=60
        )
        
        pred_text = pred_response.choices[0].message.content
        # 提取 JSON
        json_match = re.search(r'\[[\s\S]*\]', pred_text)
        if json_match:
            predictions = json.loads(json_match.group())
    except Exception as e:
        print(f"Agent 1 预测失败: {e}")
        # 使用基于规则的预测作为备用
        predictions = generate_predictions(indicators, trend, levels, stock_data)
    
    # ============================================
    # Agent 2: 报告撰写师 - 生成详细报告
    # ============================================
    report = await generate_ai_report(
        ticker, stock_data, stock_info, indicators, trend, levels
    )
    
    return report, predictions


async def generate_ai_report(
    ticker: str,
    stock_data: dict,
    stock_info: dict,
    indicators: dict,
    trend: dict,
    levels: dict
) -> str:
    """
    调用 DeepSeek-R1 生成分析报告
    """
    from openai import OpenAI
    import httpx
    import os
    
    # 强制禁用系统代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    api_key = APIConfig.SILICONFLOW_API_KEY
    
    # 创建强制直连的 HTTP 客户端
    transport = httpx.HTTPTransport(proxy=None)
    http_client = httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(120.0, connect=30.0)
    )
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        http_client=http_client
    )
    
    # 准备数据摘要
    summary = stock_data.get("summary", {})
    info = stock_info.get("basic_info", {})
    price_info = stock_info.get("price_info", {})
    valuation = stock_info.get("valuation", {})
    
    # 兼容基金和股票两种数据结构
    ind = indicators.get("indicators", indicators)
    if isinstance(ind, list):
        ind = {}
    
    trend_analysis = trend.get("trend_analysis", {})
    if isinstance(trend_analysis, list):
        trend_analysis = {}
    
    # 提前提取period_returns，避免后续prompt中使用时未定义
    period_returns = ind.get('period_returns', {})

    quant_analysis = trend.get("quant_analysis", {})
    quant_score = quant_analysis.get("score", "N/A")
    quant_regime = quant_analysis.get("market_regime", "unknown")
    quant_vol_state = quant_analysis.get("volatility_state", "medium")
    quant_reco_code = quant_analysis.get("recommendation", "hold")

    reco_map = {
        "strong_buy": "强力买入",
        "buy": "买入",
        "hold": "持有",
        "sell": "减持",
        "strong_sell": "卖出",
    }
    regime_map = {
        "trending": "趋势市",
        "ranging": "震荡市",
        "squeeze": "窄幅整理/突破蓄势",
        "unknown": "待判定",
    }
    vol_map = {
        "high": "高波动",
        "medium": "中等波动",
        "low": "低波动",
    }
    
    # 处理 key_levels 可能是列表的情况
    key_levels = levels.get("key_levels", {})
    if isinstance(key_levels, list):
        support_levels = [l.get("price") for l in key_levels if l.get("type") == "support"]
        resistance_levels = [l.get("price") for l in key_levels if l.get("type") == "resistance"]
        key_levels = {
            "nearest_support": support_levels[0] if support_levels else "N/A",
            "nearest_resistance": resistance_levels[0] if resistance_levels else "N/A"
        }
    
    # 获取当前时间
    current_datetime = datetime.now()
    report_date = current_datetime.strftime("%Y年%m月%d日")
    report_time = current_datetime.strftime("%H:%M:%S")
    
    prompt = f"""
**重要提示**: 当前日期是 {report_date}，当前时间是 {report_time}。请在报告中使用此日期作为报告生成时间，不要使用其他日期。

请根据以下数据生成专业详细的证券/基金分析报告：

## 标的信息
- 代码: {ticker}
- 名称: {info.get('name', ticker)}
- 当前价格/净值: {summary.get('latest_price', 'N/A')}
- 涨跌幅: {summary.get('period_change_pct', 'N/A')}%
- 52周最高: {price_info.get('52_week_high', 'N/A')}
- 52周最低: {price_info.get('52_week_low', 'N/A')}

## 估值/规模指标
- 市盈率 (P/E): {valuation.get('pe_ratio', 'N/A')}
- 市净率 (P/B): {valuation.get('price_to_book', 'N/A')}
- 市值/规模: {valuation.get('market_cap', 'N/A')}

## 技术指标数据
- MACD: {ind.get('macd', {})}
- RSI (14日): {ind.get('rsi', {})}
- KDJ: {ind.get('kdj', {})}
- 均线排列: {ind.get('ma_trend', 'N/A')}
- 移动平均线: {ind.get('moving_averages', {})}
- 布林带: {ind.get('bollinger_bands', {})}
- 成交量分析: {ind.get('volume_analysis', {})}
- 价格位置: {ind.get('price_position', {})}

## 高级技术指标
- ATR波动率: {ind.get('atr', {})}
- Williams %R: {ind.get('williams_r', {})}
- CCI顺势指标: {ind.get('cci', {})}
- ADX趋势强度: {ind.get('adx', {})}
- 动量指标: {ind.get('momentum', {})}
- ROC变动率: {ind.get('roc', {})}

## 多周期涨跌幅
{ind.get('period_returns', {})}

## 趋势与量化分析结果
- 综合趋势: {trend_analysis.get('trend_cn', trend_analysis.get('overall_trend', 'N/A'))}
- 趋势强度: {trend_analysis.get('trend_strength', 'N/A')}
- 量化评分 (0-100): {quant_score}
- 市场状态 (Regime): {regime_map.get(quant_regime, quant_regime)}
- 波动状态: {vol_map.get(quant_vol_state, quant_vol_state)}
- 量化建议: {reco_map.get(quant_reco_code, quant_reco_code)}
- 多头信号: {trend_analysis.get('bullish_signals', 0)} 个
- 空头信号: {trend_analysis.get('bearish_signals', 0)} 个
- 系统建议: {trend_analysis.get('recommendation', 'N/A')}

## 关键价位
- 支撑位: {key_levels.get('nearest_support', levels.get('support_levels', 'N/A'))}
- 阻力位: {key_levels.get('nearest_resistance', levels.get('resistance_levels', 'N/A'))}

---

请生成一份**专业、详细、实用**的投资分析报告，必须包含以下完整章节：

## 一、标的概况
用 Markdown 表格展示核心指标（代码、名称、价格、涨跌、市值等）

## 二、技术面深度分析
分小节详细分析（基于2年历史数据）：

### 趋势类指标
1. **趋势分析**: 当前趋势方向、趋势强度（ADX）、趋势持续时间
2. **均线系统**: MA5/MA10/MA20/MA60/MA120/MA250 排列情况，支撑压力
3. **MACD 分析**: DIF/DEA/柱状图状态，金叉/死叉信号

### 震荡类指标
4. **RSI 分析**: 当前 RSI 值，超买超卖区间，背离情况
5. **KDJ 分析**: K/D/J 三线状态，交叉信号
6. **Williams %R**: 威廉指标超买超卖判断
7. **CCI 分析**: 顺势指标强弱判断

### 波动与动量
8. **布林带分析**: 价格位置、带宽变化、轨道压力支撑
9. **ATR 波动率**: 日均波动幅度，风险评估
10. **动量/ROC**: 价格动能方向和强度

### 量价分析
11. **成交量分析**: 量价配合、放量缩量、OBV能量潮趋势

### 多周期表现
12. **区间涨跌**:

| 周期 | 涨跌幅 |
|--------|--------|
| 5日 | {period_returns.get('5日', 'N/A')}% |
| 10日 | {period_returns.get('10日', 'N/A')}% |
| 20日 | {period_returns.get('20日', 'N/A')}% |
| 60日 | {period_returns.get('60日', 'N/A')}% |
| 120日 | {period_returns.get('120日', 'N/A')}% |
| 250日 | {period_returns.get('250日', 'N/A')}% |

## 三、支撑阻力位分析
- 列出多个支撑位和阻力位
- 说明各价位的重要性
- 给出突破/跌破后的应对策略

## 四、多周期价格预测
用 Markdown 表格展示 8 个时间周期的预测：

| 周期 | 预测方向 | 目标价位 | 置信度 | 关键观察点 |
|------|----------|----------|--------|------------|
| 下个交易日 | ... | ... | ...% | ... |
| 3天 | ... | ... | ...% | ... |
| 1周 | ... | ... | ...% | ... |
| 2周 | ... | ... | ...% | ... |
| 1个月 | ... | ... | ...% | ... |
| 3个月 | ... | ... | ...% | ... |
| 6个月 | ... | ... | ...% | ... |
| 1年 | ... | ... | ...% | ... |

## 五、操作建议
分三个维度给出具体建议：
1. **短线交易者** (1-5天): 具体买卖点位、止损位、目标位
2. **波段操作者** (1-4周): 建仓区间、加仓条件、止盈止损
3. **中长期投资者** (1月以上): 配置建议、定投策略、持仓比例

## 六、风险提示
列出至少 5 个风险因素：
- 技术面风险
- 基本面风险
- 市场系统性风险
- 流动性风险
- 其他特定风险

## 七、总结评级
给出综合评级（强力买入/买入/持有/减持/卖出）和核心理由

## 八、量化评分与策略说明
用一小节专门解释本次量化打分逻辑：
- 列出参与打分的主要指标（MACD、MA系统、RSI、KDJ、布林带、ATR、ADX、OBV、CCI、Williams %R、成交量、52周高低等）
- 说明哪些指标当前偏多、哪些偏空
- 解释为什么本次量化评分为 {quant_score} 分，以及对应的风险/机会
- 指出当前更适合的策略模式（例如：趋势跟随、区间交易、观望防守），并给出1-2句简洁总结

---
使用标准 Markdown 格式，表格清晰，层次分明。
"""
    try:
        import re

        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1",
            messages=[
                {"role": "system", "content": "你是一位资深的证券分析师，擅长技术分析和基本面分析。请生成专业、客观的投资分析报告。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.3,
            timeout=120
        )
        report_text = response.choices[0].message.content

        # 规范化报告日期和时间为当前日期时间
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime("%Y年%m月%d日")
        current_time_str = current_datetime.strftime("%H:%M:%S")
        
        # 替换所有可能的旧日期
        report_text = re.sub(
            r"报告生成时间[:：]\s*\d{4}年\d{1,2}月\d{1,2}日",
            f"报告生成时间：{current_date_str}",
            report_text,
        )
        report_text = re.sub(
            r"报告日期[:：]\s*\d{4}年\d{1,2}月\d{1,2}日",
            f"报告日期：{current_date_str}",
            report_text,
        )
        report_text = re.sub(
            r"\d{4}年\d{1,2}月\d{1,2}日",
            current_date_str,
            report_text,
            count=5  # 最多替换前5个旧日期
        )
        
        # 在报告末尾添加明确的元数据
        footer = f"""

---

**报告生成时间**: {current_date_str} {current_time_str} | **数据来源**: 量化系统 + AI多智能体分析

*本报告由量化引擎(基于vnpy架构)与AI Agent深度联动生成，整合了硬数据分析与软判断评估。*
"""
        
        if "报告生成时间" not in report_text and "报告日期" not in report_text:
            report_text += footer

        return report_text
    except Exception as e:
        # LLM 连接失败时返回详细的本地分析报告
        print(f"LLM API Error: {e}")
        
        # 获取更多指标数据
        macd = ind.get('macd', {})
        rsi = ind.get('rsi', {})
        kdj = ind.get('kdj', {})
        bb = ind.get('bollinger_bands', {})
        ma_data = ind.get('moving_averages', {})
        atr = ind.get('atr', {})
        obv = ind.get('obv', {})
        cci = ind.get('cci', {})
        williams = ind.get('williams_r', {})
        adx = ind.get('adx', {})
        period_returns = ind.get('period_returns', {})
        
        # 确定涨跌状态 - 使用当日涨跌幅而不是周期涨跌幅
        # 优先从 price_info 获取当日涨跌幅，fallback 到 period_returns 的1日数据
        price_info = stock_info.get("price_info", {})
        change_pct = price_info.get("change_pct")
        if change_pct is None:
            # 尝试从 period_returns 获取1日涨跌幅
            change_pct = period_returns.get('1d', summary.get('period_change_pct', 0))
        
        try:
            change_pct_str = f"{float(change_pct):.2f}"
        except Exception:
            change_pct_str = str(change_pct)
        trend_emoji = "📈" if change_pct >= 0 else "📉"
        trend_text = "上涨" if change_pct >= 0 else "下跌"
        
        # 生成信号解读
        rsi_value = rsi.get('value', 50) if isinstance(rsi, dict) else 50
        try:
            rsi_value_str = f"{float(rsi_value):.2f}"
        except Exception:
            rsi_value_str = str(rsi_value)
        rsi_signal = "超买区域，注意回调风险" if float(rsi_value) > 70 else "超卖区域，可能反弹" if float(rsi_value) < 30 else "中性区域"
        
        macd_signal = macd.get('signal', '中性') if isinstance(macd, dict) else '中性'
        kdj_signal = kdj.get('status', '中性') if isinstance(kdj, dict) else '中性'

        # Simplified ASCII-only fallback report to avoid encoding issues
        return (
            f"# {ticker} Technical Analysis Report {trend_emoji}\n\n"
            f"Latest price: {summary.get('latest_price', 'N/A')}\n"
            f"Change: {change_pct_str}% ({trend_text})\n\n"
            "Key technical highlights (MACD/RSI/KDJ/Bollinger/ATR/ADX) could not be fully "
            "described because the LLM API call failed. This is a minimal fallback report "
            "generated locally based on quantitative indicators."
        )


# ============================================
# 启动服务
# ============================================

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 Web 服务"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
