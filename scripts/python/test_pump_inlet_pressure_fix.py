#!/usr/bin/env python3
"""
测试pump_inlet_pressure修复后的计算结果
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.calculation.shared.shared_services import SharedServices
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings


def test_pump_inlet_pressure():
    """测试pump_inlet_pressure计算"""

    print("=" * 80)
    print("pump_inlet_pressure 修复验证测试")
    print("=" * 80)

    # 步骤1: 初始化
    print("\n📋 步骤1: 初始化数据库和 SharedServices")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    shared_services = SharedServices()
    
    print("✅ SharedServices 初始化完成")
    
    # 步骤2: 配置测试参数
    print("\n📋 步骤2: 配置测试参数")
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]  # 所有6台泵
    
    # 使用有数据的时间范围（2025-10-22 16:00 ~ 2025-10-23 15:00）
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=tz)
    
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    
    # 步骤3: 使用 Scheduler 调度计算
    print("\n📋 步骤3: 使用 Scheduler 调度计算")
    print("=" * 80)
    
    import time
    start_exec = time.time()
    
    result = shared_services.scheduler.schedule_single_metric(
        metric_key='pump_inlet_pressure',
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24  # 24小时分片（整个时间范围）
    )
    
    duration = time.time() - start_exec
    
    # 步骤4: 打印结果
    print("\n📊 执行结果摘要")
    print("=" * 80)
    print(f"✅ 总耗时: {duration:.2f}秒")
    print(f"✅ 总任务数: {result['total_tasks']}")
    print(f"✅ 成功任务: {result['success_count']}")
    print(f"✅ 失败任务: {result['failure_count']}")
    print(f"✅ 成功率: {result['success_rate']}")
    print(f"✅ 写入记录: {result['total_points']:,}条")
    print(f"✅ 平均任务耗时: {result['avg_duration_per_task_seconds']:.2f}秒")
    
    # 步骤5: 验证计算结果
    print("\n📋 步骤5: 验证计算结果")
    print("=" * 80)
    
    from app.adapters.db import get_connection
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 先查询metric_id
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure'
            """)
            metric_row = cur.fetchone()
            if not metric_row:
                print("\n❌ 未找到pump_inlet_pressure的metric_id配置")
                return result

            metric_id = metric_row[0]
            print(f"   - pump_inlet_pressure的metric_id: {metric_id}")

            # 查询刚才写入的数据
            cur.execute("""
                SELECT device_id,
                       COUNT(*) as count,
                       MIN(value) as min_value,
                       MAX(value) as max_value,
                       AVG(value) as avg_value
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id IN (1, 2, 3, 4, 5, 6)
                  AND ts_raw >= %s
                  AND ts_raw < %s
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id, start_time, end_time))
            
            rows = cur.fetchall()
            
            if rows:
                print("\n✅ 计算结果统计（按设备）：")
                print(f"{'设备ID':<10} {'记录数':<10} {'最小值(MPa)':<15} {'最大值(MPa)':<15} {'平均值(MPa)':<15}")
                print("-" * 70)
                
                for row in rows:
                    device_id, count, min_val, max_val, avg_val = row
                    print(f"{device_id:<10} {count:<10} {min_val:<15.6f} {max_val:<15.6f} {avg_val:<15.6f}")
                
                # 验证压力值合理性
                print("\n📊 合理性检查：")
                all_valid = True
                for row in rows:
                    device_id, count, min_val, max_val, avg_val = row
                    if min_val < 0:
                        print(f"  ❌ 设备{device_id}: 最小值为负数 ({min_val:.6f} MPa)")
                        all_valid = False
                    elif min_val < 0.05:
                        print(f"  ⚠️  设备{device_id}: 最小值偏小 ({min_val:.6f} MPa)")
                    elif max_val > 1.0:
                        print(f"  ⚠️  设备{device_id}: 最大值偏大 ({max_val:.6f} MPa)")
                    else:
                        print(f"  ✅ 设备{device_id}: 压力值在合理范围内")
                
                if all_valid:
                    print("\n✅ 所有设备的压力值都为正数，修复成功！")
                else:
                    print("\n❌ 部分设备的压力值异常，需要进一步检查")
            else:
                print("\n⚠️  未找到计算结果数据")
    
    return result


if __name__ == "__main__":
    try:
        result = test_pump_inlet_pressure()
        sys.exit(0 if result['success_count'] > 0 else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

