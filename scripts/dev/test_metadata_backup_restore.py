#!/usr/bin/env python
"""
测试元数据表的备份和恢复机制

目的：验证 dim_metric_metadata 和 dim_metric_metadata_override 的备份/恢复是否正常
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_connection, init_database
from app.services.ingest.prepare_dim.backup import BackupManager


def main():
    """主函数"""
    print("=" * 80)
    print("  测试元数据表的备份和恢复机制")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 初始化数据库连接池
    init_database(settings)
    
    # 测试表列表
    test_tables = [
        "dim_metric_metadata",
        "dim_metric_metadata_override",
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 步骤1：检查当前表状态
            print("\n步骤1：检查当前表状态")
            print("-" * 80)
            for table in test_tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table}: {count} 行")
            
            # 步骤2：执行备份
            print("\n步骤2：执行备份")
            print("-" * 80)
            backup_manager = BackupManager()
            backup_result = backup_manager.backup_tables(cur, test_tables)
            
            for table, result in backup_result.items():
                if result["status"] == "ok":
                    print(f"  ✓ {table}: 备份成功，版本 v{result['version']}，{result['rows']} 行")
                    print(f"    文件: {result['file']}")
                elif result["status"] == "skipped":
                    print(f"  ⊘ {table}: {result['message']}")
                else:
                    print(f"  ✗ {table}: 备份失败 - {result['message']}")
            
            # 步骤3：清空表（模拟数据丢失）
            print("\n步骤3：清空表（模拟数据丢失）")
            print("-" * 80)
            for table in test_tables:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                print(f"  ✓ {table}: 已清空")
            
            # 验证清空
            print("\n验证清空结果:")
            for table in test_tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table}: {count} 行")
            
            # 步骤4：从备份恢复
            print("\n步骤4：从备份恢复")
            print("-" * 80)
            for table in test_tables:
                restore_result = backup_manager.restore_table(cur, table)
                if restore_result["status"] == "ok":
                    print(f"  ✓ {table}: 恢复成功，版本 v{restore_result['version']}")
                    print(f"    文件: {restore_result['file']}")
                else:
                    print(f"  ✗ {table}: 恢复失败 - {restore_result['message']}")
            
            # 步骤5：验证恢复结果
            print("\n步骤5：验证恢复结果")
            print("-" * 80)
            for table in test_tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table}: {count} 行")
            
            # 提交事务
            conn.commit()
    
    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

