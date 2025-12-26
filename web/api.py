"""
============================================
FastAPI 后端 API 服务
提供证券分析的 REST API 接口
============================================
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import re
import base64

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_llm_config, APIConfig, SystemConfig
from tools.data_fetcher import get_stock_data, get_stock_info, get_financial_data, search_ticker
from tools.technical_analysis import calculate_all_indicators, analyze_trend, get_support_resistance_levels
from web.auth import (
    RegisterRequest, LoginRequest, WatchlistItem, ReminderItem,
    get_user_by_username, get_user_by_phone, create_user, verify_password,
    create_session, get_current_user, delete_session,
    get_user_watchlist, add_to_watchlist, remove_from_watchlist, batch_add_to_watchlist,
    batch_remove_from_watchlist,
    save_user_report, get_user_reports, get_user_report, delete_user_report,
    create_analysis_task, update_analysis_task, get_user_analysis_tasks,
    get_user_reminders, add_reminder, update_reminder, delete_reminder,
    get_symbol_reminders, batch_add_reminders,
    get_all_users, update_user_status, update_user_role, is_admin, is_approved
)


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

def get_beijing_now() -> datetime:
    """获取当前北京时间 (UTC+8)，不依赖系统时区配置。"""
    return datetime.utcnow() + timedelta(hours=8)


# 存储分析任务状态
analysis_tasks: Dict[str, Dict[str, Any]] = {}

# 启动定时任务调度器
try:
    from web.scheduler import start_scheduler
    start_scheduler()
except Exception as e:
    print(f"启动调度器失败: {e}")

# 分析统计（用于热门标的）
ANALYSIS_STATS_PATH = Path(__file__).parent / "analysis_stats.json"
analysis_stats: Dict[str, Dict[str, Any]] = {}

if ANALYSIS_STATS_PATH.exists():
    try:
        analysis_stats = json.loads(ANALYSIS_STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        analysis_stats = {}


# ============================================
# FastAPI 应用
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio
    from web.database import migrate_database
    
    print("[START] Securities Analysis API starting...")
    
    # 执行数据库迁移
    migrate_database()
    
    # 启动价格触发检查后台任务
    task = asyncio.create_task(check_price_triggers())
    
    yield
    
    # 取消后台任务
    task.cancel()
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
            "timestamp": get_beijing_now().isoformat()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ============================================
# 用户认证 API
# ============================================

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        if get_user_by_username(request.username):
            raise HTTPException(status_code=400, detail="用户名已被注册")
        
        # 检查手机号是否已存在
        if get_user_by_phone(request.phone):
            raise HTTPException(status_code=400, detail="手机号已被注册")
        
        # 创建用户
        user = create_user(request.username, request.password, request.phone)
        
        return {
            "status": "success",
            "message": "注册成功",
            "user": user
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """用户登录 - 支持用户名或手机号登录"""
    try:
        # 先尝试用户名查找
        user = get_user_by_username(request.username)
        
        # 如果用户名找不到，尝试用手机号查找
        if not user:
            user = get_user_by_phone(request.username)
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        if not verify_password(request.password, user['password'], user['salt']):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建会话
        token = create_session(user['username'])
        
        return {
            "status": "success",
            "message": "登录成功",
            "token": token,
            "user": {
                "username": user['username'],
                "phone": user['phone'],
                "role": user.get('role', 'user'),
                "status": user.get('status', 'pending')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
async def get_me(authorization: str = Header(None)):
    """获取当前用户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    return {
        "status": "success",
        "user": user
    }


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    """退出登录"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        delete_session(token)
    
    return {"status": "success", "message": "已退出登录"}


# ============================================
# 管理员 API
# ============================================

@app.get("/api/admin/users")
async def admin_get_users(authorization: str = Header(None)):
    """获取所有用户（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    users = get_all_users()
    return {"status": "success", "users": users}


@app.get("/api/admin/pending-count")
async def admin_get_pending_count(authorization: str = Header(None)):
    """获取待审核用户数量（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        return {"status": "success", "count": 0}
    
    users = get_all_users()
    pending_count = len([u for u in users if u.get('status') == 'pending'])
    return {"status": "success", "count": pending_count}


@app.post("/api/admin/users/{username}/approve")
async def admin_approve_user(username: str, authorization: str = Header(None)):
    """审核通过用户（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    success = update_user_status(username, 'approved')
    if success:
        return {"status": "success", "message": f"用户 {username} 已审核通过"}
    else:
        raise HTTPException(status_code=404, detail="用户不存在")


@app.post("/api/admin/users/{username}/reject")
async def admin_reject_user(username: str, authorization: str = Header(None)):
    """拒绝用户（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    success = update_user_status(username, 'rejected')
    if success:
        return {"status": "success", "message": f"用户 {username} 已拒绝"}
    else:
        raise HTTPException(status_code=404, detail="用户不存在")


# ============================================
# 自选列表 API
# ============================================

@app.get("/api/watchlist")
async def get_watchlist(authorization: str = Header(None)):
    """获取自选列表"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    watchlist = get_user_watchlist(user['username'])
    
    return {
        "status": "success",
        "watchlist": watchlist
    }


@app.post("/api/watchlist")
async def add_watchlist_item(
    item: WatchlistItem,
    authorization: str = Header(None)
):
    """添加自选 - 自动识别股票名称和类型"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 自动获取股票名称和类型
    item_data = item.dict()
    symbol = item_data.get('symbol', '').upper()
    
    # 如果没有提供名称，自动获取
    if not item_data.get('name'):
        try:
            stock_info_result = await asyncio.to_thread(get_stock_info, symbol)
            info_dict = json.loads(stock_info_result)
            if info_dict.get('status') == 'success':
                basic_info = info_dict.get('basic_info', {})
                item_data['name'] = basic_info.get('name', '')
                # 自动识别类型
                quote_type = basic_info.get('quote_type', '').upper()
                if not item_data.get('type'):
                    if quote_type == 'ETF':
                        item_data['type'] = 'etf'
                    elif quote_type == 'MUTUALFUND':
                        item_data['type'] = 'fund'
                    else:
                        item_data['type'] = 'stock'
        except Exception as e:
            print(f"获取股票信息失败: {e}")
    
    success = add_to_watchlist(user['username'], item_data)
    
    if success:
        return {"status": "success", "message": "添加成功", "name": item_data.get('name', '')}
    else:
        return {"status": "error", "message": "该标的已在自选列表中"}


@app.delete("/api/watchlist/{symbol}")
async def delete_watchlist_item(
    symbol: str,
    authorization: str = Header(None)
):
    """删除自选"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    success = remove_from_watchlist(user['username'], symbol)
    
    if success:
        return {"status": "success", "message": "删除成功"}
    else:
        raise HTTPException(status_code=404, detail="未找到该标的")


@app.post("/api/watchlist/batch")
async def batch_add_watchlist_items(
    items: List[WatchlistItem],
    authorization: str = Header(None)
):
    """批量添加自选 - 自动识别股票名称和类型"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 处理每个标的，自动获取名称
    processed_items = []
    for item in items:
        item_data = item.dict()
        symbol = item_data.get('symbol', '').upper()
        
        # 如果没有提供名称，自动获取
        if not item_data.get('name'):
            try:
                stock_info_result = await asyncio.to_thread(get_stock_info, symbol)
                info_dict = json.loads(stock_info_result)
                if info_dict.get('status') == 'success':
                    basic_info = info_dict.get('basic_info', {})
                    item_data['name'] = basic_info.get('name', '')
                    # 自动识别类型
                    quote_type = basic_info.get('quote_type', '').upper()
                    if not item_data.get('type'):
                        if quote_type == 'ETF':
                            item_data['type'] = 'etf'
                        elif quote_type == 'MUTUALFUND':
                            item_data['type'] = 'fund'
                        else:
                            item_data['type'] = 'stock'
            except Exception as e:
                print(f"获取股票信息失败 [{symbol}]: {e}")
        
        processed_items.append(item_data)
    
    result = batch_add_to_watchlist(user['username'], processed_items)
    
    return {
        "status": "success",
        "added": result['added'],
        "skipped": result['skipped'],
        "message": f"成功添加 {len(result['added'])} 个，跳过 {len(result['skipped'])} 个已存在的标的"
    }


@app.put("/api/watchlist/{symbol}/star")
async def toggle_watchlist_star(
    symbol: str,
    authorization: str = Header(None)
):
    """切换自选的特别关注状态"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        # 获取当前状态
        cursor.execute(
            "SELECT starred FROM watchlist WHERE username = ? AND symbol = ?",
            (user['username'], symbol.upper())
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="未找到该标的")
        
        # 切换状态
        new_starred = 0 if row['starred'] else 1
        cursor.execute(
            "UPDATE watchlist SET starred = ? WHERE username = ? AND symbol = ?",
            (new_starred, user['username'], symbol.upper())
        )
        conn.commit()
    
    return {
        "status": "success",
        "symbol": symbol.upper(),
        "starred": bool(new_starred)
    }


# ============================================
# OCR 图片识别 API
# ============================================

@app.post("/api/ocr/recognize")
async def recognize_stocks_from_images(
    files: List[UploadFile] = File(...),
    authorization: str = Header(None)
):
    """从多张图片识别股票代码（最多10张）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 限制最多10张图片
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="最多只能上传10张图片")
    
    try:
        all_recognized = []
        
        # 并行处理所有图片
        async def process_image(file: UploadFile):
            content = await file.read()
            base64_image = base64.b64encode(content).decode('utf-8')
            return await recognize_stocks_with_ai(base64_image, file.content_type or "image/jpeg")
        
        # 并行执行所有图片识别
        tasks = [process_image(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果，去重
        seen_symbols = set()
        for result in results:
            if isinstance(result, list):
                for item in result:
                    symbol = item.get('symbol', '')
                    if symbol and symbol not in seen_symbols:
                        seen_symbols.add(symbol)
                        all_recognized.append(item)
        
        print(f"OCR 识别完成，共识别到 {len(all_recognized)} 个标的")
        
        return {
            "status": "success",
            "recognized": all_recognized,
            "image_count": len(files)
        }
    except Exception as e:
        print(f"OCR 识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")


async def recognize_stocks_with_ai(base64_image: str, content_type: str) -> List[Dict]:
    """使用 AI 识别图片中的股票代码"""
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
    
    prompt = """请仔细分析这张图片，识别出其中所有的股票、ETF、基金代码和名称。

请按以下JSON格式返回识别结果（只返回JSON，不要其他内容）：
```json
[
  {"symbol": "600519", "name": "贵州茅台", "type": "stock"},
  {"symbol": "159915", "name": "创业板ETF", "type": "etf"},
  {"symbol": "AAPL", "name": "苹果", "type": "stock"}
]
```

识别规则：
1. A股代码为6位数字（如600519、000001）
2. ETF代码为6位数字（如510300、159915）
3. 美股代码为英文字母（如AAPL、TSLA）
4. 基金代码为6位数字（如000001基金）
5. 如果无法确定名称，name可以为空字符串
6. type可以是：stock（股票）、etf、fund（基金）

如果图片中没有股票代码，返回空数组：[]"""

    try:
        # 尝试使用支持视觉的模型
        response = client.chat.completions.create(
            model="Qwen/Qwen2-VL-72B-Instruct",  # 使用支持视觉的模型
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1,
            timeout=120
        )
        
        result_text = response.choices[0].message.content
        
        # 提取 JSON
        json_match = re.search(r'\[[\s\S]*?\]', result_text)
        if json_match:
            recognized = json.loads(json_match.group())
            return recognized
        
        return []
        
    except Exception as e:
        print(f"AI 图片识别错误: {e}")
        # 如果视觉模型失败，返回空结果
        return []


# ============================================
# 自选批量删除 API
# ============================================

@app.post("/api/watchlist/batch-delete")
async def batch_delete_watchlist_items(
    symbols: List[str],
    authorization: str = Header(None)
):
    """批量删除自选"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    result = batch_remove_from_watchlist(user['username'], symbols)
    
    return {
        "status": "success",
        "removed": result['removed'],
        "not_found": result['not_found'],
        "message": f"成功删除 {len(result['removed'])} 个标的"
    }


# ============================================
# 分析报告 API
# ============================================

@app.get("/api/reports")
async def get_reports_list(authorization: str = Header(None)):
    """获取用户的分析报告列表"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    reports = get_user_reports(user['username'])
    
    # 简化报告数据，只返回摘要信息
    summary_reports = []
    for report in reports:
        data = report.get('data', {})
        summary_reports.append({
            'id': report.get('id'),
            'symbol': report.get('symbol'),
            'created_at': report.get('created_at'),
            'status': report.get('status'),
            'name': data.get('name', ''),
            'recommendation': data.get('recommendation', ''),
            'quant_score': data.get('quant_score'),
            'price': data.get('price'),
            'change_percent': data.get('change_percent')
        })
    
    return {
        "status": "success",
        "reports": summary_reports
    }


@app.get("/api/reports/{symbol}")
async def get_report_detail(symbol: str, authorization: str = Header(None)):
    """获取某个标的的详细报告"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    report = get_user_report(user['username'], symbol)
    
    if not report:
        raise HTTPException(status_code=404, detail="未找到该标的的报告")
    
    return {
        "status": "success",
        "report": report
    }


@app.delete("/api/reports/{symbol}")
async def delete_report(symbol: str, authorization: str = Header(None)):
    """删除某个标的的报告"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    success = delete_user_report(user['username'], symbol)
    
    if not success:
        raise HTTPException(status_code=404, detail="未找到该标的的报告")
    
    return {"status": "success", "message": "报告已删除"}


# ============================================
# 后台分析任务 API
# ============================================

@app.post("/api/analyze/background")
async def start_background_analysis(
    request: AnalysisRequest,
    authorization: str = Header(None)
):
    """启动后台分析任务（用户可关闭页面）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    task_id = str(uuid.uuid4())
    username = user['username']
    symbol = request.ticker.upper()
    
    # 创建任务记录
    create_analysis_task(username, symbol, task_id)
    
    # 使用线程启动后台任务，完全脱离当前请求
    import threading
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_background_analysis_full(username, symbol, task_id))
        loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    return {
        "status": "success",
        "task_id": task_id,
        "symbol": symbol,
        "message": "分析任务已启动，您可以关闭页面，稍后查看报告"
    }


@app.post("/api/analyze/batch")
async def start_batch_analysis(
    symbols: List[str],
    authorization: str = Header(None)
):
    """批量启动后台分析任务（真正并行执行）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    username = user['username']
    tasks = []
    
    for symbol in symbols:
        symbol = symbol.upper()
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        create_analysis_task(username, symbol, task_id)
        
        tasks.append({
            "task_id": task_id,
            "symbol": symbol
        })
    
    # 使用独立线程并行启动所有分析任务
    import threading
    
    def create_analysis_runner(uname: str, sym: str, tid: str):
        """创建分析任务运行器"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_background_analysis_full(uname, sym, tid))
            except Exception as e:
                print(f"分析任务异常 [{sym}]: {e}")
            finally:
                loop.close()
        return run
    
    # 先创建所有线程
    threads = []
    for task_info in tasks:
        runner = create_analysis_runner(username, task_info["symbol"], task_info["task_id"])
        t = threading.Thread(target=runner, daemon=True)
        threads.append(t)
    
    # 同时启动所有线程
    for t in threads:
        t.start()
    
    print(f"已并行启动 {len(threads)} 个分析任务")
    
    return {
        "status": "success",
        "tasks": tasks,
        "message": f"已启动 {len(tasks)} 个分析任务并行执行，您可以关闭页面，稍后查看报告"
    }


@app.get("/api/analyze/tasks")
async def get_analysis_tasks_status(authorization: str = Header(None)):
    """获取用户的分析任务状态"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    tasks = get_user_analysis_tasks(user['username'])
    
    return {
        "status": "success",
        "tasks": tasks
    }


async def run_background_analysis_full(username: str, ticker: str, task_id: str):
    """
    后台执行完整的多 Agent 分析（复用原有分析逻辑）
    """
    try:
        # 检查是否是场外基金（不支持技术分析）
        pure_code = ticker.replace('.SZ', '').replace('.SS', '').replace('.SH', '')
        if pure_code.isdigit() and len(pure_code) == 6:
            # 场外基金代码通常以 0、1、2、3、4、5、6、7、8、9 开头
            # ETF代码：51xxxx(上证), 15xxxx/16xxxx(深证)
            # 场外基金：00xxxx, 01xxxx, 02xxxx 等
            if pure_code.startswith(('00', '01', '02', '03', '04', '05', '06', '07', '08', '09')) and \
               not pure_code.startswith(('000', '001', '002', '003')):  # 排除A股
                # 可能是场外基金
                if not pure_code.startswith(('51', '15', '16', '58', '56')):  # 排除ETF
                    raise Exception(f"{ticker} 是场外基金，暂不支持技术分析。请添加对应的ETF代码进行分析。")
        
        # === 第一阶段：数据获取 ===
        update_analysis_task(username, ticker, {
            'status': 'running',
            'progress': 5,
            'current_step': 'AI Agents正在集结'
        })
        await asyncio.sleep(0.2)
        
        # 自动识别并标准化 ticker
        update_analysis_task(username, ticker, {
            'progress': 10,
            'current_step': '正在获取实时行情数据'
        })
        
        search_result = await asyncio.to_thread(search_ticker, ticker)
        search_dict = json.loads(search_result)
        
        if search_dict.get("status") == "success":
            ticker = search_dict.get("ticker", ticker)
        
        stock_data = await asyncio.to_thread(get_stock_data, ticker, "2y", "1d")
        stock_data_dict = json.loads(stock_data)
        
        if stock_data_dict.get("status") != "success":
            raise Exception(f"无法获取 {ticker} 的行情数据")
        
        # 基本面分析
        update_analysis_task(username, ticker, {
            'progress': 25,
            'current_step': '基本面分析师正在评估价值'
        })
        
        stock_info = await asyncio.to_thread(get_stock_info, ticker)
        stock_info_dict = json.loads(stock_info)
        
        # === 第二阶段：量化分析 ===
        update_analysis_task(username, ticker, {
            'progress': 35,
            'current_step': '技术面分析师正在计算指标'
        })
        
        indicators = await asyncio.to_thread(calculate_all_indicators, stock_data)
        indicators_dict = json.loads(indicators)
        
        if indicators_dict.get("status") == "error" or not indicators_dict.get("indicators"):
            raise Exception(f"无法计算 {ticker} 的技术指标")
        
        update_analysis_task(username, ticker, {
            'progress': 45,
            'current_step': '量化引擎正在生成信号'
        })
        
        trend = await asyncio.to_thread(analyze_trend, indicators)
        trend_dict = json.loads(trend)
        
        if trend_dict.get("status") == "error":
            raise Exception(f"无法分析 {ticker} 的趋势")
        
        update_analysis_task(username, ticker, {
            'progress': 55,
            'current_step': '数据审计员正在验证来源'
        })
        
        levels = await asyncio.to_thread(get_support_resistance_levels, stock_data)
        levels_dict = json.loads(levels)
        
        # === 第三阶段：AI分析 ===
        update_analysis_task(username, ticker, {
            'progress': 65,
            'current_step': '风险管理专家正在评估风险'
        })
        await asyncio.sleep(0.3)
        
        update_analysis_task(username, ticker, {
            'progress': 75,
            'current_step': '首席投资官正在生成报告'
        })
        
        # 调用 AI 生成报告和预测（与原分析相同）
        report, predictions = await generate_ai_report_with_predictions(
            ticker, 
            stock_data_dict, 
            stock_info_dict, 
            indicators_dict, 
            trend_dict, 
            levels_dict
        )
        
        # 提取量化分析数据
        quant_analysis = trend_dict.get("quant_analysis", {})
        trend_analysis = trend_dict.get("trend_analysis", trend_dict)
        signal_details = trend_dict.get("signal_details", [])
        
        quant_score = quant_analysis.get("score")
        market_regime = quant_analysis.get("market_regime", "unknown")
        volatility_state = quant_analysis.get("volatility_state", "medium")
        quant_reco = quant_analysis.get("recommendation", "hold")
        
        # 技术指标摘要
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
        
        # 映射表
        reco_map = {"strong_buy": "强力买入", "buy": "建议买入", "hold": "持有观望", "sell": "建议减持", "strong_sell": "强力卖出"}
        regime_map = {"trending": "趋势市", "ranging": "震荡市", "squeeze": "窄幅整理", "unknown": "待判定"}
        vol_map = {"high": "高波动", "medium": "中等波动", "low": "低波动"}
        
        score_text = f"{quant_score:.1f}" if isinstance(quant_score, (int, float)) else "N/A"
        regime_cn = regime_map.get(market_regime, "待判定")
        vol_cn = vol_map.get(volatility_state, "波动适中")
        reco_cn = reco_map.get(quant_reco, "观望")
        
        bullish_signals = trend_analysis.get("bullish_signals", 0) if isinstance(trend_analysis, dict) else 0
        bearish_signals = trend_analysis.get("bearish_signals", 0) if isinstance(trend_analysis, dict) else 0
        
        ai_summary = f"量化评分 {score_text} 分，当前处于{regime_cn}，{vol_cn}环境。多头信号 {bullish_signals} 个、空头信号 {bearish_signals} 个，综合建议：{reco_cn}。"
        
        update_analysis_task(username, ticker, {
            'progress': 90,
            'current_step': '质量控制专员正在审核'
        })
        
        # 规范化报告时间戳
        completed_at = get_beijing_now()
        report = normalize_report_timestamp(report, completed_at)
        
        # 构建完整报告数据（与原分析格式一致）
        report_data = {
            'status': 'completed',
            'ticker': ticker,
            'report': report,
            'predictions': predictions,
            'quant_analysis': quant_analysis,
            'trend_analysis': trend_analysis,
            'ai_summary': ai_summary,
            'indicator_overview': indicator_overview,
            'signal_details': signal_details,
            'stock_info': stock_info_dict,
            'indicators': indicators_dict,
            'levels': levels_dict
        }
        
        # 保存报告到数据库
        save_user_report(username, ticker, report_data)
        
        # 更新任务状态为完成
        update_analysis_task(username, ticker, {
            'status': 'completed',
            'progress': 100,
            'current_step': '分析完成',
            'result': json.dumps(report_data, ensure_ascii=False)
        })
        
    except Exception as e:
        print(f"后台分析失败 [{ticker}]: {e}")
        update_analysis_task(username, ticker, {
            'status': 'failed',
            'current_step': '分析失败',
            'error': str(e)
        })


async def generate_ai_report_for_background(symbol: str, info: Dict, indicators: Dict, trend: Dict) -> Dict:
    """为后台任务生成AI报告"""
    from openai import OpenAI
    import httpx
    import os
    
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    api_key = APIConfig.SILICONFLOW_API_KEY
    
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
    
    # 构建分析提示词
    basic_info = info.get('basic_info', {})
    price_info = info.get('price_info', {})
    
    prompt = f"""请对以下证券进行专业分析：

## 基本信息
- 代码: {symbol}
- 名称: {basic_info.get('name', 'N/A')}
- 当前价格: {price_info.get('current_price', 'N/A')}
- 涨跌幅: {price_info.get('change_pct', 0):.2f}%

## 技术指标
{json.dumps(indicators, ensure_ascii=False, indent=2)}

## 趋势分析
{json.dumps(trend, ensure_ascii=False, indent=2)}

请提供：
1. 市场概况分析（100字以内）
2. 技术面分析（200字以内）
3. 操作建议
4. 风险提示

请用专业但易懂的语言输出分析报告。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": "你是一位专业的证券分析师，擅长技术分析和基本面分析。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        report_text = response.choices[0].message.content
        
        # 生成简要摘要
        summary = report_text[:200] + "..." if len(report_text) > 200 else report_text
        
        return {
            'report': report_text,
            'summary': summary,
            'predictions': []
        }
        
    except Exception as e:
        print(f"AI 报告生成错误: {e}")
        return {
            'report': f'AI 报告生成失败: {str(e)}',
            'summary': '报告生成失败',
            'predictions': []
        }


@app.get("/api/search/{query}")
async def search_stock(query: str):
    """搜索股票代码"""
    try:
        result = search_ticker(query)
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/popular_tickers")
async def get_popular_tickers(limit: int = 5):
    """获取最常分析的标的列表"""
    try:
        items = [
            {
                "symbol": symbol,
                "count": int(data.get("count", 0)),
                "last_time": data.get("last_time"),
            }
            for symbol, data in analysis_stats.items()
        ]
        # 按分析次数倒序，其次按最后时间倒序
        items.sort(key=lambda x: (-x["count"], x["last_time"] or ""), reverse=False)
        max_limit = max(1, min(limit, 20))
        return {"status": "success", "items": items[:max_limit]}
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
        "created_at": get_beijing_now().isoformat()
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
        
        regime_cn = regime_map.get(market_regime, "待判定")
        vol_cn = vol_map.get(volatility_state, "波动适中")
        reco_cn = reco_map.get(quant_reco, "观望")
        bullish_signals = trend_analysis.get("bullish_signals", 0) if isinstance(trend_analysis, dict) else 0
        bearish_signals = trend_analysis.get("bearish_signals", 0) if isinstance(trend_analysis, dict) else 0
        
        ai_summary = (
            f"量化评分 {score_text} 分，当前处于{regime_cn}，{vol_cn}环境。"
            f"多头信号 {bullish_signals} 个、空头信号 {bearish_signals} 个，综合建议：{reco_cn}。"
        )
        
        short_term_view = ""
        mid_term_view = ""
        long_term_view = ""
        if isinstance(trend_analysis, dict):
            short_term_view = trend_analysis.get("short_term_view", "") or ""
            mid_term_view = trend_analysis.get("mid_term_view", "") or ""
            long_term_view = trend_analysis.get("long_term_view", "") or ""
        
        if not short_term_view:
            short_term_view = "短线关注近支撑位与阻力位附近的价格反应，严格设置止损。"
        if not mid_term_view:
            mid_term_view = "中线可结合趋势强度选择顺势持有或区间交易，避免在剧烈波动时重仓追涨杀跌。"
        if not long_term_view:
            long_term_view = "长期则根据指数和基本面判断整体配置价值，分批建仓或减仓，控制好最大回撤。"
        
        ai_summary += f"短线：{short_term_view} 中线：{mid_term_view} 长线：{long_term_view}"

        # 使用任务真正完成的北京时间统一规范报告中的“报告生成时间”字段
        completed_at = get_beijing_now()
        report = normalize_report_timestamp(report, completed_at)

        task["progress"] = 100
        task["current_step"] = "分析完成"
        task["status"] = "completed"
        task["result"] = json.dumps({
            "ticker": ticker,  # 标准化后的 ticker
            "report": report,
            "predictions": predictions,
            "quant_analysis": quant_analysis,
            "trend_analysis": trend_analysis,
            "ai_summary": ai_summary,
            "indicator_overview": indicator_overview,
            "signal_details": signal_details,
        }, ensure_ascii=False)

        # 记录成功分析次数，用于热门标的统计
        try:
            stat = analysis_stats.get(ticker, {}) or {}
            count = int(stat.get("count", 0)) + 1
            analysis_stats[ticker] = {
                "count": count,
                "last_time": get_beijing_now().isoformat(),
            }
            ANALYSIS_STATS_PATH.write_text(
                json.dumps(analysis_stats, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            # 统计失败不影响主流程
            pass
        
    except Exception as e:
        msg = str(e)
        if "timed out" in msg.lower():
            msg = "LLM 请求超时（SiliconFlow DeepSeek 接口在 180 秒内未响应），请稍后重试。"
        task["status"] = "failed"
        task["error"] = msg
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
        timeout=httpx.Timeout(300.0, connect=60.0)
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

    async def call_predictions() -> list:
        """调用 DeepSeek 生成多周期预测，如失败则使用本地量化规则回退。"""
        predictions_local: list = []
        try:
            # Agent 1 调用
            pred_response = client.chat.completions.create(
                model=APIConfig.SILICONFLOW_MODEL,
                messages=[
                    {"role": "system", "content": "你是量化分析师，只输出JSON格式的预测数据，不要输出其他内容。"},
                    {"role": "user", "content": prediction_prompt}
                ],
                max_tokens=1000,
                temperature=0.2,
                timeout=180
            )
            
            pred_text = pred_response.choices[0].message.content
            # 提取 JSON
            json_match = re.search(r'\[[\s\S]*\]', pred_text)
            if json_match:
                predictions_local = json.loads(json_match.group())
        except Exception as e:
            print(f"Agent 1 预测失败: {e}")
            # 使用基于规则的预测作为备用
            predictions_local = generate_predictions(indicators, trend, levels, stock_data)
        
        return predictions_local
    
    # 并行运行预测和报告生成，以减少整体等待时间
    predictions_task = asyncio.create_task(call_predictions())
    report_task = asyncio.create_task(
        generate_ai_report(ticker, stock_data, stock_info, indicators, trend, levels)
    )
    
    predictions = await predictions_task
    report = await report_task
    
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
        timeout=httpx.Timeout(300.0, connect=60.0)
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

    symbol = (
        info.get("symbol")
        or info.get("code")
        or ticker.replace(".SH", "").replace(".SZ", "").replace(".sh", "").replace(".sz", "")
    )
    display_name = info.get("name", ticker)
    current_price = price_info.get("current_price") or summary.get("latest_price", "N/A")
    day_change_pct = price_info.get("change_pct")
    if isinstance(day_change_pct, (int, float)):
        day_change_str = f"{day_change_pct:+.2f}"
    else:
        day_change_str = str(summary.get("period_change_pct", "N/A"))
    market_cap_display = valuation.get("market_cap_str")
    if not market_cap_display:
        market_cap_value = valuation.get("market_cap")
        if isinstance(market_cap_value, (int, float)) and market_cap_value > 0:
            if market_cap_value >= 1e12:
                market_cap_display = f"¥{market_cap_value/1e12:.2f}万亿"
            elif market_cap_value >= 1e8:
                market_cap_display = f"¥{market_cap_value/1e8:.2f}亿"
            elif market_cap_value >= 1e4:
                market_cap_display = f"¥{market_cap_value/1e4:.2f}万"
            else:
                market_cap_display = f"¥{market_cap_value:.0f}"
        else:
            market_cap_display = "未披露"
    
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
    
    # 获取当前北京时间
    current_datetime = get_beijing_now()
    report_date = current_datetime.strftime("%Y年%m月%d日")
    report_time = current_datetime.strftime("%H:%M:%S")
    
    prompt = f"""
**重要提示**: 当前日期是 {report_date}，当前时间是 {report_time}。请在报告中使用此日期作为报告生成时间，不要使用其他日期。

请根据以下数据生成专业详细的证券/基金分析报告：

## 标的信息
- 代码: {symbol}
- 名称: {display_name}
- 当前价格/净值: {current_price}
- 日涨跌幅: {day_change_str}%
- 52周最高: {price_info.get('52_week_high', 'N/A')}
- 52周最低: {price_info.get('52_week_low', 'N/A')}

## 估值/规模指标
- 市盈率 (P/E): {valuation.get('pe_ratio', 'N/A')}
- 市净率 (P/B): {valuation.get('price_to_book', 'N/A')}
- 市值/规模: {market_cap_display}

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
            model=APIConfig.SILICONFLOW_MODEL,
            messages=[
                {"role": "system", "content": "你是一位资深的证券分析师，擅长技术分析和基本面分析。请生成专业、客观的投资分析报告。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.3,
            timeout=180
        )
        report_text = response.choices[0].message.content

        # 规范化报告日期和时间为当前北京时间
        current_datetime = get_beijing_now()
        current_date_str = current_datetime.strftime("%Y年%m月%d日")
        current_time_str = current_datetime.strftime("%H:%M:%S")
        
        # 替换所有可能的旧日期
        report_text = re.sub(
            r"(报告生成时间[:：]\s*)[^\n]*",
            rf"\1{current_date_str} {current_time_str}",
            report_text,
        )
        report_text = re.sub(
            r"(报告日期[:：]\s*)[^\n]*",
            rf"\1{current_date_str} {current_time_str}",
            report_text,
        )
        report_text = re.sub(
            r"\d{4}年\d{1,2}月\d{1,2}日",
            current_date_str,
            report_text,
            count=5  # 最多替换前5个旧日期
        )

        try:
            if symbol:
                report_text = re.sub(
                    r"\|\s*代码\s*\|[^\n]*\n",
                    f"| 代码 | {symbol} |\n",
                    report_text,
                )
            if display_name:
                report_text = re.sub(
                    r"\|\s*名称\s*\|[^\n]*\n",
                    f"| 名称 | {display_name} |\n",
                    report_text,
                )
            if isinstance(current_price, (int, float)) and current_price > 0:
                price_str = f"{current_price:.4f}".rstrip("0").rstrip(".")
                report_text = re.sub(
                    r"\|\s*当前价格[^|]*\|[^\n]*\n",
                    f"| 当前价格 | {price_str} |\n",
                    report_text,
                )
                report_text = re.sub(
                    r"\|\s*当前价格/净值[^|]*\|[^\n]*\n",
                    f"| 当前价格/净值 | {price_str} |\n",
                    report_text,
                )
            if day_change_str not in ("N/A", "", None):
                change_value = day_change_str
                report_text = re.sub(
                    r"\|\s*日?涨跌幅\s*\|[^\n]*\n",
                    f"| 日涨跌幅 | {change_value}% |\n",
                    report_text,
                )
            if market_cap_display:
                report_text = re.sub(
                    r"\|\s*市值规模\s*\|[^\n]*\n",
                    f"| 市值规模 | {market_cap_display} |\n",
                    report_text,
                )
        except Exception:
            pass
        
        # 根据多周期收益率数据，强制规范“多周期表现/区间涨跌”小节为标准表格
        report_text = normalize_multi_period_section(report_text, period_returns)

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
        # LLM 连接失败时仅记录错误并向上抛出，让上层标记任务失败
        print(f"LLM API Error: {e}")
        raise


def normalize_report_timestamp(report_text: str, completed_at: datetime) -> str:
    """统一规范报告中的报告生成时间，使其与任务真正完成时间保持一致。

    - 将所有出现的“报告生成时间:”或“报告日期:”行替换为 completed_at
    - 尝试替换前几处孤立日期字符串为 completed_at 的日期
    - 若已存在脚注形式的“报告生成时间”则更新为 completed_at
    """
    try:
        import re

        date_str = completed_at.strftime("%Y年%m月%d日")
        time_str = completed_at.strftime("%H:%M:%S")

        # 替换“报告生成时间:”或“报告日期:”行
        def _replace_line(match: "re.Match[str]") -> str:
            prefix = match.group(1)
            return f"{prefix}{date_str} {time_str}"

        report_text = re.sub(r"(报告生成时间[:：]\s*)[^\n]*", _replace_line, report_text)
        report_text = re.sub(r"(报告日期[:：]\s*)[^\n]*", _replace_line, report_text)

        # 替换孤立日期（最多前 5 个），包括可能缺少世纪或带前缀的格式
        report_text = re.sub(
            r"\d{4}年\d{1,2}月\d{1,2}日",
            date_str,
            report_text,
            count=5,
        )
        # 处理类似 "25年12月18日" 或 "P25年12月18日" 这种不规范年份
        report_text = re.sub(
            r"P?\d{1,2}年\d{1,2}月\d{1,2}日",
            date_str,
            report_text,
        )

        # 处理形如 "**P25年12月18日 02:40:45" 的整行时间，统一替换为当前任务完成时间
        report_text = re.sub(
            r"\*\*P?\d{1,4}年\d{1,2}月\d{1,2}日\s+\d{2}:\d{2}:\d{2}",
            f"**{date_str} {time_str}",
            report_text,
        )

        # 规范脚注形式的“报告生成时间”
        def _replace_footer(match: "re.Match[str]") -> str:
            prefix = match.group(1)
            return f"{prefix}{date_str} {time_str}"

        report_text = re.sub(
            r"(\*\*报告生成时间\*\*[:：]?\s*)[^\n]*",
            _replace_footer,
            report_text,
        )

        # 如果完全没有“报告生成时间”相关字段，则追加标准脚注
        if "报告生成时间" not in report_text and "报告日期" not in report_text:
            footer = (
                f"\n\n---\n\n"
                f"**报告生成时间**: {date_str} {time_str} | **数据来源**: 量化系统 + AI多智能体分析\n\n"
                f"*本报告由量化引擎(基于vnpy架构)与AI Agent深度联动生成，整合了硬数据分析与软判断评估。*"
            )
            report_text += footer

        return report_text
    except Exception:
        # 任何异常都不影响主流程，直接返回原始报告
        return report_text


def normalize_multi_period_section(report_text: str, period_returns: dict) -> str:
    """根据 period_returns 重写报告中的“多周期表现/区间涨跌”小节。

    - 避免 LLM 生成一整行 "| 周期 | 日涨跌幅 ..." 的异常表格
    - 使用后端的真实收益率数据构建标准 Markdown 表格
    """
    try:
        import re

        if not period_returns:
            return report_text

        def _fmt(key: str) -> str:
            v = period_returns.get(key)
            if isinstance(v, (int, float)):
                return f"{v:+.2f}%"
            if isinstance(v, str) and v.strip():
                # 如果已经带 % 就直接用
                return v
            return "N/A"

        table_lines = [
            "### 多周期表现",
            "",
            "12. **区间涨跌**:",
            "",
            "| 周期 | 涨跌幅 |",
            "|------|--------|",
            f"| 5日 | {_fmt('5日')} |",
            f"| 10日 | {_fmt('10日')} |",
            f"| 20日 | {_fmt('20日')} |",
            f"| 60日 | {_fmt('60日')} |",
            f"| 120日 | {_fmt('120日')} |",
            f"| 250日 | {_fmt('250日')} |",
            "",
        ]
        new_block = "\n".join(table_lines)

        # 用正则找到原有 “### 多周期表现” 小节并整体替换
        pattern = r"### 多周期表现[\s\S]*?(?=\n## |\Z)"
        if re.search(pattern, report_text):
            report_text = re.sub(pattern, new_block, report_text)
        else:
            # 如果原文没有该小节，则在报告后面追加
            report_text = report_text.rstrip() + "\n\n" + new_block

        return report_text
    except Exception:
        return report_text


# ============================================
# 定时提醒 API
# ============================================

@app.get("/api/reminders")
async def get_reminders_list(authorization: str = Header(None)):
    """获取用户的所有定时提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    reminders = get_user_reminders(user['username'])
    # 转换 reminder_id 为 id 以匹配前端接口
    for r in reminders:
        if 'reminder_id' in r:
            r['id'] = r['reminder_id']
    return {"status": "success", "reminders": reminders}


@app.get("/api/reminders/symbol/{symbol}")
async def get_symbol_reminders_list(symbol: str, authorization: str = Header(None)):
    """获取某个证券的定时提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    reminders = get_symbol_reminders(user['username'], symbol)
    # 转换 reminder_id 为 id 以匹配前端接口
    for r in reminders:
        if 'reminder_id' in r:
            r['id'] = r['reminder_id']
    return {"status": "success", "reminders": reminders}


@app.post("/api/reminders")
async def create_reminder(
    reminder: ReminderItem,
    authorization: str = Header(None)
):
    """创建价格触发提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 检查是否有对应的AI报告，从报告中获取买入卖出价
    report = get_user_report(user['username'], reminder.symbol)
    has_report = report is not None
    
    buy_price = reminder.buy_price
    sell_price = reminder.sell_price
    
    # 如果没有指定价格，尝试从报告中获取
    if report and report.get('data') and (buy_price is None or sell_price is None):
        report_data = report['data']
        if isinstance(report_data, dict):
            if buy_price is None and 'buy_price' in report_data:
                buy_price = report_data.get('buy_price')
            if sell_price is None and 'sell_price' in report_data:
                sell_price = report_data.get('sell_price')
            if 'recommendation' in report_data:
                rec = report_data['recommendation']
                if isinstance(rec, dict):
                    buy_price = buy_price or rec.get('buy_price')
                    sell_price = sell_price or rec.get('sell_price')
    
    reminder_dict = reminder.dict()
    reminder_dict['buy_price'] = buy_price
    reminder_dict['sell_price'] = sell_price
    
    result = add_reminder(user['username'], reminder_dict)
    
    return {
        "status": "success",
        "reminder": result,
        "has_report": has_report,
        "message": "提醒创建成功" if has_report else "提醒创建成功，但该证券尚无AI分析报告，无法获取买卖价格"
    }


@app.post("/api/reminders/batch")
async def batch_create_reminders(
    symbols: List[str],
    reminder_type: str,
    frequency: str = "trading_day",
    analysis_time: str = "09:30",
    weekday: Optional[int] = None,
    day_of_month: Optional[int] = None,
    authorization: str = Header(None)
):
    """批量创建价格触发提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 为每个标的获取AI分析报告中的买入卖出价
    results = []
    symbols_without_report = []
    
    for symbol in symbols:
        report = get_user_report(user['username'], symbol)
        if report and report.get('data'):
            report_data = report['data']
            # 从报告中提取买入卖出价
            buy_price = None
            sell_price = None
            
            if isinstance(report_data, dict):
                # 尝试从不同位置获取价格
                if 'buy_price' in report_data:
                    buy_price = report_data.get('buy_price')
                if 'sell_price' in report_data:
                    sell_price = report_data.get('sell_price')
                # 也可能在 recommendation 中
                if 'recommendation' in report_data:
                    rec = report_data['recommendation']
                    if isinstance(rec, dict):
                        buy_price = buy_price or rec.get('buy_price')
                        sell_price = sell_price or rec.get('sell_price')
            
            reminder_config = {
                'symbol': symbol,
                'name': report.get('name', symbol),
                'reminder_type': reminder_type,
                'frequency': frequency,
                'analysis_time': analysis_time,
                'weekday': weekday,
                'day_of_month': day_of_month,
                'buy_price': buy_price,
                'sell_price': sell_price
            }
            result = add_reminder(user['username'], reminder_config)
            results.append(result)
        else:
            symbols_without_report.append(symbol)
    
    return {
        "status": "success",
        "result": {'added': results, 'count': len(results)},
        "symbols_without_report": symbols_without_report
    }


@app.put("/api/reminders/{reminder_id}")
async def update_reminder_item(
    reminder_id: str,
    updates: dict,
    authorization: str = Header(None)
):
    """更新定时提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    success = update_reminder(user['username'], reminder_id, updates)
    
    if success:
        return {"status": "success", "message": "更新成功"}
    else:
        raise HTTPException(status_code=404, detail="未找到该提醒")


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder_item(
    reminder_id: str,
    authorization: str = Header(None)
):
    """删除定时提醒"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    success = delete_reminder(user['username'], reminder_id)
    
    if success:
        return {"status": "success", "message": "删除成功"}
    else:
        raise HTTPException(status_code=404, detail="未找到该提醒")


# ============================================
# 实时行情 API
# ============================================

@app.get("/api/quotes")
async def get_quotes(symbols: str, authorization: str = Header(None)):
    """获取实时行情数据
    symbols: 逗号分隔的标的代码列表
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    
    # 批量获取实时行情数据
    quotes = get_batch_quotes(symbol_list)
    
    return {"status": "success", "quotes": quotes}


# 缓存行情数据，避免频繁请求
_quote_cache = {
    'etf': {'data': None, 'time': None},
    'lof': {'data': None, 'time': None},
    'stock': {'data': None, 'time': None}
}
_cache_ttl = 10  # 交易时间缓存10秒
_cache_ttl_non_trading = 300  # 非交易时间缓存5分钟


def get_batch_quotes(symbols: list) -> dict:
    """批量获取行情数据，使用缓存优化"""
    import akshare as ak
    import math
    from datetime import datetime, timedelta
    
    def safe_float(val, default=0.0):
        """安全转换为float，处理NaN和Infinity"""
        try:
            if val is None:
                return default
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default
    
    now = datetime.now()
    quotes = {}
    
    # 根据是否交易时间调整缓存时间
    cache_ttl = _cache_ttl if is_trading_time() else _cache_ttl_non_trading
    
    # 提取纯数字代码
    code_map = {}
    for symbol in symbols:
        code = symbol[2:] if symbol.startswith(("sz", "sh")) else symbol
        code_map[code] = symbol
    
    codes = set(code_map.keys())
    print(f"[Quotes] 请求代码: {codes}, 交易时间: {is_trading_time()}, 缓存TTL: {cache_ttl}s")
    
    # 获取 ETF 数据（使用缓存）
    try:
        if _quote_cache['etf']['data'] is None or \
           _quote_cache['etf']['time'] is None or \
           (now - _quote_cache['etf']['time']).seconds > cache_ttl:
            print("[Quotes] 正在获取 ETF 数据...")
            _quote_cache['etf']['data'] = ak.fund_etf_spot_em()
            _quote_cache['etf']['time'] = now
            print(f"[Quotes] ETF 数据获取成功，共 {len(_quote_cache['etf']['data'])} 条")
        
        df_etf = _quote_cache['etf']['data']
        matched = df_etf[df_etf['代码'].isin(codes)]
        print(f"[Quotes] ETF 匹配到 {len(matched)} 条")
        for _, row in matched.iterrows():
            code = row['代码']
            symbol = code_map.get(code, code)
            quotes[symbol] = {
                'symbol': symbol,
                'current_price': safe_float(row['最新价']),
                'change_percent': safe_float(row['涨跌幅'])
            }
            codes.discard(code)
    except Exception as e:
        print(f"ETF批量行情获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 获取 LOF 数据
    if codes:
        try:
            if _quote_cache['lof']['data'] is None or \
               _quote_cache['lof']['time'] is None or \
               (now - _quote_cache['lof']['time']).seconds > cache_ttl:
                _quote_cache['lof']['data'] = ak.fund_lof_spot_em()
                _quote_cache['lof']['time'] = now
            
            df_lof = _quote_cache['lof']['data']
            for _, row in df_lof[df_lof['代码'].isin(codes)].iterrows():
                code = row['代码']
                symbol = code_map.get(code, code)
                quotes[symbol] = {
                    'symbol': symbol,
                    'current_price': safe_float(row['最新价']),
                    'change_percent': safe_float(row['涨跌幅'])
                }
                codes.discard(code)
        except Exception as e:
            print(f"LOF批量行情获取失败: {e}")
    
    # 获取 A股 数据
    if codes:
        try:
            if _quote_cache['stock']['data'] is None or \
               _quote_cache['stock']['time'] is None or \
               (now - _quote_cache['stock']['time']).seconds > cache_ttl:
                _quote_cache['stock']['data'] = ak.stock_zh_a_spot_em()
                _quote_cache['stock']['time'] = now
            
            df_stock = _quote_cache['stock']['data']
            for _, row in df_stock[df_stock['代码'].isin(codes)].iterrows():
                code = row['代码']
                symbol = code_map.get(code, code)
                quotes[symbol] = {
                    'symbol': symbol,
                    'current_price': safe_float(row['最新价']),
                    'change_percent': safe_float(row['涨跌幅'])
                }
                codes.discard(code)
        except Exception as e:
            print(f"A股批量行情获取失败: {e}")
    
    # 获取场外基金净值数据
    if codes:
        remaining_codes = list(codes)
        for code in remaining_codes:
            # 判断是否为场外基金（6位数字，非ETF/LOF/A股）
            if code.isdigit() and len(code) == 6:
                # 排除场内代码
                if code.startswith(('159', '16', '51', '56', '58', '52', '6', '0', '3')):
                    continue
                try:
                    # 使用天天基金接口获取实时估值
                    import requests
                    import re
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "http://fund.eastmoney.com/"
                    }
                    info_url = f"http://fundgz.1234567.com.cn/js/{code}.js"
                    response = requests.get(info_url, headers=headers, timeout=5)
                    
                    if response.status_code == 200 and "jsonpgz" in response.text:
                        json_str = re.search(r'jsonpgz\((.*)\)', response.text)
                        if json_str:
                            import json
                            fund_info = json.loads(json_str.group(1))
                            symbol = code_map.get(code, code)
                            # gsz: 估算净值, gszzl: 估算涨跌幅
                            quotes[symbol] = {
                                'symbol': symbol,
                                'current_price': safe_float(fund_info.get('gsz', fund_info.get('dwjz', 0))),
                                'change_percent': safe_float(fund_info.get('gszzl', 0))
                            }
                            codes.discard(code)
                except Exception as e:
                    print(f"场外基金 {code} 净值获取失败: {e}")
    
    print(f"[Quotes] 返回 {len(quotes)} 条行情数据")
    return quotes


def get_realtime_quote(symbol: str) -> dict:
    """获取单个标的的实时行情
    使用 akshare 或其他数据源获取
    """
    try:
        import akshare as ak
        
        # 提取纯数字代码
        code = symbol
        if symbol.startswith("sz") or symbol.startswith("sh"):
            code = symbol[2:]
        
        # 先尝试从 ETF 获取
        try:
            df_etf = ak.fund_etf_spot_em()
            row = df_etf[df_etf['代码'] == code]
            if not row.empty:
                return {
                    'symbol': symbol,
                    'current_price': float(row.iloc[0]['最新价']),
                    'change_percent': float(row.iloc[0]['涨跌幅'])
                }
        except Exception as e:
            print(f"ETF行情获取失败: {e}")
        
        # 尝试从 LOF 基金获取
        try:
            df_lof = ak.fund_lof_spot_em()
            row = df_lof[df_lof['代码'] == code]
            if not row.empty:
                return {
                    'symbol': symbol,
                    'current_price': float(row.iloc[0]['最新价']),
                    'change_percent': float(row.iloc[0]['涨跌幅'])
                }
        except Exception as e:
            print(f"LOF行情获取失败: {e}")
        
        # 尝试从 A股 获取
        try:
            df_stock = ak.stock_zh_a_spot_em()
            row = df_stock[df_stock['代码'] == code]
            if not row.empty:
                return {
                    'symbol': symbol,
                    'current_price': float(row.iloc[0]['最新价']),
                    'change_percent': float(row.iloc[0]['涨跌幅'])
                }
        except Exception as e:
            print(f"A股行情获取失败: {e}")
        
    except Exception as e:
        print(f"获取行情出错: {e}")
    
    return None


# ============================================
# 后台任务：自动AI分析 + 价格触发检查
# ============================================

def is_trading_day() -> bool:
    """检查今天是否是交易日（简单判断：周一到周五）"""
    return datetime.now().weekday() < 5


def is_trading_time() -> bool:
    """检查当前是否在交易时间内（A股：9:30-11:30, 13:00-15:00）"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周末
        return False
    current_time = now.strftime("%H:%M")
    # A股交易时间
    return ("09:30" <= current_time <= "11:30") or ("13:00" <= current_time <= "15:00")


def should_analyze_today(frequency: str, last_analysis_at: str, weekday: int = None, day_of_month: int = None) -> bool:
    """根据频率判断今天是否需要分析"""
    now = datetime.now()
    
    if last_analysis_at:
        try:
            last_time = datetime.fromisoformat(last_analysis_at)
            # 今天已经分析过了
            if last_time.date() == now.date():
                return False
        except:
            pass
    
    if frequency == 'trading_day':
        return is_trading_day()
    elif frequency == 'weekly':
        # weekday: 1=周一, 7=周日 -> Python: 0=周一, 6=周日
        target_weekday = (weekday - 1) if weekday else 0
        return now.weekday() == target_weekday
    elif frequency == 'monthly':
        # 每月指定日期
        target_day = day_of_month if day_of_month else 1
        return now.day == target_day
    
    return False


async def check_price_triggers():
    """后台任务：检查AI分析时间 + 价格触发提醒"""
    from web.database import db_get_all_reminders, db_update_reminder
    import asyncio
    
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            all_reminders = db_get_all_reminders()
            
            for username, user_reminders in all_reminders.items():
                user = get_user_by_username(username)
                if not user:
                    continue
                
                phone = user.get('phone')
                
                for reminder in user_reminders:
                    if not reminder.get('enabled'):
                        continue
                    
                    symbol = reminder['symbol']
                    reminder_id = reminder.get('reminder_id', reminder.get('id'))
                    reminder_type = reminder['reminder_type']
                    # 使用 AI 分析频率设置
                    ai_frequency = reminder.get('ai_analysis_frequency', 'trading_day')
                    ai_time = reminder.get('ai_analysis_time', '09:30')
                    ai_weekday = reminder.get('ai_analysis_weekday')
                    ai_day_of_month = reminder.get('ai_analysis_day_of_month')
                    last_analysis_at = reminder.get('last_analysis_at')
                    
                    # 检查是否到了AI分析时间（使用 AI 分析频率设置）
                    if current_time == ai_time and should_analyze_today(ai_frequency, last_analysis_at, ai_weekday, ai_day_of_month):
                        print(f"[AI分析] 开始分析 {symbol} for {username}")
                        try:
                            # 触发AI分析
                            await trigger_ai_analysis(username, symbol)
                            
                            # 更新最后分析时间
                            db_update_reminder(username, reminder_id, 
                                             last_analysis_at=now.isoformat())
                            
                            # 获取最新报告中的买卖价格
                            report = get_user_report(username, symbol)
                            if report and report.get('data'):
                                report_data = report['data']
                                buy_price = None
                                sell_price = None
                                
                                if isinstance(report_data, dict):
                                    buy_price = report_data.get('buy_price')
                                    sell_price = report_data.get('sell_price')
                                    if 'recommendation' in report_data:
                                        rec = report_data['recommendation']
                                        if isinstance(rec, dict):
                                            buy_price = buy_price or rec.get('buy_price')
                                            sell_price = sell_price or rec.get('sell_price')
                                
                                # 更新提醒中的买卖价格
                                if buy_price or sell_price:
                                    db_update_reminder(username, reminder_id,
                                                     buy_price=buy_price,
                                                     sell_price=sell_price,
                                                     last_notified_type=None)  # 重置通知状态
                        except Exception as e:
                            print(f"[AI分析] {symbol} 分析失败: {e}")
                    
                    # 检查价格触发（只在交易时间内检查）
                    if is_trading_day() and "09:30" <= current_time <= "15:00" and phone:
                        buy_price = reminder.get('buy_price')
                        sell_price = reminder.get('sell_price')
                        last_notified_type = reminder.get('last_notified_type')
                        
                        if not buy_price and not sell_price:
                            continue
                        
                        quote = get_realtime_quote(symbol)
                        if not quote:
                            continue
                        
                        current_price = quote['current_price']
                        
                        # 检查买入触发
                        if buy_price and (reminder_type in ['buy', 'both']):
                            if current_price <= buy_price and last_notified_type != 'buy':
                                msg = f"【买入提醒】{reminder.get('name', symbol)} 当前价 {current_price}，已触发买入价 {buy_price}"
                                send_sms_notification(phone, msg)
                                db_update_reminder(username, reminder_id,
                                                 last_notified_type='buy',
                                                 last_notified_at=now.isoformat())
                        
                        # 检查卖出触发
                        if sell_price and (reminder_type in ['sell', 'both']):
                            if current_price >= sell_price and last_notified_type != 'sell':
                                msg = f"【卖出提醒】{reminder.get('name', symbol)} 当前价 {current_price}，已触发卖出价 {sell_price}"
                                send_sms_notification(phone, msg)
                                db_update_reminder(username, reminder_id,
                                                 last_notified_type='sell',
                                                 last_notified_at=now.isoformat())
        
        except Exception as e:
            print(f"[后台任务] 出错: {e}")
        
        # 每60秒检查一次
        await asyncio.sleep(60)


async def trigger_ai_analysis(username: str, symbol: str):
    """触发AI分析任务"""
    # 创建分析任务
    task_id = str(uuid.uuid4())
    create_analysis_task(username, task_id, symbol)
    
    # 这里调用实际的分析逻辑
    # 简化版：直接调用分析函数
    try:
        from core.analysis_engine import run_analysis
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_analysis, symbol
        )
        if result:
            save_user_report(username, symbol, result.get('name', symbol), result)
            update_analysis_task(username, task_id, status='completed', progress=100)
    except Exception as e:
        print(f"AI分析执行失败: {e}")
        update_analysis_task(username, task_id, status='failed', error=str(e))


def send_sms_notification(phone: str, message: str) -> bool:
    """发送通知（使用微信推送）
    使用 PushPlus 服务发送微信通知
    """
    return send_wechat_notification(message)


def send_wechat_notification(message: str, title: str = "AI智能投研提醒", token: str = None) -> bool:
    """发送微信推送通知
    使用 PushPlus 服务：https://www.pushplus.plus/
    """
    import requests
    import os
    
    # 优先使用传入的 token，否则使用环境变量
    pushplus_token = token or os.environ.get("PUSHPLUS_TOKEN", "")
    
    if not pushplus_token:
        print(f"[WeChat] PushPlus Token 未配置，消息: {message}")
        return False
    
    try:
        url = "http://www.pushplus.plus/send"
        data = {
            "token": pushplus_token,
            "title": title,
            "content": message,
            "template": "html"
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("code") == 200:
            print(f"[WeChat] 推送成功: {title}")
            return True
        else:
            print(f"[WeChat] 推送失败: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"[WeChat] 推送异常: {e}")
        return False


def get_pushplus_remaining(token: str) -> dict:
    """获取 PushPlus 剩余推送次数"""
    import requests
    
    if not token:
        return {"remaining": -1, "total": 200, "error": "Token 未配置"}
    
    try:
        # PushPlus 查询接口
        url = f"http://www.pushplus.plus/api/open/user/info?token={token}"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            return {
                "remaining": data.get("limitCount", 200) - data.get("sendCount", 0),
                "total": data.get("limitCount", 200),
                "used": data.get("sendCount", 0)
            }
        else:
            # API 返回错误，返回 -1 表示未知
            return {"remaining": -1, "total": 200, "error": result.get("msg")}
    except Exception as e:
        # 网络错误，返回 -1 表示未知
        return {"remaining": -1, "total": 200, "error": str(e)}


def send_price_alert_notification(username: str, symbol: str, name: str, 
                                   alert_type: str, current_price: float, 
                                   target_price: float, ai_summary: str = "") -> bool:
    """发送价格提醒通知（带 AI 分析）"""
    from web.database import get_db
    
    # 获取用户的 PushPlus Token
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pushplus_token FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        user_token = row['pushplus_token'] if row else None
    
    if not user_token:
        print(f"[Alert] 用户 {username} 未配置 PushPlus Token")
        return False
    
    # 构建富文本消息
    action = "买入" if alert_type == "buy" else "卖出"
    action_color = "#10B981" if alert_type == "buy" else "#F43F5E"
    
    message = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
            <h2 style="margin: 0; font-size: 18px;">🔔 {action}价格提醒</h2>
        </div>
        
        <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div>
                    <div style="font-size: 20px; font-weight: bold; color: #1e293b;">{name}</div>
                    <div style="font-size: 14px; color: #64748b;">{symbol}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: bold; color: {action_color};">¥{current_price:.3f}</div>
                    <div style="font-size: 12px; color: #64748b;">当前价格</div>
                </div>
            </div>
            
            <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="color: #64748b;">触发类型</span>
                    <span style="color: {action_color}; font-weight: bold;">{action}提醒</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #64748b;">目标价格</span>
                    <span style="font-weight: bold;">¥{target_price:.3f}</span>
                </div>
            </div>
            
            {f'''
            <div style="background: #eff6ff; border-left: 4px solid #6366f1; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 15px;">
                <div style="font-size: 12px; color: #6366f1; font-weight: bold; margin-bottom: 5px;">🤖 AI 分析摘要</div>
                <div style="font-size: 13px; color: #334155; line-height: 1.5;">{ai_summary}</div>
            </div>
            ''' if ai_summary else ''}
            
            <div style="font-size: 11px; color: #94a3b8; text-align: center;">
                {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · AI智能投研
            </div>
        </div>
    </div>
    """
    
    return send_wechat_notification(message, f"【{action}提醒】{name} ¥{current_price:.3f}", user_token)


# ============================================
# 用户设置 API
# ============================================

@app.get("/api/user/settings")
async def get_user_settings(authorization: str = Header(None)):
    """获取用户设置"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pushplus_token FROM users WHERE username = ?", (user['username'],))
        row = cursor.fetchone()
        pushplus_token = row['pushplus_token'] if row else None
    
    # 获取剩余推送次数
    remaining_info = get_pushplus_remaining(pushplus_token) if pushplus_token else None
    
    return {
        "status": "success",
        "settings": {
            "pushplus_token": pushplus_token or "",
            "pushplus_configured": bool(pushplus_token),
            "pushplus_remaining": remaining_info
        }
    }


@app.post("/api/user/settings")
async def update_user_settings(
    pushplus_token: str = Query(default=""),
    authorization: str = Header(None)
):
    """更新用户设置"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import get_db
    
    # 验证 Token 格式（简单验证，不调用远程 API）
    if pushplus_token and len(pushplus_token) < 10:
        raise HTTPException(status_code=400, detail="PushPlus Token 格式不正确")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET pushplus_token = ? WHERE username = ?",
            (pushplus_token if pushplus_token else None, user['username'])
        )
        conn.commit()
    
    return {
        "status": "success",
        "message": "设置已保存"
    }


@app.post("/api/user/test-push")
async def test_user_push(
    token: str = Query(default=""),
    authorization: str = Header(None)
):
    """测试用户的推送配置"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    auth_token = authorization.replace("Bearer ", "")
    user = get_current_user(auth_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 优先使用传入的 token，否则使用已保存的
    pushplus_token = token
    if not pushplus_token:
        from web.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pushplus_token FROM users WHERE username = ?", (user['username'],))
            row = cursor.fetchone()
            pushplus_token = row['pushplus_token'] if row else None
    
    if not pushplus_token:
        raise HTTPException(status_code=400, detail="请先输入或配置 PushPlus Token")
    
    # 发送测试消息
    test_message = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
            <h2 style="margin: 0; font-size: 18px;">✅ 推送测试成功</h2>
        </div>
        
        <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-radius: 0 0 12px 12px;">
            <p style="color: #334155; margin: 0 0 15px 0;">恭喜！您的微信推送已配置成功。</p>
            <p style="color: #64748b; font-size: 13px; margin: 0 0 15px 0;">当您设置的价格提醒触发时，将会收到类似的推送通知。</p>
            
            <div style="background: #eff6ff; border-radius: 8px; padding: 12px; margin-bottom: 15px;">
                <div style="font-size: 12px; color: #6366f1; font-weight: bold;">💡 温馨提示</div>
                <div style="font-size: 13px; color: #334155; margin-top: 5px;">
                    PushPlus 免费版每月有 200 次推送额度，请合理设置提醒频率。
                </div>
            </div>
            
            <div style="font-size: 11px; color: #94a3b8; text-align: center;">
                {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · AI智能投研
            </div>
        </div>
    </div>
    """
    
    result = send_wechat_notification(test_message, "AI智能投研 - 推送测试", pushplus_token)
    
    if result:
        return {"status": "success", "message": "测试推送已发送，请检查微信"}
    else:
        raise HTTPException(status_code=500, detail="推送失败，请检查 Token 是否正确")


# ============================================
# 启动服务
# ============================================

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 Web 服务"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
