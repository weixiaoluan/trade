#!/bin/bash

# ============================================
# AI 证券分析系统 - Linux 一键部署脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="ai-trade"
APP_DIR="/opt/${APP_NAME}"
BACKEND_PORT=8000
FRONTEND_PORT=3000
PYTHON_VERSION="3.11"
NODE_VERSION="20"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo bash deploy.sh"
        exit 1
    fi
}

# 检测系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        OS_ID=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi
    log_info "检测到操作系统: $OS $VERSION"
}

# 安装系统依赖 - Ubuntu/Debian
install_deps_debian() {
    log_info "更新软件包列表..."
    apt-get update -y

    log_info "安装基础依赖..."
    apt-get install -y \
        curl \
        wget \
        git \
        build-essential \
        software-properties-common \
        ca-certificates \
        gnupg \
        lsb-release

    # 安装 Python
    log_info "安装 Python ${PYTHON_VERSION}..."
    apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev python3-pip
    
    # 设置 Python 默认版本
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 || true
    
    # 安装 Node.js
    log_info "安装 Node.js ${NODE_VERSION}..."
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
        apt-get install -y nodejs
    fi

    # 安装 PM2
    log_info "安装 PM2 进程管理器..."
    npm install -g pm2
}

# 安装系统依赖 - CentOS/RHEL/AlmaLinux
install_deps_rhel() {
    log_info "更新软件包列表..."
    yum update -y

    log_info "安装基础依赖..."
    yum install -y \
        curl \
        wget \
        git \
        gcc \
        gcc-c++ \
        make \
        openssl-devel \
        bzip2-devel \
        libffi-devel \
        zlib-devel

    # 安装 Python
    log_info "安装 Python ${PYTHON_VERSION}..."
    yum install -y python3 python3-pip python3-devel || {
        # 如果默认仓库没有，尝试编译安装
        log_info "从源码编译安装 Python..."
        cd /tmp
        wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz
        tar xzf Python-3.11.0.tgz
        cd Python-3.11.0
        ./configure --enable-optimizations
        make altinstall
        cd -
    }

    # 安装 Node.js
    log_info "安装 Node.js ${NODE_VERSION}..."
    if ! command -v node &> /dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_${NODE_VERSION}.x | bash -
        yum install -y nodejs
    fi

    # 安装 PM2
    log_info "安装 PM2 进程管理器..."
    npm install -g pm2
}

# 安装系统依赖
install_system_deps() {
    case $OS_ID in
        ubuntu|debian)
            install_deps_debian
            ;;
        centos|rhel|almalinux|rocky)
            install_deps_rhel
            ;;
        *)
            log_error "不支持的操作系统: $OS_ID"
            log_info "支持的系统: Ubuntu, Debian, CentOS, RHEL, AlmaLinux, Rocky Linux"
            exit 1
            ;;
    esac
}

# 创建应用目录
setup_app_dir() {
    log_info "设置应用目录: ${APP_DIR}"
    
    if [ -d "${APP_DIR}" ]; then
        log_warn "应用目录已存在，将备份旧版本..."
        mv "${APP_DIR}" "${APP_DIR}.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    mkdir -p "${APP_DIR}"
    
    # 复制项目文件
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    log_info "从 ${SCRIPT_DIR} 复制项目文件..."
    
    cp -r "${SCRIPT_DIR}"/* "${APP_DIR}/"
    
    # 设置权限
    chown -R root:root "${APP_DIR}"
    chmod -R 755 "${APP_DIR}"
}

# 设置 Python 虚拟环境和依赖
setup_python_env() {
    log_info "创建 Python 虚拟环境..."
    cd "${APP_DIR}"
    
    python3 -m venv venv
    source venv/bin/activate
    
    log_info "升级 pip..."
    pip install --upgrade pip
    
    log_info "安装 Python 依赖..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        # 如果没有 requirements.txt，安装核心依赖
        pip install \
            fastapi \
            uvicorn[standard] \
            httpx \
            openai \
            pandas \
            numpy \
            python-dotenv \
            aiohttp \
            pydantic
    fi
    
    deactivate
    log_success "Python 环境设置完成"
}

# 设置前端依赖
setup_frontend() {
    log_info "安装前端依赖..."
    cd "${APP_DIR}/frontend"
    
    npm install
    
    log_info "构建前端生产版本..."
    npm run build || log_warn "前端构建失败，将使用开发模式运行"
    
    log_success "前端设置完成"
}

# 创建环境配置文件
create_env_file() {
    log_info "创建环境配置文件..."
    
    ENV_FILE="${APP_DIR}/.env"
    
    if [ ! -f "${ENV_FILE}" ]; then
        cat > "${ENV_FILE}" << 'EOF'
# AI 证券分析系统配置文件
# 请根据实际情况修改以下配置

# LLM API 配置
# Google Gemini API (可选)
GOOGLE_API_KEY=your_google_api_key_here

# SiliconFlow API (推荐)
SILICONFLOW_API_KEY=your_siliconflow_api_key_here

# 默认 LLM 提供商: google 或 siliconflow
DEFAULT_LLM_PROVIDER=siliconflow

# 服务配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000

# 日志级别
LOG_LEVEL=INFO
EOF
        log_warn "已创建 .env 文件，请编辑并配置 API 密钥: ${ENV_FILE}"
    else
        log_info ".env 文件已存在，跳过创建"
    fi
}

# 创建 PM2 配置文件
create_pm2_config() {
    log_info "创建 PM2 配置文件..."
    
    cat > "${APP_DIR}/ecosystem.config.js" << EOF
module.exports = {
  apps: [
    {
      name: '${APP_NAME}-backend',
      cwd: '${APP_DIR}',
      script: 'venv/bin/python',
      args: '-m uvicorn web.api:app --host 0.0.0.0 --port ${BACKEND_PORT}',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: '${APP_DIR}/logs/backend-error.log',
      out_file: '${APP_DIR}/logs/backend-out.log',
      merge_logs: true,
    },
    {
      name: '${APP_NAME}-frontend',
      cwd: '${APP_DIR}/frontend',
      script: 'npm',
      args: 'start',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: ${FRONTEND_PORT},
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: '${APP_DIR}/logs/frontend-error.log',
      out_file: '${APP_DIR}/logs/frontend-out.log',
      merge_logs: true,
    }
  ]
};
EOF
    
    # 创建日志目录
    mkdir -p "${APP_DIR}/logs"
    
    log_success "PM2 配置文件创建完成"
}

# 创建 systemd 服务文件（备选方案）
create_systemd_services() {
    log_info "创建 systemd 服务文件..."
    
    # 后端服务
    cat > /etc/systemd/system/${APP_NAME}-backend.service << EOF
[Unit]
Description=AI Trade Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
Environment=PATH=${APP_DIR}/venv/bin:/usr/local/bin:/usr/bin
ExecStart=${APP_DIR}/venv/bin/python -m uvicorn web.api:app --host 0.0.0.0 --port ${BACKEND_PORT}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 前端服务
    cat > /etc/systemd/system/${APP_NAME}-frontend.service << EOF
[Unit]
Description=AI Trade Frontend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}/frontend
Environment=NODE_ENV=production
Environment=PORT=${FRONTEND_PORT}
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_success "systemd 服务文件创建完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    # 检查是否使用 ufw (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        ufw allow ${BACKEND_PORT}/tcp || true
        ufw allow ${FRONTEND_PORT}/tcp || true
        log_info "已开放端口 ${BACKEND_PORT} 和 ${FRONTEND_PORT} (ufw)"
    fi
    
    # 检查是否使用 firewalld (CentOS/RHEL)
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=${BACKEND_PORT}/tcp || true
        firewall-cmd --permanent --add-port=${FRONTEND_PORT}/tcp || true
        firewall-cmd --reload || true
        log_info "已开放端口 ${BACKEND_PORT} 和 ${FRONTEND_PORT} (firewalld)"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "${APP_DIR}"
    
    # 使用 PM2 启动
    pm2 start ecosystem.config.js
    
    # 设置 PM2 开机自启
    pm2 save
    pm2 startup || true
    
    log_success "服务启动完成"
}

# 显示服务状态
show_status() {
    echo ""
    echo "============================================"
    echo -e "${GREEN}部署完成!${NC}"
    echo "============================================"
    echo ""
    echo "服务状态:"
    pm2 status
    echo ""
    echo "访问地址:"
    echo -e "  前端: ${GREEN}http://$(hostname -I | awk '{print $1}'):${FRONTEND_PORT}${NC}"
    echo -e "  后端: ${GREEN}http://$(hostname -I | awk '{print $1}'):${BACKEND_PORT}${NC}"
    echo -e "  API文档: ${GREEN}http://$(hostname -I | awk '{print $1}'):${BACKEND_PORT}/docs${NC}"
    echo ""
    echo "管理命令:"
    echo "  查看状态: pm2 status"
    echo "  查看日志: pm2 logs"
    echo "  重启服务: pm2 restart all"
    echo "  停止服务: pm2 stop all"
    echo ""
    echo -e "${YELLOW}重要: 请编辑 ${APP_DIR}/.env 文件配置 API 密钥${NC}"
    echo ""
}

# 创建管理脚本
create_manage_script() {
    log_info "创建管理脚本..."
    
    cat > "${APP_DIR}/manage.sh" << 'EOF'
#!/bin/bash

APP_DIR="/opt/ai-trade"

case "$1" in
    start)
        echo "启动服务..."
        cd "$APP_DIR"
        pm2 start ecosystem.config.js
        ;;
    stop)
        echo "停止服务..."
        pm2 stop all
        ;;
    restart)
        echo "重启服务..."
        pm2 restart all
        ;;
    status)
        pm2 status
        ;;
    logs)
        pm2 logs
        ;;
    update)
        echo "更新代码..."
        cd "$APP_DIR"
        git pull origin main
        source venv/bin/activate
        pip install -r requirements.txt
        deactivate
        cd frontend
        npm install
        npm run build
        pm2 restart all
        echo "更新完成"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
EOF

    chmod +x "${APP_DIR}/manage.sh"
    
    # 创建全局命令
    ln -sf "${APP_DIR}/manage.sh" /usr/local/bin/ai-trade
    
    log_success "管理脚本创建完成，可使用 'ai-trade' 命令管理服务"
}

# 主函数
main() {
    echo ""
    echo "============================================"
    echo "   AI 证券分析系统 - Linux 一键部署"
    echo "============================================"
    echo ""
    
    check_root
    detect_os
    
    log_info "开始部署..."
    
    install_system_deps
    setup_app_dir
    setup_python_env
    setup_frontend
    create_env_file
    create_pm2_config
    create_systemd_services
    create_manage_script
    configure_firewall
    start_services
    show_status
}

# 运行主函数
main "$@"
