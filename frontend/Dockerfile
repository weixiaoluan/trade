# ============================================
# AI 证券分析系统 - 前端 Docker 镜像
# 优化构建速度：利用缓存层
# ============================================

FROM node:20-alpine AS builder

WORKDIR /app

# 1. 先只复制 package 文件（利用缓存）
COPY package*.json ./

# 2. 安装依赖（只有 package.json 变化时才重新安装）
RUN npm ci --prefer-offline

# 3. 复制源代码
COPY . .

# 4. 构建生产版本
RUN npm run build

# ============================================
# 生产镜像（更小）
# ============================================

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# 只复制运行时必要的文件
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# 暴露端口
EXPOSE 3000

# 启动命令（使用 standalone 模式）
CMD ["node", "server.js"]
