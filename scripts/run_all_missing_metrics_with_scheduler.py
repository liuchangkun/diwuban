"""
使用 Scheduler 批量执行所有已实现的缺失指标计算

执行范围：
- pump_flow_rate（泵流量）
- pump_head（泵扬程）
- pump_efficiency（泵效率）
- pump_speed（泵转速）
- pump_torque（泵扭矩）
- pump_hydraulic_power（泵水力功率）
- pump_shaft_power（泵轴功率）
- main_pipeline_inlet_pressure（总管入口压力）
- pump_inlet_pressure（泵入口压力）

时间范围：2025-10-22 08:00:00 ~ 2025-10-23 07:13:29 (UTC)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import time

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.shared_services import SharedServices
from app.services.calculation.shared.scheduler import Scheduler


def main():
    """主函数"""
    print("="*80)
    print("使用 Scheduler 批量执行所有已实现的缺失指标计算")
    print("="*80)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 初始化 SharedServices
    print("\n📋 步骤1: 初始化 SharedServices")
    shared_services = SharedServices()
    print("✅ SharedServices 初始化完成")
    
    # 创建 Scheduler
    print("\n📋 步骤2: 创建 Scheduler")
    scheduler = Scheduler()
    print("✅ Scheduler 创建完成")
    
    # 配置计算参数
    station_id = 1
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)
    
    print(f"\n📋 步骤3: 配置计算参数")
    print(f"  - 泵站ID: {station_id}")
    print(f"  - 时间范围: {start_time} ~ {end_time}")
    print(f"  - 时间跨度: {(end_time - start_time).total_seconds() / 3600:.1f} 小时")
    
    # 定义要计算的指标（使用 Scheduler 的 METRIC_ORDER）
    # 注意：pump_hydraulic_power 需要添加到 METRIC_ORDER 中
    metrics_to_calculate = [
        'pump_flow_rate',
        'pump_inlet_pressure',
        'main_pipeline_inlet_pressure',
        'pump_head',
        'pump_efficiency',
        'pump_speed',
        'pump_shaft_power',
        'pump_torque',
        'pump_hydraulic_power',  # 新增指标
    ]

    # 所有设备（包括泵设备1-6和总管设备7）
    all_device_ids = [1, 2, 3, 4, 5, 6, 7]

    print(f"\n📋 步骤4: 准备计算任务")
    print(f"  - 指标数量: {len(metrics_to_calculate)}")
    print(f"  - 设备范围: {all_device_ids}")

    # 执行计算（使用 Scheduler 的 schedule_all_metrics 方法）
    print(f"\n📋 步骤5: 开始批量计算")
    print("="*80)

    overall_start = time.time()

    # 使用 Scheduler 的 schedule_all_metrics 方法
    # 它会按 METRIC_ORDER 顺序自动调度所有指标
    all_results = scheduler.schedule_all_metrics(
        device_ids=all_device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24,  # 使用24小时分片
        metrics=metrics_to_calculate
    )

    overall_duration = time.time() - overall_start
    
    # 汇总统计
    print("\n" + "="*80)
    print("📊 执行汇总")
    print("="*80)

    # all_results 是一个字典：{metric_key: result_dict}
    total_success_metrics = 0
    total_failed_metrics = 0
    total_records = 0
    total_tasks = 0

    print(f"\n各指标统计:")
    print(f"{'指标':<35} {'任务数':<8} {'成功':<8} {'失败':<8} {'记录数':<12} {'耗时(秒)':<10}")
    print("-"*100)

    for metric_key, result in all_results.items():
        success_count = result.get('success_count', 0)
        failure_count = result.get('failure_count', 0)
        total_points = result.get('total_points', 0)
        duration = result.get('duration_seconds', 0)
        task_count = success_count + failure_count

        total_tasks += task_count
        total_records += total_points

        if failure_count == 0:
            total_success_metrics += 1
        else:
            total_failed_metrics += 1

        print(f"{metric_key:<35} {task_count:<8} {success_count:<8} {failure_count:<8} {total_points:<12,} {duration:<10.1f}")

    print("-"*100)
    print(f"{'总计':<35} {total_tasks:<8} {'-':<8} {'-':<8} {total_records:<12,} {overall_duration:<10.1f}")

    print(f"\n总体统计:")
    print(f"  - 总指标数: {len(all_results)}")
    print(f"  - 成功指标: {total_success_metrics} ({total_success_metrics/len(all_results)*100:.1f}%)")
    print(f"  - 失败指标: {total_failed_metrics}")
    print(f"  - 总任务数: {total_tasks}")
    print(f"  - 总写入记录: {total_records:,} 条")
    print(f"  - 总执行耗时: {overall_duration:.1f} 秒")
    print(f"  - 平均速度: {total_records/overall_duration:.0f} 条/秒")

    print("\n✅ 批量计算完成")
    
    return all_results


if __name__ == '__main__':
    results = main()

