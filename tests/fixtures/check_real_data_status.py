"""
检查真实数据状态

检查device_id=1-3的数据记录数和时间范围。
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
    """检查真实数据状态"""
    
    print("=" * 80)
    print("检查真实数据状态 (device_id=1-3)")
    print("=" * 80)
    print()
    
    # 初始化数据库连接池
    settings = load_settings(Path("configs"))
    init_database(settings)
    print("✅ 数据库连接池已初始化\n")
    
    # 目标时间范围
    target_start = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    target_end = datetime(2025, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
    
    # 原始真实数据的时间范围
    real_start = datetime(2025, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    real_end = datetime(2025, 10, 23, 7, 0, 0, tzinfo=timezone.utc)  # 23小时
    
    print(f"📅 原始真实数据范围: {real_start} ~ {real_end} (23小时)")
    print(f"📅 目标数据范围: {target_start} ~ {target_end} (30天)")
    print()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 检查每个设备的数据
            print("=" * 80)
            print("设备数据统计")
            print("=" * 80)
            print()
            
            for device_id in [1, 2, 3]:
                # 查询总记录数和时间范围
                cur.execute("""
                    SELECT COUNT(*) as total_count,
                           MIN(ts_bucket) as min_ts,
                           MAX(ts_bucket) as max_ts,
                           COUNT(DISTINCT metric_id) as metric_count
                    FROM fact_measurements
                    WHERE device_id = %s
                """, (device_id,))
                
                result = cur.fetchone()
                total_count, min_ts, max_ts, metric_count = result
                
                print(f"device_id={device_id}:")
                print(f"  总记录数: {total_count:,}")
                print(f"  指标数: {metric_count}")
                
                if min_ts and max_ts:
                    print(f"  时间范围: {min_ts} ~ {max_ts}")
                    
                    # 计算时间跨度
                    time_span = max_ts - min_ts
                    hours = time_span.total_seconds() / 3600
                    days = time_span.days
                    
                    print(f"  时间跨度: {days}天 {hours % 24:.1f}小时 (总计{hours:.1f}小时)")
                    
                    # 检查是否有扩展数据（超过23小时）
                    if max_ts > real_end:
                        print(f"  ✅ 已有扩展数据（超过原始23小时）")
                        
                        # 查询扩展数据的记录数
                        cur.execute("""
                            SELECT COUNT(*) as extended_count
                            FROM fact_measurements
                            WHERE device_id = %s
                              AND ts_bucket > %s
                        """, (device_id, real_end))
                        
                        extended_count = cur.fetchone()[0]
                        print(f"  扩展数据记录数: {extended_count:,}")
                    else:
                        print(f"  ❌ 仅有原始数据（23小时）")
                    
                    # 检查是否达到目标时间
                    if max_ts >= target_end:
                        print(f"  ✅ 已达到目标时间（30天）")
                    else:
                        remaining_seconds = (target_end - max_ts).total_seconds()
                        remaining_days = remaining_seconds / 86400
                        print(f"  ⚠️  距离目标时间还差: {remaining_days:.1f}天")
                else:
                    print(f"  ❌ 无数据")
                
                print()
            
            # 检查是否有source_hint='e2e_test_data'的记录（扩展数据的标记）
            print("=" * 80)
            print("扩展数据标记检查")
            print("=" * 80)
            print()
            
            cur.execute("""
                SELECT device_id,
                       COUNT(*) as extended_count,
                       MIN(ts_bucket) as min_ts,
                       MAX(ts_bucket) as max_ts
                FROM fact_measurements
                WHERE device_id IN (1, 2, 3)
                  AND source_hint = 'e2e_test_data'
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            results = cur.fetchall()
            
            if results:
                for row in results:
                    device_id, extended_count, min_ts, max_ts = row
                    print(f"device_id={device_id}:")
                    print(f"  扩展数据记录数: {extended_count:,}")
                    print(f"  时间范围: {min_ts} ~ {max_ts}")
                    print()
            else:
                print("❌ 未找到扩展数据标记（source_hint='e2e_test_data'）")
                print()
    
    print("=" * 80)
    print("✅ 数据状态检查完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()

