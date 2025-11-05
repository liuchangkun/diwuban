#!/usr/bin/env python3
"""
测试外键约束的级联行为

用途：验证外键约束的 CASCADE 规则是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings


def test_device_id_cascade():
    """测试 device_id 的级联更新"""
    print("\n" + "="*80)
    print("测试1.1：验证 device_id 的级联更新")
    print("="*80 + "\n")
    
    settings = Settings()
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 1. 选择一个现有的 device_id
            cur.execute("SELECT id, name FROM dim_devices LIMIT 1")
            device = cur.fetchone()
            device_id = device[0]
            device_name = device[1]
            
            print(f"✓ 选择测试设备: ID={device_id}, Name={device_name}\n")
            
            # 2. 记录更新前的相关表记录数
            print("更新前的记录数：")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM calculation_parameters WHERE device_id = '{device_id}'
            """)
            calc_params_count = cur.fetchone()[0]
            print(f"  - calculation_parameters: {calc_params_count} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM device_rated_params WHERE device_id = '{device_id}'
            """)
            rated_params_count = cur.fetchone()[0]
            print(f"  - device_rated_params: {rated_params_count} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM device_running_thresholds WHERE device_id = '{device_id}'
            """)
            thresholds_count = cur.fetchone()[0]
            print(f"  - device_running_thresholds: {thresholds_count} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM metric_anomaly_strategy WHERE device_id = '{device_id}'
            """)
            anomaly_count = cur.fetchone()[0]
            print(f"  - metric_anomaly_strategy: {anomaly_count} 条")
            
            # 3. 执行自我更新以触发外键约束检查
            print("\n执行自我更新（触发外键约束检查）...")
            try:
                cur.execute(f"UPDATE dim_devices SET id = id WHERE id = '{device_id}'")
                print("✅ 更新成功！外键约束正常工作")
            except Exception as e:
                print(f"❌ 更新失败: {e}")
                return False
            
            # 4. 验证记录数没有变化
            print("\n更新后的记录数：")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM calculation_parameters WHERE device_id = '{device_id}'
            """)
            calc_params_count_after = cur.fetchone()[0]
            print(f"  - calculation_parameters: {calc_params_count_after} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM device_rated_params WHERE device_id = '{device_id}'
            """)
            rated_params_count_after = cur.fetchone()[0]
            print(f"  - device_rated_params: {rated_params_count_after} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM device_running_thresholds WHERE device_id = '{device_id}'
            """)
            thresholds_count_after = cur.fetchone()[0]
            print(f"  - device_running_thresholds: {thresholds_count_after} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM metric_anomaly_strategy WHERE device_id = '{device_id}'
            """)
            anomaly_count_after = cur.fetchone()[0]
            print(f"  - metric_anomaly_strategy: {anomaly_count_after} 条")
            
            # 5. 验证记录数一致
            if (calc_params_count == calc_params_count_after and
                rated_params_count == rated_params_count_after and
                thresholds_count == thresholds_count_after and
                anomaly_count == anomaly_count_after):
                print("\n✅ 验证通过：记录数保持一致")
                return True
            else:
                print("\n❌ 验证失败：记录数不一致")
                return False
        
        conn.commit()


def test_metric_key_cascade():
    """测试 metric_key 的级联更新"""
    print("\n" + "="*80)
    print("测试1.2：验证 metric_key 的级联更新")
    print("="*80 + "\n")
    
    settings = Settings()
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 1. 选择一个现有的 metric_key
            cur.execute("""
                SELECT metric_key, unit_display 
                FROM dim_metric_config 
                WHERE metric_key = 'pump_efficiency'
            """)
            result = cur.fetchone()
            
            if not result:
                print("⚠️  pump_efficiency 不存在，选择其他指标...")
                cur.execute("SELECT metric_key, unit_display FROM dim_metric_config LIMIT 1")
                result = cur.fetchone()
            
            metric_key = result[0]
            unit_display = result[1]
            
            print(f"✓ 选择测试指标: metric_key={metric_key}, unit_display={unit_display}\n")
            
            # 2. 记录更新前的相关表记录数
            print("更新前的记录数：")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM calculation_validation_config WHERE metric_key = '{metric_key}'
            """)
            validation_count = cur.fetchone()[0]
            print(f"  - calculation_validation_config: {validation_count} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM metric_capability_policy WHERE metric_key = '{metric_key}'
            """)
            policy_count = cur.fetchone()[0]
            print(f"  - metric_capability_policy: {policy_count} 条")
            
            # 3. 执行自我更新以触发外键约束检查
            print("\n执行自我更新（触发外键约束检查）...")
            try:
                cur.execute(f"UPDATE dim_metric_config SET metric_key = metric_key WHERE metric_key = '{metric_key}'")
                print("✅ 更新成功！外键约束正常工作")
            except Exception as e:
                print(f"❌ 更新失败: {e}")
                return False
            
            # 4. 验证记录数没有变化
            print("\n更新后的记录数：")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM calculation_validation_config WHERE metric_key = '{metric_key}'
            """)
            validation_count_after = cur.fetchone()[0]
            print(f"  - calculation_validation_config: {validation_count_after} 条")
            
            cur.execute(f"""
                SELECT COUNT(*) FROM metric_capability_policy WHERE metric_key = '{metric_key}'
            """)
            policy_count_after = cur.fetchone()[0]
            print(f"  - metric_capability_policy: {policy_count_after} 条")
            
            # 5. 验证记录数一致
            if (validation_count == validation_count_after and
                policy_count == policy_count_after):
                print("\n✅ 验证通过：记录数保持一致")
                return True
            else:
                print("\n❌ 验证失败：记录数不一致")
                return False
        
        conn.commit()


def test_foreign_key_constraints():
    """检查外键约束状态"""
    print("\n" + "="*80)
    print("测试1.3：检查外键约束状态")
    print("="*80 + "\n")
    
    settings = Settings()
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 查询所有外键约束
            cur.execute("""
                SELECT 
                    tc.table_name AS 源表名,
                    kcu.column_name AS 源列名,
                    ccu.table_name AS 目标表名,
                    ccu.column_name AS 目标列名,
                    rc.update_rule AS UPDATE规则,
                    rc.delete_rule AS DELETE规则
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name IN (
                        'calculation_validation_config',
                        'device_running_thresholds',
                        'metric_anomaly_strategy',
                        'metric_quality_rules',
                        'metric_rule_auto_baseline',
                        'metric_capability_policy'
                    )
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name
            """)
            
            results = cur.fetchall()
            
            print(f"✓ 找到 {len(results)} 个外键约束\n")
            
            # 按表分组显示
            current_table = None
            for row in results:
                table_name = row[0]
                column_name = row[1]
                foreign_table = row[2]
                foreign_column = row[3]
                update_rule = row[4]
                delete_rule = row[5]
                
                if table_name != current_table:
                    if current_table is not None:
                        print()
                    print(f"📋 {table_name}:")
                    current_table = table_name
                
                print(f"  - {column_name} → {foreign_table}.{foreign_column} (UPDATE: {update_rule}, DELETE: {delete_rule})")
            
            # 验证所有外键都是 CASCADE
            non_cascade = [row for row in results if row[4] != 'CASCADE' or row[5] != 'CASCADE']
            
            if not non_cascade:
                print("\n✅ 验证通过：所有外键约束都配置了 CASCADE 规则")
                return True
            else:
                print(f"\n❌ 验证失败：发现 {len(non_cascade)} 个外键约束未配置 CASCADE 规则")
                for row in non_cascade:
                    print(f"  - {row[0]}.{row[1]} → {row[2]}.{row[3]} (UPDATE: {row[4]}, DELETE: {row[5]})")
                return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("外键约束级联行为测试")
    print("="*80)
    
    results = []
    
    # 测试1.1：device_id 级联更新
    try:
        result = test_device_id_cascade()
        results.append(("device_id 级联更新", result))
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("device_id 级联更新", False))
    
    # 测试1.2：metric_key 级联更新
    try:
        result = test_metric_key_cascade()
        results.append(("metric_key 级联更新", result))
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("metric_key 级联更新", False))
    
    # 测试1.3：外键约束状态
    try:
        result = test_foreign_key_constraints()
        results.append(("外键约束状态", result))
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("外键约束状态", False))
    
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

