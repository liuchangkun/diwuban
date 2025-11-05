#!/usr/bin/env python3
"""
执行维度表ID迁移脚本

用途：使用Python执行SQL迁移脚本，避免Windows编码问题
作者：AI
创建日期：2025-10-29
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def execute_migration():
    """执行数据库迁移"""
    print("=" * 80)
    print("开始执行维度表ID迁移")
    print("=" * 80)
    print()

    # 读取SQL脚本
    sql_file = project_root / "scripts" / "sql" / "migration" / "migrate_dim_ids_to_fixed.sql"

    if not sql_file.exists():
        print(f"❌ SQL脚本不存在: {sql_file}")
        return False

    print(f"读取SQL脚本: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')

    # 移除psql特定的命令（\echo等）
    lines = sql_content.split('\n')
    cleaned_lines = []
    for line in lines:
        # 跳过psql特定命令
        if line.strip().startswith('\\echo'):
            continue
        else:
            cleaned_lines.append(line)

    cleaned_sql = '\n'.join(cleaned_lines)

    # 执行SQL
    print("开始执行SQL迁移...")
    print()

    try:
        with get_connection() as conn:
            # 设置连接为自动提交模式，因为SQL脚本中已经有BEGIN/COMMIT
            conn.autocommit = True
            with conn.cursor() as cur:
                # 执行整个脚本
                cur.execute(cleaned_sql)

        print()
        print("=" * 80)
        print("✅ 迁移成功完成！")
        print("=" * 80)
        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 迁移失败！")
        print("=" * 80)
        print(f"错误信息: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行迁移
    success = execute_migration()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

