"""为device_id=1和7补充pump_head数据"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

settings = load_settings(Path("configs"))
init_database(settings)

# pump_head的metric_id=16
PUMP_HEAD_METRIC_ID = 16

def add_pump_head_for_device(device_id: int, station_id: int = 1):
    """为指定设备添加pump_head数据
    
    pump_head数据是从现有的pump_flow_rate数据计算得出的。
    使用简化的扬程曲线公式：H = H0 - K*Q²
    """
    
    print(f"\n{'='*80}")
    print(f"为device_id={device_id}添加pump_head数据")
    print(f"{'='*80}\n")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取额定参数
            cur.execute("""
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE device_id = %s
                  AND param_key IN ('rated_flow', 'rated_head')
            """, (device_id,))
            
            params = {row[0]: float(row[1]) for row in cur.fetchall()}
            rated_flow = params.get('rated_flow', 400.0)
            rated_head = params.get('rated_head', 25.0)

            print(f"额定参数: 流量={rated_flow} m³/h, 扬程={rated_head} m")

            # 计算扬程曲线系数
            H0 = rated_head * 1.2  # 零流量扬程
            K_h = (H0 - rated_head) / (rated_flow ** 2)  # 扬程系数
            
            print(f"扬程曲线: H = {H0:.2f} - {K_h:.6f}*Q²")
            
            # 获取所有pump_flow_rate数据
            cur.execute("""
                SELECT ts_bucket, value
                FROM fact_measurements
                WHERE station_id = %s
                  AND device_id = %s
                  AND metric_id = 14  -- pump_flow_rate
                ORDER BY ts_bucket
            """, (station_id, device_id))
            
            flow_data = cur.fetchall()
            print(f"找到{len(flow_data)}条流量数据")
            
            if not flow_data:
                print("❌ 未找到流量数据，无法计算扬程")
                return
            
            # 计算pump_head数据
            head_records = []
            for ts_bucket, flow in flow_data:
                # H = H0 - K*Q²
                flow = float(flow)  # 转换Decimal为float
                head = H0 - K_h * (flow ** 2)
                head = max(0, head)  # 确保非负
                
                head_records.append((
                    station_id,
                    device_id,
                    PUMP_HEAD_METRIC_ID,
                    ts_bucket,
                    ts_bucket,
                    head
                ))
            
            print(f"计算得到{len(head_records)}条扬程数据")
            
            # 批量插入
            batch_size = 30000
            total_inserted = 0
            
            for i in range(0, len(head_records), batch_size):
                batch = head_records[i:i+batch_size]
                
                # 生成id（使用MD5哈希）
                cur.executemany("""
                    INSERT INTO fact_measurements
                    (id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
                    SELECT
                        abs(('x' || substr(md5(%s::text || '-' || %s::text || '-' || %s::text || '-' || %s::text), 1, 16))::bit(64)::bigint),
                        %s, %s, %s, %s, %s, %s, 'e2e_test_data'
                    ON CONFLICT (station_id, device_id, metric_id, ts_bucket) DO NOTHING
                """, [(
                    row[0], row[1], row[2], row[4],  # for MD5
                    row[0], row[1], row[2], row[3], row[4], row[5]  # actual values
                ) for row in batch])
                
                conn.commit()
                total_inserted += len(batch)
                
                if (i // batch_size + 1) % 10 == 0:
                    print(f"  已插入: {total_inserted}/{len(head_records)} ({total_inserted/len(head_records)*100:.1f}%)")
            
            print(f"✅ 完成！共插入{total_inserted}条pump_head数据")


if __name__ == "__main__":
    # 为device_id=1和7添加pump_head数据
    add_pump_head_for_device(device_id=1, station_id=1)
    add_pump_head_for_device(device_id=7, station_id=1)
    
    print("\n" + "="*80)
    print("所有设备的pump_head数据已添加完成")
    print("="*80)

