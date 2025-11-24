"""
重新运行所有9个指标的计算，验证修复效果
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.services.calculation.shared.scheduler import Scheduler


def main():
    """主函数"""
    print("\n" + "="*100)
    print("重新运行所有9个指标的计算")
    print("="*100 + "\n")
    
    # 初始化
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 定义时间范围（最近2小时）
    end_time = datetime(2025, 10, 23, 8, 0, 0)
    start_time = end_time - timedelta(hours=2)
    
    print(f"时间范围: {start_time} ~ {end_time}")
    print(f"{'='*100}\n")
    
    # 定义所有指标
    metrics = [
        'pump_flow_rate',
        'pump_inlet_pressure',
        'pump_head',
        'pump_efficiency',
        'pump_speed',
        'pump_torque',
        'pump_hydraulic_power',
        'pump_shaft_power',
        'main_pipeline_inlet_pressure'
    ]
    
    # 定义设备
    devices = [1, 2, 3, 4, 5, 6]
    
    # 运行每个指标
    scheduler = Scheduler()

    for metric in metrics:
        print(f"\n{'='*100}")
        print(f"运行指标: {metric}")
        print(f"{'='*100}")

        try:
            # 为所有设备运行
            tasks = scheduler.schedule_single_metric(
                metric_key=metric,
                device_ids=devices,
                start_time=start_time,
                end_time=end_time,
                time_chunk_hours=2
            )

            print(f"\n  生成了 {len(tasks)} 个任务")

            # 执行任务
            from app.services.calculation.shared.calculator import calculate_task
            results = scheduler.execute_tasks(tasks, calculate_task)

            # 统计结果
            success_count = sum(1 for r in results if r.success)
            total_records = sum(r.records_written for r in results if r.success)

            print(f"  ✅ 成功: {success_count}/{len(results)} 个任务")
            print(f"  📝 写入: {total_records:,} 条记录")

            # 显示失败的任务
            failed_tasks = [r for r in results if not r.success]
            if failed_tasks:
                print(f"\n  ❌ 失败的任务:")
                for r in failed_tasks[:3]:  # 只显示前3个
                    print(f"    - 设备{r.device_id}: {r.error}")

            print(f"\n{metric} 完成")

        except Exception as e:
            print(f"\n❌ {metric} 失败: {e}")
    
    print(f"\n{'='*100}")
    print("所有指标运行完成")
    print(f"{'='*100}\n")


if __name__ == '__main__':
    main()

