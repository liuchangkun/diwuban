"""
检查所有metric_id=18的数据（包括所有设备）
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
    print("检查所有 metric_id=18 的数据")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询所有metric_id=18的数据
            cur.execute("""
                SELECT 
                    device_id,
                    COUNT(*) as count,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value
                FROM fact_measurements
                WHERE station_id = 1
                  AND metric_id = 18
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\n找到 {len(rows)} 个设备的metric_id=18数据:")
                total_count = 0
                for row in rows:
                    device_id, count, min_time, max_time, min_value, max_value, avg_value = row
                    total_count += count
                    print(f"\n设备{device_id}:")
                    print(f"  - 记录数: {count}")
                    print(f"  - 时间范围: {min_time} ~ {max_time}")
                    print(f"  - 值范围: {min_value:.2f} ~ {max_value:.2f}")
                    print(f"  - 平均值: {avg_value:.2f}")
                
                print(f"\n总记录数: {total_count}")
            else:
                print("\n⚠️ 未找到metric_id=18的数据")

            # 查询metric_key
            cur.execute("""
                SELECT metric_key, metric_name_cn
                FROM dim_metric_config
                WHERE id = 18
            """)
            row = cur.fetchone()
            if row:
                print(f"\nmetric_id=18 对应的指标: {row[0]} ({row[1]})")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 检查数据
    check_data()

