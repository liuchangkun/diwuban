"""
重新计算 pump_inlet_pressure 历史数据

计算范围:
- 设备: 1, 2, 3, 4, 5, 6
- 时间: 全部历史数据
- 使用修正后的公式和参数

执行方式:
    python scripts/recalculate_pump_inlet_pressure_20251119.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings
from app.services.calculation.shared.shared_services import SharedServices

def main():
    """重新计算历史数据"""
    print("=" * 100)
    print("开始重新计算 pump_inlet_pressure 历史数据")
    print("=" * 100)
    
    # 加载配置并初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)

    # 查询时间范围
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询所有设备的时间范围
            print("\n[1/3] 查询历史数据时间范围...")
            cur.execute("""
                SELECT 
                    device_id,
                    MIN(ts_bucket) as min_ts,
                    MAX(ts_bucket) as max_ts,
                    COUNT(*) as count
                FROM fact_measurements
                WHERE device_id = ANY(%s)
                GROUP BY device_id
                ORDER BY device_id
            """, ([1, 2, 3, 4, 5, 6],))
            
            device_ranges = {}
            print("\n   设备ID | 最早时间            | 最晚时间            | 数据量")
            print("   " + "-" * 80)
            
            for row in cur.fetchall():
                device_id, min_ts, max_ts, count = row
                device_ranges[device_id] = (min_ts, max_ts, count)
                print(f"   {device_id:6d} | {min_ts} | {max_ts} | {count:9d}")
            
            if not device_ranges:
                print("\n⚠️  没有历史数据需要计算")
                return
            
            # 计算全局时间范围
            global_min_ts = min(r[0] for r in device_ranges.values())
            global_max_ts = max(r[1] for r in device_ranges.values())
            total_count = sum(r[2] for r in device_ranges.values())
            
            print("   " + "-" * 80)
            print(f"   全局   | {global_min_ts} | {global_max_ts} | {total_count:9d}")
    
    # 执行计算
    print(f"\n[2/3] 重新计算 pump_inlet_pressure...")
    print(f"   时间范围: {global_min_ts} ~ {global_max_ts}")
    print(f"   设备数量: {len(device_ranges)} 个")
    print(f"   预计数据量: {total_count} 条")

    # 初始化 SharedServices
    shared_services = SharedServices()

    # 设置时区
    tz = pytz.timezone('Asia/Shanghai')

    # 使用 scheduler 调度计算
    try:
        result = shared_services.scheduler.schedule_single_metric(
            metric_key='pump_inlet_pressure',
            device_ids=sorted(device_ranges.keys()),
            start_time=global_min_ts.astimezone(tz) if global_min_ts.tzinfo else tz.localize(global_min_ts),
            end_time=(global_max_ts + timedelta(seconds=1)).astimezone(tz) if global_max_ts.tzinfo else tz.localize(global_max_ts + timedelta(seconds=1)),
            time_chunk_hours=24
        )

        total_success = result.get('total_success', 0)
        total_failed = result.get('total_failed', 0)

        print(f"\n   ✓ 计算完成: 成功 {total_success} 条, 失败 {total_failed} 条")

    except Exception as e:
        print(f"\n   ❌ 计算失败: {e}")
        import traceback
        traceback.print_exc()
        total_success = 0
        total_failed = total_count
    
    # 验证结果
    print(f"\n[3/3] 验证计算结果...")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询 pump_inlet_pressure 的 metric_id
            cur.execute("""
                SELECT id FROM dim_metric_config WHERE metric_key = %s
            """, ('pump_inlet_pressure',))
            
            metric_id = cur.fetchone()[0]
            
            # 统计计算结果
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as total_count,
                    COUNT(value) as valid_count,
                    COUNT(*) - COUNT(value) as invalid_count,
                    ROUND(COUNT(value)::numeric / COUNT(*) * 100, 2) as valid_ratio,
                    MIN(value) as min_pressure,
                    MAX(value) as max_pressure,
                    ROUND(AVG(value)::numeric, 4) as avg_pressure
                FROM fact_measurements
                WHERE metric_id = %s
                  AND device_id = ANY(%s)
                GROUP BY device_id
                ORDER BY device_id
            """, (metric_id, [1, 2, 3, 4, 5, 6]))
            
            print("\n   设备ID | 总数    | 有效数  | 无效数  | 有效率  | 最小值   | 最大值   | 平均值")
            print("   " + "-" * 90)
            
            total_valid = 0
            total_invalid = 0
            
            for row in cur.fetchall():
                device_id, total, valid, invalid, ratio, min_val, max_val, avg_val = row
                total_valid += valid
                total_invalid += invalid
                print(f"   {device_id:6d} | {total:7d} | {valid:7d} | {invalid:7d} | {ratio:6.2f}% | {float(min_val or 0):8.4f} | {float(max_val or 0):8.4f} | {float(avg_val or 0):8.4f}")
            
            overall_ratio = (total_valid / (total_valid + total_invalid) * 100) if (total_valid + total_invalid) > 0 else 0
            
            print("   " + "-" * 90)
            print(f"   总计   | {total_valid + total_invalid:7d} | {total_valid:7d} | {total_invalid:7d} | {overall_ratio:6.2f}%")
    
    # 最终结果
    print("\n" + "=" * 100)
    print("重新计算完成")
    print("=" * 100)
    print(f"   成功: {total_success} 条")
    print(f"   失败: {total_failed} 条")
    print(f"   有效率: {overall_ratio:.2f}%")
    
    if overall_ratio >= 99.0:
        print("\n✅ 计算成功！无效值比例 < 1%")
    else:
        print(f"\n⚠️  警告：无效值比例 {100 - overall_ratio:.2f}% 超过 1%")
    
    print("=" * 100)

if __name__ == "__main__":
    main()

