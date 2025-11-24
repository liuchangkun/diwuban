"""
pump_hydraulic_power 测试脚本

用途：测试pump_hydraulic_power指标的计算功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from app.services.calculation.metrics.pump_hydraulic_power import calculate_pump_hydraulic_power
from app.services.calculation.shared.scheduler import Task
from app.services.calculation.shared.shared_services import SharedServices
from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def test_single_device(device_id: int, hours: int = 1):
    """
    测试单个设备的pump_hydraulic_power计算

    Args:
        device_id: 设备ID
        hours: 测试时间范围（小时）
    """
    print(f"\n{'='*80}")
    print(f"测试设备 {device_id} 的 pump_hydraulic_power 计算")
    print(f"{'='*80}")

    # 初始化SharedServices
    shared_services = SharedServices()

    # 设置时间范围（使用UTC时间）
    # 使用已知有数据的时间范围：2025-10-22 08:00:00 ~ 2025-10-23 07:13:29 (UTC)
    from datetime import timezone
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 10, 23, 7, 13, 29, tzinfo=timezone.utc)

    print(f"时间范围: {start_time} ~ {end_time} (UTC)")
    print(f"  (使用已知有数据的时间范围)")

    # 创建任务
    task = Task(
        task_id=f"test_pump_hydraulic_power_dev{device_id}",
        station_id=1,
        device_id=device_id,
        metric_key='pump_hydraulic_power',
        start_time=start_time,
        end_time=end_time
    )

    # 执行计算
    result = calculate_pump_hydraulic_power(task)

    # 显示结果
    print(f"\n执行结果:")
    print(f"  - 成功: {result.success}")
    print(f"  - 写入记录数: {result.results_count}")
    if result.error_message:
        print(f"  - 错误信息: {result.error_message}")

    # 查询数据库验证
    if result.success and result.results_count > 0:
        print(f"\n数据库验证:")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_count,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        AVG(value) as avg_value,
                        STDDEV(value) as stddev_value
                    FROM fact_measurements
                    WHERE station_id = 1
                      AND device_id = %s
                      AND metric_id = 67
                      AND ts_bucket >= %s
                      AND ts_bucket < %s
                """, (device_id, start_time, end_time))
                row = cur.fetchone()
                if row:
                    print(f"  - 总记录数: {row[0]}")
                    print(f"  - 最小值: {row[1]:.2f} kW")
                    print(f"  - 最大值: {row[2]:.2f} kW")
                    print(f"  - 平均值: {row[3]:.2f} kW")
                    print(f"  - 标准差: {row[4]:.2f} kW")

    return result


def test_all_devices(hours: int = 1):
    """
    测试所有设备的pump_hydraulic_power计算

    Args:
        hours: 测试时间范围（小时）
    """
    print(f"\n{'='*80}")
    print(f"测试所有设备的 pump_hydraulic_power 计算")
    print(f"{'='*80}")

    device_ids = [1, 2, 3, 4, 5, 6]
    results = {}

    for device_id in device_ids:
        result = test_single_device(device_id, hours)
        results[device_id] = result

    # 汇总结果
    print(f"\n{'='*80}")
    print(f"汇总结果")
    print(f"{'='*80}")

    total_success = sum(1 for r in results.values() if r.success)
    total_records = sum(r.results_count for r in results.values())

    print(f"\n总体统计:")
    print(f"  - 成功设备数: {total_success}/{len(device_ids)}")
    print(f"  - 总写入记录数: {total_records}")

    print(f"\n各设备详情:")
    for device_id, result in results.items():
        status = "✅" if result.success else "❌"
        print(f"  - 设备{device_id}: {status} 写入{result.results_count}条")

    return results


if __name__ == '__main__':
    import argparse

    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)

    parser = argparse.ArgumentParser(description='测试pump_hydraulic_power计算')
    parser.add_argument('--device', type=int, help='设备ID（1-6）')
    parser.add_argument('--hours', type=int, default=1, help='测试时间范围（小时）')
    parser.add_argument('--all', action='store_true', help='测试所有设备')

    args = parser.parse_args()

    if args.all:
        test_all_devices(args.hours)
    elif args.device:
        test_single_device(args.device, args.hours)
    else:
        print("请指定 --device <设备ID> 或 --all")
        print("示例：")
        print("  python scripts/test_pump_hydraulic_power.py --device 1 --hours 1")
        print("  python scripts/test_pump_hydraulic_power.py --all --hours 24")

