#!/bin/bash
# ============================================
# AI Trade 一键部署脚本
# 用法: bash scripts/deploy.sh
# ============================================

set -e

echo "=========================================="
echo "AI Trade 部署脚本"
echo "=========================================="

cd /root/trade

# 1. 拉取最新代码
echo "[1/5] 拉取最新代码..."
git fetch --all
git reset --hard origin/main

# 2. 停止旧的本地API进程
echo "[2/5] 停止旧API进程..."
pkill -f "uvicorn web.api:app" || true
sleep 2

# 3. 安装/更新依赖（仅在需要时）
echo "[3/5] 检查并安装依赖..."
pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt

# 4. 验证导入
echo "[4/5] 验证代码..."
python -c "from web import api; print('代码验证通过')" 2>&1 | tail -1

# 5. 启动API服务
echo "[5/5] 启动API服务..."
nohup python -m uvicorn web.api:app --host 0.0.0.0 --port 6066 > /root/trade/api.log 2>&1 &

# 等待启动
sleep 3

# 检查状态
if pgrep -f "uvicorn web.api:app" > /dev/null; then
    echo "=========================================="
    echo "✅ 部署成功!"
    echo "API地址: http://localhost:6066"
    echo "日志文件: /root/trade/api.log"
    echo "=========================================="
    
    # 健康检查
    curl -s http://localhost:6066/api/health | python -m json.tool 2>/dev/null || echo "健康检查完成"
else
    echo "=========================================="
    echo "❌ 部署失败，请检查日志:"
    echo "tail -50 /root/trade/api.log"
    echo "=========================================="
    exit 1
fi
