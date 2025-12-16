"""
验证数据完整性

检查所有测试设备的数据是否完整。
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def main():
    """验证数据完整性"""
    
    print("=" * 80)
    print("验证数据完整性")
    print("=" * 80)
    print()
    
    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    # 目标时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    
    print(f"📅 目标时间范围: {start_time} ~ {end_time}")
    print(f"📏 时间跨度: 30天\n")
    
    # 测试设备列表
    test_devices = list(range(7, 19))  # device_id=7-18
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 检查每个设备的数据
            print("=" * 80)
            print("检查设备数据")
            print("=" * 80)
            print()
            
            for device_id in test_devices:
                # 查询记录数
                cur.execute("""
                    SELECT COUNT(*) as record_count,
                           MIN(ts_bucket) as min_ts,
                           MAX(ts_bucket) as max_ts,
                           COUNT(DISTINCT metric_id) as metric_count
                    FROM fact_measurements
                    WHERE device_id = %s
                      AND ts_bucket >= %s
                      AND ts_bucket < %s
                """, (device_id, start_time, end_time))
                
                result = cur.fetchone()
                record_count, min_ts, max_ts, metric_count = result
                
                # 预期记录数：30天 × 86400秒 × 5指标 = 12,960,000
                expected_count = 30 * 86400 * 5
                
                status = "✅" if record_count == expected_count and metric_count == 5 else "❌"
                
                print(f"{status} device_id={device_id:2d}: {record_count:>10,} 条记录 "
                      f"(预期: {expected_count:,}), {metric_count} 个指标")
                
                if min_ts and max_ts:
                    print(f"   时间范围: {min_ts} ~ {max_ts}")
                
                if record_count != expected_count:
                    print(f"   ⚠️  记录数不匹配！差异: {record_count - expected_count:,}")
                
                if metric_count != 5:
                    print(f"   ⚠️  指标数不匹配！预期5个，实际{metric_count}个")
                
                print()
            
            # 检查运行状态视图
            print("=" * 80)
            print("检查运行状态视图")
            print("=" * 80)
            print()
            
            cur.execute("""
                SELECT device_id,
                       COUNT(*) as state_count,
                       MIN(ts_bucket) as min_ts,
                       MAX(ts_bucket) as max_ts,
                       SUM(CASE WHEN running = 1 THEN 1 ELSE 0 END) as running_count,
                       SUM(CASE WHEN running = 0 THEN 1 ELSE 0 END) as stopped_count
                FROM mv_device_running_1s
                WHERE device_id = ANY(%s)
                  AND ts_bucket >= %s
                  AND ts_bucket < %s
                GROUP BY device_id
                ORDER BY device_id
            """, (test_devices, start_time, end_time))
            
            results = cur.fetchall()
            
            for row in results:
                device_id, state_count, min_ts, max_ts, running_count, stopped_count = row
                
                # 预期状态数：30天 × 86400秒 = 2,592,000
                expected_state_count = 30 * 86400
                
                running_ratio = running_count / state_count * 100 if state_count > 0 else 0
                
                status = "✅" if state_count == expected_state_count else "❌"
                
                print(f"{status} device_id={device_id:2d}: {state_count:>10,} 条状态记录 "
                      f"(预期: {expected_state_count:,})")
                print(f"   运行: {running_count:,} ({running_ratio:.1f}%), "
                      f"停机: {stopped_count:,} ({100-running_ratio:.1f}%)")
                
                if min_ts and max_ts:
                    print(f"   时间范围: {min_ts} ~ {max_ts}")
                
                print()
    
    print("=" * 80)
    print("✅ 数据完整性验证完成！")
    print("=" * 80)
    print()
    print("下一步: 执行任务10（创建单泵测试脚本）")


if __name__ == "__main__":
    main()

