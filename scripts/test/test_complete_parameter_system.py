#!/usr/bin/env python
"""
完整参数体系综合测试
验证三级参数体系（全局→泵站→设备）的完整性和一致性
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn

def test_complete_system():
    """综合测试"""
    settings = load_settings(Path("configs"))
    
    print("=" * 80)
    print("完整参数体系综合测试")
    print("=" * 80)
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 测试1：device_rated_params三级参数体系
            print("\n[测试1] device_rated_params 三级参数体系")
            cur.execute("""
                WITH levels AS (
                    SELECT 
                        CASE 
                            WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
                            WHEN station_id IS NOT NULL AND device_id IS NULL THEN '泵站级'
                            WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN '设备级'
                            ELSE '未知'
                        END as level
                    FROM device_rated_params
                )
                SELECT level, COUNT(*) as count
                FROM levels
                GROUP BY level
                ORDER BY 
                    CASE level
                        WHEN '全局级' THEN 1
                        WHEN '泵站级' THEN 2
                        WHEN '设备级' THEN 3
                        ELSE 4
                    END
            """)
            stats = cur.fetchall()
            print("  参数分布：")
            for row in stats:
                print(f"    {row[0]}: {row[1]} 行")
            
            # 测试2：calculation_parameters三级参数体系
            print("\n[测试2] calculation_parameters 三级参数体系")
            cur.execute("""
                WITH levels AS (
                    SELECT 
                        CASE 
                            WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
                            WHEN station_id IS NOT NULL AND device_id IS NULL THEN '泵站级'
                            WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN '设备级'
                            ELSE '未知'
                        END as level
                    FROM calculation_parameters
                )
                SELECT level, COUNT(*) as count
                FROM levels
                GROUP BY level
                ORDER BY 
                    CASE level
                        WHEN '全局级' THEN 1
                        WHEN '泵站级' THEN 2
                        WHEN '设备级' THEN 3
                        ELSE 4
                    END
            """)
            stats = cur.fetchall()
            print("  参数分布：")
            for row in stats:
                print(f"    {row[0]}: {row[1]} 行")
            
            # 测试3：验证设备级参数完整性
            print("\n[测试3] 设备级参数完整性（6台泵×8个方法）")
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(DISTINCT method_id) as method_count,
                    COUNT(*) as param_count
                FROM calculation_parameters
                WHERE device_id BETWEEN 1 AND 6
                GROUP BY device_id
                ORDER BY device_id
            """)
            devices = cur.fetchall()
            all_complete = True
            for row in devices:
                status = "✓" if row[1] == 8 else "✗"
                print(f"    {status} 设备{row[0]}: {row[1]} 个方法, {row[2]} 个参数")
                if row[1] != 8:
                    all_complete = False
            
            if all_complete:
                print("  ✓ 所有设备参数完整")
            else:
                print("  ✗ 部分设备参数不完整")
            
            # 测试4：验证泵站级参数
            print("\n[测试4] 泵站级参数验证")
            cur.execute("""
                SELECT param_key, value_numeric, unit
                FROM device_rated_params
                WHERE station_id = 1 AND device_id IS NULL
                ORDER BY param_key
            """)
            station_params = cur.fetchall()
            print(f"  泵站级参数数量: {len(station_params)}")
            expected_params = {'pipe_diameter', 'pipe_length', 'roughness_rel', 'C_hazen', 'ambient_temp', 'ambient_pressure'}
            actual_params = {row[0] for row in station_params}
            
            if expected_params == actual_params:
                print("  ✓ 泵站级参数完整（管道参数 + 环境参数）")
            else:
                missing = expected_params - actual_params
                extra = actual_params - expected_params
                if missing:
                    print(f"  ✗ 缺少参数: {missing}")
                if extra:
                    print(f"  ⚠ 额外参数: {extra}")
            
            # 测试5：验证唯一索引和约束
            print("\n[测试5] 唯一索引和约束验证")
            
            # device_rated_params
            cur.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' 
                  AND tablename = 'device_rated_params'
                  AND indexname = 'uq_device_rated_params_3tier'
            """)
            if cur.fetchone():
                print("  ✓ device_rated_params 唯一索引已创建")
            else:
                print("  ✗ device_rated_params 唯一索引缺失")
            
            # calculation_parameters
            cur.execute("""
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'public.calculation_parameters'::regclass
                  AND contype = 'u'
            """)
            if cur.fetchone():
                print("  ✓ calculation_parameters 唯一约束已创建")
            else:
                print("  ✗ calculation_parameters 唯一约束缺失")
            
            # 测试6：验证外键完整性
            print("\n[测试6] 外键完整性验证")
            cur.execute("""
                SELECT COUNT(*)
                FROM device_rated_params drp
                LEFT JOIN dim_stations s ON s.id = drp.station_id
                WHERE drp.station_id IS NOT NULL AND s.id IS NULL
            """)
            orphan_count = cur.fetchone()[0]
            if orphan_count == 0:
                print("  ✓ device_rated_params 无孤立记录")
            else:
                print(f"  ✗ device_rated_params 有 {orphan_count} 条孤立记录")
            
            # 测试7：验证问题1修复（metric_quality_rules）
            print("\n[测试7] 问题1修复验证（metric_quality_rules）")
            cur.execute("SELECT COUNT(*) FROM metric_rule_auto_baseline")
            baseline_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM metric_quality_rules")
            rules_count = cur.fetchone()[0]
            
            print(f"  metric_rule_auto_baseline: {baseline_count} 行")
            print(f"  metric_quality_rules: {rules_count} 行")
            
            if baseline_count > 0 and rules_count > 0:
                print("  ✓ 问题1已修复（质量规则生成正常）")
            else:
                print("  ✗ 问题1未完全修复")
            
            # 测试8：数据一致性检查
            print("\n[测试8] 数据一致性检查")
            
            # 检查device_rated_params的station_id是否与device的station_id一致
            cur.execute("""
                SELECT COUNT(*)
                FROM device_rated_params drp
                JOIN dim_devices d ON d.id = drp.device_id
                WHERE drp.station_id != d.station_id
            """)
            inconsistent_count = cur.fetchone()[0]
            if inconsistent_count == 0:
                print("  ✓ device_rated_params.station_id 与 dim_devices.station_id 一致")
            else:
                print(f"  ✗ 发现 {inconsistent_count} 条不一致记录")
            
            # 测试9：性能测试（参数查询）
            print("\n[测试9] 参数查询性能测试")
            import time
            
            # 测试设备级参数查询
            start = time.time()
            cur.execute("""
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE device_id = 1
            """)
            device_params = cur.fetchall()
            elapsed = (time.time() - start) * 1000
            print(f"  设备级参数查询: {len(device_params)} 行, 耗时 {elapsed:.2f}ms")
            
            # 测试泵站级参数查询
            start = time.time()
            cur.execute("""
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE station_id = 1 AND device_id IS NULL
            """)
            station_params = cur.fetchall()
            elapsed = (time.time() - start) * 1000
            print(f"  泵站级参数查询: {len(station_params)} 行, 耗时 {elapsed:.2f}ms")
            
            # 测试10：总结
            print("\n[测试10] 总结")
            cur.execute("""
                SELECT 
                    'device_rated_params' as table_name,
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1 END) as global_count,
                    COUNT(DISTINCT CASE WHEN station_id IS NOT NULL AND device_id IS NULL THEN 1 END) as station_count,
                    COUNT(DISTINCT CASE WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN 1 END) as device_count
                FROM device_rated_params
                UNION ALL
                SELECT 
                    'calculation_parameters' as table_name,
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1 END) as global_count,
                    COUNT(DISTINCT CASE WHEN station_id IS NOT NULL AND device_id IS NULL THEN 1 END) as station_count,
                    COUNT(DISTINCT CASE WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN 1 END) as device_count
                FROM calculation_parameters
            """)
            summary = cur.fetchall()
            print("  参数体系总览：")
            for row in summary:
                print(f"    {row[0]}:")
                print(f"      总行数: {row[1]}")
                print(f"      全局级: {row[2]} 种")
                print(f"      泵站级: {row[3]} 种")
                print(f"      设备级: {row[4]} 种")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_complete_system()

