#!/usr/bin/env python3
"""
验证三个缺失指标的完整计算流程
- pump_flow_rate
- pump_inlet_pressure  
- pump_head
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.calculation.shared.shared_services import SharedServices
from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def test_three_metrics():
    """测试三个缺失指标的完整计算流程"""
    
    print("=" * 100)
    print("三个缺失指标完整计算流程验证")
    print("=" * 100)
    
    # 初始化
    print("\n📋 步骤1: 初始化")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    shared_services = SharedServices()
    print("✅ 初始化完成")
    
    # 配置测试参数
    print("\n📋 步骤2: 配置测试参数")
    device_ids = [1, 2, 3, 4, 5, 6]  # 所有6台泵
    tz = pytz.timezone('Asia/Shanghai')
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=tz)
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=tz)
    
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    
    # 定义三个指标
    metrics = ['pump_flow_rate', 'pump_inlet_pressure', 'pump_head']
    
    print(f"   - 测试指标: {metrics}")
    
    # 执行计算
    print("\n📋 步骤3: 使用调度器执行三个指标的计算")
    print("=" * 100)
    
    import time
    overall_start = time.time()
    
    all_results = {}
    
    for metric_key in metrics:
        print(f"\n{'='*100}")
        print(f"🔄 正在计算指标: {metric_key}")
        print(f"{'='*100}")
        
        metric_start = time.time()
        
        result = shared_services.scheduler.schedule_single_metric(
            metric_key=metric_key,
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=24
        )
        
        metric_duration = time.time() - metric_start
        
        all_results[metric_key] = {
            'result': result,
            'duration': metric_duration
        }
        
        print(f"\n✅ {metric_key} 计算完成")
        print(f"   - 耗时: {metric_duration:.2f}秒")
        print(f"   - 总任务: {result['total_tasks']}")
        print(f"   - 成功: {result['success_count']}")
        print(f"   - 失败: {result['failure_count']}")
        print(f"   - 写入记录: {result['total_points']:,}条")
    
    overall_duration = time.time() - overall_start
    
    # 打印总体结果
    print("\n" + "=" * 100)
    print("📊 总体执行结果")
    print("=" * 100)
    print(f"✅ 总耗时: {overall_duration:.2f}秒")
    print(f"\n各指标详情:")
    
    total_tasks = 0
    total_success = 0
    total_failure = 0
    total_points = 0
    
    for metric_key, data in all_results.items():
        result = data['result']
        duration = data['duration']
        
        total_tasks += result['total_tasks']
        total_success += result['success_count']
        total_failure += result['failure_count']
        total_points += result['total_points']
        
        print(f"\n  {metric_key}:")
        print(f"    - 耗时: {duration:.2f}秒")
        print(f"    - 任务: {result['total_tasks']} (成功:{result['success_count']}, 失败:{result['failure_count']})")
        print(f"    - 写入: {result['total_points']:,}条")
        success_rate_str = str(result['success_rate'])
        if success_rate_str.endswith('%'):
            success_rate_str = success_rate_str[:-1]
        print(f"    - 成功率: {success_rate_str}%")
    
    print(f"\n汇总:")
    print(f"  - 总任务数: {total_tasks}")
    print(f"  - 总成功数: {total_success}")
    print(f"  - 总失败数: {total_failure}")
    print(f"  - 总写入记录: {total_points:,}条")
    print(f"  - 总体成功率: {(total_success/total_tasks*100) if total_tasks > 0 else 0:.1f}%")
    
    # 验证数据库写入
    print("\n" + "=" * 100)
    print("📋 步骤4: 验证数据库写入结果")
    print("=" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for metric_key in metrics:
                # 查询metric_id
                cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = %s", (metric_key,))
                metric_row = cur.fetchone()
                if not metric_row:
                    print(f"\n❌ {metric_key}: 未找到metric_id配置")
                    continue
                
                metric_id = metric_row[0]
                
                # 查询写入的数据统计
                cur.execute("""
                    SELECT COUNT(*) as total_count,
                           COUNT(DISTINCT device_id) as device_count
                    FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id IN (1, 2, 3, 4, 5, 6)
                      AND ts_raw >= %s
                      AND ts_raw < %s
                """, (metric_id, start_time, end_time))
                
                row = cur.fetchone()
                total_count, device_count = row
                
                print(f"\n✅ {metric_key} (metric_id={metric_id}):")
                print(f"   - 数据库记录数: {total_count:,}条")
                print(f"   - 涉及设备数: {device_count}台")
    
    print("\n" + "=" * 100)
    print("✅ 三个缺失指标完整计算流程验证完成")
    print("=" * 100)
    
    return all_results


if __name__ == "__main__":
    try:
        results = test_three_metrics()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

