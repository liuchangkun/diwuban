"""
检查pump_flow_rate和pump_head数据
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def check_data():
    """检查数据"""
    print("="*80)
    print("检查 pump_flow_rate 和 pump_head 数据")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询pump_flow_rate和pump_head的数据
            cur.execute("""
                SELECT 
                    metric_id,
                    COUNT(*) as total_count,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time,
                    COUNT(DISTINCT device_id) as device_count
                FROM fact_measurements
                WHERE station_id = 1
                  AND metric_id IN (18, 17)  -- pump_flow_rate, pump_head
                GROUP BY metric_id
                ORDER BY metric_id
            """)
            
            rows = cur.fetchall()
            print(f"\n找到 {len(rows)} 个指标:")
            for row in rows:
                metric_id, total_count, min_time, max_time, device_count = row
                metric_name = 'pump_flow_rate' if metric_id == 18 else 'pump_head'
                print(f"\n{metric_name} (metric_id={metric_id}):")
                print(f"  - 总记录数: {total_count}")
                print(f"  - 时间范围: {min_time} ~ {max_time}")
                print(f"  - 设备数: {device_count}")

            # 查询每个设备的数据
            print(f"\n各设备数据统计:")
            cur.execute("""
                SELECT 
                    device_id,
                    metric_id,
                    COUNT(*) as count,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time
                FROM fact_measurements
                WHERE station_id = 1
                  AND metric_id IN (18, 17)
                GROUP BY device_id, metric_id
                ORDER BY device_id, metric_id
            """)
            
            rows = cur.fetchall()
            for row in rows:
                device_id, metric_id, count, min_time, max_time = row
                metric_name = 'pump_flow_rate' if metric_id == 18 else 'pump_head'
                print(f"  设备{device_id} - {metric_name}: {count}条 ({min_time} ~ {max_time})")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 检查数据
    check_data()

