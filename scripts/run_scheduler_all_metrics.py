"""
调度器执行所有已完成指标的计算任务

执行8个已完成的指标：
1. pump_flow_rate
2. pump_inlet_pressure
3. main_pipeline_inlet_pressure
4. pump_head
5. pump_efficiency
6. pump_speed
7. pump_shaft_power
8. pump_torque

设备范围：1-6（泵设备）
时间范围：2025-10-22 08:00:00 UTC ~ 2025-10-23 07:19:37 UTC（约23小时）
泵站ID：1
"""

from pathlib import Path
from datetime import datetime, timezone
import time
import json

# 初始化数据库
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

# 导入Scheduler
from app.services.calculation.shared.scheduler import Scheduler

def main():
    print("=" * 100)
    print("调度器执行所有已完成指标的计算任务")
    print("=" * 100)
    
    # 配置参数
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 19, 37, tzinfo=timezone.utc)
    
    # 已完成的指标列表（不包括main_pipeline_outlet_pressure）
    metrics = [
        "pump_flow_rate",
        "pump_inlet_pressure",
        "main_pipeline_inlet_pressure",
        "pump_head",
        "pump_efficiency",
        "pump_speed",
        "pump_shaft_power",
        "pump_torque",
    ]
    
    print(f"\n📋 执行配置:")
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 指标数量: {len(metrics)}个")
    print(f"   - 指标列表: {', '.join(metrics)}")
    
    # 创建调度器
    print(f"\n📊 创建调度器...")
    scheduler = Scheduler(max_workers=10, enable_adaptive_chunk=True)
    print(f"   ✅ 调度器已创建（max_workers=10, 自适应分片已启用）")
    
    # 执行所有指标计算
    print(f"\n🚀 开始执行所有指标计算...")
    print(f"{'=' * 100}")
    
    execution_start = time.time()
    
    results = scheduler.schedule_all_metrics(
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=None,  # 使用自适应分片
        metrics=metrics
    )
    
    execution_duration = time.time() - execution_start
    
    # 打印结果摘要
    print(f"\n{'=' * 100}")
    print(f"📊 执行结果摘要")
    print(f"{'=' * 100}")
    
    total_success = 0
    total_failure = 0
    total_points = 0
    
    for metric_key, result in results.items():
        success_count = result.get('success_count', 0)
        failure_count = result.get('failure_count', 0)
        points = result.get('total_points', 0)
        duration = result.get('total_duration_seconds', 0)
        success_rate = result.get('success_rate', 'N/A')
        
        total_success += success_count
        total_failure += failure_count
        total_points += points
        
        status = "✅" if failure_count == 0 else "⚠️"
        print(f"\n{status} {metric_key}:")
        print(f"   - 成功任务: {success_count}/{success_count + failure_count}")
        print(f"   - 成功率: {success_rate}")
        print(f"   - 写入记录: {points:,}条")
        print(f"   - 耗时: {duration:.2f}秒")
    
    print(f"\n{'=' * 100}")
    print(f"📈 总体统计:")
    print(f"   - 总指标数: {len(results)}个")
    print(f"   - 总成功任务: {total_success}个")
    print(f"   - 总失败任务: {total_failure}个")
    print(f"   - 总写入记录: {total_points:,}条")
    print(f"   - 总耗时: {execution_duration:.2f}秒")
    print(f"   - 平均每指标耗时: {execution_duration / len(results):.2f}秒")
    print(f"{'=' * 100}")
    
    # 保存结果到JSON文件
    output_file = "缺失指标计算改造/scheduler_execution_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 转换结果为可序列化格式
        serializable_results = {}
        for metric_key, result in results.items():
            serializable_results[metric_key] = {
                'total_tasks': result.get('total_tasks', 0),
                'success_count': result.get('success_count', 0),
                'failure_count': result.get('failure_count', 0),
                'total_points': result.get('total_points', 0),
                'total_duration_seconds': result.get('total_duration_seconds', 0),
                'success_rate': result.get('success_rate', 'N/A'),
            }
        
        json.dump({
            'execution_time': execution_duration,
            'total_success': total_success,
            'total_failure': total_failure,
            'total_points': total_points,
            'metrics': serializable_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 执行结果已保存到: {output_file}")
    print(f"\n✅ 所有指标计算完成！")

if __name__ == '__main__':
    main()

