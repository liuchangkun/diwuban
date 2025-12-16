"""
重新运行 pump_shaft_power 计算

使用 Scheduler 运行单个指标
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database
from app.core.config.loader_new import load_settings
from app.services.calculation.shared.scheduler import Scheduler


def main():
    """主函数"""
    print("="*100)
    print("重新运行 pump_shaft_power 计算")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 创建 Scheduler
    scheduler = Scheduler()
    
    # 配置参数
    station_id = 1
    device_ids = [1, 2, 3, 4, 5, 6]
    metric_key = 'pump_shaft_power'
    
    # 时间范围（UTC）
    start_time = datetime(2025, 10, 22, 0, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)
    
    print(f"\n配置:")
    print(f"  泵站ID: {station_id}")
    print(f"  设备ID: {device_ids}")
    print(f"  指标: {metric_key}")
    print(f"  时间范围: {start_time} ~ {end_time}")
    
    # 运行计算
    print(f"\n开始计算...")
    print("-"*100)
    
    result = scheduler.schedule_single_metric(
        metric_key=metric_key,
        device_ids=device_ids,
        start_time=start_time,
        end_time=end_time,
        time_chunk_hours=24  # 24小时一个chunk
    )

    # 提取结果列表
    results = result.get('results', [])
    
    # 统计结果
    print(f"\n{'='*100}")
    print("计算完成")
    print(f"{'='*100}")
    
    total_tasks = len(results)
    success_tasks = sum(1 for r in results if r.success)
    total_records = sum(r.results_count for r in results)
    total_duration = sum(r.duration_seconds for r in results)
    
    print(f"\n总任务数: {total_tasks}")
    print(f"成功任务数: {success_tasks}")
    print(f"成功率: {success_tasks/total_tasks*100:.1f}%")
    print(f"写入记录数: {total_records}")
    print(f"总耗时: {total_duration:.2f}秒")
    
    if total_duration > 0:
        print(f"平均速度: {total_records/total_duration:.0f}条/秒")
    
    # 显示每个设备的结果
    print(f"\n{'='*100}")
    print("各设备结果:")
    print(f"{'='*100}")
    print(f"{'设备ID':<10} {'状态':<10} {'记录数':<15} {'耗时(秒)':<15}")
    print("-"*100)
    
    for result in results:
        device_id = result.device_id
        success = '✅ 成功' if result.success else '❌ 失败'
        written_count = result.results_count
        duration = result.duration_seconds

        print(f"{device_id:<10} {success:<10} {written_count:<15} {duration:<15.2f}")

        # 如果失败，显示错误信息
        if not result.success and result.error_message:
            print(f"  错误: {result.error_message}")
    
    print("\n下一步：运行验证脚本检查修复效果")
    print("python scripts/verify_pump_shaft_power_results.py")


if __name__ == '__main__':
    main()

