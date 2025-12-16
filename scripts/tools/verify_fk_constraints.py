#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 calculation_parameters 表的外键约束

用途: 验证迁移脚本 108 执行后，外键约束是否正确修改
创建日期: 2025-11-14
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def verify_constraints() -> bool:
    """验证外键约束"""
    print("=" * 80)
    print("验证 calculation_parameters 表的外键约束")
    print("=" * 80)
    print()

    # 查询SQL
    query_sql = """
    SELECT 
        tc.constraint_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        rc.update_rule,
        rc.delete_rule
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    JOIN information_schema.referential_constraints AS rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'calculation_parameters'
        AND tc.table_schema = 'public'
    ORDER BY tc.constraint_name;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql)
                rows = cur.fetchall()

        if not rows:
            print("❌ 未找到任何外键约束！")
            return False

        # 打印表头
        print("📋 外键约束详情:")
        print()
        print(f"{'约束名':<50} {'列名':<20} {'引用表':<30} {'更新规则':<15} {'删除规则':<15}")
        print("-" * 130)

        # 预期值
        expected_rules = {
            'calculation_parameters_metric_key_fkey': ('CASCADE', 'RESTRICT'),
            'calculation_parameters_device_id_fkey': ('CASCADE', 'CASCADE'),
            'calculation_parameters_station_id_fkey': ('CASCADE', 'CASCADE'),
            'calculation_parameters_method_id_fkey': ('NO ACTION', 'NO ACTION'),
        }

        # 验证结果
        all_passed = True
        for row in rows:
            constraint_name = row[0]
            column_name = row[1]
            foreign_table = row[2]
            foreign_column = row[3]
            update_rule = row[4]
            delete_rule = row[5]

            # 打印行
            print(f"{constraint_name:<50} {column_name:<20} {foreign_table:<30} {update_rule:<15} {delete_rule:<15}")

            # 验证
            if constraint_name in expected_rules:
                expected_update, expected_delete = expected_rules[constraint_name]
                if update_rule != expected_update or delete_rule != expected_delete:
                    print(f"  ❌ 验证失败: 预期 UPDATE={expected_update}, DELETE={expected_delete}")
                    all_passed = False
                else:
                    print(f"  ✅ 验证通过")

        print()
        print("=" * 80)
        if all_passed:
            print("✅ 所有外键约束验证通过！")
            print()
            print("📋 验证结果:")
            print("  - metric_key 外键: ON DELETE RESTRICT ✅")
            print("  - device_id 外键: ON DELETE CASCADE ✅")
            print("  - station_id 外键: ON DELETE CASCADE ✅")
            print("  - method_id 外键: ON DELETE NO ACTION ✅")
        else:
            print("❌ 部分外键约束验证失败！")
            print()
            print("🔄 如需重新执行迁移，请运行:")
            print("  python scripts/tools/execute_migration_108.py")
        print("=" * 80)
        print()

        return all_passed

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 验证失败！")
        print("=" * 80)
        print(f"错误信息: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 加载配置
    settings = load_settings(project_root / "configs")

    # 初始化连接池
    try:
        initialize_pool(settings)
    except Exception as e:
        print(f"❌ 初始化连接池失败: {e}")
        return 1

    try:
        # 验证约束
        success = verify_constraints()
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

