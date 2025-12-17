# AI 证券分析系统 - Docker 部署指南

本指南介绍如何使用 Docker 快速部署 AI 证券分析系统。这种方式避免了复杂的依赖安装和编译问题。

## 前置要求

- 只需要一台安装了 Linux 的服务器（Ubuntu/CentOS/Debian 均可）
- Git

## 快速部署

1. **克隆代码**（如果还没克隆）
   ```bash
   git clone https://github.com/weixiaoluan/trade.git
   cd trade
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 API KEY
   vi .env
   ```

3. **一键启动**
   ```bash
   chmod +x easy_deploy.sh
   ./easy_deploy.sh
   ```
   该脚本会自动：
   - 安装 Docker（如果没有）
   - 拉取最新代码
   - 构建并启动所有服务

## 手动管理

如果不使用脚本，也可以使用标准的 Docker 命令：

```bash
# 启动
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止
docker compose down

# 重启
docker compose restart
```

## 端口说明

- **前端页面**: http://服务器IP:8088
- **后端 API**: http://服务器IP:8000

## 常见问题

1. **Docker 安装失败**
   如果脚本无法安装 Docker，请参考 [Docker 官方文档](https://docs.docker.com/engine/install/) 手动安装。

2. **端口冲突**
   如果 8088 或 8000 端口被占用，请修改 `docker-compose.yml` 中的 `ports` 映射。

3. **修改代码后不生效**
   修改代码后需要重新构建镜像：
   ```bash
   docker compose up -d --build
   ```
