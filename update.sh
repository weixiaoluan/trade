#!/bin/bash

# ============================================
# AI 证券分析系统 - 更新与重启脚本
# 功能：拉取最新代码 -> 自动清理空间 -> 重启服务
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 最小磁盘空间要求 (MB)
MIN_DISK_SPACE=2000

echo -e "${GREEN}=== 开始更新 AI 证券分析系统 ===${NC}"

# 检查磁盘空间函数
check_disk_space() {
    AVAILABLE_SPACE=$(df -m / | awk 'NR==2 {print $4}')
    echo -e "${BLUE}[INFO]${NC} 当前可用磁盘空间: ${AVAILABLE_SPACE}MB"
    
    if [ "$AVAILABLE_SPACE" -lt "$MIN_DISK_SPACE" ]; then
        return 1
    fi
    return 0
}

# 清理 Docker 缓存函数
cleanup_docker() {
    echo -e "${YELLOW}[CLEANUP]${NC} 磁盘空间不足，开始清理 Docker 缓存..."
    
    # 清理未使用的镜像
    echo -e "${BLUE}[INFO]${NC} 清理未使用的 Docker 镜像..."
    docker image prune -a -f 2>/dev/null || true
    
    # 清理构建缓存
    echo -e "${BLUE}[INFO]${NC} 清理 Docker 构建缓存..."
    docker builder prune -a -f 2>/dev/null || true
    
    # 清理未使用的容器
    echo -e "${BLUE}[INFO]${NC} 清理已停止的容器..."
    docker container prune -f 2>/dev/null || true
    
    # 清理未使用的网络
    echo -e "${BLUE}[INFO]${NC} 清理未使用的网络..."
    docker network prune -f 2>/dev/null || true
    
    # 清理日志文件
    echo -e "${BLUE}[INFO]${NC} 清理 Docker 容器日志..."
    find /var/lib/docker/containers/ -name "*-json.log" -exec truncate -s 0 {} \; 2>/dev/null || true
    
    # 显示清理后的空间
    AVAILABLE_SPACE=$(df -m / | awk 'NR==2 {print $4}')
    echo -e "${GREEN}[SUCCESS]${NC} 清理完成，当前可用空间: ${AVAILABLE_SPACE}MB"
}

# 1. 检查磁盘空间，必要时清理
echo -e "${BLUE}[INFO]${NC} 检查磁盘空间..."
if ! check_disk_space; then
    cleanup_docker
    
    # 再次检查
    if ! check_disk_space; then
        echo -e "${RED}[ERROR]${NC} 磁盘空间仍然不足 (需要至少 ${MIN_DISK_SPACE}MB)"
        echo -e "${YELLOW}[TIP]${NC} 请手动清理磁盘空间后重试"
        exit 1
    fi
fi

# 2. 更新代码
echo -e "${YELLOW}正在拉取最新代码...${NC}"
git fetch --all
git reset --hard origin/main

# 3. 配置 Nginx（如果存在配置文件）
if [ -f nginx.conf ]; then
    echo -e "${YELLOW}正在更新 Nginx 配置...${NC}"
    if command -v nginx &> /dev/null; then
        cp nginx.conf /etc/nginx/conf.d/ai-trade.conf
        nginx -t && systemctl restart nginx
        echo -e "${GREEN}Nginx 重启成功${NC}"
    fi
fi

# 4. 重启 Docker 服务（带重试机制）
echo -e "${YELLOW}正在重建并重启 Docker 服务...${NC}"

build_and_start() {
    if docker compose version &> /dev/null; then
        docker compose up -d --build
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        echo -e "${RED}未找到 docker compose，请先运行 easy_deploy.sh 安装环境${NC}"
        exit 1
    fi
}

# 第一次尝试构建
if ! build_and_start 2>&1; then
    echo -e "${YELLOW}[RETRY]${NC} 构建失败，尝试清理后重新构建..."
    cleanup_docker
    
    # 第二次尝试
    if ! build_and_start 2>&1; then
        echo -e "${RED}[ERROR]${NC} 构建失败，请检查错误信息"
        exit 1
    fi
fi

# 5. 清理旧镜像（构建成功后）
echo -e "${BLUE}[INFO]${NC} 清理旧版本镜像..."
docker image prune -f 2>/dev/null || true

# 6. 完成
echo -e "${GREEN}=== 更新完成 ===${NC}"
echo -e "域名访问: http://etf.flytest.com.cn"
echo -e "前端直连: http://$(hostname -I | awk '{print $1}'):8088"
echo -e "后端直连: http://$(hostname -I | awk '{print $1}'):8000"
echo -e ""
echo -e "查看日志: docker compose logs -f"

# 显示最终磁盘空间
FINAL_SPACE=$(df -h / | awk 'NR==2 {print $4}')
echo -e "${BLUE}[INFO]${NC} 当前可用磁盘空间: ${FINAL_SPACE}"
