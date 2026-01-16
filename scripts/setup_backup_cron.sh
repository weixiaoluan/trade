#!/bin/bash

# ============================================
# 设置数据库自动备份定时任务
# 每天凌晨3点自动备份
# ============================================

APP_DIR="/root/trade"  # 项目目录，根据实际情况修改
BACKUP_SCRIPT="$APP_DIR/scripts/backup_db.sh"

# 确保备份脚本可执行
chmod +x "$BACKUP_SCRIPT"

# 检查是否已存在备份任务
if crontab -l 2>/dev/null | grep -q "backup_db.sh"; then
    echo "备份定时任务已存在"
    crontab -l | grep "backup_db.sh"
else
    # 添加定时任务：每天凌晨3点执行备份
    (crontab -l 2>/dev/null; echo "0 3 * * * $BACKUP_SCRIPT >> $APP_DIR/logs/backup.log 2>&1") | crontab -
    echo "✅ 已添加每日自动备份任务（凌晨3点）"
fi

# 显示当前定时任务
echo ""
echo "当前定时任务列表:"
crontab -l

# 创建日志目录
mkdir -p "$APP_DIR/logs"

echo ""
echo "备份文件将保存在: $APP_DIR/web/data/backups/"
echo "备份日志: $APP_DIR/logs/backup.log"
