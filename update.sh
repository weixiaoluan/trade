#!/bin/bash

# ============================================
# AI 证券分析系统 - 更新与重启脚本
# 功能：拉取最新代码 -> 配置 Nginx -> 重启服务
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== 开始更新 AI 证券分析系统 ===${NC}"

# 1. 更新代码
echo -e "${YELLOW}正在拉取最新代码...${NC}"
git fetch --all
git reset --hard origin/main

# 2. 配置 Nginx
echo -e "${YELLOW}正在更新 Nginx 配置...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}未检测到 Nginx，正在安装...${NC}"
    if [ -f /etc/redhat-release ]; then
        # 关键修复：使用 --nogpgcheck 跳过 GPG 密钥检查
        yum install -y nginx --nogpgcheck
        systemctl enable nginx
    else
        apt-get install -y nginx
    fi
fi

# 复制配置文件
cp nginx.conf /etc/nginx/conf.d/ai-trade.conf

# 检查配置并重启 Nginx
echo -e "${YELLOW}检查 Nginx 配置...${NC}"
nginx -t
if [ $? -eq 0 ]; then
    systemctl restart nginx
    echo -e "${GREEN}Nginx 重启成功${NC}"
else
    echo -e "${RED}Nginx 配置检查失败，请查看错误日志${NC}"
    exit 1
fi

# 3. 重启 Docker 服务
echo -e "${YELLOW}正在重建并重启 Docker 服务...${NC}"
if docker compose version &> /dev/null; then
    docker compose down
    docker compose up -d --build
elif command -v docker-compose &> /dev/null; then
    docker-compose down
    docker-compose up -d --build
else
    echo -e "${RED}未找到 docker compose，请先运行 easy_deploy.sh 安装环境${NC}"
    exit 1
fi

# 4. 完成
echo -e "${GREEN}=== 更新完成 ===${NC}"
echo -e "域名访问: http://etf.flytest.com.cn"
echo -e "前端直连: http://$(hostname -I | awk '{print $1}'):8088"
echo -e "后端直连: http://$(hostname -I | awk '{print $1}'):8000"
echo -e ""
echo -e "查看日志: docker compose logs -f"
