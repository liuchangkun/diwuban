"""
检查pump_flow_rate计算结果数据
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
    print("检查 pump_flow_rate 计算结果数据（metric_id=18）")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询pump_flow_rate的数据（设备1-6）
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
                  AND metric_id = 18  -- pump_flow_rate
                  AND device_id IN (1, 2, 3, 4, 5, 6)
                GROUP BY device_id
                ORDER BY device_id
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\n找到 {len(rows)} 个设备的pump_flow_rate数据:")
                for row in rows:
                    device_id, count, min_time, max_time, min_value, max_value, avg_value = row
                    print(f"\n设备{device_id}:")
                    print(f"  - 记录数: {count}")
                    print(f"  - 时间范围: {min_time} ~ {max_time}")
                    print(f"  - 值范围: {min_value:.2f} ~ {max_value:.2f} m³/h")
                    print(f"  - 平均值: {avg_value:.2f} m³/h")
            else:
                print("\n⚠️ 未找到pump_flow_rate计算结果数据（设备1-6）")
                print("   可能需要先运行pump_flow_rate计算")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 检查数据
    check_data()

