"""
诊断4个指标的完整执行流程

测试指标：
1. pump_inlet_pressure
2. main_pipeline_inlet_pressure
3. pump_speed
4. pump_torque
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from datetime import datetime, timezone
import time

# 初始化数据库
from app.adapters.db import init_database
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

# 导入调度器
from app.services.calculation.shared.scheduler import Scheduler

def main():
    print("\n" + "=" * 100)
    print("[DIAGNOSIS] 4个指标诊断测试")
    print("=" * 100)
    
    # 测试参数
    start_time = datetime(2025, 10, 23, 4, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 4, 5, 0, tzinfo=timezone.utc)  # 5分钟测试
    
    # 创建调度器
    scheduler = Scheduler(max_workers=4, enable_adaptive_chunk=False)
    
    # 测试4个指标
    metrics_to_test = [
        {
            'metric_key': 'pump_inlet_pressure',
            'device_ids': [6],  # 只测试设备6
            'description': '泵入口压力'
        },
        {
            'metric_key': 'main_pipeline_inlet_pressure',
            'device_ids': [7],  # 总管设备
            'description': '总管入口压力'
        },
        {
            'metric_key': 'pump_speed',
            'device_ids': [6],  # 只测试设备6
            'description': '泵转速'
        },
        {
            'metric_key': 'pump_torque',
            'device_ids': [6],  # 只测试设备6
            'description': '泵扭矩'
        }
    ]
    
    print(f"\n[CONFIG] 测试配置:")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    print(f"   - 指标数量: {len(metrics_to_test)}个")
    print(f"   - 测试设备: 设备6(泵)和设备7(总管)")
    
    # 逐个测试每个指标
    all_results = {}
    
    for i, metric_config in enumerate(metrics_to_test, 1):
        metric_key = metric_config['metric_key']
        device_ids = metric_config['device_ids']
        description = metric_config['description']
        
        print(f"\n{'=' * 100}")
        print(f"[{i}/{len(metrics_to_test)}] 测试指标: {metric_key} ({description})")
        print(f"{'=' * 100}")
        
        try:
            metric_start = time.time()
            
            result = scheduler.schedule_single_metric(
                metric_key=metric_key,
                device_ids=device_ids,
                start_time=start_time,
                end_time=end_time,
                time_chunk_hours=1  # 1小时分片
            )
            
            metric_duration = time.time() - metric_start
            
            all_results[metric_key] = result

            print(f"\n[SUCCESS] {metric_key} 执行完成:")
            print(f"   - 总任务数: {result.get('total_tasks', 0)}")
            print(f"   - 成功任务: {result.get('success_count', 0)}")
            print(f"   - 失败任务: {result.get('total_tasks', 0) - result.get('success_count', 0)}")
            print(f"   - 写入记录: {result.get('total_points', 0):,} 条")
            print(f"   - 执行时长: {metric_duration:.2f} 秒")

            # 打印失败任务的错误信息
            if result.get('results'):
                failed_results = [r for r in result['results'] if not r.success]
                if failed_results:
                    print(f"\n   失败任务详情:")
                    for failed_result in failed_results[:3]:  # 只显示前3个
                        print(f"   - 任务ID: {failed_result.task_id}")
                        print(f"     设备ID: {failed_result.device_id}")
                        if failed_result.error_message:
                            # 只显示前500个字符
                            error_msg = failed_result.error_message[:500]
                            print(f"     错误: {error_msg}")

        except Exception as e:
            print(f"\n[ERROR] {metric_key} 执行失败:")
            print(f"   - 错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            all_results[metric_key] = {
                'error': str(e),
                'total_tasks': 0,
                'success_count': 0,
                'failed_count': 0,
                'total_points': 0
            }
    
    # 打印总结
    print(f"\n{'=' * 100}")
    print("[SUMMARY] 诊断总结")
    print(f"{'=' * 100}")

    for metric_key, result in all_results.items():
        if 'error' in result:
            print(f"\n[FAILED] {metric_key}: 失败")
            print(f"   错误: {result['error']}")
        else:
            success_rate = result['success_count'] / result['total_tasks'] * 100 if result['total_tasks'] > 0 else 0
            print(f"\n[SUCCESS] {metric_key}: 成功")
            print(f"   成功率: {success_rate:.1f}% ({result['success_count']}/{result['total_tasks']})")
            print(f"   写入记录: {result['total_points']:,} 条")

    # 关闭调度器
    scheduler.shutdown()

    print(f"\n{'=' * 100}")
    print("[DONE] 诊断测试完成")
    print(f"{'=' * 100}\n")

if __name__ == "__main__":
    main()

