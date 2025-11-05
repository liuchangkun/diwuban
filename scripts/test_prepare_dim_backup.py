#!/usr/bin/env python3
"""
测试 prepare_dim 备份和恢复机制

用途：验证21个表的备份和恢复是否正常
"""

import sys
from pathlib import Path
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings


def get_table_counts(cur, tables):
    """获取表的记录数"""
    counts = {}
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        except Exception as e:
            counts[table] = f"ERROR: {e}"
    return counts


def check_backup_files():
    """检查备份文件是否生成"""
    print("\n" + "="*80)
    print("测试2.2：验证备份文件")
    print("="*80 + "\n")
    
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("❌ 备份目录不存在")
        return False
    
    # 定义需要备份的21个表
    tables_to_backup = [
        # A类：手动配置表（10个）
        "dim_device_capabilities",
        "dim_metric_metadata_override",
        "pump_characteristic_curves",
        "quality_code_dict",
        "calculation_validation_config",
        "metric_capability_policy",
        "metric_anomaly_strategy",
        "device_metric_candidates",
        "dim_metric_metadata",
        "optimization_history",
        # B类：配置表（4个）
        "calculation_parameters",
        "device_rated_params",
        "calculation_method_registry",
        "metric_calculation_order",
        # C类：维度表（1个）
        "dim_metric_config",
        # D类：规则表（6个）
        "metric_rule_auto_baseline",
        "metric_rule_auto_baseline_shadow",
        "metric_quality_rules",
        "metric_quality_rules_shadow",
        "device_running_thresholds",
        "device_running_thresholds_shadow",
    ]
    
    print(f"检查 {len(tables_to_backup)} 个表的备份文件...\n")
    
    backup_found = 0
    backup_missing = 0
    
    for table in tables_to_backup:
        table_backup_dir = backup_dir / table
        if table_backup_dir.exists():
            # 查找最新的备份文件
            backup_files = list(table_backup_dir.glob(f"{table}_v*.sql"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
                file_size = latest_backup.stat().st_size
                print(f"  ✅ {table}: {latest_backup.name} ({file_size} bytes)")
                backup_found += 1
            else:
                print(f"  ❌ {table}: 备份目录存在但没有备份文件")
                backup_missing += 1
        else:
            print(f"  ❌ {table}: 备份目录不存在")
            backup_missing += 1
    
    print(f"\n总结：")
    print(f"  - 找到备份: {backup_found} 个")
    print(f"  - 缺少备份: {backup_missing} 个")
    
    if backup_missing == 0:
        print("\n✅ 验证通过：所有21个表都有备份文件")
        return True
    else:
        print(f"\n❌ 验证失败：{backup_missing} 个表缺少备份文件")
        return False


def verify_restore_results():
    """验证恢复结果"""
    print("\n" + "="*80)
    print("测试2.3：验证恢复结果")
    print("="*80 + "\n")
    
    settings = Settings()
    
    # 定义需要恢复的9个手动配置表
    manual_config_tables = [
        "dim_metric_metadata_override",
        "pump_characteristic_curves",
        "quality_code_dict",
        "calculation_validation_config",
        "metric_capability_policy",
        "metric_anomaly_strategy",
        "device_metric_candidates",
        "dim_metric_metadata",
        "optimization_history",
    ]
    
    # 预期的记录数（从之前的查询结果）
    expected_counts = {
        "calculation_validation_config": 50,
        "device_metric_candidates": 0,
        "dim_metric_metadata": 0,
        "dim_metric_metadata_override": 0,
        "metric_anomaly_strategy": 0,
        "metric_capability_policy": 53,
        "optimization_history": 2,
        "pump_characteristic_curves": 0,
        "quality_code_dict": 34,
    }
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            print("恢复后的记录数：\n")
            
            actual_counts = get_table_counts(cur, manual_config_tables)
            
            all_match = True
            for table in manual_config_tables:
                actual = actual_counts.get(table, "ERROR")
                expected = expected_counts.get(table, "UNKNOWN")
                
                if isinstance(actual, str):
                    print(f"  ❌ {table}: {actual}")
                    all_match = False
                elif actual == expected:
                    print(f"  ✅ {table}: {actual} 条（与备份前一致）")
                else:
                    print(f"  ⚠️  {table}: {actual} 条（备份前: {expected} 条）")
                    all_match = False
            
            if all_match:
                print("\n✅ 验证通过：所有表的记录数与备份前一致")
                return True
            else:
                print("\n❌ 验证失败：部分表的记录数与备份前不一致")
                return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("prepare_dim 备份和恢复机制测试")
    print("="*80)
    
    results = []
    
    # 测试2.2：验证备份文件
    try:
        result = check_backup_files()
        results.append(("备份文件验证", result))
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("备份文件验证", False))
    
    # 测试2.3：验证恢复结果
    try:
        result = verify_restore_results()
        results.append(("恢复结果验证", result))
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("恢复结果验证", False))
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80 + "\n")
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())

