#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行迁移脚本 108: 修改 calculation_parameters 表的 metric_key 外键约束

用途: 将 ON DELETE CASCADE 改为 ON DELETE RESTRICT，防止意外的级联删除
创建日期: 2025-11-14
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def execute_migration() -> bool:
    """执行迁移脚本"""
    print("=" * 80)
    print("开始执行迁移脚本 108: 修改 calculation_parameters 表的 metric_key 外键约束")
    print("=" * 80)
    print()

    # 读取SQL脚本
    sql_file = project_root / "scripts" / "sql" / "migrations" / "108_fix_calculation_parameters_metric_key_fk.sql"

    if not sql_file.exists():
        print(f"❌ SQL脚本不存在: {sql_file}")
        return False

    print(f"📄 读取SQL脚本: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')

    # 移除psql特定的命令（\echo、\encoding等）
    lines = sql_content.split('\n')
    cleaned_lines = []
    for line in lines:
        # 跳过psql特定命令
        if line.strip().startswith('\\'):
            continue
        else:
            cleaned_lines.append(line)

    cleaned_sql = '\n'.join(cleaned_lines)

    # 执行SQL
    print("🔄 开始执行SQL迁移...")
    print()

    try:
        with get_connection() as conn:
            # 先提交当前事务（如果有）
            try:
                conn.commit()
            except Exception:
                pass
            
            # 设置连接为自动提交模式，因为SQL脚本中已经有BEGIN/COMMIT
            conn.autocommit = True
            
            with conn.cursor() as cur:
                # 执行整个脚本
                cur.execute(cleaned_sql)

        print()
        print("=" * 80)
        print("✅ 迁移成功完成！")
        print("=" * 80)
        print()
        print("📋 修改内容:")
        print("  - calculation_parameters.metric_key 外键: ON DELETE CASCADE → ON DELETE RESTRICT")
        print("  - calculation_parameters.device_id 外键: ON DELETE CASCADE (未修改)")
        print("  - calculation_parameters.station_id 外键: ON DELETE CASCADE (未修改)")
        print("  - calculation_parameters.method_id 外键: ON DELETE NO ACTION (未修改)")
        print()
        print("🔍 下一步: 运行验证脚本")
        print("  python scripts/tools/verify_fk_constraints.py")
        print()
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
        print()
        print("🔄 如需回滚，请执行:")
        print("  python scripts/tools/execute_migration_108_rollback.py")
        print()
        return False


def main():
    """主函数"""
    # 加载配置
    settings = load_settings(project_root / "configs")

    # 初始化连接池
    try:
        initialize_pool(settings)
        print("✅ 数据库连接池已初始化")
        print()
    except Exception as e:
        print(f"❌ 初始化连接池失败: {e}")
        return 1

    try:
        # 执行迁移
        success = execute_migration()
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
            print("✅ 数据库连接池已关闭")
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

