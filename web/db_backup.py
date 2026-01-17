"""
============================================
数据库备份管理模块
Database Backup Management
============================================
"""

import os
import shutil
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 数据库和备份目录
DB_DIR = Path(__file__).parent / "data"
BACKUP_DIR = DB_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# 主数据库文件
MAIN_DB = DB_DIR / "ai_trade.db"
ETF_DB = DB_DIR.parent / "etf_data.db"

# 备份设置文件
SETTINGS_FILE = BACKUP_DIR / "backup_settings.json"

# 默认设置
DEFAULT_SETTINGS = {
    "auto_backup_enabled": True,
    "backup_time": "03:00",  # 每天凌晨3点
    "keep_days": 7,  # 保留7天
    "last_auto_backup": None
}


def get_backup_settings() -> Dict:
    """获取备份设置"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # 合并默认设置
                return {**DEFAULT_SETTINGS, **settings}
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def update_backup_settings(
    auto_backup_enabled: bool = None,
    backup_time: str = None,
    keep_days: int = None
) -> Dict:
    """更新备份设置"""
    try:
        settings = get_backup_settings()
        
        if auto_backup_enabled is not None:
            settings["auto_backup_enabled"] = auto_backup_enabled
        if backup_time is not None:
            settings["backup_time"] = backup_time
        if keep_days is not None:
            settings["keep_days"] = max(1, min(30, keep_days))  # 1-30天
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "settings": settings}
    except Exception as e:
        logger.error(f"更新备份设置失败: {e}")
        return {"success": False, "error": str(e)}


def create_backup(manual: bool = False, created_by: str = None) -> Dict:
    """
    创建数据库备份
    
    Args:
        manual: 是否为手动备份
        created_by: 创建者用户名
        
    Returns:
        备份结果
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_type = "manual" if manual else "auto"
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = BACKUP_DIR / backup_name
        backup_path.mkdir(exist_ok=True)
        
        files_backed_up = []
        total_size = 0
        
        # 备份主数据库
        if MAIN_DB.exists():
            dest = backup_path / "ai_trade.db"
            shutil.copy2(MAIN_DB, dest)
            files_backed_up.append("ai_trade.db")
            total_size += dest.stat().st_size
        
        # 备份ETF数据库
        if ETF_DB.exists():
            dest = backup_path / "etf_data.db"
            shutil.copy2(ETF_DB, dest)
            files_backed_up.append("etf_data.db")
            total_size += dest.stat().st_size
        
        # 保存备份元信息
        meta = {
            "backup_name": backup_name,
            "created_at": datetime.now().isoformat(),
            "type": backup_type,
            "created_by": created_by or "system",
            "files": files_backed_up,
            "size_bytes": total_size
        }
        
        with open(backup_path / "meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # 更新最后备份时间
        if not manual:
            settings = get_backup_settings()
            settings["last_auto_backup"] = datetime.now().isoformat()
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        
        # 清理过期备份
        cleanup_old_backups()
        
        logger.info(f"数据库备份成功: {backup_name}, 大小: {total_size / 1024:.1f}KB")
        
        return {
            "success": True,
            "backup_name": backup_name,
            "files": files_backed_up,
            "size_bytes": total_size,
            "size_display": format_size(total_size)
        }
        
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        return {"success": False, "error": str(e)}


def list_backups() -> List[Dict]:
    """列出所有备份"""
    backups = []
    
    if not BACKUP_DIR.exists():
        return backups
    
    for item in BACKUP_DIR.iterdir():
        if item.is_dir() and item.name.startswith("backup_"):
            meta_file = item / "meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        meta["size_display"] = format_size(meta.get("size_bytes", 0))
                        backups.append(meta)
                except:
                    # 没有meta文件，构造基本信息
                    size = sum(f.stat().st_size for f in item.iterdir() if f.is_file())
                    backups.append({
                        "backup_name": item.name,
                        "created_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                        "type": "manual" if "manual" in item.name else "auto",
                        "size_bytes": size,
                        "size_display": format_size(size)
                    })
    
    # 按创建时间降序排列
    backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return backups


def restore_backup(backup_name: str) -> Dict:
    """
    恢复数据库备份
    
    Args:
        backup_name: 备份名称
        
    Returns:
        恢复结果
    """
    try:
        backup_path = BACKUP_DIR / backup_name
        
        if not backup_path.exists():
            return {"success": False, "error": "备份不存在"}
        
        files_restored = []
        
        # 先创建当前状态的备份（防止误操作）
        pre_restore_backup = create_backup(manual=False, created_by="pre_restore")
        
        # 恢复主数据库
        backup_main_db = backup_path / "ai_trade.db"
        if backup_main_db.exists():
            shutil.copy2(backup_main_db, MAIN_DB)
            files_restored.append("ai_trade.db")
        
        # 恢复ETF数据库
        backup_etf_db = backup_path / "etf_data.db"
        if backup_etf_db.exists():
            shutil.copy2(backup_etf_db, ETF_DB)
            files_restored.append("etf_data.db")
        
        logger.info(f"数据库恢复成功: {backup_name}, 恢复文件: {files_restored}")
        
        return {
            "success": True,
            "backup_name": backup_name,
            "files_restored": files_restored,
            "pre_restore_backup": pre_restore_backup.get("backup_name")
        }
        
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        return {"success": False, "error": str(e)}


def delete_backup(backup_name: str) -> Dict:
    """删除备份"""
    try:
        backup_path = BACKUP_DIR / backup_name
        
        if not backup_path.exists():
            return {"success": False, "error": "备份不存在"}
        
        shutil.rmtree(backup_path)
        
        logger.info(f"删除备份成功: {backup_name}")
        
        return {"success": True, "backup_name": backup_name}
        
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        return {"success": False, "error": str(e)}


def cleanup_old_backups():
    """清理过期备份"""
    try:
        settings = get_backup_settings()
        keep_days = settings.get("keep_days", 7)
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for backup in list_backups():
            # 只清理自动备份
            if backup.get("type") != "auto":
                continue
            
            created_at_str = backup.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_date:
                        delete_backup(backup["backup_name"])
                        logger.info(f"清理过期备份: {backup['backup_name']}")
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"清理过期备份失败: {e}")


def should_auto_backup() -> bool:
    """检查是否应该执行自动备份"""
    settings = get_backup_settings()
    
    if not settings.get("auto_backup_enabled"):
        return False
    
    backup_time = settings.get("backup_time", "03:00")
    last_backup_str = settings.get("last_auto_backup")
    
    now = datetime.now()
    
    # 解析备份时间
    try:
        hour, minute = map(int, backup_time.split(":"))
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except:
        return False
    
    # 检查是否在备份时间窗口内（前后5分钟）
    time_diff = abs((now - scheduled_time).total_seconds())
    if time_diff > 300:  # 超过5分钟
        return False
    
    # 检查今天是否已经备份过
    if last_backup_str:
        try:
            last_backup = datetime.fromisoformat(last_backup_str)
            if last_backup.date() == now.date():
                return False
        except:
            pass
    
    return True


def run_auto_backup():
    """执行自动备份（由调度器调用）"""
    if should_auto_backup():
        result = create_backup(manual=False, created_by="scheduler")
        if result["success"]:
            logger.info(f"自动备份完成: {result['backup_name']}")
        else:
            logger.error(f"自动备份失败: {result.get('error')}")


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f}MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.1f}GB"
