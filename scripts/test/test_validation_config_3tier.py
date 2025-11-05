#!/usr/bin/env python
"""
calculation_validation_config 三级参数体系验证测试
验证表结构、代码逻辑和参数优先级
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn

def test_validation_config_3tier():
    """验证三级参数体系"""
    settings = load_settings(Path("configs"))
    
    print("=" * 80)
    print("calculation_validation_config 三级参数体系验证")
    print("=" * 80)
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 测试1：表结构验证
            print("\n[测试1] 表结构验证")
            cur.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                  AND table_name = 'calculation_validation_config'
                  AND column_name IN ('station_id', 'device_id', 'metric_key', 'validator_type', 'params')
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            print("  关键字段：")
            for col in columns:
                nullable = "可空" if col[2] == "YES" else "非空"
                print(f"    {col[0]}: {col[1]} ({nullable})")
            
            # 验证station_id和device_id是否可空
            station_id_nullable = any(col[0] == 'station_id' and col[2] == 'YES' for col in columns)
            device_id_nullable = any(col[0] == 'device_id' and col[2] == 'YES' for col in columns)
            
            if station_id_nullable and device_id_nullable:
                print("  ✓ station_id 和 device_id 字段支持NULL（三级参数体系）")
            else:
                print("  ✗ station_id 或 device_id 字段不支持NULL")
            
            # 测试2：唯一索引验证
            print("\n[测试2] 唯一索引验证")
            cur.execute("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' 
                  AND tablename = 'calculation_validation_config'
                  AND indexname = 'uq_validation_config'
            """)
            index = cur.fetchone()
            if index:
                print(f"  ✓ 唯一索引已创建: {index[0]}")
                print(f"    定义: {index[1]}")
                if 'COALESCE' in index[1]:
                    print("  ✓ 索引使用COALESCE处理NULL值")
                else:
                    print("  ⚠ 索引未使用COALESCE处理NULL值")
            else:
                print("  ✗ 唯一索引缺失")
            
            # 测试3：外键约束验证
            print("\n[测试3] 外键约束验证")
            cur.execute("""
                SELECT 
                    conname as constraint_name,
                    pg_get_constraintdef(oid) as constraint_definition
                FROM pg_constraint
                WHERE conrelid = 'public.calculation_validation_config'::regclass
                  AND contype = 'f'
                ORDER BY conname
            """)
            fkeys = cur.fetchall()
            print(f"  外键数量: {len(fkeys)}")
            for fkey in fkeys:
                print(f"    {fkey[0]}: {fkey[1]}")
            
            expected_fkeys = {'dim_stations', 'dim_devices', 'dim_metric_config'}
            actual_fkeys = {fkey[1].split('REFERENCES ')[1].split('(')[0].strip() for fkey in fkeys}
            
            if expected_fkeys.issubset(actual_fkeys):
                print("  ✓ 所有必要的外键约束已创建")
            else:
                missing = expected_fkeys - actual_fkeys
                print(f"  ✗ 缺少外键约束: {missing}")
            
            # 测试4：数据分布验证
            print("\n[测试4] 数据分布验证")
            cur.execute("""
                WITH levels AS (
                    SELECT 
                        CASE 
                            WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
                            WHEN station_id IS NOT NULL AND device_id IS NULL THEN '泵站级'
                            WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN '设备级'
                            ELSE '未知'
                        END as level
                    FROM calculation_validation_config
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
            
            # 测试5：验证器类型统计
            print("\n[测试5] 验证器类型统计")
            cur.execute("""
                SELECT 
                    validator_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT metric_key) as metrics
                FROM calculation_validation_config
                WHERE is_enabled = TRUE
                GROUP BY validator_type
                ORDER BY count DESC
            """)
            validators = cur.fetchall()
            print("  验证器类型：")
            for row in validators:
                print(f"    {row[0]}: {row[1]} 个配置, 覆盖 {row[2]} 个指标")
            
            # 测试6：指标覆盖度
            print("\n[测试6] 指标覆盖度")
            cur.execute("""
                SELECT 
                    metric_key,
                    COUNT(*) as validator_count,
                    STRING_AGG(validator_type, ', ' ORDER BY priority) as validators
                FROM calculation_validation_config
                WHERE is_enabled = TRUE
                GROUP BY metric_key
                ORDER BY validator_count DESC, metric_key
            """)
            metrics = cur.fetchall()
            print(f"  已配置验证规则的指标数: {len(metrics)}")
            print("  前5个指标：")
            for row in metrics[:5]:
                print(f"    {row[0]}: {row[1]} 个验证器 ({row[2]})")
            
            # 测试7：参数完整性检查
            print("\n[测试7] 参数完整性检查")
            cur.execute("""
                SELECT 
                    metric_key,
                    validator_type,
                    params
                FROM calculation_validation_config
                WHERE params IS NULL OR params = '{}'::jsonb
                LIMIT 5
            """)
            empty_params = cur.fetchall()
            if empty_params:
                print(f"  ⚠ 发现 {len(empty_params)} 个空参数配置（示例）：")
                for row in empty_params:
                    print(f"    {row[0]}.{row[1]}: {row[2]}")
            else:
                print("  ✓ 所有配置都有参数")
            
            # 测试8：优先级分布
            print("\n[测试8] 优先级分布")
            cur.execute("""
                SELECT 
                    priority,
                    COUNT(*) as count
                FROM calculation_validation_config
                WHERE is_enabled = TRUE
                GROUP BY priority
                ORDER BY priority
            """)
            priorities = cur.fetchall()
            print("  优先级分布：")
            for row in priorities:
                print(f"    优先级 {row[0]}: {row[1]} 个配置")
            
            # 测试9：三级参数优先级模拟
            print("\n[测试9] 三级参数优先级模拟")
            # 模拟查询：全局 + 泵站 + 设备
            cur.execute("""
                SELECT
                    metric_key,
                    validator_type,
                    params,
                    priority,
                    CASE
                        WHEN device_id IS NOT NULL THEN '设备级'
                        WHEN station_id IS NOT NULL THEN '泵站级'
                        ELSE '全局级'
                    END as config_level,
                    CASE
                        WHEN device_id IS NOT NULL THEN 3
                        WHEN station_id IS NOT NULL THEN 2
                        ELSE 1
                    END as level_priority
                FROM calculation_validation_config
                WHERE is_enabled = TRUE
                    AND metric_key = 'pump_flow_rate'
                    AND (
                        (station_id IS NULL AND device_id IS NULL)  -- 全局配置
                        OR (station_id = 1 AND device_id IS NULL)  -- 站点配置
                        OR (station_id = 1 AND device_id = 1)     -- 设备配置
                    )
                ORDER BY metric_key, level_priority DESC, priority ASC
            """)
            priority_test = cur.fetchall()
            print(f"  pump_flow_rate 指标的验证配置（模拟station_id=1, device_id=1）：")
            if priority_test:
                for row in priority_test:
                    print(f"    {row[4]}: {row[1]} (优先级={row[3]})")
            else:
                print("    无配置")
            
            # 测试10：数据一致性检查
            print("\n[测试10] 数据一致性检查")
            
            # 检查外键完整性
            cur.execute("""
                SELECT COUNT(*)
                FROM calculation_validation_config cvc
                LEFT JOIN dim_stations s ON s.id = cvc.station_id
                WHERE cvc.station_id IS NOT NULL AND s.id IS NULL
            """)
            orphan_stations = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*)
                FROM calculation_validation_config cvc
                LEFT JOIN dim_devices d ON d.id = cvc.device_id
                WHERE cvc.device_id IS NOT NULL AND d.id IS NULL
            """)
            orphan_devices = cur.fetchone()[0]
            
            if orphan_stations == 0 and orphan_devices == 0:
                print("  ✓ 无孤立记录（外键完整性良好）")
            else:
                print(f"  ✗ 发现孤立记录: {orphan_stations} 个泵站, {orphan_devices} 个设备")
            
            # 测试11：总结
            print("\n[测试11] 总结")
            cur.execute("""
                SELECT 
                    COUNT(*) as total_configs,
                    COUNT(DISTINCT metric_key) as total_metrics,
                    COUNT(DISTINCT validator_type) as total_validators,
                    COUNT(CASE WHEN is_enabled = TRUE THEN 1 END) as enabled_configs,
                    COUNT(CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1 END) as global_configs,
                    COUNT(CASE WHEN station_id IS NOT NULL AND device_id IS NULL THEN 1 END) as station_configs,
                    COUNT(CASE WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN 1 END) as device_configs
                FROM calculation_validation_config
            """)
            summary = cur.fetchone()
            print("  验证配置总览：")
            print(f"    总配置数: {summary[0]}")
            print(f"    覆盖指标数: {summary[1]}")
            print(f"    验证器类型数: {summary[2]}")
            print(f"    启用配置数: {summary[3]}")
            print(f"    全局级配置: {summary[4]}")
            print(f"    泵站级配置: {summary[5]}")
            print(f"    设备级配置: {summary[6]}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_validation_config_3tier()

