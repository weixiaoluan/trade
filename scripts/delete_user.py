#!/usr/bin/env python3
"""
删除指定用户的脚本
用法: python scripts/delete_user.py <username>
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.database import db_delete_user, db_get_user_by_username

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/delete_user.py <username>")
        print("示例: python scripts/delete_user.py 'malicious_user'")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # 检查用户是否存在
    user = db_get_user_by_username(username)
    if not user:
        print(f"用户 '{username}' 不存在")
        sys.exit(1)
    
    print(f"即将删除用户: {username}")
    print(f"  手机号: {user.get('phone', 'N/A')}")
    print(f"  角色: {user.get('role', 'N/A')}")
    print(f"  状态: {user.get('status', 'N/A')}")
    print(f"  创建时间: {user.get('created_at', 'N/A')}")
    
    confirm = input("\n确认删除? (输入 'yes' 确认): ")
    if confirm.lower() != 'yes':
        print("已取消")
        sys.exit(0)
    
    # 执行删除
    success = db_delete_user(username)
    if success:
        print(f"✅ 用户 '{username}' 已删除")
    else:
        print(f"❌ 删除失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
