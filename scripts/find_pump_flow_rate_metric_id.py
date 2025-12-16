"""
查找pump_flow_rate的metric_id
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def find_metric_id():
    """查找metric_id"""
    print("="*80)
    print("查找 pump_flow_rate 的 metric_id")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询pump_flow_rate的metric_id
            cur.execute("""
                SELECT id, metric_key, name
                FROM dim_metric_config
                WHERE metric_key LIKE '%flow%'
                ORDER BY id
            """)
            
            rows = cur.fetchall()
            print(f"\n找到 {len(rows)} 个流量相关指标:")
            for row in rows:
                metric_id, metric_key, name = row
                print(f"  - metric_id={metric_id}: {metric_key} ({name})")

            # 查询pump_flow_rate
            cur.execute("""
                SELECT id, metric_key, name
                FROM dim_metric_config
                WHERE metric_key = 'pump_flow_rate'
            """)
            
            row = cur.fetchone()
            if row:
                metric_id, metric_key, name = row
                print(f"\n✅ pump_flow_rate 的 metric_id = {metric_id}")
                
                # 查询该metric_id的数据
                cur.execute("""
                    SELECT 
                        device_id,
                        COUNT(*) as count
                    FROM fact_measurements
                    WHERE station_id = 1
                      AND metric_id = %s
                    GROUP BY device_id
                    ORDER BY device_id
                """, (metric_id,))
                
                rows = cur.fetchall()
                if rows:
                    print(f"\n找到 {len(rows)} 个设备的数据:")
                    for row in rows:
                        device_id, count = row
                        print(f"  - 设备{device_id}: {count}条")
                else:
                    print(f"\n⚠️ 未找到metric_id={metric_id}的数据")
            else:
                print(f"\n⚠️ 未找到pump_flow_rate指标")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 查找metric_id
    find_metric_id()

