# ============================================
# AI 证券分析系统 - Docker 镜像
# ============================================

FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ============================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 复制构建好的前端
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json ./frontend/package.json

# 暴露端口
EXPOSE 8000 3000

# 创建启动脚本
RUN echo '#!/bin/bash\n\
cd /app && python -m uvicorn web.api:app --host 0.0.0.0 --port 8000 &\n\
cd /app/frontend && npm start &\n\
wait' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
