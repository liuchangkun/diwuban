"""
删除 pump_inlet_pressure 错误的历史数据

删除范围:
- 设备: 1, 2, 3, 4, 5, 6
- 指标: pump_inlet_pressure
- 时间: 全部历史数据

执行方式:
    python scripts/delete_pump_inlet_pressure_data_20251119.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

def main():
    """删除错误的历史数据"""
    print("=" * 100)
    print("开始删除 pump_inlet_pressure 错误的历史数据")
    print("=" * 100)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 执行删除
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            try:
                # 1. 查询 pump_inlet_pressure 的 metric_id
                print("\n[1/3] 查询 pump_inlet_pressure 的 metric_id...")
                cur.execute("""
                    SELECT id, metric_key, unit_display
                    FROM dim_metric_config
                    WHERE metric_key = %s
                """, ('pump_inlet_pressure',))

                result = cur.fetchone()
                if not result:
                    raise Exception("未找到 pump_inlet_pressure 的配置")

                metric_id, metric_key, unit_display = result
                print(f"   ✓ metric_id = {metric_id}, metric_key = {metric_key}, unit_display = {unit_display}")
                
                # 2. 统计要删除的数据量
                print("\n[2/3] 统计要删除的数据量...")
                cur.execute("""
                    SELECT 
                        device_id,
                        COUNT(*) as count,
                        MIN(ts_bucket) as min_ts,
                        MAX(ts_bucket) as max_ts
                    FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id = ANY(%s)
                    GROUP BY device_id
                    ORDER BY device_id
                """, (metric_id, [1, 2, 3, 4, 5, 6]))
                
                total_count = 0
                print("\n   设备ID | 数据量    | 最早时间            | 最晚时间")
                print("   " + "-" * 70)
                
                for row in cur.fetchall():
                    device_id, count, min_ts, max_ts = row
                    total_count += count
                    print(f"   {device_id:6d} | {count:9d} | {min_ts} | {max_ts}")
                
                print("   " + "-" * 70)
                print(f"   总计   | {total_count:9d}")
                
                if total_count == 0:
                    print("\n⚠️  没有数据需要删除")
                    return
                
                # 3. 删除数据
                print(f"\n[3/3] 删除 {total_count} 条数据...")
                cur.execute("""
                    DELETE FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id = ANY(%s)
                """, (metric_id, [1, 2, 3, 4, 5, 6]))
                
                deleted_count = cur.rowcount
                print(f"   ✓ 删除完成: {deleted_count} 条数据")
                
                if deleted_count != total_count:
                    raise Exception(f"删除数量不匹配: 期望{total_count}条，实际{deleted_count}条")
                
                # 提交事务
                conn.commit()
                
                # 验证删除结果
                print("\n" + "=" * 100)
                print("验证删除结果")
                print("=" * 100)
                
                cur.execute("""
                    SELECT COUNT(*)
                    FROM fact_measurements
                    WHERE metric_id = %s
                      AND device_id = ANY(%s)
                """, (metric_id, [1, 2, 3, 4, 5, 6]))
                
                remaining_count = cur.fetchone()[0]
                print(f"   剩余数据量: {remaining_count} 条")
                
                if remaining_count != 0:
                    raise Exception(f"删除验证失败: 仍有{remaining_count}条数据")
                
                print("=" * 100)
                print(f"\n✅ 成功删除 {deleted_count} 条错误数据！")
                
            except Exception as e:
                conn.rollback()
                print(f"\n❌ 数据删除失败: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

if __name__ == "__main__":
    main()

