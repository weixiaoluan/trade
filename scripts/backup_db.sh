#!/bin/bash

# ============================================
# 数据库自动备份脚本
# 每小时自动备份，保留最近7天的备份
# ============================================

# 配置
APP_DIR="/root/trade"  # 项目目录，根据实际情况修改
DB_FILE="$APP_DIR/web/data/ai_trade.db"
BACKUP_DIR="$APP_DIR/web/data/backups"
KEEP_DAYS=7

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名（带日期时间）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ai_trade_$TIMESTAMP.db"

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} 数据库文件不存在: $DB_FILE"
    exit 1
fi

# 执行备份
echo -e "${GREEN}[BACKUP]${NC} 开始备份数据库..."
cp "$DB_FILE" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # 压缩备份文件
    gzip "$BACKUP_FILE"
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo -e "${GREEN}[SUCCESS]${NC} 备份完成: ${BACKUP_FILE}.gz ($BACKUP_SIZE)"
else
    echo -e "${RED}[ERROR]${NC} 备份失败"
    exit 1
fi

# 清理旧备份（保留最近N天）
echo -e "${YELLOW}[CLEANUP]${NC} 清理 $KEEP_DAYS 天前的备份..."
find "$BACKUP_DIR" -name "ai_trade_*.db.gz" -mtime +$KEEP_DAYS -delete

# 显示当前备份列表
echo -e "${GREEN}[INFO]${NC} 当前备份列表:"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null | tail -10

echo -e "${GREEN}[DONE]${NC} 备份任务完成"
