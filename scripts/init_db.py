#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库初始化脚本

1. 如果存在预置数据库文件，使用预置文件恢复数据库
2. 否则创建新的数据库并初始化表结构和默认数据
3. 统一使用ppt_assistant.db文件，避免多个数据库文件
"""

import sys
import os
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.models import init_db
from apps.api.config import settings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def restore_from_preset():
    """从预置数据库文件恢复数据库"""
    preset_db_path = project_root / "init_data" / "db" / "ppt_assistant.db"
    target_db_path = settings.DB_DIR / "ppt_assistant.db"
    
    if preset_db_path.exists():
        logger.info(f"发现预置数据库文件: {preset_db_path}")
        
        # 确保目标目录存在
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 备份现有数据库（如果存在）
        if target_db_path.exists():
            backup_path = target_db_path.with_suffix('.backup')
            shutil.copy2(target_db_path, backup_path)
            logger.info(f"备份现有数据库到: {backup_path}")
        
        # 复制预置数据库文件
        shutil.copy2(preset_db_path, target_db_path)
        logger.info(f"从预置文件恢复数据库到: {target_db_path}")
        return True
    
    return False

def create_new_database():
    """创建新的数据库"""
    logger.info("创建新的数据库并初始化...")
    
    # 确保数据库目录存在
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 调用模型初始化方法
    init_db()
    
    logger.info("数据库初始化完成")

def cleanup_old_databases():
    """清理旧的数据库文件"""
    old_db_path = settings.DB_DIR / "app.db"
    if old_db_path.exists():
        logger.info(f"删除旧的数据库文件: {old_db_path}")
        old_db_path.unlink()

def main():
    """主函数"""
    try:
        logger.info("开始数据库初始化...")
        
        # 清理旧的数据库文件
        cleanup_old_databases()
        
        # 检查是否需要从预置文件恢复
        force_new = "--force-new" in sys.argv
        if not force_new and restore_from_preset():
            logger.info("数据库已从预置文件恢复完成")
            return
        
        # 创建新数据库
        create_new_database()
        
        logger.info("数据库初始化成功完成")
        logger.info("默认管理员账户: admin/admin123")
        logger.info("请及时修改默认密码和API配置")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("用法: python scripts/init_db.py [选项]")
        print("选项:")
        print("  --force-new    强制创建新数据库，不使用预置文件")
        print("  --help         显示此帮助信息")
        sys.exit(0)
    
    main() 