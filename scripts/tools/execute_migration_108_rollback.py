#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行回滚脚本 108: 恢复 calculation_parameters 表的 metric_key 外键约束

用途: 将 ON DELETE RESTRICT 改回 ON DELETE CASCADE，恢复原始状态
创建日期: 2025-11-14
警告: 回滚后，dim_metric_config 表被清空时会级联删除 calculation_parameters 表
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def execute_rollback() -> bool:
    """执行回滚脚本"""
    print("=" * 80)
    print("⚠️  警告: 即将回滚迁移脚本 108")
    print("=" * 80)
    print()
    print("回滚后，calculation_parameters 表的 metric_key 外键将恢复为 ON DELETE CASCADE")
    print("这意味着 dim_metric_config 表被清空时会级联删除 calculation_parameters 表")
    print()
    
    # 确认回滚
    response = input("确认回滚？(yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ 回滚已取消")
        return False
    
    print()
    print("=" * 80)
    print("开始执行回滚脚本")
    print("=" * 80)
    print()

    # 读取SQL脚本
    sql_file = project_root / "scripts" / "sql" / "migrations" / "108_fix_calculation_parameters_metric_key_fk_ROLLBACK.sql"

    if not sql_file.exists():
        print(f"❌ 回滚脚本不存在: {sql_file}")
        return False

    print(f"📄 读取回滚脚本: {sql_file}")
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
    print("🔄 开始执行回滚...")
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
        print("✅ 回滚成功完成！")
        print("=" * 80)
        print()
        print("📋 回滚内容:")
        print("  - calculation_parameters.metric_key 外键: ON DELETE RESTRICT → ON DELETE CASCADE")
        print()
        print("⚠️  警告: 现在 dim_metric_config 表被清空时会级联删除 calculation_parameters 表")
        print()
        print("🔍 下一步: 运行验证脚本")
        print("  python scripts/tools/verify_fk_constraints.py")
        print()
        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 回滚失败！")
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
        # 执行回滚
        success = execute_rollback()
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

