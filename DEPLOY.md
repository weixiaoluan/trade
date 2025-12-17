# AI 证券分析系统 - Linux 部署指南

## 快速部署

### 方式一：一键部署脚本（推荐）

```bash
# 1. 上传项目到服务器
scp -r ./Ai-trade root@your-server:/tmp/

# 2. 登录服务器
ssh root@your-server

# 3. 执行部署脚本
cd /tmp/Ai-trade
chmod +x deploy.sh
sudo bash deploy.sh
```

### 方式二：手动部署

#### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
apt update
apt install -y python3.11 python3.11-venv python3-pip nodejs npm git
npm install -g pm2
```

**CentOS/RHEL:**
```bash
yum install -y python3 python3-pip nodejs npm git
npm install -g pm2
```

#### 2. 部署项目

```bash
# 创建项目目录
mkdir -p /opt/ai-trade
cd /opt/ai-trade

# 复制项目文件（或 git clone）
cp -r /path/to/project/* .

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 安装前端依赖
cd frontend
npm install
npm run build
cd ..
```

#### 3. 配置环境变量

```bash
# 编辑 .env 文件
nano /opt/ai-trade/.env
```

添加以下内容：
```env
# SiliconFlow API 密钥（必填）
SILICONFLOW_API_KEY=your_api_key_here

# Google Gemini API 密钥（可选）
GOOGLE_API_KEY=your_google_api_key_here

# 默认 LLM 提供商
DEFAULT_LLM_PROVIDER=siliconflow
```

#### 4. 启动服务

```bash
# 使用 PM2 启动
pm2 start ecosystem.config.js

# 设置开机自启
pm2 save
pm2 startup
```

## 服务管理

部署完成后，可使用以下命令管理服务：

```bash
# 查看服务状态
ai-trade status
# 或
pm2 status

# 查看日志
ai-trade logs
# 或
pm2 logs

# 重启服务
ai-trade restart
# 或
pm2 restart all

# 停止服务
ai-trade stop
# 或
pm2 stop all

# 更新代码并重启
ai-trade update
```

## 访问地址

- **前端界面**: http://your-server-ip:3000
- **后端 API**: http://your-server-ip:8000
- **API 文档**: http://your-server-ip:8000/docs

## 端口配置

默认端口：
- 后端: 8000
- 前端: 3000

如需修改端口，编辑 `/opt/ai-trade/ecosystem.config.js`

## 防火墙配置

**Ubuntu/Debian (ufw):**
```bash
ufw allow 3000/tcp
ufw allow 8000/tcp
```

**CentOS/RHEL (firewalld):**
```bash
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

## Nginx 反向代理配置（可选）

如果需要通过域名访问，可配置 Nginx 反向代理：

```nginx
# /etc/nginx/sites-available/ai-trade
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

## 日志位置

- 后端日志: `/opt/ai-trade/logs/backend-*.log`
- 前端日志: `/opt/ai-trade/logs/frontend-*.log`
- PM2 日志: `~/.pm2/logs/`

## 常见问题

### 1. 前端构建失败
```bash
cd /opt/ai-trade/frontend
rm -rf node_modules
npm install
npm run build
```

### 2. Python 依赖安装失败
```bash
cd /opt/ai-trade
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 服务无法访问
- 检查防火墙是否开放端口
- 检查服务是否正常运行: `pm2 status`
- 查看错误日志: `pm2 logs`

### 4. API 调用失败
- 确保 `.env` 文件中配置了正确的 API 密钥
- 检查网络是否能访问 LLM API 服务

## 系统要求

- **操作系统**: Ubuntu 20.04+, Debian 10+, CentOS 7+, RHEL 7+
- **内存**: 最少 2GB，推荐 4GB+
- **CPU**: 2核+
- **磁盘**: 10GB+
- **Python**: 3.10+
- **Node.js**: 18+

## 技术支持

如有问题，请提交 Issue 或联系开发者。
