"""
============================================
FastAPI 后端 API 服务
提供证券分析的 REST API 接口
============================================
"""

import asyncio
import json
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, UploadFile, File, Form, Query, Request
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
from tools.technical_analysis import calculate_all_indicators, analyze_trend, get_support_resistance_levels, generate_trading_signals
from web.auth import (
    RegisterRequest, LoginRequest, WatchlistItem,
    get_user_by_username, get_user_by_phone, create_user, verify_password,
    create_session, get_current_user, delete_session,
    get_user_watchlist, add_to_watchlist, remove_from_watchlist, batch_add_to_watchlist,
    batch_remove_from_watchlist,
    save_user_report, get_user_reports, get_user_report, delete_user_report,
    create_analysis_task, update_analysis_task, get_user_analysis_tasks,
    get_all_users, update_user_status, update_user_role, is_admin, is_approved
)
from web.database import (
    get_db, db_get_user_by_username, db_get_user_reports,
    db_update_user_info, db_delete_user
)


# ============================================
# 数据模型
# ============================================

class AnalysisRequest(BaseModel):
    """分析请求"""
    ticker: str
    analysis_type: str = "full"  # full, quick, technical, fundamental
    holding_period: str = "swing"  # short(短线1-5天), swing(波段1-4周), long(中长线1月以上)


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


def normalize_symbol_for_url(symbol: str) -> str:
    """规范化symbol用于URL路径，将点号替换为下划线，避免URL解析问题"""
    if symbol:
        return symbol.replace('.', '_')
    return symbol


def restore_symbol_from_url(symbol: str) -> str:
    """从URL路径还原symbol，将下划线还原为点号"""
    if symbol:
        # 只还原特定模式的下划线（如 SPAX_PVT -> SPAX.PVT）
        # 避免误还原本身就有下划线的symbol
        import re
        # 匹配 字母数字_字母数字 的模式（美股常见格式如 SPAX.PVT）
        return re.sub(r'([A-Z0-9]+)_([A-Z]+)$', r'\1.\2', symbol, flags=re.IGNORECASE)
    return symbol


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
    from web.database import migrate_database
    
    print("[START] Securities Analysis API starting...")
    
    # 执行数据库迁移
    migrate_database()
    
    yield
    
    print("[STOP] Securities Analysis API shutting down...")


app = FastAPI(
    title="证券数据分析学习系统 API",
    description="个人学习研究使用，不对外开放",
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
        # 额外的安全检查：防止特殊字符注入攻击
        # 用户名只允许中文、英文字母、数字
        import re
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]{2,20}$', request.username):
            raise HTTPException(status_code=400, detail="用户名只能包含中文、英文字母或数字，长度2-20位")
        
        # 检查是否包含危险字符（防止注入攻击）
        dangerous_patterns = ['${', 'jndi:', '<script', 'javascript:', 'onerror', 'onload']
        username_lower = request.username.lower()
        for pattern in dangerous_patterns:
            if pattern in username_lower:
                raise HTTPException(status_code=400, detail="用户名包含非法字符")
        
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
async def login(request: LoginRequest, req: Request = None):
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
        
        # 记录登录活动
        from web.database import db_add_user_activity
        ip_address = req.client.host if req and req.client else None
        user_agent = req.headers.get("user-agent", "") if req else None
        db_add_user_activity(user['username'], 'login', '用户登录', ip_address, user_agent)
        
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
    import time
    start = time.time()
    print(f"[API] /api/auth/me 请求开始")
    
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    print(f"[API] /api/auth/me 耗时: {time.time() - start:.3f}s")
    
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


class AdminCreateUserRequest(BaseModel):
    """管理员创建用户请求"""
    username: str
    password: str
    phone: str


@app.post("/api/admin/users/create")
async def admin_create_user(request: AdminCreateUserRequest, authorization: str = Header(None)):
    """管理员创建用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    try:
        # 检查用户名是否已存在
        if get_user_by_username(request.username):
            raise HTTPException(status_code=400, detail="用户名已被注册")
        
        # 检查手机号是否已存在
        if get_user_by_phone(request.phone):
            raise HTTPException(status_code=400, detail="手机号已被注册")
        
        # 创建用户（管理员创建的用户直接审核通过）
        new_user = create_user(request.username, request.password, request.phone)
        
        # 直接设置为已审核状态
        update_user_status(request.username, 'approved')
        
        return {
            "status": "success",
            "message": f"用户 {request.username} 创建成功",
            "user": new_user
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/admin/users/{username}/detail")
async def admin_get_user_detail(username: str, authorization: str = Header(None)):
    """获取用户详情（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 获取用户基本信息
    target_user = db_get_user_by_username(username)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户自选列表
    watchlist = get_user_watchlist(username)
    
    # 获取用户报告
    reports = db_get_user_reports(username)
    reports_summary = [{
        'id': r['id'],
        'symbol': r['symbol'],
        'name': r.get('name', ''),
        'created_at': r['created_at']
    } for r in reports]
    
    # 获取用户操作记录
    from web.database import db_get_user_activities
    activities = db_get_user_activities(username, limit=100)
    
    return {
        "status": "success",
        "user": {
            "username": target_user['username'],
            "phone": target_user['phone'],
            "role": target_user.get('role', 'user'),
            "status": target_user.get('status', 'pending'),
            "wechat_openid": target_user.get('wechat_openid', ''),
            "created_at": target_user['created_at'],
            "can_view_ai_picks": target_user.get('can_view_ai_picks', 0)
        },
        "watchlist": watchlist,
        "reports": reports_summary,
        "activities": activities
    }


class AdminUpdateUserRequest(BaseModel):
    """管理员更新用户请求"""
    new_username: str = None
    phone: str = None
    wechat_openid: str = None


@app.put("/api/admin/users/{username}")
async def admin_update_user(username: str, request: AdminUpdateUserRequest, authorization: str = Header(None)):
    """更新用户信息（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    target_user = db_get_user_by_username(username)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新用户信息
    if request.new_username or request.phone:
        db_update_user_info(username, request.new_username, request.phone)
    
    # 更新微信OpenID
    if request.wechat_openid is not None:
        with get_db() as conn:
            cursor = conn.cursor()
            actual_username = request.new_username if request.new_username else username
            cursor.execute('UPDATE users SET wechat_openid = ? WHERE username = ?', 
                          (request.wechat_openid, actual_username))
    
    return {"status": "success", "message": "用户信息已更新"}


@app.delete("/api/admin/users/{username}")
async def admin_delete_user(username: str, authorization: str = Header(None)):
    """删除用户（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    target_user = db_get_user_by_username(username)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除管理员
    if target_user.get('role') == 'admin':
        raise HTTPException(status_code=400, detail="不能删除管理员账户")
    
    success = db_delete_user(username)
    if success:
        return {"status": "success", "message": f"用户 {username} 已删除"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@app.post("/api/admin/users/delete-by-phone")
async def admin_delete_user_by_phone(data: dict, authorization: str = Header(None)):
    """通过手机号删除用户（仅管理员）- 用于处理特殊字符用户名"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    phone = data.get('phone')
    if not phone:
        raise HTTPException(status_code=400, detail="请提供手机号")
    
    target_user = get_user_by_phone(phone)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除管理员
    if target_user.get('role') == 'admin':
        raise HTTPException(status_code=400, detail="不能删除管理员账户")
    
    success = db_delete_user(target_user['username'])
    if success:
        return {"status": "success", "message": f"用户已删除（手机号: {phone}）"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@app.post("/api/admin/users/{username}/ai-picks-permission")
async def admin_set_ai_picks_permission(
    username: str, 
    data: dict,
    authorization: str = Header(None)
):
    """设置用户研究列表查看权限（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限访问")
    
    target_user = db_get_user_by_username(username)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    can_view = data.get('can_view', False)
    from web.database import db_set_user_ai_picks_permission
    success = db_set_user_ai_picks_permission(username, can_view)
    
    if success:
        return {"status": "success", "message": f"已{'开通' if can_view else '关闭'}用户 {username} 的研究列表权限"}
    else:
        raise HTTPException(status_code=500, detail="设置失败")


# ============================================
# 自选列表 API
# ============================================

@app.get("/api/dashboard/init")
async def get_dashboard_init_data(authorization: str = Header(None)):
    """一次性获取dashboard所有初始数据，减少请求次数"""
    import time
    start = time.time()
    print(f"[API] /api/dashboard/init 请求开始")
    
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    username = user['username']
    
    # 获取所有数据
    t1 = time.time()
    watchlist = get_user_watchlist(username)
    print(f"[API] watchlist 耗时: {time.time() - t1:.3f}s")
    
    t2 = time.time()
    tasks = get_user_analysis_tasks(username)
    print(f"[API] tasks 耗时: {time.time() - t2:.3f}s")
    
    # 使用摘要查询，避免加载完整报告数据
    t3 = time.time()
    from web.database import db_get_user_reports_summary
    reports = db_get_user_reports_summary(username)
    print(f"[API] reports 耗时: {time.time() - t3:.3f}s")
    
    # 获取用户设置
    t4 = time.time()
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pushplus_token, wechat_openid FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        pushplus_token = row['pushplus_token'] if row else None
        wechat_openid = row['wechat_openid'] if row else None
    print(f"[API] settings 耗时: {time.time() - t4:.3f}s")
    
    wechat_configured = bool(wechat_openid and WECHAT_APP_SECRET and WECHAT_TEMPLATE_ID)
    
    print(f"[API] /api/dashboard/init 总耗时: {time.time() - start:.3f}s")
    
    return {
        "status": "success",
        "watchlist": watchlist,
        "tasks": tasks,
        "reports": reports,
        "settings": {
            "pushplus_token": pushplus_token or "",
            "wechat_openid": wechat_openid or "",
            "wechat_configured": wechat_configured
        }
    }


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
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """添加自选 - 快速添加，名称后台异步获取"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    item_data = item.dict()
    symbol = item_data.get('symbol', '').upper().strip()
    
    # 快速识别类型（不调用外部API）
    if symbol.isdigit() and len(symbol) == 6:
        # 中国标的快速识别
        # ETF: 51xxxx/52xxxx/56xxxx/58xxxx(上证), 159xxx(深证)
        if symbol.startswith(('510', '511', '512', '513', '515', '516', '517', '518', '520', '560', '561', '562', '563', '588')) or symbol.startswith('159'):
            item_data['type'] = 'etf'
        # LOF: 16xxxx(深证)
        elif symbol.startswith('16'):
            item_data['type'] = 'lof'
        # A股: 6xxxxx(上证主板), 000xxx/001xxx/002xxx/003xxx(深证主板/中小板), 300xxx/301xxx(创业板), 688xxx(科创板)
        elif symbol.startswith(('6', '000', '001', '002', '003', '300', '301', '688')):
            item_data['type'] = 'stock'
        # 场外基金: 其他6位数字
        else:
            item_data['type'] = 'fund'
        # 名称暂时用代码
        if not item_data.get('name'):
            item_data['name'] = symbol
    else:
        # 非中国标的（美股等）
        if not item_data.get('type'):
            item_data['type'] = 'stock'
        if not item_data.get('name'):
            item_data['name'] = symbol
    
    success = add_to_watchlist(user['username'], item_data)
    
    if success:
        # 记录添加自选活动
        from web.database import db_add_user_activity
        db_add_user_activity(user['username'], 'add_watchlist', f'添加自选: {symbol}')
        
        # 后台异步获取名称和更精确的类型
        background_tasks.add_task(update_watchlist_name_and_type, user['username'], symbol)
        return {"status": "success", "message": "添加成功", "name": item_data.get('name', '')}
    else:
        return {"status": "error", "message": "该标的已在自选列表中"}


def update_watchlist_name_and_type(username: str, symbol: str):
    """后台任务：更新自选标的的名称和类型"""
    try:
        from tools.data_fetcher import get_stock_info
        from web.auth import update_watchlist_item
        
        # 获取股票信息
        stock_info_result = get_stock_info(symbol)
        info_dict = json.loads(stock_info_result)
        
        if info_dict.get('status') == 'success':
            basic_info = info_dict.get('basic_info', {})
            name = basic_info.get('name', '')
            quote_type = basic_info.get('quote_type', '').upper()
            
            # 如果名称为空或者是默认名称，尝试其他方式获取
            if not name or name == symbol or name.startswith('股票 ') or name.startswith('ETF ') or name.startswith('基金 ') or name.startswith('LOF '):
                # 尝试从 fund_info 获取（场外基金）
                fund_info = info_dict.get('fund_info', {})
                if fund_info.get('name'):
                    name = fund_info.get('name')
                # 尝试从 etf_specific 获取
                etf_info = info_dict.get('etf_specific', {})
                if etf_info.get('tracking_index') and not name:
                    name = etf_info.get('tracking_index')
            
            # 根据 quote_type 确定类型
            asset_type = None
            if quote_type in ('ETF', 'EXCHANGETRADEDFUND'):
                asset_type = 'etf'
            elif quote_type == 'LOF':
                asset_type = 'lof'
            elif quote_type in ('MUTUALFUND', 'FUND'):
                asset_type = 'fund'
            elif quote_type in ('EQUITY', 'STOCK'):
                asset_type = 'stock'
            
            # 更新数据库
            update_data = {}
            if name and name != symbol and not name.startswith('股票 ') and not name.startswith('ETF ') and not name.startswith('基金 ') and not name.startswith('LOF '):
                update_data['name'] = name
            if asset_type:
                update_data['type'] = asset_type
            
            if update_data:
                update_watchlist_item(username, symbol, **update_data)
                print(f"[Watchlist] 更新 {symbol}: {update_data}")
            else:
                print(f"[Watchlist] {symbol} 无需更新")
        else:
            print(f"[Watchlist] 获取 {symbol} 信息失败: {info_dict.get('message', '未知错误')}")
    except Exception as e:
        print(f"[Watchlist] 获取 {symbol} 信息失败: {e}")


# 保留旧函数名以兼容
def update_watchlist_name(username: str, symbol: str):
    """后台任务：更新自选标的的名称（兼容旧调用）"""
    update_watchlist_name_and_type(username, symbol)


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
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """批量添加自选 - 快速添加，名称后台异步获取"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 快速处理每个标的
    processed_items = []
    for item in items:
        item_data = item.dict()
        symbol = item_data.get('symbol', '').upper().strip()
        
        # 快速识别类型（不调用外部API）
        if not item_data.get('type'):
            if symbol.isdigit() and len(symbol) == 6:
                if symbol.startswith('159') or symbol.startswith(('51', '56', '58', '52')):
                    item_data['type'] = 'etf'
                elif symbol.startswith('16'):
                    item_data['type'] = 'lof'
                elif symbol.startswith(('6', '0', '3')):
                    item_data['type'] = 'stock'
                else:
                    item_data['type'] = 'fund'
            else:
                item_data['type'] = 'stock'
        
        # 名称用传入的或代码
        if not item_data.get('name'):
            item_data['name'] = symbol
        
        processed_items.append(item_data)
    
    result = batch_add_to_watchlist(user['username'], processed_items)
    
    # 后台异步获取名称和更精确的类型（针对成功添加的标的）
    for symbol in result['added']:
        background_tasks.add_task(update_watchlist_name_and_type, user['username'], symbol)
    
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


class UpdateWatchlistItemRequest(BaseModel):
    """更新自选项请求"""
    position: float = None
    cost_price: float = None
    holding_period: str = None


@app.put("/api/watchlist/{symbol}")
async def update_watchlist_item(
    symbol: str,
    request: UpdateWatchlistItemRequest,
    authorization: str = Header(None)
):
    """更新自选项（持仓数量、成本价、持有周期）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        # 检查是否存在
        cursor.execute(
            "SELECT * FROM watchlist WHERE username = ? AND UPPER(symbol) = ?",
            (user['username'], symbol.upper())
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="未找到该标的")
        
        # 构建更新语句
        updates = []
        values = []
        if request.position is not None:
            updates.append("position = ?")
            values.append(request.position)
        if request.cost_price is not None:
            updates.append("cost_price = ?")
            values.append(request.cost_price)
        if request.holding_period is not None:
            updates.append("holding_period = ?")
            values.append(request.holding_period)
        
        if updates:
            values.extend([user['username'], symbol.upper()])
            cursor.execute(
                f"UPDATE watchlist SET {', '.join(updates)} WHERE username = ? AND UPPER(symbol) = ?",
                values
            )
            conn.commit()
    
    return {
        "status": "success",
        "symbol": symbol.upper(),
        "message": "更新成功"
    }


# ============================================
# OCR 图片识别 API
# ============================================

@app.post("/api/ocr/recognize")
async def recognize_stocks_from_images(
    files: List[UploadFile] = File(...),
    authorization: str = Header(None)
):
    """从多张图片识别证券代码（最多10张）- 仅用于代码提取，不构成任何投资建议"""
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
        
        print(f"[代码识别] 完成，共识别到 {len(all_recognized)} 个代码")
        
        return {
            "status": "success",
            "recognized": all_recognized,
            "image_count": len(files),
            "disclaimer": "本功能仅用于从图片中提取证券代码，便于添加到研究列表。识别结果不代表任何投资建议或推荐，请自行判断是否添加到自选进行研究。"
        }
    except Exception as e:
        print(f"[代码识别] 失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")


async def recognize_stocks_with_ai(base64_image: str, content_type: str) -> List[Dict]:
    """使用 AI 识别图片中的证券代码 - 仅提取代码，不做任何投资判断"""
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
    
    # 优化后的提示词 - 强调仅做代码提取，不涉及投资建议
    prompt = """请从这张图片中提取所有出现的证券代码（股票、ETF、基金）。

注意：这是一个纯粹的代码提取任务，仅识别图片中出现的代码和名称，不做任何投资相关的判断或建议。

请按以下JSON格式返回识别结果（只返回JSON，不要其他内容）：
```json
[
  {"symbol": "600519", "name": "贵州茅台", "type": "stock"},
  {"symbol": "159915", "name": "创业板ETF", "type": "etf"},
  {"symbol": "AAPL", "name": "苹果", "type": "stock"}
]
```

代码格式规则：
1. A股代码为6位数字（如600519、000001）
2. ETF代码为6位数字（如510300、159915）
3. 美股代码为英文字母（如AAPL、TSLA）
4. 基金代码为6位数字
5. 如果无法确定名称，name可以为空字符串
6. type可以是：stock（股票）、etf、fund（基金）

重要：只提取代码信息，不要对图片中可能出现的任何"推荐"、"建议"等内容做任何判断或转述。

如果图片中没有证券代码，返回空数组：[]"""

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
# 研究列表 API
# ============================================

@app.get("/api/ai-picks")
async def get_ai_picks(
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """获取研究列表（需要权限）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 只有已审核用户可以查看
    if not is_approved(user):
        raise HTTPException(status_code=403, detail="账户待审核，暂无权限查看")
    
    # 检查研究列表权限（管理员始终有权限）
    from web.database import db_get_user_ai_picks_permission
    if not is_admin(user) and not db_get_user_ai_picks_permission(user['username']):
        raise HTTPException(status_code=403, detail="暂无研究列表查看权限，请联系管理员开通")
    
    # 管理员看到全部，普通用户看到排除已处理的
    if is_admin(user):
        from web.database import db_get_ai_picks
        picks = db_get_ai_picks()
    else:
        from web.database import db_get_ai_picks_for_user
        picks = db_get_ai_picks_for_user(user['username'])
    
    # 检查是否有需要更新名称的标的（名称为空或等于代码）
    for pick in picks:
        if not pick.get('name') or pick.get('name') == pick.get('symbol'):
            background_tasks.add_task(update_ai_pick_name_and_type, pick['symbol'])
    
    return {
        "status": "success",
        "picks": picks,
        "is_admin": is_admin(user)
    }


@app.post("/api/ai-picks/dismiss")
async def dismiss_ai_pick(
    data: dict,
    authorization: str = Header(None)
):
    """用户标记研究列表标的为已处理（从列表中移除）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_approved(user):
        raise HTTPException(status_code=403, detail="账户待审核，暂无权限操作")
    
    symbol = data.get('symbol', '').upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="请提供标的代码")
    
    from web.database import db_dismiss_ai_pick
    db_dismiss_ai_pick(user['username'], symbol)
    
    return {"status": "success", "message": f"{symbol} 已从研究列表中移除"}


@app.post("/api/ai-picks/dismiss-batch")
async def dismiss_ai_picks_batch(
    data: dict,
    authorization: str = Header(None)
):
    """用户批量标记研究列表标的为已处理"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_approved(user):
        raise HTTPException(status_code=403, detail="账户待审核，暂无权限操作")
    
    symbols = data.get('symbols', [])
    if not symbols:
        raise HTTPException(status_code=400, detail="请提供标的代码列表")
    
    from web.database import db_dismiss_ai_picks_batch
    count = db_dismiss_ai_picks_batch(user['username'], symbols)
    
    return {"status": "success", "message": f"已移除 {count} 个标的", "count": count}


@app.post("/api/ai-picks/dismiss-all")
async def dismiss_all_ai_picks(
    authorization: str = Header(None)
):
    """用户清空所有研究列表"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_approved(user):
        raise HTTPException(status_code=403, detail="账户待审核，暂无权限操作")
    
    from web.database import db_dismiss_all_ai_picks
    count = db_dismiss_all_ai_picks(user['username'])
    
    return {"status": "success", "message": f"已清空 {count} 个标的", "count": count}


@app.post("/api/ai-picks/refresh")
async def refresh_ai_picks(
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """刷新所有研究列表标的的名称和类型（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限操作")
    
    from web.database import db_get_ai_picks
    picks = db_get_ai_picks()
    
    for pick in picks:
        background_tasks.add_task(update_ai_pick_name_and_type, pick['symbol'])
    
    return {
        "status": "success",
        "message": f"已开始刷新 {len(picks)} 个标的的信息"
    }


class AiPickItem(BaseModel):
    """研究列表项"""
    symbol: str
    name: str = ""
    type: str = "stock"


@app.post("/api/ai-picks")
async def add_ai_pick(
    item: AiPickItem,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """添加到研究列表（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限操作")
    
    # 快速识别类型（不调用外部API）
    symbol = item.symbol.upper().strip()
    name = item.name or symbol
    asset_type = item.type or 'stock'
    
    if symbol.isdigit() and len(symbol) == 6:
        # 中国标的快速识别
        if symbol.startswith(('510', '511', '512', '513', '515', '516', '517', '518', '520', '560', '561', '562', '563', '588')) or symbol.startswith('159'):
            asset_type = 'etf'
        elif symbol.startswith('16'):
            asset_type = 'lof'
        elif symbol.startswith(('6', '000', '001', '002', '003', '300', '301', '688')):
            asset_type = 'stock'
        else:
            asset_type = 'fund'
    
    from web.database import db_add_ai_pick
    success = db_add_ai_pick(symbol, name, asset_type, user['username'])
    
    if success:
        # 后台异步获取名称和更精确的类型
        background_tasks.add_task(update_ai_pick_name_and_type, symbol)
        return {"status": "success", "message": f"{symbol} 已添加到研究列表"}
    else:
        return {"status": "error", "message": "添加失败"}


def update_ai_pick_name_and_type(symbol: str):
    """后台任务：更新研究列表标的的名称和类型"""
    try:
        from tools.data_fetcher import get_stock_info
        from web.database import db_update_ai_pick
        
        # 获取股票信息
        stock_info_result = get_stock_info(symbol)
        info_dict = json.loads(stock_info_result)
        
        if info_dict.get('status') == 'success':
            basic_info = info_dict.get('basic_info', {})
            name = basic_info.get('name', '')
            quote_type = basic_info.get('quote_type', '').upper()
            
            # 如果名称为空或者是默认名称，尝试其他方式获取
            if not name or name == symbol or name.startswith('股票 ') or name.startswith('ETF ') or name.startswith('基金 ') or name.startswith('LOF '):
                # 尝试从 fund_info 获取（场外基金）
                fund_info = info_dict.get('fund_info', {})
                if fund_info.get('name'):
                    name = fund_info.get('name')
                # 尝试从 etf_specific 获取
                etf_info = info_dict.get('etf_specific', {})
                if etf_info.get('tracking_index') and not name:
                    name = etf_info.get('tracking_index')
            
            # 根据 quote_type 确定类型
            asset_type = None
            if quote_type in ('ETF', 'EXCHANGETRADEDFUND'):
                asset_type = 'etf'
            elif quote_type == 'LOF':
                asset_type = 'lof'
            elif quote_type in ('MUTUALFUND', 'FUND'):
                asset_type = 'fund'
            elif quote_type in ('EQUITY', 'STOCK'):
                asset_type = 'stock'
            
            # 更新数据库
            if name and name != symbol and not name.startswith('股票 ') and not name.startswith('ETF ') and not name.startswith('基金 ') and not name.startswith('LOF '):
                db_update_ai_pick(symbol, name=name, type_=asset_type)
                print(f"[AI Picks] 更新 {symbol}: name={name}, type={asset_type}")
            elif asset_type:
                db_update_ai_pick(symbol, type_=asset_type)
                print(f"[AI Picks] 更新 {symbol}: type={asset_type}")
            else:
                print(f"[AI Picks] {symbol} 无需更新")
        else:
            print(f"[AI Picks] 获取 {symbol} 信息失败: {info_dict.get('message', '未知错误')}")
    except Exception as e:
        print(f"[AI Picks] 获取 {symbol} 信息失败: {e}")


@app.post("/api/ai-picks/batch")
async def batch_add_ai_picks(
    items: List[AiPickItem],
    authorization: str = Header(None)
):
    """批量添加到研究列表（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限操作")
    
    from web.database import db_add_ai_pick
    added = []
    for item in items:
        if db_add_ai_pick(item.symbol, item.name, item.type, user['username']):
            added.append(item.symbol)
    
    return {
        "status": "success",
        "added": added,
        "message": f"成功添加 {len(added)} 个标的到研究列表"
    }


@app.delete("/api/ai-picks/{symbol}")
async def remove_ai_pick(
    symbol: str,
    authorization: str = Header(None)
):
    """从研究列表移除（仅管理员）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="无权限操作")
    
    from web.database import db_remove_ai_pick
    success = db_remove_ai_pick(symbol)
    
    if success:
        return {"status": "success", "message": f"{symbol} 已从研究列表移除"}
    else:
        raise HTTPException(status_code=404, detail="未找到该标的")


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
    
    # 使用摘要查询，避免加载完整报告数据
    from web.database import db_get_user_reports_summary
    reports = db_get_user_reports_summary(user['username'])
    
    return {
        "status": "success",
        "reports": reports
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
    
    try:
        # 统一转为大写，与保存时保持一致
        symbol = symbol.upper()
        print(f"[报告查询] 原始symbol: {symbol}")
        
        # symbol已经是URL规范化格式（点号已替换为下划线），直接使用
        report = get_user_report(user['username'], symbol)
        print(f"[报告查询] 使用 {symbol} 查询结果: {'找到' if report else '未找到'}")
        
        if not report:
            # 尝试还原点号格式再查询一次（兼容旧数据）
            original_symbol = restore_symbol_from_url(symbol)
            print(f"[报告查询] 还原后symbol: {original_symbol}")
            if original_symbol != symbol:
                report = get_user_report(user['username'], original_symbol)
                print(f"[报告查询] 使用 {original_symbol} 查询结果: {'找到' if report else '未找到'}")
        
        if not report:
            raise HTTPException(status_code=404, detail="未找到该标的的报告")
        
        print(f"[报告查询] 返回报告数据，ID: {report.get('id')}")
        return {
            "status": "success",
            "report": report
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[报告查询] 错误: {e}")
        print(f"[报告查询] 堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取报告失败: {str(e)}")


def clean_nan_values(obj):
    """递归清理数据中的 NaN 和 Infinity 值，替换为 None"""
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(v) for v in obj]
    else:
        return obj


@app.get("/api/share/report/{symbol}")
async def get_shared_report(symbol: str, authorization: str = Header(None)):
    """获取分享的报告（需要登录且审核通过）"""
    from web.database import get_db
    
    # 验证登录状态
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录后查看")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 验证用户是否审核通过
    if not is_approved(user) and not is_admin(user):
        raise HTTPException(status_code=403, detail="您的账户正在审核中，审核通过后即可查看")
    
    symbol = symbol.upper()
    # 尝试两种格式查询（下划线格式和点号格式）
    original_symbol = restore_symbol_from_url(symbol)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # 查找最新的该标的报告（任意用户的），同时匹配两种格式
            cursor.execute('''
                SELECT id, symbol, name, report_data, created_at, username
                FROM reports 
                WHERE UPPER(symbol) = UPPER(?) OR UPPER(symbol) = UPPER(?)
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (symbol, original_symbol))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="报告不存在或已被删除")
            
            report = dict(row)
            report_data = json.loads(report['report_data'])
            # 清理 NaN 值
            report_data = clean_nan_values(report_data)
            
            # 返回报告数据（隐藏用户名）
            return {
                "status": "success",
                "report": {
                    "id": report['id'],
                    "symbol": report['symbol'],
                    "name": report['name'],
                    "data": report_data,
                    "created_at": report['created_at']
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[分享报告] 错误: {e}")
        print(f"[分享报告] 堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取报告失败: {str(e)}")


@app.delete("/api/reports/{symbol}")
async def delete_report(symbol: str, authorization: str = Header(None)):
    """删除某个标的的报告"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 统一转为大写，与保存时保持一致
    symbol = symbol.upper()
    success = delete_user_report(user['username'], symbol)
    
    if not success:
        # 尝试还原点号格式再删除一次（兼容旧数据）
        original_symbol = restore_symbol_from_url(symbol)
        if original_symbol != symbol:
            success = delete_user_report(user['username'], original_symbol)
    
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
    holding_period = request.holding_period  # short, swing, long
    
    # 获取用户的持仓信息
    watchlist = get_user_watchlist(username)
    position_info = None
    for item in watchlist:
        if item['symbol'].upper() == symbol:
            position_info = {
                'position': item.get('position'),
                'cost_price': item.get('cost_price')
            }
            break
    
    # 创建任务记录
    create_analysis_task(username, symbol, task_id)
    
    # 记录分析活动
    from web.database import db_add_user_activity
    db_add_user_activity(username, 'start_analysis', f'启动分析: {symbol}')
    
    # 使用线程启动后台任务，完全脱离当前请求
    import threading
    def run_in_thread():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_background_analysis_full(
                username, symbol, task_id, holding_period, position_info
            ))
            loop.close()
        except Exception as e:
            print(f"[后台分析线程异常] {symbol}: {e}")
            import traceback
            traceback.print_exc()
            # 更新任务状态为失败
            try:
                update_analysis_task(username, symbol, {
                    'status': 'failed',
                    'current_step': '分析失败',
                    'error': str(e)
                })
            except:
                pass
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    return {
        "status": "success",
        "task_id": task_id,
        "symbol": symbol,
        "holding_period": holding_period,
        "message": "分析任务已启动，您可以关闭页面，稍后查看报告"
    }


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    symbols: List[str]
    holding_period: str = "swing"  # short, swing, long


@app.post("/api/analyze/batch")
async def start_batch_analysis(
    request: BatchAnalysisRequest,
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
    symbols = request.symbols
    holding_period = request.holding_period
    tasks = []
    
    # 获取用户的持仓信息
    watchlist = get_user_watchlist(username)
    position_map = {}
    for item in watchlist:
        position_map[item['symbol'].upper()] = {
            'position': item.get('position'),
            'cost_price': item.get('cost_price')
        }
    
    for symbol in symbols:
        symbol = symbol.upper()
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        create_analysis_task(username, symbol, task_id)
        
        tasks.append({
            "task_id": task_id,
            "symbol": symbol,
            "position_info": position_map.get(symbol)
        })
    
    # 使用独立线程并行启动所有分析任务
    import threading
    
    def create_analysis_runner(uname: str, sym: str, tid: str, hp: str, pos_info: dict):
        """创建分析任务运行器"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_background_analysis_full(uname, sym, tid, hp, pos_info))
            except Exception as e:
                print(f"分析任务异常 [{sym}]: {e}")
                # 确保任务状态更新为失败
                try:
                    update_analysis_task(uname, sym, {
                        'status': 'failed',
                        'current_step': '分析失败',
                        'error': str(e)
                    })
                except Exception as update_err:
                    print(f"更新任务状态失败 [{sym}]: {update_err}")
            finally:
                loop.close()
        return run
    
    # 先创建所有线程
    threads = []
    for task_info in tasks:
        runner = create_analysis_runner(
            username, task_info["symbol"], task_info["task_id"], 
            holding_period, task_info.get("position_info")
        )
        t = threading.Thread(target=runner, daemon=True)
        threads.append(t)
    
    # 同时启动所有线程
    for t in threads:
        t.start()
    
    print(f"已并行启动 {len(threads)} 个分析任务，持有周期: {holding_period}")
    
    return {
        "status": "success",
        "tasks": [{"task_id": t["task_id"], "symbol": t["symbol"]} for t in tasks],
        "holding_period": holding_period,
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


async def run_background_analysis_full(username: str, ticker: str, task_id: str, holding_period: str = "swing", position_info: dict = None):
    """
    后台执行完整的多 Agent 分析（异步并行优化版）
    
    Args:
        username: 用户名
        ticker: 证券代码
        task_id: 任务ID
        holding_period: 持有周期 - short(短线1-5天), swing(波段1-4周), long(中长线1月以上)
        position_info: 持仓信息 - {'position': 持仓数量, 'cost_price': 成本价}
    
    进度分配（基于实际耗时）：
    - 0-5%: 初始化
    - 5-15%: 数据获取（并行：行情+基本面）约2-5秒
    - 15-25%: 量化分析（并行：指标+支撑阻力）约1-3秒
    - 25-30%: 趋势分析 约1秒
    - 30-95%: AI报告生成（最耗时）约30-120秒
    - 95-100%: 保存报告
    """
    import time
    start_time = time.time()
    
    # 持有周期映射
    holding_period_map = {
        'short': '短线（1-5天）',
        'swing': '波段（1-4周）',
        'long': '中长线（1月以上）'
    }
    holding_period_cn = holding_period_map.get(holding_period, '波段（1-4周）')
    
    # 持仓信息
    user_position = position_info.get('position') if position_info else None
    user_cost_price = position_info.get('cost_price') if position_info else None
    
    # 保存原始 symbol 用于更新任务状态
    original_symbol = ticker
    print(f"[分析开始] {ticker} 任务ID: {task_id}, 持有周期: {holding_period_cn}, 持仓: {user_position}, 成本: {user_cost_price}")
    
    # 检查是否是场外基金 - 使用统一的识别函数
    from tools.data_fetcher import is_cn_offexchange_fund, is_cn_onexchange_etf
    
    is_otc_fund = False
    pure_code = ticker.replace('.SZ', '').replace('.SS', '').replace('.SH', '')
    if is_cn_offexchange_fund(pure_code):
        is_otc_fund = True
        print(f"[分析] {ticker} 识别为场外基金，将使用基金净值数据进行分析")
    elif is_cn_onexchange_etf(pure_code):
        print(f"[分析] {ticker} 识别为场内ETF/LOF")
    
    try:
        # === 初始化 ===
        update_analysis_task(username, original_symbol, {
            'status': 'running',
            'progress': 2,
            'current_step': '初始化分析环境'
        })
        
        # === 阶段1：数据获取（5-15%）===
        update_analysis_task(username, original_symbol, {
            'progress': 5,
            'current_step': '识别证券代码'
        })
        
        # 场外基金使用专门的数据获取方法
        if is_otc_fund:
            from tools.data_fetcher import get_cn_fund_data, get_cn_fund_info
            
            update_analysis_task(username, original_symbol, {
                'progress': 8,
                'current_step': '获取基金净值数据'
            })
            
            # 获取基金数据
            stock_data = await asyncio.to_thread(get_cn_fund_data, pure_code, "2y")
            stock_info = await asyncio.to_thread(get_cn_fund_info, pure_code)
            
            stock_data_dict = json.loads(stock_data)
            stock_info_dict = json.loads(stock_info)
            
            if stock_data_dict.get("status") != "success":
                raise Exception(f"无法获取 {ticker} 的基金净值数据")
            
            print(f"[分析] {ticker} 基金数据获取完成 耗时{time.time()-start_time:.1f}s")
        else:
            # 非场外基金使用原有逻辑
            search_result = await asyncio.to_thread(search_ticker, ticker)
            search_dict = json.loads(search_result)
            if search_dict.get("status") == "success":
                ticker = search_dict.get("ticker", ticker)
            
            update_analysis_task(username, original_symbol, {
                'progress': 8,
                'current_step': '获取行情和基本面数据'
            })
            
            # 并行获取数据
            stock_data_task = asyncio.create_task(asyncio.to_thread(get_stock_data, ticker, "2y", "1d"))
            stock_info_task = asyncio.create_task(asyncio.to_thread(get_stock_info, ticker))
            
            stock_data, stock_info = await asyncio.gather(stock_data_task, stock_info_task)
            stock_data_dict = json.loads(stock_data)
            stock_info_dict = json.loads(stock_info)
            
            if stock_data_dict.get("status") != "success":
                raise Exception(f"无法获取 {ticker} 的行情数据")
            
            print(f"[分析] {ticker} 数据获取完成 耗时{time.time()-start_time:.1f}s")
        
        # === 阶段2：量化分析（15-25%）===
        update_analysis_task(username, original_symbol, {
            'progress': 15,
            'current_step': '计算技术指标'
        })
        
        # 并行计算指标和支撑阻力
        indicators_task = asyncio.create_task(asyncio.to_thread(calculate_all_indicators, stock_data))
        levels_task = asyncio.create_task(asyncio.to_thread(get_support_resistance_levels, stock_data))
        
        indicators, levels = await asyncio.gather(indicators_task, levels_task)
        indicators_dict = json.loads(indicators)
        levels_dict = json.loads(levels)
        
        if indicators_dict.get("status") == "error" or not indicators_dict.get("indicators"):
            raise Exception(f"无法计算 {ticker} 的技术指标")
        
        update_analysis_task(username, original_symbol, {
            'progress': 22,
            'current_step': '分析市场趋势'
        })
        
        # === 阶段3：趋势分析（25-30%）===
        trend = await asyncio.to_thread(analyze_trend, indicators)
        trend_dict = json.loads(trend)
        
        if trend_dict.get("status") == "error":
            raise Exception(f"无法分析 {ticker} 的趋势")
        
        # === 阶段3.5：生成交易信号 ===
        update_analysis_task(username, original_symbol, {
            'progress': 25,
            'current_step': '生成交易信号'
        })
        
        # 提取量化分析和趋势分析数据，传递给交易信号生成器
        quant_analysis_raw = trend_dict.get("quant_analysis", {})
        # 确保 quant_score 字段存在（trading_signals.py 使用 quant_score，而 quant_analysis 使用 score）
        quant_analysis_for_signal = {
            **quant_analysis_raw,
            'quant_score': quant_analysis_raw.get('score', quant_analysis_raw.get('quant_score', 50))
        }
        trend_analysis_for_signal = trend_dict.get("trend_analysis", trend_dict)
        
        # 生成交易信号（整合AI分析+量化数据指标，包含多周期信号）
        trading_signals = await asyncio.to_thread(
            generate_trading_signals, 
            indicators, 
            levels,
            quant_analysis_for_signal,
            trend_analysis_for_signal,
            holding_period
        )
        trading_signals_dict = json.loads(trading_signals)
        
        print(f"[分析] {ticker} 量化分析完成 耗时{time.time()-start_time:.1f}s")
        
        # === 阶段4：AI报告生成（30-95%）===
        update_analysis_task(username, original_symbol, {
            'progress': 30,
            'current_step': f'AI正在生成{holding_period_cn}分析报告（约需1-2分钟）'
        })
        
        try:
            report, predictions = await generate_ai_report_with_predictions(
                ticker, stock_data_dict, stock_info_dict, 
                indicators_dict, trend_dict, levels_dict,
                holding_period=holding_period,
                position_info={'position': user_position, 'cost_price': user_cost_price},
                # 传入进度回调
                progress_callback=lambda p, s: update_analysis_task(username, original_symbol, {
                    'progress': 30 + int(p * 0.65),  # 30-95%
                    'current_step': s
                })
            )
        except Exception as ai_error:
            print(f"[分析] {ticker} AI报告生成失败: {ai_error}")
            raise Exception(f"AI报告生成失败: {ai_error}")
        
        print(f"[分析] {ticker} AI报告完成 耗时{time.time()-start_time:.1f}s")
        
        # === 阶段5：保存报告（95-100%）===
        update_analysis_task(username, original_symbol, {
            'progress': 95,
            'current_step': '保存分析报告'
        })
        
        # 提取量化数据
        quant_analysis = trend_dict.get("quant_analysis", {})
        trend_analysis = trend_dict.get("trend_analysis", trend_dict)
        signal_details = trend_dict.get("signal_details", [])
        
        quant_score = quant_analysis.get("score")
        market_regime = quant_analysis.get("market_regime", "unknown")
        volatility_state = quant_analysis.get("volatility_state", "medium")
        quant_reco = quant_analysis.get("recommendation", "hold")
        
        ind_root = indicators_dict.get("indicators", indicators_dict or {})
        adx_data = ind_root.get("adx", {}) if isinstance(ind_root, dict) else {}
        atr_data = ind_root.get("atr", {}) if isinstance(ind_root, dict) else {}
        
        indicator_overview = {
            "adx_value": adx_data.get("adx"),
            "adx_trend_strength": adx_data.get("trend_strength"),
            "atr_value": atr_data.get("value"),
            "atr_pct": atr_data.get("percentage"),
        }
        
        reco_map = {"strong_buy": "强势", "buy": "偏强", "hold": "中性", "sell": "偏弱", "strong_sell": "弱势"}
        regime_map = {"trending": "趋势市", "ranging": "震荡市", "squeeze": "窄幅整理", "unknown": "待判定"}
        vol_map = {"high": "高波动", "medium": "中等波动", "low": "低波动"}
        
        score_text = f"{quant_score:.1f}" if isinstance(quant_score, (int, float)) else "N/A"
        ai_summary = f"量化评分 {score_text} 分，{regime_map.get(market_regime, '待判定')}，{vol_map.get(volatility_state, '中等波动')}。技术面评级：{reco_map.get(quant_reco, '中性')}。"
        
        completed_at = get_beijing_now()
        report = normalize_report_timestamp(report, completed_at)
        
        # 提取交易信号数据（包含多周期信号）
        trading_signal_data = None
        if trading_signals_dict.get("status") == "success":
            # 获取多周期信号和完整分析
            multi_period_signals = trading_signals_dict.get('multi_period_signals', {})
            multi_period_analysis = trading_signals_dict.get('multi_period_analysis', {})
            
            trading_signal_data = {
                'signal': trading_signals_dict.get('trading_signal', {}),
                'risk_management': trading_signals_dict.get('risk_management', {}),
                'action_suggestion': trading_signals_dict.get('action_suggestion', ''),
                'current_price': trading_signals_dict.get('current_price', 0),
                'holding_period': holding_period,
                'quant_score': quant_score,  # 添加量化评分，确保与仪表盘一致
                'multi_period_signals': multi_period_signals,  # 多周期信号类型
                'multi_period_analysis': multi_period_analysis,  # 多周期完整分析
                'disclaimer': trading_signals_dict.get('disclaimer', '')
            }
        
        report_data = {
            'status': 'completed',
            'ticker': original_symbol,
            'report': report,
            'predictions': predictions,
            'quant_analysis': quant_analysis,
            'trend_analysis': trend_analysis,
            'ai_summary': ai_summary,
            'indicator_overview': indicator_overview,
            'signal_details': signal_details,
            'trading_signal': trading_signal_data,
            'stock_info': stock_info_dict,
            'indicators': indicators_dict,
            'levels': levels_dict
        }
        
        # 保存报告时使用规范化的symbol（点号替换为下划线）
        save_symbol = normalize_symbol_for_url(original_symbol)
        print(f"[报告保存] 原始symbol: {original_symbol}, 规范化后: {save_symbol}")
        save_user_report(username, save_symbol, report_data)
        
        # 从报告中提取技术分析参考价位并更新到自选列表
        # 注意：这些价位仅供学习研究参考，不构成任何投资建议
        try:
            from web.database import db_update_watchlist_ai_prices
            import re
            
            # 从技术分析中提取支撑位/阻力位
            ai_buy_price = None  # 支撑位
            ai_sell_price = None  # 阻力位
            ai_buy_quantity = None
            ai_sell_quantity = None
            
            # 尝试从报告中解析参考价位表格
            if report:
                print(f"[技术分析] 开始从报告中提取参考价位...")
                
                # 匹配多种格式的支撑位（支持 $ 和 ¥）
                buy_patterns = [
                    r'\*\*支撑位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*\*\*支撑位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*支撑位\s*\|\s*[$¥]?([\d.]+)',
                    r'支撑位[：:]\s*[$¥]?([\d.]+)',
                    r'技术支撑[：:]\s*[$¥]?([\d.]+)',
                    r'\*\*参考低位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*参考低位\s*\|\s*[$¥]?([\d.]+)',
                    r'参考低位[：:]\s*[$¥]?([\d.]+)',
                ]
                for pattern in buy_patterns:
                    buy_match = re.search(pattern, report)
                    if buy_match:
                        try:
                            ai_buy_price = float(buy_match.group(1))
                            print(f"[技术分析] 从报告中提取到支撑位: {ai_buy_price}")
                            break
                        except:
                            pass
                
                # 匹配多种格式的阻力位（支持 $ 和 ¥）
                sell_patterns = [
                    r'\*\*阻力位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*\*\*阻力位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*阻力位\s*\|\s*[$¥]?([\d.]+)',
                    r'阻力位[：:]\s*[$¥]?([\d.]+)',
                    r'技术阻力[：:]\s*[$¥]?([\d.]+)',
                    r'\*\*参考高位\*\*\s*\|\s*[$¥]?([\d.]+)',
                    r'\|\s*参考高位\s*\|\s*[$¥]?([\d.]+)',
                    r'参考高位[：:]\s*[$¥]?([\d.]+)',
                ]
                for pattern in sell_patterns:
                    sell_match = re.search(pattern, report)
                    if sell_match:
                        try:
                            ai_sell_price = float(sell_match.group(1))
                            print(f"[技术分析] 从报告中提取到阻力位: {ai_sell_price}")
                            break
                        except:
                            pass
                
                # 提取参考数量 - 从表格行中提取（支持 $ 和 ¥）
                buy_qty_patterns = [
                    r'\*\*支撑位\*\*\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'\|\s*\*\*支撑位\*\*\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'\|\s*支撑位\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'支撑位[^|]*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'参考数量[：:]\s*([\d,]+)\s*(?:股|份)?',
                ]
                for pattern in buy_qty_patterns:
                    qty_match = re.search(pattern, report)
                    if qty_match:
                        try:
                            qty_str = qty_match.group(1).replace(',', '').replace('，', '')
                            ai_buy_quantity = int(qty_str)
                            if ai_buy_quantity > 0:
                                print(f"[技术分析] 从报告中提取到参考数量: {ai_buy_quantity}")
                                break
                        except:
                            pass
                
                # 提取阻力位数量 - 从表格行中提取（支持 $ 和 ¥）
                sell_qty_patterns = [
                    r'\*\*阻力位\*\*\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'\|\s*\*\*阻力位\*\*\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'\|\s*阻力位\s*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                    r'阻力位[^|]*\|\s*[$¥]?[\d.]+\s*\|\s*([\d,]+)\s*(?:股|份)',
                ]
                for pattern in sell_qty_patterns:
                    qty_match = re.search(pattern, report)
                    if qty_match:
                        try:
                            qty_str = qty_match.group(1).replace(',', '').replace('，', '')
                            ai_sell_quantity = int(qty_str)
                            if ai_sell_quantity > 0:
                                print(f"[技术分析] 从报告中提取到阻力位数量: {ai_sell_quantity}")
                                break
                        except:
                            pass
            
            # 如果报告中没有提取到，则从技术分析的支撑位/阻力位获取
            if not ai_buy_price or not ai_sell_price:
                print(f"[技术分析] 从技术分析中获取支撑位/阻力位...")
                key_levels = levels_dict.get('key_levels', {})
                if isinstance(key_levels, list):
                    # 列表格式
                    support_prices = [l.get('price') for l in key_levels if l.get('type') == 'support' and l.get('price')]
                    resistance_prices = [l.get('price') for l in key_levels if l.get('type') == 'resistance' and l.get('price')]
                    if not ai_buy_price and support_prices:
                        ai_buy_price = support_prices[0]
                        print(f"[技术分析] 从key_levels列表获取支撑位: {ai_buy_price}")
                    if not ai_sell_price and resistance_prices:
                        ai_sell_price = resistance_prices[0]
                        print(f"[技术分析] 从key_levels列表获取阻力位: {ai_sell_price}")
                elif isinstance(key_levels, dict):
                    # 字典格式
                    if not ai_buy_price:
                        ai_buy_price = key_levels.get('nearest_support')
                        if ai_buy_price:
                            print(f"[技术分析] 从key_levels字典获取支撑位: {ai_buy_price}")
                    if not ai_sell_price:
                        ai_sell_price = key_levels.get('nearest_resistance')
                        if ai_sell_price:
                            print(f"[技术分析] 从key_levels字典获取阻力位: {ai_sell_price}")
                
                # 如果key_levels没有，尝试从support_levels/resistance_levels获取
                if not ai_buy_price:
                    support_levels = levels_dict.get('support_levels', [])
                    if support_levels:
                        if isinstance(support_levels[0], dict):
                            ai_buy_price = support_levels[0].get('price')
                        elif isinstance(support_levels[0], (int, float)):
                            ai_buy_price = support_levels[0]
                        if ai_buy_price:
                            print(f"[技术分析] 从support_levels获取支撑位: {ai_buy_price}")
                
                if not ai_sell_price:
                    resistance_levels = levels_dict.get('resistance_levels', [])
                    if resistance_levels:
                        if isinstance(resistance_levels[0], dict):
                            ai_sell_price = resistance_levels[0].get('price')
                        elif isinstance(resistance_levels[0], (int, float)):
                            ai_sell_price = resistance_levels[0]
                        if ai_sell_price:
                            print(f"[技术分析] 从resistance_levels获取阻力位: {ai_sell_price}")
            
            # 确保价格是数值类型
            if isinstance(ai_buy_price, str):
                ai_buy_price = None
            if isinstance(ai_sell_price, str):
                ai_sell_price = None
            
            # 从报告中提取技术面评级（强势/偏强/中性/偏弱/弱势）
            ai_recommendation = None
            if report:
                # 匹配总结评级部分的评级
                reco_patterns = [
                    r'综合评级[：:]\s*\*?\*?(强势|偏强|中性|偏弱|弱势)',
                    r'总结评级[：:]\s*\*?\*?(强势|偏强|中性|偏弱|弱势)',
                    r'技术面评级[：:]\s*\*?\*?(强势|偏强|中性|偏弱|弱势)',
                    r'评级[：:]\s*\*?\*?(强势|偏强|中性|偏弱|弱势)',
                    r'\*\*(强势|偏强|中性|偏弱|弱势)\*\*',
                ]
                for pattern in reco_patterns:
                    reco_match = re.search(pattern, report)
                    if reco_match:
                        ai_recommendation = reco_match.group(1)
                        print(f"[技术评级] 从报告中提取到评级: {ai_recommendation}")
                        break
                
                # 如果没有匹配到，尝试从量化评级获取
                if not ai_recommendation:
                    # 量化评级映射
                    quant_reco_map = {
                        'strong_buy': '强势',
                        'buy': '偏强',
                        'hold': '中性',
                        'sell': '偏弱',
                        'strong_sell': '弱势',
                    }
                    ai_recommendation = quant_reco_map.get(quant_reco, None)
                    if ai_recommendation:
                        print(f"[技术评级] 从量化分析获取评级: {ai_recommendation}")
            
            # 从报告中提取多周期价位（短线/波段/中长线的支撑位、阻力位、风险位）
            multi_period_prices = {'short': {}, 'swing': {}, 'long': {}}
            if report:
                print(f"[多周期价位] 开始从报告中提取多周期价位...")
                
                # 定义周期关键词映射（更全面的匹配）
                period_configs = {
                    'short': {
                        'keywords': ['短线', '1-5天', '1-5日', '1～5天', '1～5日'],
                        'section_patterns': [
                            r'###\s*短线[^#]*?(?=###|##\s|$)',
                            r'###\s*1-5[天日][^#]*?(?=###|##\s|$)',
                            r'\*\*短线[^*]*\*\*[^#]*?(?=\*\*波段|\*\*中长|###|##\s|$)',
                        ]
                    },
                    'swing': {
                        'keywords': ['波段', '1-4周', '1～4周'],
                        'section_patterns': [
                            r'###\s*波段[^#]*?(?=###|##\s|$)',
                            r'###\s*1-4周[^#]*?(?=###|##\s|$)',
                            r'\*\*波段[^*]*\*\*[^#]*?(?=\*\*中长|###|##\s|$)',
                        ]
                    },
                    'long': {
                        'keywords': ['中长线', '中长期', '1月以上', '1个月以上'],
                        'section_patterns': [
                            r'###\s*中长[线期][^#]*?(?=###|##\s|$)',
                            r'###\s*1月以上[^#]*?(?=###|##\s|$)',
                            r'\*\*中长[线期][^*]*\*\*[^#]*?(?=###|##\s|$)',
                        ]
                    }
                }
                
                # 通用价格提取模式（支持多种格式）
                def extract_price_from_section(section_text, price_type):
                    """从区域文本中提取指定类型的价格"""
                    if price_type == 'support':
                        patterns = [
                            r'\|\s*\*\*支撑位\*\*\s*\|\s*[$¥￥]?([\d.]+)',
                            r'\|\s*支撑位\s*\|\s*[$¥￥]?([\d.]+)',
                            r'支撑位[：:]\s*[$¥￥]?([\d.]+)',
                            r'\*\*支撑位\*\*[：:\s]*[$¥￥]?([\d.]+)',
                        ]
                    elif price_type == 'resistance':
                        patterns = [
                            r'\|\s*\*\*阻力位\*\*\s*\|\s*[$¥￥]?([\d.]+)',
                            r'\|\s*阻力位\s*\|\s*[$¥￥]?([\d.]+)',
                            r'阻力位[：:]\s*[$¥￥]?([\d.]+)',
                            r'\*\*阻力位\*\*[：:\s]*[$¥￥]?([\d.]+)',
                        ]
                    else:  # risk
                        patterns = [
                            r'\|\s*\*\*风险位\*\*\s*\|\s*[$¥￥]?([\d.]+)',
                            r'\|\s*风险位\s*\|\s*[$¥￥]?([\d.]+)',
                            r'\|\s*\*\*风险观察位\*\*\s*\|\s*[$¥￥]?([\d.]+)',
                            r'\|\s*风险观察位\s*\|\s*[$¥￥]?([\d.]+)',
                            r'风险位[：:]\s*[$¥￥]?([\d.]+)',
                            r'风险观察位[：:]\s*[$¥￥]?([\d.]+)',
                            r'\*\*风险位\*\*[：:\s]*[$¥￥]?([\d.]+)',
                        ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, section_text)
                        if match:
                            try:
                                return float(match.group(1))
                            except:
                                pass
                    return None
                
                # 提取每个周期的价位
                for period_key, config in period_configs.items():
                    section_text = None
                    
                    # 尝试多种模式匹配区域
                    for section_pattern in config['section_patterns']:
                        section_match = re.search(section_pattern, report, re.DOTALL | re.IGNORECASE)
                        if section_match:
                            section_text = section_match.group(0)
                            print(f"[多周期价位] 找到 {period_key} 区域，长度: {len(section_text)}")
                            break
                    
                    if section_text:
                        # 提取支撑位
                        support = extract_price_from_section(section_text, 'support')
                        if support:
                            multi_period_prices[period_key]['support'] = support
                            print(f"[多周期价位] {period_key} 支撑位: {support}")
                        
                        # 提取阻力位
                        resistance = extract_price_from_section(section_text, 'resistance')
                        if resistance:
                            multi_period_prices[period_key]['resistance'] = resistance
                            print(f"[多周期价位] {period_key} 阻力位: {resistance}")
                        
                        # 提取风险位
                        risk = extract_price_from_section(section_text, 'risk')
                        if risk:
                            multi_period_prices[period_key]['risk'] = risk
                            print(f"[多周期价位] {period_key} 风险位: {risk}")
                    else:
                        print(f"[多周期价位] 未找到 {period_key} 区域")
                
                # 如果某些周期没有提取到数据，尝试从全文提取（作为备选）
                # 使用当前周期的支撑位/阻力位作为默认值
                if ai_buy_price and not any(multi_period_prices[p].get('support') for p in ['short', 'swing', 'long']):
                    # 根据持有周期设置默认值
                    if holding_period == 'short':
                        multi_period_prices['short']['support'] = ai_buy_price
                    elif holding_period == 'long':
                        multi_period_prices['long']['support'] = ai_buy_price
                    else:
                        multi_period_prices['swing']['support'] = ai_buy_price
                    print(f"[多周期价位] 使用默认支撑位: {ai_buy_price}")
                
                if ai_sell_price and not any(multi_period_prices[p].get('resistance') for p in ['short', 'swing', 'long']):
                    if holding_period == 'short':
                        multi_period_prices['short']['resistance'] = ai_sell_price
                    elif holding_period == 'long':
                        multi_period_prices['long']['resistance'] = ai_sell_price
                    else:
                        multi_period_prices['swing']['resistance'] = ai_sell_price
                    print(f"[多周期价位] 使用默认阻力位: {ai_sell_price}")
                
                print(f"[多周期价位] 最终提取结果: {multi_period_prices}")
            
            # 检查是否有任何多周期价位数据
            has_multi_period = any(
                multi_period_prices[p].get('support') or 
                multi_period_prices[p].get('resistance') or 
                multi_period_prices[p].get('risk')
                for p in ['short', 'swing', 'long']
            )
            
            # 从交易信号中提取多周期信号类型（现在直接使用返回的多周期信号）
            multi_period_signals = None
            if trading_signals_dict.get("status") == "success":
                # 优先使用返回的多周期信号
                multi_period_signals = trading_signals_dict.get('multi_period_signals')
                
                # 如果没有多周期信号，则使用当前周期的信号
                if not multi_period_signals:
                    trading_signal = trading_signals_dict.get('trading_signal', {})
                    signal_type = trading_signal.get('signal_type', 'hold')
                    
                    # 根据持有周期设置对应的信号
                    multi_period_signals = {'short': None, 'swing': None, 'long': None}
                    if holding_period == 'short':
                        multi_period_signals['short'] = signal_type
                    elif holding_period == 'long':
                        multi_period_signals['long'] = signal_type
                    else:
                        multi_period_signals['swing'] = signal_type
                
                print(f"[交易信号] {original_symbol} 多周期信号: {multi_period_signals}")
            
            if ai_buy_price or ai_sell_price or ai_recommendation or has_multi_period or multi_period_signals:
                db_update_watchlist_ai_prices(
                    username, original_symbol, 
                    ai_buy_price, ai_sell_price, 
                    ai_buy_quantity, ai_sell_quantity, 
                    ai_recommendation,
                    multi_period_prices if has_multi_period else None,
                    multi_period_signals
                )
                print(f"[AI价格] 已更新 {original_symbol}: 评级={ai_recommendation}, 支撑位={ai_buy_price}, 阻力位={ai_sell_price}")
                if has_multi_period:
                    print(f"[AI价格] 多周期价位已更新: {multi_period_prices}")
                if multi_period_signals:
                    print(f"[AI价格] 多周期信号已更新: {multi_period_signals}")
                
                # 将AI建议价格添加到report_data中，便于前端获取
                report_data['ai_buy_price'] = ai_buy_price
                report_data['ai_sell_price'] = ai_sell_price
                report_data['ai_buy_quantity'] = ai_buy_quantity
                report_data['ai_sell_quantity'] = ai_sell_quantity
                report_data['ai_recommendation'] = ai_recommendation
                report_data['multi_period_prices'] = multi_period_prices
                report_data['multi_period_signals'] = multi_period_signals
            
            # 更新持有周期到自选列表
            from web.database import db_update_watchlist_item
            db_update_watchlist_item(username, original_symbol, holding_period=holding_period)
            print(f"[周期更新] 已更新 {original_symbol} 的持有周期: {holding_period}")
        except Exception as e:
            print(f"[AI价格] 更新建议价格失败: {e}")
        
        total_time = time.time() - start_time
        print(f"[分析完成] {original_symbol} 总耗时 {total_time:.1f}s")
        
        update_analysis_task(username, original_symbol, {
            'status': 'completed',
            'progress': 100,
            'current_step': f'分析完成（耗时{total_time:.0f}秒）',
            'result': json.dumps(report_data, ensure_ascii=False)
        })
        
    except Exception as e:
        import traceback
        print(f"[分析失败] {original_symbol}: {e}")
        traceback.print_exc()
        update_analysis_task(username, original_symbol, {
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
            "strong_buy": "强势",
            "buy": "偏强",
            "hold": "中性",
            "sell": "偏弱",
            "strong_sell": "弱势",
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
        reco_cn = reco_map.get(quant_reco, "中性")
        bullish_signals = trend_analysis.get("bullish_signals", 0) if isinstance(trend_analysis, dict) else 0
        bearish_signals = trend_analysis.get("bearish_signals", 0) if isinstance(trend_analysis, dict) else 0
        
        ai_summary = (
            f"量化评分 {score_text} 分，当前处于{regime_cn}，{vol_cn}环境。"
            f"多头信号 {bullish_signals} 个、空头信号 {bearish_signals} 个，技术面评级：{reco_cn}。"
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
    每个标的根据实际数据动态计算，不使用固定值
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
    kdj_k = kdj.get("k", 50) if isinstance(kdj, dict) else 50
    kdj_d = kdj.get("d", 50) if isinstance(kdj, dict) else 50
    
    ma_trend = ind.get("ma_trend", "unknown")
    
    bb = ind.get("bollinger_bands", {})
    bb_position = bb.get("position", 0) if isinstance(bb, dict) else 0
    bb_width = bb.get("width", 0.05) if isinstance(bb, dict) else 0.05  # 布林带宽度反映波动率
    
    # 获取ATR（平均真实波幅）作为波动率参考
    atr = ind.get("atr", {})
    atr_value = atr.get("value", 0) if isinstance(atr, dict) else 0
    atr_pct = atr.get("pct", 2.0) if isinstance(atr, dict) else 2.0  # ATR占价格的百分比
    
    # 获取ADX（趋势强度）
    adx = ind.get("adx", {})
    adx_value = adx.get("value", 25) if isinstance(adx, dict) else 25
    
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
    
    # 计算动态波动率基准（基于ATR和布林带宽度）
    base_volatility = max(atr_pct / 100, bb_width, 0.01)  # 至少1%
    
    # 计算综合得分 (-100 到 100)
    score = 0
    
    # RSI 贡献 (-30 到 30)
    if rsi_value < 30:
        score += 25 + (30 - rsi_value)  # 越超卖越看涨
    elif rsi_value > 70:
        score -= 25 + (rsi_value - 70)  # 越超买越看跌
    else:
        score += (50 - rsi_value) * 0.5  # 中性区间
    
    # MACD 贡献 (-25 到 25)
    if macd_trend == "bullish":
        score += 20
    elif macd_trend == "bearish":
        score -= 20
    if isinstance(macd_histogram, (int, float)):
        if macd_histogram > 0:
            score += min(macd_histogram * 2, 5)
        elif macd_histogram < 0:
            score += max(macd_histogram * 2, -5)
    
    # KDJ 贡献 (-20 到 20)
    if kdj_status == "oversold" or kdj_k < 20:
        score += 15 + (20 - kdj_k) * 0.5
    elif kdj_status == "overbought" or kdj_k > 80:
        score -= 15 + (kdj_k - 80) * 0.5
    # 金叉死叉
    if kdj_k > kdj_d:
        score += 5
    else:
        score -= 5
    
    # 均线趋势贡献 (-15 到 15)
    if ma_trend == "bullish_alignment":
        score += 15
    elif ma_trend == "bearish_alignment":
        score -= 15
    elif ma_trend == "bullish":
        score += 10
    elif ma_trend == "bearish":
        score -= 10
    
    # 布林带位置贡献 (-10 到 10)
    if bb_position < -50:
        score += 10  # 接近下轨，看涨
    elif bb_position > 50:
        score -= 10  # 接近上轨，看跌
    
    # ADX趋势强度调整（趋势越强，预测越可靠）
    trend_strength_factor = min(adx_value / 25, 1.5)  # ADX>25表示强趋势
    
    # 根据得分生成预测
    def get_trend_and_target(base_score, period_factor, period_volatility):
        adjusted_score = base_score * period_factor * trend_strength_factor
        
        if adjusted_score > 30:
            trend = "bullish"
            target_pct = min(adjusted_score * period_volatility, 50)
        elif adjusted_score < -30:
            trend = "bearish"
            target_pct = max(adjusted_score * period_volatility, -50)
        else:
            trend = "neutral"
            target_pct = adjusted_score * period_volatility * 0.5
        
        # 置信度 - 基于得分绝对值和ADX
        abs_score = abs(adjusted_score)
        if abs_score > 50 and adx_value > 30:
            confidence = "high"
        elif abs_score > 35 or (abs_score > 25 and adx_value > 25):
            confidence = "medium"
        else:
            confidence = "low"
        
        return trend, target_pct, confidence
    
    # 生成各周期预测 - 波动率根据实际数据动态计算
    predictions = []
    periods = [
        ("1D", "明日", 0.3, base_volatility * 0.3),
        ("3D", "3天", 0.5, base_volatility * 0.5),
        ("1W", "1周", 0.7, base_volatility * 1.0),
        ("15D", "15天", 0.85, base_volatility * 1.5),
        ("1M", "1个月", 1.0, base_volatility * 2.5),
        ("3M", "3个月", 1.2, base_volatility * 5.0),
        ("6M", "6个月", 1.3, base_volatility * 7.5),
        ("1Y", "1年", 1.5, base_volatility * 12.0),
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
    levels: dict,
    holding_period: str = "swing",
    position_info: dict = None,
    progress_callback=None
) -> tuple:
    """
    调用 AI 多Agent分析生成报告和预测
    返回: (report, predictions)
    
    Args:
        holding_period: 持有周期 - short(短线), swing(波段), long(中长线)
        position_info: 持仓信息 - {'position': 持仓数量, 'cost_price': 成本价}
        progress_callback: 可选的进度回调函数 callback(progress: float, step: str)
                          progress 范围 0-100
    """
    from openai import OpenAI
    import httpx
    import os
    import re
    
    # 持有周期映射
    holding_period_map = {
        'short': '短线（1-5天）',
        'swing': '波段（1-4周）',
        'long': '中长线（1月以上）'
    }
    holding_period_cn = holding_period_map.get(holding_period, '波段（1-4周）')
    
    # 持仓信息
    user_position = position_info.get('position') if position_info else None
    user_cost_price = position_info.get('cost_price') if position_info else None
    
    # 进度更新辅助函数
    def update_progress(progress: float, step: str):
        if progress_callback:
            try:
                progress_callback(progress, step)
            except:
                pass
    
    update_progress(5, f'AI{holding_period_cn}预测模型准备中')
    
    # 强制禁用系统代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    api_key = APIConfig.SILICONFLOW_API_KEY
    
    # 创建优化的 HTTP 客户端配置
    transport = httpx.HTTPTransport(
        proxy=None,
        retries=3  # 自动重试3次
    )
    http_client = httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(
            900.0,  # 总超时900秒
            connect=60.0,  # 连接超时60秒
            read=600.0,  # 读取超时600秒
            write=60.0  # 写入超时60秒
        )
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
    
    # 获取量化分析数据（与智能研报一致）
    quant_data = stock_data.get("quant_analysis", {})
    quant_score = quant_data.get("score", 50)
    quant_regime = quant_data.get("market_regime", "unknown")
    quant_vol_state = quant_data.get("volatility_state", "medium")
    quant_reco_code = quant_data.get("recommendation", "hold")
    
    regime_map = {"trending": "趋势市", "ranging": "震荡市", "squeeze": "窄幅整理", "unknown": "待判定"}
    vol_map = {"high": "高波动", "medium": "中等波动", "low": "低波动"}
    reco_map = {"strong_buy": "强势", "buy": "偏强", "hold": "中性", "sell": "偏弱", "strong_sell": "弱势"}
    
    # 获取基本面数据
    valuation = stock_info.get("valuation", {})
    market_cap = info.get("market_cap", valuation.get("market_cap"))
    
    prediction_prompt = f"""你是一位资深的量化分析师，请基于以下多维度数据，对标的进行多周期价格预测。

## 标的基本信息
- 代码: {ticker}
- 名称: {info.get('name', ticker)}
- 当前价格: {latest_price}
- 日涨跌幅: {price_info.get('day_change', 'N/A')}%
- 52周最高: {price_info.get('52_week_high', 'N/A')}
- 52周最低: {price_info.get('52_week_low', 'N/A')}
- 市盈率(P/E): {valuation.get('pe_ratio', 'N/A')}
- 市净率(P/B): {valuation.get('price_to_book', 'N/A')}
- 市值: {market_cap}

## 量化分析结果
- 量化评分(0-100): {quant_score}
- 市场状态: {regime_map.get(quant_regime, quant_regime)}
- 波动状态: {vol_map.get(quant_vol_state, quant_vol_state)}
- 量化建议: {reco_map.get(quant_reco_code, quant_reco_code)}
- 多头信号数: {trend_analysis.get('bullish_signals', 0)}
- 空头信号数: {trend_analysis.get('bearish_signals', 0)}
- 综合趋势: {trend_analysis.get('trend_cn', trend_analysis.get('overall_trend', 'N/A'))}
- 趋势强度: {trend_analysis.get('trend_strength', 'N/A')}

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
- 成交量分析: {ind.get('volume_analysis', {})}

## 新增技术指标
- VWAP成交量加权均价: {ind.get('vwap', {})}
- 资金流向MFI: {ind.get('mfi', {})}
- 换手率: {ind.get('turnover_rate', {})}
- BIAS乖离率: {ind.get('bias', {})}
- DMI趋向指标: {ind.get('dmi', {})}
- SAR抛物线: {ind.get('sar', {})}

## 关键价位
- 支撑位: {levels.get('support_levels', levels.get('nearest_support', 'N/A'))}
- 阻力位: {levels.get('resistance_levels', levels.get('nearest_resistance', 'N/A'))}

## 多周期涨跌幅历史
{ind.get('period_returns', {})}

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

**综合分析要点**：
1. **量化信号权重**：量化评分>70看多，<30看空；参考多空信号数量对比
2. **技术指标共振**：RSI/KDJ超买超卖、MACD/均线金叉死叉、CCI/Williams %R趋势、DMI方向
3. **资金面分析**：OBV能量潮、MFI资金流向、换手率活跃度、成交量变化
4. **波动与风险**：ATR波动率、布林带宽度、市场状态（趋势/震荡）
5. **价位参考**：当前价格相对支撑阻力位的位置，VWAP偏离度
6. **历史表现**：短期参考5日/10日涨跌幅，长期参考60日/250日涨跌幅
7. **估值参考**：PE/PB是否合理，市值规模
8. **置信度规则**：短期预测置信度更高，长期降低；信号冲突时选neutral
9. **涨跌幅范围**：短期(1D-1W)±0.5%~5%，中期(15D-1M)±3%~15%，长期(3M-1Y)±10%~50%"""

    async def call_predictions() -> list:
        """调用 DeepSeek 生成多周期预测，如失败则使用本地量化规则回退。"""
        predictions_local: list = []
        try:
            # Agent 1 调用（使用线程池避免阻塞）
            def sync_call():
                return client.chat.completions.create(
                    model=APIConfig.SILICONFLOW_MODEL,
                    messages=[
                        {"role": "system", "content": "你是量化分析师，只输出JSON格式的预测数据，不要输出其他内容。"},
                        {"role": "user", "content": prediction_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.2,
                    timeout=180
                )
            
            pred_response = await asyncio.to_thread(sync_call)
            
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
    
    update_progress(15, f'AI{holding_period_cn}预测和报告并行生成中')
    
    # 并行运行预测和报告生成
    predictions_task = asyncio.create_task(call_predictions())
    report_task = asyncio.create_task(
        generate_ai_report(ticker, stock_data, stock_info, indicators, trend, levels, holding_period, position_info)
    )
    
    # 等待预测完成（通常较快）
    predictions = await predictions_task
    update_progress(50, 'AI预测完成，报告生成中')
    
    # 等待报告完成，添加超时处理
    try:
        report = await asyncio.wait_for(report_task, timeout=360)  # 6分钟超时
    except asyncio.TimeoutError:
        print(f"[AI报告] {ticker} 报告生成超时（360秒）")
        raise Exception("AI报告生成超时，请稍后重试")
    except Exception as e:
        print(f"[AI报告] {ticker} 报告生成失败: {e}")
        raise
    
    update_progress(95, 'AI报告生成完成')
    
    return report, predictions


async def generate_ai_report(
    ticker: str,
    stock_data: dict,
    stock_info: dict,
    indicators: dict,
    trend: dict,
    levels: dict,
    holding_period: str = "swing",
    position_info: dict = None
) -> str:
    """
    调用 DeepSeek-R1 生成分析报告
    
    Args:
        holding_period: 持有周期 - short(短线), swing(波段), long(中长线)
        position_info: 持仓信息 - {'position': 持仓数量, 'cost_price': 成本价}
    """
    from openai import OpenAI
    import httpx
    import os
    
    # 持仓信息
    user_position = position_info.get('position') if position_info else None
    user_cost_price = position_info.get('cost_price') if position_info else None
    
    # 持有周期映射
    holding_period_map = {
        'short': '短线（1-5天）',
        'swing': '波段（1-4周）',
        'long': '中长线（1月以上）'
    }
    holding_period_cn = holding_period_map.get(holding_period, '波段（1-4周）')
    
    # 强制禁用系统代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    api_key = APIConfig.SILICONFLOW_API_KEY
    
    # 创建优化的 HTTP 客户端配置（流式输出需要更长超时）
    transport = httpx.HTTPTransport(
        proxy=None,
        retries=2  # 自动重试2次
    )
    http_client = httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(
            300.0,  # 总超时300秒（5分钟）
            connect=30.0,  # 连接超时30秒
            read=300.0,  # 读取超时300秒
            write=30.0  # 写入超时30秒
        )
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
    
    # 根据股票类型确定货币符号
    from tools.data_fetcher import is_us_stock, get_currency_symbol
    currency_symbol = get_currency_symbol(ticker)
    
    market_cap_display = valuation.get("market_cap_str")
    if not market_cap_display:
        market_cap_value = valuation.get("market_cap")
        if isinstance(market_cap_value, (int, float)) and market_cap_value > 0:
            if is_us_stock(ticker):
                # 美股用美元和B/M单位
                if market_cap_value >= 1e12:
                    market_cap_display = f"${market_cap_value/1e12:.2f}T"
                elif market_cap_value >= 1e9:
                    market_cap_display = f"${market_cap_value/1e9:.2f}B"
                elif market_cap_value >= 1e6:
                    market_cap_display = f"${market_cap_value/1e6:.2f}M"
                else:
                    market_cap_display = f"${market_cap_value:.0f}"
            else:
                # 中国股票用人民币和亿/万单位
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
        "strong_buy": "强势",
        "buy": "偏强",
        "hold": "中性",
        "sell": "偏弱",
        "strong_sell": "弱势",
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
    
    # 根据持有周期设置不同的分析重点
    if holding_period == 'short':
        period_focus = """
**短线技术分析重点（1-5天）**：
- 关注日内和日线级别的技术信号
- 支撑位基于当日支撑位计算，阻力位基于短期阻力位计算"""
        price_guidance = "短线支撑位应在当前价格下方1-3%的支撑位附近，阻力位应在当前价格上方2-5%的阻力位附近"
    elif holding_period == 'long':
        period_focus = """
**中长线技术分析重点（1月以上）**：
- 关注周线、月线级别的趋势方向
- 支撑位基于重要支撑位计算，阻力位基于长期阻力位计算"""
        price_guidance = "中长线支撑位应在当前价格下方5-15%的重要支撑位，阻力位应在当前价格上方10-30%的长期阻力位"
    else:  # swing
        period_focus = """
**波段技术分析重点（1-4周）**：
- 关注日线和周线级别的技术形态
- 支撑位基于波段支撑位计算，阻力位基于波段阻力位计算"""
        price_guidance = "波段支撑位应在当前价格下方3-8%的支撑位，阻力位应在当前价格上方5-15%的阻力位"
    
    # 构建持仓信息提示（只有持仓和成本价都有值时才显示）
    position_hint = ""
    if user_position and user_cost_price:
        position_hint = f"\n4. 用户持仓: {user_position}股，成本价: {currency_symbol}{user_cost_price}，请据此给出参考数量"
    
    prompt = f"""**重要提示**: 
1. 当前日期: {report_date} {report_time}
2. 持有周期: **{holding_period_cn}**
3. 请基于最新行情数据、分时/日K/周K/月K等多周期技术指标进行深度分析{position_hint}

{period_focus}

## 标的基本信息
- 代码: {symbol}
- 名称: {display_name}
- 当前价格: {current_price}
- 日涨跌幅: {day_change_str}%
- 52周最高: {price_info.get('52_week_high', 'N/A')}
- 52周最低: {price_info.get('52_week_low', 'N/A')}
- 市盈率(P/E): {valuation.get('pe_ratio', 'N/A')}
- 市净率(P/B): {valuation.get('price_to_book', 'N/A')}
- 市值/规模: {market_cap_display}

## 技术指标数据（基于最新行情）
### 趋势指标
- MACD: {ind.get('macd', {})}
- 均线系统: {ind.get('moving_averages', {})}
- ADX趋势强度: {ind.get('adx', {})}

### 震荡指标
- RSI(14日): {ind.get('rsi', {})}
- KDJ: {ind.get('kdj', {})}
- Williams %R: {ind.get('williams_r', {})}
- CCI顺势指标: {ind.get('cci', {})}

### 波动与动量
- 布林带: {ind.get('bollinger_bands', {})}
- ATR波动率: {ind.get('atr', {})}
- 动量指标: {ind.get('momentum', {})}
- ROC变动率: {ind.get('roc', {})}

### 量价分析
- 成交量分析: {ind.get('volume_analysis', {})}
- 价格位置: {ind.get('price_position', {})}

### 多周期涨跌幅
{ind.get('period_returns', {})}

## 量化分析结果
- 综合趋势: {trend_analysis.get('trend_cn', trend_analysis.get('overall_trend', 'N/A'))}
- 趋势强度: {trend_analysis.get('trend_strength', 'N/A')}
- 量化评分(0-100): {quant_score}
- 市场状态: {regime_map.get(quant_regime, quant_regime)}
- 波动状态: {vol_map.get(quant_vol_state, quant_vol_state)}
- 量化建议: {reco_map.get(quant_reco_code, quant_reco_code)}
- 多头信号数: {trend_analysis.get('bullish_signals', 0)}
- 空头信号数: {trend_analysis.get('bearish_signals', 0)}
- 系统建议: {trend_analysis.get('recommendation', 'N/A')}

## 关键价位
- 支撑位: {key_levels.get('nearest_support', levels.get('support_levels', 'N/A'))}
- 阻力位: {key_levels.get('nearest_resistance', levels.get('resistance_levels', 'N/A'))}

---
请生成**{holding_period_cn}**专业分析报告，包含以下章节：

## 一、标的概况
用Markdown表格展示核心指标（当前价格、日涨跌幅、52周区间、市值规模、综合趋势、趋势强度、市场状态）

**多周期表现（区间涨跌）**：
（注意：表格前后必须有空行，表头和分隔符必须对齐）

| 周期 | 涨跌幅 |
|:-----|:-------|
| 5日 | +X.XX% |
| 10日 | +X.XX% |
| 20日 | +X.XX% |
| 60日 | +X.XX% |
| 120日 | +X.XX% |
| 250日 | +X.XX% |

## 二、AI深度研判
### 2.1 消息面与情绪分析
简要分析近期消息、市场情绪、资金动向

### 2.2 多周期技术共振
综合分时/日K/周K/月K研判趋势方向

### 2.3 综合结论
当前技术面分析结论和核心逻辑

## 三、技术指标分析
分析MACD、RSI、KDJ、布林带等关键指标状态

## 四、支撑阻力位
列出关键支撑位和阻力位

## 五、多周期参考价位（仅供研究参考）
> 注：参考价位基于历史数据与技术指标计算，为市场分析提供辅助视角，并非未来价格保证。

**必须严格按照以下格式提供三个周期的价位数据（精确到小数点后3位）：**

### 短线（1-5天）

| 类型 | 价格 | 说明 |
|:-----|:-----|:-----|
| **支撑位** | {currency_symbol}X.XXX | 基于日内/日线支撑位计算 |
| **阻力位** | {currency_symbol}X.XXX | 基于短期阻力位计算 |
| **风险位** | {currency_symbol}X.XXX | 若跌破该位，短线技术结构转弱 |

### 波段（1-4周）

| 类型 | 价格 | 说明 |
|:-----|:-----|:-----|
| **支撑位** | {currency_symbol}X.XXX | 基于波段支撑位计算 |
| **阻力位** | {currency_symbol}X.XXX | 基于波段阻力位计算 |
| **风险位** | {currency_symbol}X.XXX | 若跌破该位，波段技术结构转弱 |

### 中长线（1月以上）

| 类型 | 价格 | 说明 |
|:-----|:-----|:-----|
| **支撑位** | {currency_symbol}X.XXX | 基于重要支撑位计算 |
| **阻力位** | {currency_symbol}X.XXX | 基于长期阻力位计算 |
| **风险位** | {currency_symbol}X.XXX | 若跌破该位，中长线技术结构转弱 |

{f"用户持仓: {user_position}股，成本: " + currency_symbol + f"{user_cost_price}" if user_position and user_cost_price else ""}

## 六、技术面总结与风险提示
给出{holding_period_cn}技术面客观分析总结和主要技术风险因素（禁止给出任何操作建议）

## 七、综合评级
技术面综合评级（强势/偏强/中性/偏弱/弱势），仅描述技术面状态，禁止给出任何操作建议或行动指引

**格式要求（必须严格遵守）**：
1. 所有Markdown表格前后必须有空行，表头行、分隔符行、数据行必须对齐
2. 必须给出三个周期（短线、波段、中长线）的支撑位、阻力位、风险位数字（精确到小数点后3位）
3. 每个周期的价位必须是合理的数值，不能为空或0
4. 所有内容必须是客观技术分析，禁止使用"介入"、"建仓"、"止盈"、"止损"、"操作上"、"建议"等引导性词汇

---
**重要声明**：本分析报告由AI基于公开数据和技术指标自动生成，仅供个人学习研究参考，不构成任何投资建议。投资有风险，决策需谨慎。
"""
    try:
        import re

        # 使用流式API调用，边生成边接收，减少超时风险
        def sync_stream_call():
            """使用流式输出，逐块接收响应，带重试机制"""
            max_retries = 2
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    print(f"[AI报告] 开始生成报告，尝试 {attempt + 1}/{max_retries + 1}")
                    chunks = []
                    chunk_count = 0
                    stream = client.chat.completions.create(
                        model=APIConfig.SILICONFLOW_MODEL,
                        messages=[
                            {"role": "system", "content": """你是资深证券技术分析师。请基于数据生成专业、客观的技术分析报告。

**合规要求（必须严格遵守）**：
1. 禁止使用任何交易引导性语言，包括但不限于：
   - "介入"、"建仓"、"加仓"、"减仓"、"清仓"、"止盈"、"止损"
   - "买入机会"、"卖出时机"、"获利了结"、"逢低吸纳"
   - "操作上"、"建议"、"推荐"、"不宜追高"、"可以考虑"
   - "寻找机会"、"把握时机"、"适时介入"
2. 参考价位说明只能使用纯技术描述：
   - 参考低位说明：只能写"基于XX支撑位计算"、"技术支撑参考"
   - 参考高位说明：只能写"基于XX阻力位计算"、"技术阻力参考"
   - 风险控制位说明：只能写"若跌破该位，短线技术结构转弱"
3. 综合评级部分：
   - 只能给出评级（强势/偏强/中性/偏弱/弱势）和技术面客观描述
   - 禁止给出任何操作建议或行动指引
4. 所有内容必须是客观的技术分析陈述，不能有任何主观交易建议"""},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=4000,  # token数量
                        temperature=0.3,
                        stream=True,  # 启用流式输出
                        timeout=300  # 5分钟超时
                    )
                    
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            chunks.append(chunk.choices[0].delta.content)
                            chunk_count += 1
                            if chunk_count % 50 == 0:
                                print(f"[AI报告] 已接收 {chunk_count} 个chunk，当前长度: {sum(len(c) for c in chunks)}")
                    
                    result = "".join(chunks)
                    print(f"[AI报告] 生成完成，总长度: {len(result)}")
                    if result and len(result) > 100:  # 确保有有效内容
                        return result
                    else:
                        raise Exception("AI返回内容过短或为空")
                        
                except Exception as e:
                    last_error = e
                    print(f"[AI报告] 生成失败: {e}")
                    if attempt < max_retries:
                        print(f"[AI报告] 流式输出失败，第{attempt + 1}次重试: {e}")
                        import time
                        time.sleep(2)  # 等待2秒后重试
                    else:
                        raise last_error
            
            raise last_error if last_error else Exception("AI报告生成失败")
        
        report_text = await asyncio.to_thread(sync_stream_call)

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
                f"**报告生成时间**: {date_str} {time_str} | **数据来源**: 量化系统 + AI多智能体分析"
            )
            report_text += footer

        return report_text
    except Exception:
        # 任何异常都不影响主流程，直接返回原始报告
        return report_text


def normalize_multi_period_section(report_text: str, period_returns: dict) -> str:
    """根据 period_returns 重写报告中的"多周期表现/区间涨跌"小节。

    - 删除AI生成的多周期表现内容（避免重复）
    - 使用后端的真实收益率数据构建标准 Markdown 表格
    - 将多周期表现紧跟在"一、标的概况"之后，"二、AI深度研判"之前
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
                return v
            return "N/A"

        # 构建标准的多周期表现表格（确保格式正确）
        table_lines = [
            "",
            "**多周期表现（区间涨跌）：**",
            "",
            "| 周期 | 涨跌幅 |",
            "|:-----|:-------|",
            f"| 5日 | {_fmt('5日')} |",
            f"| 10日 | {_fmt('10日')} |",
            f"| 20日 | {_fmt('20日')} |",
            f"| 60日 | {_fmt('60日')} |",
            f"| 120日 | {_fmt('120日')} |",
            f"| 250日 | {_fmt('250日')} |",
            "",
        ]
        new_block = "\n".join(table_lines)

        # 删除所有可能的多周期表现相关内容
        patterns_to_remove = [
            # 匹配 **多周期表现** 或 多周期表现 开头的内容块
            r"\*?\*?多周期表现[^#]*?(?=\n## |\n---|\n\*\*报告生成时间|\Z)",
            # 匹配 区间涨跌 开头的表格
            r"区间涨跌[:：]?\s*\n+\|[^\n]+\n\|[-:]+[^\n]*\n(?:\|[^\n]+\n)*",
            # 匹配格式错误的表格（| 周期 | 日涨跌幅 | 开头）
            r"\|\s*周期\s*\|\s*日?涨跌幅[^\n]*\n\|[-:]+[^\n]*\n(?:\|[^\n]+\n)*",
        ]
        
        for pattern in patterns_to_remove:
            report_text = re.sub(pattern, "\n", report_text, flags=re.MULTILINE | re.DOTALL)
        
        # 清理可能残留的多余空行
        report_text = re.sub(r'\n{3,}', '\n\n', report_text)
        
        # 将多周期表现插入到"## 二、AI深度研判"之前
        pattern_insert = r"(## 二、AI深度研判)"
        if re.search(pattern_insert, report_text):
            report_text = re.sub(pattern_insert, new_block + "\n" + r"\1", report_text)
        else:
            # 如果找不到"二、AI深度研判"，尝试在"一、标的概况"的表格后面插入
            # 查找标的概况表格的结束位置（市场状态行之后）
            pattern_after_table = r"(\|\s*市场状态\s*\|[^\n]*\n)"
            if re.search(pattern_after_table, report_text):
                report_text = re.sub(pattern_after_table, r"\1" + new_block + "\n", report_text)
            else:
                # 尝试在任何 ## 二 之前插入
                pattern_before_section2 = r"(\n## 二)"
                if re.search(pattern_before_section2, report_text):
                    report_text = re.sub(pattern_before_section2, new_block + r"\1", report_text)

        return report_text
    except Exception:
        return report_text


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
    
    # 使用线程池异步执行，不阻塞其他请求
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        quotes = await loop.run_in_executor(executor, get_batch_quotes, symbol_list)
    
    return {"status": "success", "quotes": quotes}


# ============================================
# 实时交易信号 API
# ============================================

@app.get("/api/signals/realtime")
async def get_realtime_signals(symbols: str, authorization: str = Header(None)):
    """获取实时交易信号
    
    根据最新行情数据实时计算交易信号，并持久化到数据库。
    适用于自选列表的信号实时更新。
    
    Args:
        symbols: 逗号分隔的标的代码列表
    
    Returns:
        包含每个标的的多周期信号（short/swing/long）
    
    注意：此接口仅供技术分析参考，不构成任何投资建议。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    username = user['username']
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    
    if len(symbol_list) > 20:
        raise HTTPException(status_code=400, detail="单次最多查询20个标的")
    
    # 使用线程池异步执行
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        signals = await loop.run_in_executor(executor, calculate_realtime_signals, symbol_list, username)
    
    return {
        "status": "success", 
        "signals": signals,
        "timestamp": get_beijing_now().isoformat(),
        "disclaimer": "以上信号仅为技术分析工具输出，不构成任何投资建议。市场有风险，投资需谨慎。"
    }


def calculate_realtime_signals(symbols: list, username: str = None) -> dict:
    """计算实时交易信号
    
    为每个标的计算最新的多周期交易信号，并持久化到数据库。
    
    Args:
        symbols: 标的代码列表
        username: 用户名（用于持久化信号到数据库）
    """
    import time
    from quant.trading_signals import generate_multi_period_analysis
    from web.database import db_update_watchlist_ai_prices
    
    signals = {}
    
    for symbol in symbols:
        try:
            start_time = time.time()
            
            # 1. 获取行情数据
            stock_data = get_stock_data(symbol, period="1y")
            stock_data_dict = json.loads(stock_data)
            
            if stock_data_dict.get("status") != "success":
                signals[symbol] = {"error": "获取行情数据失败"}
                continue
            
            # 2. 计算技术指标
            indicators_json = calculate_all_indicators(stock_data)
            indicators_dict = json.loads(indicators_json)
            
            if indicators_dict.get("status") != "success":
                signals[symbol] = {"error": "计算技术指标失败"}
                continue
            
            indicators = indicators_dict.get("indicators", indicators_dict)
            
            # 3. 获取支撑阻力位
            sr_json = get_support_resistance_levels(stock_data)
            sr_dict = json.loads(sr_json)
            
            # 4. 简单的趋势分析（基于技术指标）
            trend_json = analyze_trend(indicators_json)
            trend_dict = json.loads(trend_json)
            
            # 5. 构建量化分析数据（简化版，基于技术指标）
            quant_analysis = {
                "quant_score": _calculate_quick_quant_score(indicators),
                "recommendation": _get_quick_recommendation(indicators),
                "market_regime": indicators.get("adx", {}).get("trend_strength", "unknown")
            }
            
            # 6. 生成多周期信号
            multi_period = generate_multi_period_analysis(
                indicators,
                sr_dict,
                quant_analysis=quant_analysis,
                trend_analysis=trend_dict
            )
            
            # 7. 提取信号类型
            signal_data = {
                "short": {
                    "signal": multi_period['short']['signal_type'],
                    "type_cn": multi_period['short']['type_cn'],
                    "strength": multi_period['short']['strength'],
                    "confidence": multi_period['short']['confidence']
                },
                "swing": {
                    "signal": multi_period['swing']['signal_type'],
                    "type_cn": multi_period['swing']['type_cn'],
                    "strength": multi_period['swing']['strength'],
                    "confidence": multi_period['swing']['confidence']
                },
                "long": {
                    "signal": multi_period['long']['signal_type'],
                    "type_cn": multi_period['long']['type_cn'],
                    "strength": multi_period['long']['strength'],
                    "confidence": multi_period['long']['confidence']
                },
                "current_price": indicators.get("latest_price", 0),
                "calc_time": round(time.time() - start_time, 2),
                "updated_at": get_beijing_now().isoformat()
            }
            
            signals[symbol] = signal_data
            
            # 8. 持久化信号到数据库（如果提供了用户名）
            if username:
                try:
                    multi_period_signals = {
                        'short': multi_period['short']['signal_type'],
                        'swing': multi_period['swing']['signal_type'],
                        'long': multi_period['long']['signal_type']
                    }
                    db_update_watchlist_ai_prices(
                        username=username,
                        symbol=symbol,
                        multi_period_signals=multi_period_signals
                    )
                except Exception as db_err:
                    print(f"[Signals] {symbol} 信号持久化失败: {db_err}")
            
            print(f"[Signals] {symbol} 信号计算完成: 短线={multi_period['short']['signal_type']}, 波段={multi_period['swing']['signal_type']}, 中长线={multi_period['long']['signal_type']}, 耗时={time.time()-start_time:.2f}s")
            
        except Exception as e:
            print(f"[Signals] {symbol} 信号计算失败: {e}")
            import traceback
            traceback.print_exc()
            signals[symbol] = {"error": str(e)}
    
    return signals


def _calculate_quick_quant_score(indicators: dict) -> float:
    """快速计算量化评分（简化版）
    
    基于技术指标快速计算一个0-100的评分。
    """
    score = 50  # 基础分
    
    # 均线趋势
    ma_trend = indicators.get("ma_trend", "")
    if ma_trend == "bullish_alignment":
        score += 15
    elif ma_trend == "bearish_alignment":
        score -= 15
    
    # MACD
    macd = indicators.get("macd", {})
    if macd.get("trend") == "bullish":
        score += 8
    elif macd.get("trend") == "bearish":
        score -= 8
    if macd.get("crossover") == "golden_cross":
        score += 5
    elif macd.get("crossover") == "death_cross":
        score -= 5
    
    # RSI
    rsi = indicators.get("rsi", {})
    rsi_value = rsi.get("value", 50)
    if 40 <= rsi_value <= 60:
        score += 5  # 中性区间加分
    elif rsi_value < 30:
        score += 3  # 超卖可能反弹
    elif rsi_value > 70:
        score -= 3  # 超买可能回调
    
    # ADX趋势强度
    adx = indicators.get("adx", {})
    if adx.get("trend_strength") == "strong":
        if adx.get("trend_direction") == "bullish":
            score += 10
        else:
            score -= 10
    
    # 资金流向
    mfi = indicators.get("money_flow", {})
    if mfi.get("mfi_status") == "inflow":
        score += 8
    elif mfi.get("mfi_status") == "outflow":
        score -= 8
    
    # 云图
    ichimoku = indicators.get("ichimoku", {})
    if ichimoku.get("status") == "strong_bullish":
        score += 8
    elif ichimoku.get("status") == "strong_bearish":
        score -= 8
    
    # 限制在0-100范围内
    return max(0, min(100, score))


def _get_quick_recommendation(indicators: dict) -> str:
    """快速获取推荐（简化版）"""
    score = _calculate_quick_quant_score(indicators)
    
    if score >= 75:
        return "strong_buy"
    elif score >= 60:
        return "buy"
    elif score <= 25:
        return "strong_sell"
    elif score <= 40:
        return "sell"
    else:
        return "hold"


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
    
    # 根据市场时段动态调整缓存时间
    cache_ttl = get_quote_cache_ttl()
    market_session = get_market_session()
    
    # 提取纯数字代码
    code_map = {}
    for symbol in symbols:
        code = symbol[2:] if symbol.startswith(("sz", "sh")) else symbol
        code_map[code] = symbol
    
    codes = set(code_map.keys())
    print(f"[Quotes] 请求代码: {codes}, 市场时段: {market_session}, 缓存TTL: {cache_ttl}s")
    
    # 获取 ETF 数据（使用缓存）
    try:
        if _quote_cache['etf']['data'] is None or \
           _quote_cache['etf']['time'] is None or \
           (now - _quote_cache['etf']['time']).seconds > cache_ttl:
            print("[Quotes] 正在获取 ETF 数据...")
            _quote_cache['etf']['data'] = ak.fund_etf_spot_em()
            _quote_cache['etf']['time'] = now
            if _quote_cache['etf']['data'] is not None:
                print(f"[Quotes] ETF 数据获取成功，共 {len(_quote_cache['etf']['data'])} 条")
                print(f"[Quotes] ETF 数据列名: {list(_quote_cache['etf']['data'].columns)}")
            else:
                print("[Quotes] ETF 数据为空")
        
        df_etf = _quote_cache['etf']['data']
        if df_etf is not None and len(df_etf) > 0:
            matched = df_etf[df_etf['代码'].isin(codes)]
            print(f"[Quotes] ETF 匹配到 {len(matched)} 条")
            for _, row in matched.iterrows():
                code = row['代码']
                symbol = code_map.get(code, code)
                price = safe_float(row.get('最新价', row.get('现价', 0)))
                change = safe_float(row.get('涨跌幅', 0))
                print(f"[Quotes] ETF {code}: 价格={price}, 涨跌={change}")
                quotes[symbol] = {
                    'symbol': symbol,
                    'current_price': price,
                    'change_percent': change
                }
                codes.discard(code)
        else:
            print("[Quotes] ETF 数据为空，跳过")
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
                print("[Quotes] 正在获取 LOF 数据...")
                _quote_cache['lof']['data'] = ak.fund_lof_spot_em()
                _quote_cache['lof']['time'] = now
            
            df_lof = _quote_cache['lof']['data']
            if df_lof is not None and len(df_lof) > 0:
                for _, row in df_lof[df_lof['代码'].isin(codes)].iterrows():
                    code = row['代码']
                    symbol = code_map.get(code, code)
                    price = safe_float(row.get('最新价', row.get('现价', 0)))
                    change = safe_float(row.get('涨跌幅', 0))
                    quotes[symbol] = {
                        'symbol': symbol,
                        'current_price': price,
                        'change_percent': change
                    }
                    codes.discard(code)
        except Exception as e:
            print(f"LOF批量行情获取失败: {e}")
    
    # 获取 A股 数据 - 使用单个查询避免获取全部数据
    if codes:
        try:
            # 不再获取全部A股数据，改用单个查询
            print(f"[Quotes] 正在获取 A股 数据（单个查询）...")
            import requests
            for code in list(codes):
                try:
                    # 使用东方财富单个股票接口
                    # 判断市场：6开头上证，其他深证
                    market = "1" if code.startswith("6") else "0"
                    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f170,f58"
                    headers = {"User-Agent": "Mozilla/5.0"}
                    resp = requests.get(url, headers=headers, timeout=3)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        if data:
                            symbol = code_map.get(code, code)
                            price = safe_float(data.get("f43", 0)) / 100  # 价格需要除以100
                            change = safe_float(data.get("f170", 0)) / 100  # 涨跌幅需要除以100
                            if price > 0:
                                quotes[symbol] = {
                                    'symbol': symbol,
                                    'current_price': price,
                                    'change_percent': change
                                }
                                codes.discard(code)
                                print(f"[Quotes] A股 {code}: 价格={price}, 涨跌={change}")
                except Exception as e:
                    print(f"[Quotes] A股 {code} 获取失败: {e}")
        except Exception as e:
            print(f"A股批量行情获取失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 获取场外基金净值数据（剩余未匹配的代码）
    if codes:
        remaining_codes = list(codes)
        print(f"[Quotes] 尝试获取场外基金数据，剩余代码: {remaining_codes}")
        for code in remaining_codes:
            # 6位数字代码，尝试从天天基金获取
            if code.isdigit() and len(code) == 6:
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
                            nav = safe_float(fund_info.get('gsz', fund_info.get('dwjz', 0)))
                            change = safe_float(fund_info.get('gszzl', 0))
                            if nav > 0:
                                quotes[symbol] = {
                                    'symbol': symbol,
                                    'current_price': nav,
                                    'change_percent': change
                                }
                                codes.discard(code)
                                print(f"[Quotes] 场外基金 {code} 获取成功: 净值={nav}, 涨跌={change}%")
                except Exception as e:
                    print(f"[Quotes] 场外基金 {code} 净值获取失败: {e}")
    
    # 获取美股/港股数据（使用 yfinance）
    if codes:
        remaining_codes = list(codes)
        print(f"[Quotes] 尝试获取美股/港股数据，剩余代码: {remaining_codes}")
        try:
            import yfinance as yf
            for code in remaining_codes:
                # 非纯数字代码，可能是美股或港股
                if not code.isdigit():
                    try:
                        # 还原点号格式（如 SPAX_PVT -> SPAX.PVT）
                        ticker_code = code.replace('_', '.')
                        ticker = yf.Ticker(ticker_code)
                        info = ticker.info
                        if info:
                            symbol = code_map.get(code, code)
                            price = safe_float(info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', 0))))
                            prev_close = safe_float(info.get('previousClose', info.get('regularMarketPreviousClose', price)))
                            if price > 0 and prev_close > 0:
                                change = ((price - prev_close) / prev_close) * 100
                            else:
                                change = safe_float(info.get('regularMarketChangePercent', 0))
                            if price > 0:
                                quotes[symbol] = {
                                    'symbol': symbol,
                                    'current_price': price,
                                    'change_percent': round(change, 2)
                                }
                                codes.discard(code)
                                print(f"[Quotes] 美股/港股 {ticker_code}: 价格={price}, 涨跌={change:.2f}%")
                    except Exception as e:
                        print(f"[Quotes] 美股/港股 {code} 获取失败: {e}")
        except Exception as e:
            print(f"美股/港股批量行情获取失败: {e}")
            import traceback
            traceback.print_exc()
    
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
        
        # 尝试从 A股 获取 - 使用东方财富单个接口
        try:
            import requests
            market = "1" if code.startswith("6") else "0"
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f170,f58"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=3)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                if data:
                    price = float(data.get("f43", 0)) / 100
                    change = float(data.get("f170", 0)) / 100
                    if price > 0:
                        return {
                            'symbol': symbol,
                            'current_price': price,
                            'change_percent': change
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


def get_market_session() -> str:
    """
    获取当前市场时段
    返回值:
    - 'pre_market': 集合竞价时段 (9:15-9:25)
    - 'morning': 上午交易时段 (9:30-11:30)
    - 'noon_break': 午间休市 (11:30-13:00)
    - 'afternoon': 下午交易时段 (13:00-15:00)
    - 'after_hours': 盘后时段 (15:00-15:30)
    - 'closed': 非交易时间
    """
    now = datetime.now()
    if now.weekday() >= 5:  # 周末
        return 'closed'
    
    current_time = now.strftime("%H:%M")
    
    if "09:15" <= current_time < "09:25":
        return 'pre_market'
    elif "09:25" <= current_time < "09:30":
        return 'pre_market'  # 集合竞价撮合
    elif "09:30" <= current_time <= "11:30":
        return 'morning'
    elif "11:30" < current_time < "13:00":
        return 'noon_break'
    elif "13:00" <= current_time <= "15:00":
        return 'afternoon'
    elif "15:00" < current_time <= "15:30":
        return 'after_hours'
    else:
        return 'closed'


def get_quote_cache_ttl() -> int:
    """
    根据市场时段返回合适的行情缓存时间（秒）
    - 交易时段: 1秒（实时性要求高）
    - 集合竞价: 3秒
    - 午间休市: 30秒
    - 盘后: 300秒
    - 非交易时间: 600秒
    """
    session = get_market_session()
    cache_ttl_map = {
        'pre_market': 3,
        'morning': 1,
        'noon_break': 30,
        'afternoon': 1,
        'after_hours': 300,
        'closed': 600
    }
    return cache_ttl_map.get(session, 60)


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


# ============================================
# 微信公众号推送 (基于 go-wxpush 方案)
# ============================================

# 微信公众号配置
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "wx297904a8025f9431")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")
WECHAT_TEMPLATE_ID = os.environ.get("WECHAT_TEMPLATE_ID", "")  # 通用模板ID（备用）
WECHAT_GH_ID = os.environ.get("WECHAT_GH_ID", "gh_a1d7563f0a6f")
WECHAT_ACCOUNT = os.environ.get("WECHAT_ACCOUNT", "aiautotrade")
WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "aiautotrade2024")  # 微信服务器验证Token

# 分类型推送模板ID配置
# 股票类型模板
WECHAT_TEMPLATE_STOCK_BUY = "Yq-6n5RR-hV7UA3v7iecTdt38nuVPY7gGf4VXcQvte8"   # 股票买入提醒
WECHAT_TEMPLATE_STOCK_SELL = "lxBU9pKpciIqbr9EI2u8bCGedgZhkZmU_ZrTiKqeJz8"  # 股票卖出提醒
# 基金/ETF类型模板
WECHAT_TEMPLATE_FUND_BUY = "5HOy_cjibt1lUUZUZzZdYSUcaFjyyZVBYnNmVSo_YSQ"    # 基金买入提醒
WECHAT_TEMPLATE_FUND_SELL = "i34PuhD8B0w11NXr7zx3lh7ZOUsyxG0fxxfBP8EEt8I"   # 基金卖出提醒


def get_security_type(symbol: str) -> str:
    """根据证券代码判断类型
    返回: 'stock' (股票) 或 'fund' (基金/ETF/LOF)
    """
    if not symbol:
        return 'stock'
    
    # 去除后缀
    pure_code = symbol.replace('.SZ', '').replace('.SS', '').replace('.SH', '').upper()
    
    # 美股代码（字母）默认为股票
    if not pure_code.isdigit():
        return 'stock'
    
    # 6位数字代码判断
    if len(pure_code) == 6:
        # ETF: 51xxxx/52xxxx/56xxxx/58xxxx(上证), 159xxx(深证)
        if pure_code.startswith(('510', '511', '512', '513', '515', '516', '517', '518', '520', '560', '561', '562', '563', '588')) or pure_code.startswith('159'):
            return 'fund'
        # LOF: 16xxxx(深证)
        elif pure_code.startswith('16'):
            return 'fund'
        # 股票: 6xxxxx(上证), 000xxx/001xxx/002xxx/003xxx/300xxx/301xxx/688xxx(深证/创业板/科创板)
        elif pure_code.startswith(('6', '000', '001', '002', '003', '300', '301', '688')):
            return 'stock'
        # 其他6位数字默认为场外基金
        else:
            return 'fund'
    
    return 'stock'


def get_template_id_by_type(symbol: str, alert_type: str) -> str:
    """根据证券代码和操作类型获取对应的模板ID
    
    Args:
        symbol: 证券代码
        alert_type: 操作类型 'buy' 或 'sell'
    
    Returns:
        对应的模板ID
    """
    security_type = get_security_type(symbol)
    
    if security_type == 'fund':
        # 基金/ETF/LOF 类型
        if alert_type == 'buy':
            return WECHAT_TEMPLATE_FUND_BUY
        else:
            return WECHAT_TEMPLATE_FUND_SELL
    else:
        # 股票类型
        if alert_type == 'buy':
            return WECHAT_TEMPLATE_STOCK_BUY
        else:
            return WECHAT_TEMPLATE_STOCK_SELL

# access_token 缓存
_wechat_access_token = None
_wechat_token_expires_at = 0


# ============================================
# 微信公众号消息接收接口
# ============================================

@app.get("/api/wechat/callback")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """微信服务器验证接口"""
    import hashlib
    from fastapi.responses import PlainTextResponse
    
    # 将token、timestamp、nonce三个参数进行字典序排序
    tmp_list = [WECHAT_TOKEN, timestamp, nonce]
    tmp_list.sort()
    tmp_str = "".join(tmp_list)
    
    # 进行sha1加密
    tmp_str = hashlib.sha1(tmp_str.encode()).hexdigest()
    
    print(f"[WeChat] 验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}")
    print(f"[WeChat] 计算签名: {tmp_str}, Token: {WECHAT_TOKEN}")
    
    # 验证签名
    if tmp_str == signature:
        print(f"[WeChat] 验证成功，返回 echostr: {echostr}")
        return PlainTextResponse(content=echostr)
    else:
        print(f"[WeChat] 验证失败")
        return PlainTextResponse(content="验证失败")


@app.post("/api/wechat/callback")
async def wechat_message(request: Request):
    """微信消息接收接口 - 自动回复用户OpenID"""
    import xml.etree.ElementTree as ET
    from fastapi.responses import Response
    
    body = await request.body()
    print(f"[WeChat] 收到消息: {body[:500]}")
    
    try:
        # 解析XML消息
        root = ET.fromstring(body)
        msg_type = root.find("MsgType").text
        from_user = root.find("FromUserName").text  # 用户的OpenID
        to_user = root.find("ToUserName").text  # 公众号原始ID
        
        print(f"[WeChat] 消息类型: {msg_type}, 用户OpenID: {from_user}")
        
        # 构建回复消息
        if msg_type == "event":
            event = root.find("Event").text
            print(f"[WeChat] 事件类型: {event}")
            if event.lower() == "subscribe":
                # 用户关注事件
                reply_content = f"🎉 欢迎关注 AI智能投资提醒！\n\n您的 OpenID 是：\n{from_user}\n\n请复制上方 OpenID 到网站设置中完成绑定，即可接收投资提醒推送。"
            else:
                reply_content = f"您的 OpenID 是：\n{from_user}"
        elif msg_type == "text":
            # 文本消息，回复OpenID
            reply_content = f"您的 OpenID 是：\n{from_user}\n\n请复制上方 OpenID 到网站设置中完成绑定。"
        else:
            reply_content = f"您的 OpenID 是：\n{from_user}"
        
        # 构建XML回复
        import time
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_content}]]></Content>
</xml>"""
        
        print(f"[WeChat] 回复消息: {reply_xml[:200]}")
        return Response(content=reply_xml, media_type="application/xml")
        
    except Exception as e:
        print(f"[WeChat] 消息处理异常: {e}")
        import traceback
        traceback.print_exc()
        return Response(content="success", media_type="text/plain")


def get_wechat_access_token() -> str:
    """获取微信公众号 access_token
    参考 go-wxpush 实现，使用 client_credential 方式获取
    """
    import requests
    import time
    global _wechat_access_token, _wechat_token_expires_at
    
    # 检查缓存是否有效（提前5分钟刷新）
    if _wechat_access_token and time.time() < _wechat_token_expires_at - 300:
        return _wechat_access_token
    
    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        print("[WeChat] AppID 或 AppSecret 未配置")
        return ""
    
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if "access_token" in result:
            _wechat_access_token = result["access_token"]
            # access_token 有效期为 7200 秒
            _wechat_token_expires_at = time.time() + result.get("expires_in", 7200)
            print(f"[WeChat] 获取 access_token 成功")
            return _wechat_access_token
        else:
            print(f"[WeChat] 获取 access_token 失败: {result.get('errmsg', '未知错误')}")
            return ""
    except Exception as e:
        print(f"[WeChat] 获取 access_token 异常: {e}")
        return ""


def send_wechat_template_message(openid: str, title: str, content: str, 
                                  detail_url: str = "", symbol: str = "", 
                                  alert_type: str = "") -> bool:
    """发送微信公众号模板消息
    参考 go-wxpush 的模板消息发送逻辑
    
    Args:
        openid: 用户的微信OpenID
        title: 消息标题
        content: 消息内容
        detail_url: 点击消息跳转的URL
        symbol: 证券代码（用于选择模板）
        alert_type: 操作类型 'buy' 或 'sell'（用于选择模板）
    
    模板格式示例（需要在测试公众号中添加）:
    {{title.DATA}}
    {{content.DATA}}
    {{time.DATA}}
    """
    import requests
    import urllib.parse
    
    if not openid:
        print("[WeChat] OpenID 未配置")
        return False
    
    access_token = get_wechat_access_token()
    if not access_token:
        print("[WeChat] 无法获取 access_token")
        return False
    
    # 根据证券类型和操作类型选择模板ID
    if symbol and alert_type:
        template_id = get_template_id_by_type(symbol, alert_type)
        security_type = get_security_type(symbol)
        type_name = "基金/ETF" if security_type == "fund" else "股票"
        action_name = "买入" if alert_type == "buy" else "卖出"
        print(f"[WeChat] 使用{type_name}{action_name}模板: {template_id}")
    else:
        # 兼容旧调用方式，使用通用模板
        template_id = WECHAT_TEMPLATE_ID
        if not template_id:
            print("[WeChat] 模板ID 未配置")
            return False
    
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
        
        # 构建模板消息数据
        data = {
            "touser": openid,
            "template_id": template_id,
            "url": detail_url,  # 点击消息跳转的URL（跳转到AI分析报告）
            "data": {
                "title": {
                    "value": title,
                    "color": "#173177"
                },
                "content": {
                    "value": content,
                    "color": "#173177"
                },
                "time": {
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "color": "#173177"
                }
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("errcode") == 0:
            print(f"[WeChat] 模板消息推送成功: {title}")
            return True
        else:
            print(f"[WeChat] 模板消息推送失败: {result.get('errmsg', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"[WeChat] 模板消息推送异常: {e}")
        return False


def send_sms_notification(phone: str, message: str) -> bool:
    """发送通知（使用微信推送）
    优先使用微信公众号推送，备用 PushPlus
    """
    return send_wechat_notification(message)


def send_wechat_notification(message: str, title: str = "AI智能投研提醒", token: str = None, openid: str = None) -> bool:
    """发送微信推送通知
    优先使用微信公众号模板消息，备用 PushPlus 服务
    """
    import requests
    
    # 优先使用微信公众号推送
    if openid and WECHAT_APP_SECRET:
        result = send_wechat_template_message(openid, title, message)
        if result:
            return True
        print("[WeChat] 公众号推送失败，尝试 PushPlus 备用方案")
    
    # 备用方案：PushPlus
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
            print(f"[WeChat] PushPlus 推送成功: {title}")
            return True
        else:
            print(f"[WeChat] PushPlus 推送失败: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"[WeChat] PushPlus 推送异常: {e}")
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
                                   target_price: float, ai_summary: str = "",
                                   ai_buy_price: float = None, ai_sell_price: float = None,
                                   ai_buy_quantity: int = None, ai_sell_quantity: int = None) -> bool:
    """发送价格提醒通知（带 AI 分析）
    优先使用微信公众号模板消息推送
    """
    from web.database import get_db, db_add_reminder_log
    import urllib.parse
    
    # 获取用户的推送配置
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pushplus_token, wechat_openid FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        user_token = row['pushplus_token'] if row else None
        user_openid = row['wechat_openid'] if row else None
    
    if not user_token and not user_openid:
        print(f"[Alert] 用户 {username} 未配置推送方式")
        return False
    
    # 构建消息内容
    action = "买入" if alert_type == "buy" else "卖出"
    action_emoji = "📈" if alert_type == "buy" else "📉"
    now = datetime.now()
    trigger_time = now.strftime("%Y年%m月%d日 %H时%M分%S秒")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建技术分析参考价位信息
    ai_price_info = ""
    if ai_buy_price or ai_sell_price:
        ai_price_info = "\n\n【技术分析参考价位】"
        if ai_buy_price:
            ai_price_info += f"\n支撑位：¥{ai_buy_price:.3f}"
            if ai_buy_quantity:
                ai_price_info += f"（参考数量{ai_buy_quantity}股/份）"
        if ai_sell_price:
            ai_price_info += f"\n阻力位：¥{ai_sell_price:.3f}"
            if ai_sell_quantity:
                ai_price_info += f"（参考数量{ai_sell_quantity}股/份）"
        ai_price_info += "\n\n⚠️ 以上价位仅为技术分析参考，不构成任何投资建议"
    
    # 确保 AI 分析内容至少 50 字
    if ai_summary and len(ai_summary) < 50:
        # 补充默认分析内容
        if alert_type == "buy":
            ai_summary = ai_summary + "。当前价格已触及技术分析的支撑位，请自行判断是否进行操作。本提醒不构成任何投资建议。"
        else:
            ai_summary = ai_summary + "。当前价格已触及技术分析的阻力位，请自行判断是否进行操作。本提醒不构成任何投资建议。"
    
    # 如果没有 AI 分析，生成默认内容
    if not ai_summary:
        if alert_type == "buy":
            ai_summary = f"根据技术分析，{name}当前价格已触及设定的支撑位。这仅是价格到达技术参考位置的通知，不构成任何买入建议，请自行判断。"
        else:
            ai_summary = f"根据技术分析，{name}当前价格已触及设定的阻力位。这仅是价格到达技术参考位置的通知，不构成任何卖出建议，请自行判断。"
    
    # 优先使用微信公众号推送
    if user_openid and WECHAT_APP_SECRET:
        # 标题 - 使用中性术语
        action_display = "触及支撑位" if alert_type == "buy" else "触及阻力位"
        title = f"📊 价格提醒"
        
        # 构建完整的消息内容
        content = f"""价格变动提醒
触发时间：{trigger_time}
股票代码：{symbol}
名称：{name}
当前价格：¥{current_price:.3f}

当前价格已{action_display} ¥{target_price:.3f}。{ai_price_info}

技术分析参考：
{ai_summary}

⚠️ 重要声明：本提醒仅为价格到达技术分析参考位置的通知，不构成任何投资建议。任何投资决策请自行判断并承担风险。"""
        
        # 自动检测前端 URL
        frontend_url = os.environ.get("FRONTEND_URL", "").strip()
        if not frontend_url:
            # 尝试从请求头或配置中获取实际域名
            # 默认使用常见的部署地址
            frontend_url = "http://localhost:3000"
            # 检查是否有配置的公网域名
            public_domain = os.environ.get("PUBLIC_DOMAIN", "").strip()
            if public_domain:
                frontend_url = f"https://{public_domain}" if not public_domain.startswith("http") else public_domain
        
        # 构建详情页 URL（使用结构化参数，便于前端解析）
        detail_url = f"{frontend_url}/notify?" + urllib.parse.urlencode({
            'title': title,
            'type': alert_type,
            'symbol': symbol,
            'name': name,
            'price': f"{current_price:.3f}",
            'target': f"{target_price:.3f}",
            'time': time_str,
            'ai': ai_summary
        })
        
        result = send_wechat_template_message(user_openid, title, content, detail_url, symbol, alert_type)
        if result:
            # 记录提醒历史
            db_add_reminder_log(
                username=username,
                symbol=symbol,
                name=name,
                reminder_type=alert_type,
                buy_price=ai_buy_price,
                buy_quantity=ai_buy_quantity,
                sell_price=ai_sell_price,
                sell_quantity=ai_sell_quantity,
                current_price=current_price,
                message=f"触发{action}价格 ¥{target_price:.3f}"
            )
            return True
        print(f"[Alert] 微信公众号推送失败，尝试 PushPlus 备用方案")
    
    # 备用方案：PushPlus（支持富文本）
    if not user_token:
        print(f"[Alert] 用户 {username} 未配置 PushPlus Token")
        return False
    
    action_color = "#10B981" if alert_type == "buy" else "#F43F5E"
    
    # 构建富文本消息
    message = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
            <h2 style="margin: 0; font-size: 18px;">{action_emoji} {action}提醒</h2>
        </div>
        
        <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0;">
            <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="font-size: 12px; color: #64748b; margin-bottom: 10px;">触发时间：{trigger_time}</div>
                <div style="margin-bottom: 10px;">
                    <div style="font-size: 14px; color: #64748b;">股票代码：{symbol}</div>
                    <div style="font-size: 18px; font-weight: bold; color: #1e293b;">名称：{name}</div>
                </div>
                <div style="font-size: 16px; color: {action_color}; font-weight: bold;">当前价格：¥{current_price:.3f}</div>
            </div>
            
            <div style="background: #fef3c7; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="font-size: 14px; color: #92400e;">
                    已经触发AI分析的{action}价格 <strong>¥{target_price:.3f}</strong>，请尽快{action}。
                </div>
            </div>
            
            <div style="background: #eff6ff; border-left: 4px solid #6366f1; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 15px;">
                <div style="font-size: 12px; color: #6366f1; font-weight: bold; margin-bottom: 5px;">AI分析{action}原因：</div>
                <div style="font-size: 13px; color: #334155; line-height: 1.5;">{ai_summary}</div>
            </div>
            
            <div style="font-size: 11px; color: #94a3b8; text-align: center;">
                {now.strftime("%Y-%m-%d %H:%M:%S")} · AI智能投研
            </div>
        </div>
    </div>
    """
    
    result = send_wechat_notification(message, f"【{action}提醒】{name} ¥{current_price:.3f}", user_token)
    if result:
        # 记录提醒历史
        db_add_reminder_log(
            username=username,
            symbol=symbol,
            name=name,
            reminder_type=alert_type,
            buy_price=ai_buy_price,
            buy_quantity=ai_buy_quantity,
            sell_price=ai_sell_price,
            sell_quantity=ai_sell_quantity,
            current_price=current_price,
            message=f"触发{action}价格 ¥{target_price:.3f}"
        )
    return result


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
        cursor.execute("SELECT pushplus_token, wechat_openid FROM users WHERE username = ?", (user['username'],))
        row = cursor.fetchone()
        pushplus_token = row['pushplus_token'] if row else None
        wechat_openid = row['wechat_openid'] if row else None
    
    # 获取剩余推送次数
    remaining_info = get_pushplus_remaining(pushplus_token) if pushplus_token else None
    
    # 检查微信公众号配置状态
    wechat_configured = bool(wechat_openid and WECHAT_APP_SECRET and WECHAT_TEMPLATE_ID)
    
    return {
        "status": "success",
        "settings": {
            "pushplus_token": pushplus_token or "",
            "pushplus_configured": bool(pushplus_token),
            "pushplus_remaining": remaining_info,
            # 微信公众号推送配置
            "wechat_openid": wechat_openid or "",
            "wechat_configured": wechat_configured,
            "wechat_gh_id": WECHAT_GH_ID,
            "wechat_account": WECHAT_ACCOUNT
        }
    }


@app.post("/api/user/settings")
async def update_user_settings(
    pushplus_token: str = Query(default=""),
    wechat_openid: str = Query(default=""),
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
    
    # 验证 OpenID 格式（微信 OpenID 通常以 o 开头，长度约 28 位）
    if wechat_openid and (len(wechat_openid) < 20 or not wechat_openid.startswith('o')):
        raise HTTPException(status_code=400, detail="微信 OpenID 格式不正确")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET pushplus_token = ?, wechat_openid = ? WHERE username = ?",
            (pushplus_token if pushplus_token else None, 
             wechat_openid if wechat_openid else None,
             user['username'])
        )
        conn.commit()
    
    return {
        "status": "success",
        "message": "设置已保存"
    }


@app.post("/api/user/test-push")
async def test_user_push(
    token: str = Query(default=""),
    openid: str = Query(default=""),
    push_type: str = Query(default="auto"),  # auto, wechat, pushplus
    authorization: str = Header(None)
):
    """测试用户的推送配置 - 使用正式模板
    push_type: auto=自动选择, wechat=微信公众号, pushplus=PushPlus
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    auth_token = authorization.replace("Bearer ", "")
    user = get_current_user(auth_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    # 获取已保存的配置
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pushplus_token, wechat_openid FROM users WHERE username = ?", (user['username'],))
        row = cursor.fetchone()
        saved_token = row['pushplus_token'] if row else None
        saved_openid = row['wechat_openid'] if row else None
    
    # 优先使用传入的参数，否则使用已保存的
    pushplus_token = token or saved_token
    wechat_openid = openid or saved_openid
    
    # 测试消息内容
    test_symbol = "000001"
    test_name = "测试标的"
    test_price = 10.888
    test_target = 10.500
    action = "买入"
    
    # 根据 push_type 选择推送方式
    result = False
    used_method = ""
    
    if push_type == "wechat" or (push_type == "auto" and wechat_openid and WECHAT_APP_SECRET):
        # 微信公众号推送
        if not wechat_openid:
            raise HTTPException(status_code=400, detail="请先配置微信 OpenID")
        if not WECHAT_APP_SECRET:
            raise HTTPException(status_code=400, detail="服务端未配置微信公众号 AppSecret")
        if not WECHAT_TEMPLATE_ID:
            raise HTTPException(status_code=400, detail="服务端未配置微信模板ID")
        
        title = f"🔔 {action}价格提醒 [测试]"
        ai_reason = f"这是一条测试消息，用于验证您的微信公众号推送配置是否正常工作。当前系统运行正常，您可以放心使用AI智能投研的价格提醒功能。"
        content = f"""📈 {test_name} ({test_symbol})
当前价格: ¥{test_price:.3f}
目标{action}价: ¥{test_target:.3f}
触发类型: {action}提醒

✅ 推送配置成功！
{ai_reason}"""
        
        # 构建详情页 URL
        import urllib.parse
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip()
        public_domain = os.environ.get("PUBLIC_DOMAIN", "").strip()
        if public_domain and not frontend_url.startswith("http"):
            frontend_url = f"http://{public_domain}"
        
        detail_url = f"{frontend_url}/notify?" + urllib.parse.urlencode({
            'title': title,
            'type': 'buy',
            'symbol': test_symbol,
            'name': test_name,
            'price': f"{test_price:.3f}",
            'target': f"{test_target:.3f}",
            'time': datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
            'ai': ai_reason
        })
        
        # 传入symbol和alert_type以使用正确的模板
        result = send_wechat_template_message(wechat_openid, title, content, detail_url, test_symbol, "buy")
        used_method = "微信公众号"
        
        # 如果微信推送失败，检查access_token
        if not result:
            access_token = get_wechat_access_token()
            if not access_token:
                raise HTTPException(status_code=500, detail="微信公众号推送失败：无法获取access_token，请检查AppID和AppSecret配置")
            else:
                raise HTTPException(status_code=500, detail="微信公众号推送失败：请检查OpenID是否正确，或模板ID是否有效")
    
    elif push_type == "pushplus" or push_type == "auto":
        # PushPlus 推送
        if not pushplus_token:
            raise HTTPException(status_code=400, detail="请先输入或配置 PushPlus Token")
        
        action_color = "#10B981"
        test_message = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">🔔 {action}价格提醒 [测试]</h2>
            </div>
            
            <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #1e293b;">{test_name}</div>
                        <div style="font-size: 14px; color: #64748b;">{test_symbol}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 24px; font-weight: bold; color: {action_color};">¥{test_price:.3f}</div>
                        <div style="font-size: 12px; color: #64748b;">当前价格</div>
                    </div>
                </div>
                
                <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #64748b;">提醒类型</span>
                        <span style="color: {action_color}; font-weight: bold;">触及{action}位</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b;">参考价格</span>
                        <span style="font-weight: bold;">¥{test_target:.3f}</span>
                    </div>
                </div>
                
                <div style="background: #eff6ff; border-left: 4px solid #6366f1; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 15px;">
                    <div style="font-size: 12px; color: #6366f1; font-weight: bold; margin-bottom: 5px;">📊 技术分析说明</div>
                    <div style="font-size: 13px; color: #334155; line-height: 1.5;">这是一条测试消息，用于验证您的推送配置是否正常工作。正式提醒将包含技术分析的参考说明。</div>
                </div>
                
                <div style="background: #fef3c7; border-radius: 8px; padding: 12px; margin-bottom: 15px;">
                    <div style="font-size: 12px; color: #d97706; font-weight: bold;">✅ 推送配置成功</div>
                    <div style="font-size: 13px; color: #92400e; margin-top: 5px;">
                        恭喜！您的微信推送已配置成功。
                    </div>
                </div>
                
                <div style="font-size: 11px; color: #94a3b8; text-align: center;">
                    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · 数据分析学习
                </div>
            </div>
        </div>
        """
        
        result = send_wechat_notification(test_message, f"【{action}提醒】{test_name} ¥{test_price:.3f} [测试]", pushplus_token)
        used_method = "PushPlus"
    
    if result:
        return {"status": "success", "message": f"测试推送已发送（{used_method}），请检查微信"}
    else:
        raise HTTPException(status_code=500, detail=f"推送失败（{used_method}），请检查配置是否正确")


@app.get("/api/wechat/config")
async def get_wechat_config():
    """获取微信公众号配置信息（用于前端展示关注引导）"""
    return {
        "status": "success",
        "config": {
            "gh_id": WECHAT_GH_ID,  # 公众号原始ID
            "account": WECHAT_ACCOUNT,  # 公众号微信号
            "app_id": WECHAT_APP_ID,  # AppID（用于生成关注链接）
            "configured": bool(WECHAT_APP_SECRET and WECHAT_TEMPLATE_ID),  # 服务端是否已配置
            "description": "关注公众号后，发送任意消息获取您的 OpenID"
        }
    }


# ============================================
# 模拟交易 API
# ============================================

class SimTradeRequest(BaseModel):
    """模拟交易请求"""
    symbol: str
    name: str = None
    type: str = None
    price: float
    quantity: int
    holding_period: str = 'swing'


class SimTradeToggleRequest(BaseModel):
    """自动交易开关请求"""
    enabled: bool


@app.get("/api/sim-trade/account")
async def get_sim_trade_account(authorization: str = Header(None)):
    """获取模拟交易账户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.sim_trade import SimTradeEngine
    engine = SimTradeEngine(user['username'])
    account_info = engine.get_account_info()
    
    return {
        "status": "success",
        "data": account_info
    }


@app.post("/api/sim-trade/buy")
async def sim_trade_buy(
    request: SimTradeRequest,
    authorization: str = Header(None)
):
    """模拟买入
    
    注意：本功能仅供学习研究使用，不构成任何投资建议。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.sim_trade import SimTradeEngine
    engine = SimTradeEngine(user['username'])
    
    result = engine.execute_buy(
        symbol=request.symbol.upper(),
        name=request.name or request.symbol,
        type_=request.type or 'stock',
        price=request.price,
        quantity=request.quantity,
        holding_period=request.holding_period
    )
    
    if result['success']:
        # 记录操作
        from web.database import db_add_user_activity
        db_add_user_activity(
            user['username'], 
            'sim_trade_buy', 
            f"模拟买入: {request.symbol} {request.quantity}股 @ {request.price}"
        )
        return {"status": "success", "data": result}
    else:
        raise HTTPException(status_code=400, detail=result['message'])


@app.post("/api/sim-trade/sell")
async def sim_trade_sell(
    request: SimTradeRequest,
    authorization: str = Header(None)
):
    """模拟卖出
    
    注意：本功能仅供学习研究使用，不构成任何投资建议。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.sim_trade import SimTradeEngine
    engine = SimTradeEngine(user['username'])
    
    result = engine.execute_sell(
        symbol=request.symbol.upper(),
        price=request.price,
        quantity=request.quantity if request.quantity > 0 else None
    )
    
    if result['success']:
        # 记录操作
        from web.database import db_add_user_activity
        db_add_user_activity(
            user['username'], 
            'sim_trade_sell', 
            f"模拟卖出: {request.symbol} {result.get('quantity', request.quantity)}股 @ {request.price}, 盈亏: {result.get('profit', 0):.2f}"
        )
        return {"status": "success", "data": result}
    else:
        raise HTTPException(status_code=400, detail=result['message'])


@app.get("/api/sim-trade/positions")
async def get_sim_trade_positions(authorization: str = Header(None)):
    """获取模拟持仓"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import db_get_sim_positions
    positions = db_get_sim_positions(user['username'])
    
    return {
        "status": "success",
        "positions": positions
    }


@app.get("/api/sim-trade/records")
async def get_sim_trade_records(
    symbol: str = None,
    limit: int = 100,
    authorization: str = Header(None)
):
    """获取模拟交易记录"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import db_get_sim_trade_records
    records = db_get_sim_trade_records(user['username'], symbol, limit)
    
    return {
        "status": "success",
        "records": records
    }


@app.get("/api/sim-trade/stats")
async def get_sim_trade_stats(authorization: str = Header(None)):
    """获取模拟交易统计"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import db_get_sim_trade_stats
    stats = db_get_sim_trade_stats(user['username'])
    
    return {
        "status": "success",
        "stats": stats
    }


@app.post("/api/sim-trade/auto-trade/toggle")
async def toggle_auto_trade(
    request: SimTradeToggleRequest,
    authorization: str = Header(None)
):
    """开启/关闭自动交易"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import db_update_sim_account
    success = db_update_sim_account(
        user['username'], 
        auto_trade_enabled=1 if request.enabled else 0
    )
    
    if success:
        # 记录操作
        from web.database import db_add_user_activity
        db_add_user_activity(
            user['username'], 
            'sim_trade_auto_toggle', 
            f"自动交易: {'开启' if request.enabled else '关闭'}"
        )
        return {
            "status": "success", 
            "message": f"自动交易已{'开启' if request.enabled else '关闭'}",
            "auto_trade_enabled": request.enabled
        }
    else:
        raise HTTPException(status_code=500, detail="操作失败")


@app.post("/api/sim-trade/process")
async def process_sim_auto_trade(
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """处理自动交易（根据量化指标自动买卖）
    
    核心逻辑：
    1. 获取实时行情数据
    2. 基于量化指标生成交易信号（纯量化，不使用AI）
    3. 根据高胜率策略执行买卖
    
    注意：本功能仅供学习研究使用，不构成任何投资建议。
    模拟交易结果不代表真实交易表现。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    username = user['username']
    
    # 获取自选列表
    watchlist = get_user_watchlist(username)
    if not watchlist:
        return {"status": "success", "message": "自选列表为空", "trades": []}
    
    symbols = [item['symbol'] for item in watchlist]
    
    # 获取实时行情
    from tools.data_fetcher import get_batch_quotes
    quotes_result = get_batch_quotes(symbols)
    quotes = {}
    if quotes_result.get('status') == 'success':
        for q in quotes_result.get('quotes', []):
            quotes[q['symbol'].upper()] = q
    
    # 使用纯量化指标生成信号（不使用AI，零token消耗）
    signals = {}
    for item in watchlist:
        symbol = item['symbol']
        try:
            # 直接使用量化信号生成器
            signal = generate_quant_signal_fast(symbol, item, quotes.get(symbol.upper(), {}))
            signals[symbol.upper()] = {
                'short': signal,
                'swing': signal,
                'long': signal
            }
        except Exception as e:
            print(f"[SimTrade] 获取 {symbol} 信号失败: {e}")
    
    # 处理自动交易
    from web.sim_trade import process_auto_trade
    results = process_auto_trade(username, signals, quotes, watchlist)
    
    return {
        "status": "success",
        "message": f"处理完成，执行了 {len(results)} 笔交易",
        "trades": results,
        "signal_source": "quant_indicators",  # 标记信号来源是量化指标
        "disclaimer": "本功能仅供学习研究使用，不构成任何投资建议。"
    }


def generate_quant_signal_fast(symbol: str, watchlist_item: Dict, quote: Dict) -> Dict:
    """
    快速生成量化交易信号 v2.0（纯量化指标，不使用AI）
    
    核心逻辑：
    1. 基于价格与支撑位/阻力位的关系
    2. 基于涨跌幅和成交量
    3. 基于自选列表中保存的技术指标数据
    4. 高胜率策略：严格的入场条件
    
    这是一个轻量级的信号生成器，用于自动交易
    目标：95%+胜率
    """
    current_price = quote.get('current_price', 0)
    if current_price <= 0:
        return {'signal_type': 'hold', 'signal': 'hold', 'strength': 0, 'confidence': 0}
    
    # 获取支撑位和阻力位
    holding_period = watchlist_item.get('holding_period', 'swing')
    support_price = watchlist_item.get(f'{holding_period}_support') or watchlist_item.get('ai_buy_price', 0)
    resistance_price = watchlist_item.get(f'{holding_period}_resistance') or watchlist_item.get('ai_sell_price', 0)
    
    # 获取涨跌幅和成交量
    change_pct = quote.get('change_percent', 0)
    volume_ratio = quote.get('volume_ratio', 1)  # 量比
    
    # 初始化信号
    buy_score = 0
    sell_score = 0
    conditions = []
    veto_reasons = []  # 一票否决原因
    
    # ========== 一票否决条件（高胜率核心）==========
    # 1. 大跌超过5%不买
    if change_pct <= -5:
        veto_reasons.append(f"大跌{change_pct:.1f}%，不抄底")
    
    # 2. 大涨超过7%不追
    if change_pct >= 7:
        veto_reasons.append(f"大涨{change_pct:.1f}%，不追高")
    
    # 3. 远离支撑位超过10%不买
    if support_price and support_price > 0:
        pct_from_support = (current_price / support_price - 1) * 100
        if pct_from_support > 10:
            veto_reasons.append(f"远离支撑位{pct_from_support:.1f}%")
    
    # 4. 接近阻力位不买（距离<3%）
    if resistance_price and resistance_price > 0:
        pct_to_resistance = (resistance_price / current_price - 1) * 100
        if pct_to_resistance < 3:
            veto_reasons.append(f"接近阻力位{pct_to_resistance:.1f}%")
    
    # 5. 量化评分太低不买
    quant_score = watchlist_item.get('quant_score', 50)
    if quant_score < 40:
        veto_reasons.append(f"量化评分过低({quant_score})")
    
    # 如果有一票否决条件，直接返回观望
    if veto_reasons:
        return {
            'signal_type': 'hold',
            'signal': 'hold',
            'strength': 0,
            'confidence': 0,
            'triggered_conditions': veto_reasons,
            'buy_score': 0,
            'sell_score': 0,
            'veto': True
        }
    
    # ========== 价格位置分析（高胜率核心）==========
    # 1. 支撑位分析 - 必须接近支撑位才买
    if support_price and support_price > 0:
        pct_from_support = (current_price / support_price - 1) * 100
        if pct_from_support <= 1.5:
            # 完美位置：接近支撑位1.5%以内
            buy_score += 4
            conditions.append(f"✅ 完美接近支撑位({pct_from_support:.1f}%)")
        elif pct_from_support <= 3:
            buy_score += 3
            conditions.append(f"✅ 支撑位上方({pct_from_support:.1f}%)")
        elif pct_from_support <= 5:
            buy_score += 1
            conditions.append(f"⚠️ 距支撑位较远({pct_from_support:.1f}%)")
        else:
            # 远离支撑位，减分
            sell_score += 1
            conditions.append(f"❌ 远离支撑位({pct_from_support:.1f}%)")
    
    # 2. 阻力位分析
    if resistance_price and resistance_price > 0:
        pct_to_resistance = (resistance_price / current_price - 1) * 100
        if pct_to_resistance >= 10:
            # 远离阻力位，有上涨空间
            buy_score += 2
            conditions.append(f"✅ 远离阻力位({pct_to_resistance:.1f}%)")
        elif pct_to_resistance >= 5:
            buy_score += 1
            conditions.append(f"✅ 阻力位较远({pct_to_resistance:.1f}%)")
        elif pct_to_resistance < 3:
            # 接近阻力位，卖出信号
            sell_score += 3
            conditions.append(f"❌ 接近阻力位({pct_to_resistance:.1f}%)")
    
    # ========== 涨跌幅分析 ==========
    if change_pct <= -3 and change_pct > -5:
        # 适度下跌，可能是买入机会（如果在支撑位附近）
        if support_price and current_price <= support_price * 1.02:
            buy_score += 3
            conditions.append(f"✅ 回调至支撑位(跌{change_pct:.1f}%)")
        else:
            conditions.append(f"⚠️ 下跌中(跌{change_pct:.1f}%)")
    elif change_pct >= 5 and change_pct < 7:
        # 涨幅较大，考虑止盈
        sell_score += 2
        conditions.append(f"⚠️ 涨幅较大(涨{change_pct:.1f}%)")
    elif change_pct >= 3:
        # 小涨，观察
        sell_score += 1
        conditions.append(f"涨幅适中(涨{change_pct:.1f}%)")
    elif -1 <= change_pct <= 1:
        # 横盘，适合观察
        conditions.append(f"横盘整理({change_pct:+.1f}%)")
    
    # ========== 量比分析 ==========
    if volume_ratio > 0:
        if volume_ratio >= 2:
            # 放量，需要结合涨跌判断
            if change_pct > 0:
                buy_score += 1
                conditions.append(f"✅ 放量上涨(量比{volume_ratio:.1f})")
            else:
                sell_score += 2
                conditions.append(f"❌ 放量下跌(量比{volume_ratio:.1f})")
        elif volume_ratio >= 1.2:
            conditions.append(f"温和放量(量比{volume_ratio:.1f})")
        elif volume_ratio < 0.7:
            conditions.append(f"缩量(量比{volume_ratio:.1f})")
    
    # ========== 量化评分参考 ==========
    if quant_score >= 75:
        buy_score += 3
        conditions.append(f"✅ 量化评分优秀({quant_score})")
    elif quant_score >= 65:
        buy_score += 2
        conditions.append(f"✅ 量化评分良好({quant_score})")
    elif quant_score >= 55:
        buy_score += 1
        conditions.append(f"量化评分中等({quant_score})")
    elif quant_score <= 40:
        sell_score += 2
        conditions.append(f"❌ 量化评分较低({quant_score})")
    elif quant_score <= 50:
        sell_score += 1
        conditions.append(f"⚠️ 量化评分偏低({quant_score})")
    
    # ========== 生成最终信号（高胜率版本）==========
    score_diff = buy_score - sell_score
    
    # 高胜率策略：提高买入门槛
    if score_diff >= 6:
        signal_type = 'buy'
        strength = 5
        confidence = 95
    elif score_diff >= 5:
        signal_type = 'buy'
        strength = 4
        confidence = 90
    elif score_diff >= 4:
        signal_type = 'buy'
        strength = 4
        confidence = 85
    elif score_diff <= -5:
        signal_type = 'sell'
        strength = 5
        confidence = 95
    elif score_diff <= -4:
        signal_type = 'sell'
        strength = 4
        confidence = 90
    elif score_diff <= -3:
        signal_type = 'sell'
        strength = 4
        confidence = 85
    else:
        # 不满足高胜率条件，观望
        signal_type = 'hold'
        strength = 0
        confidence = 50
    
    return {
        'signal_type': signal_type,
        'signal': signal_type,
        'strength': strength,
        'confidence': confidence,
        'triggered_conditions': conditions,
        'buy_score': buy_score,
        'sell_score': sell_score,
        'score_diff': score_diff
    }


@app.post("/api/sim-trade/update-prices")
async def update_sim_positions_prices(authorization: str = Header(None)):
    """更新持仓的当前价格"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    from web.database import db_get_sim_positions
    from web.sim_trade import SimTradeEngine
    
    positions = db_get_sim_positions(user['username'])
    if not positions:
        return {"status": "success", "message": "没有持仓"}
    
    symbols = [p['symbol'] for p in positions]
    
    # 获取实时行情
    from tools.data_fetcher import get_batch_quotes
    quotes_result = get_batch_quotes(symbols)
    quotes = {}
    if quotes_result.get('status') == 'success':
        for q in quotes_result.get('quotes', []):
            quotes[q['symbol'].upper()] = q
    
    # 更新价格
    engine = SimTradeEngine(user['username'])
    engine.update_positions_price(quotes)
    
    return {
        "status": "success",
        "message": f"已更新 {len(positions)} 个持仓的价格"
    }


@app.post("/api/sim-trade/reset")
async def reset_sim_account(authorization: str = Header(None)):
    """重置模拟账户（清空持仓和交易记录，恢复初始资金）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    username = user['username']
    
    from web.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        # 删除持仓
        cursor.execute('DELETE FROM sim_trade_positions WHERE username = ?', (username,))
        # 删除交易记录
        cursor.execute('DELETE FROM sim_trade_records WHERE username = ?', (username,))
        # 重置账户
        cursor.execute('''
            UPDATE sim_trade_accounts 
            SET current_capital = initial_capital,
                total_profit = 0,
                total_profit_pct = 0,
                win_count = 0,
                loss_count = 0,
                win_rate = 0
            WHERE username = ?
        ''', (username,))
        conn.commit()
    
    # 记录操作
    from web.database import db_add_user_activity
    db_add_user_activity(username, 'sim_trade_reset', '重置模拟账户')
    
    return {
        "status": "success",
        "message": "模拟账户已重置"
    }


# ============================================
# 启动服务
# ============================================

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 Web 服务"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
