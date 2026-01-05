#!/bin/bash

# ============================================
# AI 证券分析系统 - Docker 一键部署脚本
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

echo -e "${GREEN}=== 开始部署 AI 证券分析系统 ===${NC}"

# 检查磁盘空间函数
check_disk_space() {
    # 获取根分区可用空间 (MB)
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
    
    # 清理未使用的卷（谨慎，可能删除数据）
    # docker volume prune -f 2>/dev/null || true
    
    # 清理日志文件
    echo -e "${BLUE}[INFO]${NC} 清理 Docker 容器日志..."
    find /var/lib/docker/containers/ -name "*-json.log" -exec truncate -s 0 {} \; 2>/dev/null || true
    
    # 显示清理后的空间
    AVAILABLE_SPACE=$(df -m / | awk 'NR==2 {print $4}')
    echo -e "${GREEN}[SUCCESS]${NC} 清理完成，当前可用空间: ${AVAILABLE_SPACE}MB"
}

# 1. 检查 Docker 环境
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}未检测到 Docker，正在安装...${NC}"
    
    # 检测是否为 CentOS/RHEL
    if [ -f /etc/redhat-release ]; then
        echo -e "${YELLOW}检测到 CentOS/RHEL 系统，使用 yum 安装...${NC}"
        # 安装工具
        yum install -y yum-utils
        
        # 使用阿里云镜像源（国内更稳定）
        yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
        
        # 安装 Docker (使用 --nogpgcheck 避免 GPG Key 验证卡住)
        echo -e "${YELLOW}正在安装 Docker 软件包...${NC}"
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin --nogpgcheck
    else
        # 其他系统使用官方脚本
        echo -e "${YELLOW}使用官方脚本安装...${NC}"
        curl -fsSL https://get.docker.com | bash
    fi
    
    # 启动 Docker
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}Docker 安装完成${NC}"
else
    echo -e "${GREEN}Docker 已安装${NC}"
fi

# 2. 检查磁盘空间，必要时清理
echo -e "${BLUE}[INFO]${NC} 检查磁盘空间..."
if ! check_disk_space; then
    cleanup_docker
    
    # 再次检查
    if ! check_disk_space; then
        echo -e "${RED}[ERROR]${NC} 磁盘空间仍然不足 (需要至少 ${MIN_DISK_SPACE}MB)"
        echo -e "${YELLOW}[TIP]${NC} 请手动清理磁盘空间后重试"
        echo -e "  可尝试: du -sh /* 2>/dev/null | sort -hr | head -20"
        exit 1
    fi
fi

# 3. 检查代码更新
echo -e "${YELLOW}正在拉取最新代码...${NC}"
git pull origin main || echo -e "${RED}拉取代码失败，请检查网络或 git 配置${NC}"

# 4. 配置文件处理
if [ ! -f .env ]; then
    echo -e "${YELLOW}未发现配置文件，从示例创建 .env...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}已创建 .env 文件，请稍后修改 API KEY${NC}"
    else
        echo -e "${RED}未找到 .env.example，跳过配置创建${NC}"
    fi
fi

# 5. 启动服务（带重试机制）
echo -e "${YELLOW}正在构建并启动服务...${NC}"

build_and_start() {
    if docker compose version &> /dev/null; then
        docker compose up -d --build
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        echo -e "${RED}未找到 docker compose 插件，尝试安装...${NC}"
        apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
        docker compose up -d --build
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

# 6. 清理旧镜像（构建成功后）
echo -e "${BLUE}[INFO]${NC} 清理旧版本镜像..."
docker image prune -f 2>/dev/null || true

# 7. 检查状态
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo -e "服务正在启动中，请使用以下命令查看日志："
echo -e "docker compose logs -f"
echo -e ""
echo -e "后端 API: http://localhost:8000"
echo -e "前端页面: http://localhost:8088"
echo -e "${YELLOW}注意：请确保防火墙已开放 8000 和 8088 端口${NC}"

# 显示最终磁盘空间
FINAL_SPACE=$(df -h / | awk 'NR==2 {print $4}')
echo -e "${BLUE}[INFO]${NC} 当前可用磁盘空间: ${FINAL_SPACE}"
