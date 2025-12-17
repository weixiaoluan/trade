#!/bin/bash

# ============================================
# AI 证券分析系统 - Docker 一键部署脚本
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== 开始部署 AI 证券分析系统 ===${NC}"

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

# 2. 检查代码更新
echo -e "${YELLOW}正在拉取最新代码...${NC}"
git pull origin main || echo -e "${RED}拉取代码失败，请检查网络或 git 配置${NC}"

# 3. 配置文件处理
if [ ! -f .env ]; then
    echo -e "${YELLOW}未发现配置文件，从示例创建 .env...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}已创建 .env 文件，请稍后修改 API KEY${NC}"
    else
        echo -e "${RED}未找到 .env.example，跳过配置创建${NC}"
    fi
fi

# 4. 启动服务
echo -e "${YELLOW}正在构建并启动服务...${NC}"
# 尝试使用新版 docker compose 命令，如果失败尝试旧版 docker-compose
if docker compose version &> /dev/null; then
    docker compose up -d --build
elif command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    echo -e "${RED}未找到 docker compose 插件，尝试安装...${NC}"
    # 简单的尝试安装 docker-compose plugin
    apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
    docker compose up -d --build
fi

# 5. 检查状态
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo -e "服务正在启动中，请使用以下命令查看日志："
echo -e "docker compose logs -f"
echo -e ""
echo -e "后端 API: http://localhost:8000"
echo -e "前端页面: http://localhost:8088"
echo -e "${YELLOW}注意：请确保防火墙已开放 8000 和 8088 端口${NC}"
