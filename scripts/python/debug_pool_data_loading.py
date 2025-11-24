#!/usr/bin/env python3
"""
调试 pool_liquid_level 数据加载问题
"""
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings


def check_pool_data_availability():
    """检查 pool_liquid_level 数据的可用性"""
    print("\n" + "=" * 100)
    print("🔍 检查 pool_liquid_level 数据可用性")
    print("=" * 100)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 获取 metric_id
            cur.execute("SELECT id FROM dim_metric_config WHERE metric_key = 'pool_liquid_level'")
            metric_id = cur.fetchone()[0]
            
            # 查询数据分布
            cur.execute("""
                SELECT 
                    station_id,
                    device_id,
                    COUNT(*) as data_count,
                    MIN(ts_bucket) as min_time,
                    MAX(ts_bucket) as max_time
                FROM fact_measurements
                WHERE metric_id = %s
                  AND ts_bucket >= '2025-10-22 16:00:00+08:00'
                  AND ts_bucket < '2025-10-23 15:00:00+08:00'
                GROUP BY station_id, device_id
                ORDER BY station_id, device_id
            """, (metric_id,))
            
            rows = cur.fetchall()
            
            if not rows:
                print("\n❌ 没有找到 pool_liquid_level 数据！")
                return None
            
            print(f"\n找到 {len(rows)} 个设备的 pool_liquid_level 数据：")
            print(f"\n{'泵站ID':<10} {'设备ID':<10} {'数据量':<15} {'开始时间':<25} {'结束时间':<25}")
            print("-" * 100)
            
            for row in rows:
                station_id, device_id, count, min_time, max_time = row
                print(f"{station_id:<10} {device_id:<10} {count:<15,} {str(min_time):<25} {str(max_time):<25}")
            
            return rows


def test_data_loader_sql():
    """测试 DataLoader 的 SQL 查询"""
    print("\n" + "=" * 100)
    print("🔍 测试 DataLoader SQL 查询")
    print("=" * 100)
    
    station_id = 1
    device_id = 1  # 测试设备1
    start_time = datetime(2025, 10, 22, 16, 0, 0, tzinfo=pytz.timezone('Asia/Shanghai'))
    end_time = datetime(2025, 10, 23, 15, 0, 0, tzinfo=pytz.timezone('Asia/Shanghai'))
    
    sql = """
        WITH metric_ids AS (
            SELECT id, metric_key
            FROM dim_metric_config
            WHERE metric_key IN (
                'pool_liquid_level',
                'pump_flow_rate'
            )
        )
        SELECT
            fm.ts_bucket,
            fm.device_id,
            mc.metric_key,
            fm.value,
            COALESCE(dr.running, 1) AS running
        FROM fact_measurements fm
        JOIN metric_ids mc ON mc.id = fm.metric_id
        LEFT JOIN mv_device_running_1s dr
            ON dr.station_id = fm.station_id
           AND dr.device_id = fm.device_id
           AND dr.ts_bucket = fm.ts_bucket
        WHERE fm.station_id = %(station_id)s
          AND fm.ts_bucket >= %(start_time)s
          AND fm.ts_bucket < %(end_time)s
          AND (
              (mc.metric_key = 'pump_flow_rate' AND fm.device_id = %(device_id)s)
              OR (mc.metric_key = 'pool_liquid_level')
          )
        ORDER BY fm.ts_bucket, fm.device_id, mc.metric_key
        LIMIT 20
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                'station_id': station_id,
                'device_id': device_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            rows = cur.fetchall()
            
            print(f"\n查询参数:")
            print(f"  - station_id: {station_id}")
            print(f"  - device_id: {device_id}")
            print(f"  - start_time: {start_time}")
            print(f"  - end_time: {end_time}")
            
            print(f"\n查询结果（前20条）:")
            print(f"{'时间戳':<25} {'设备ID':<10} {'指标':<25} {'值':<15} {'运行状态':<10}")
            print("-" * 100)
            
            pool_count = 0
            flow_count = 0
            
            for row in rows:
                ts_bucket, dev_id, metric_key, value, running = row
                print(f"{str(ts_bucket):<25} {dev_id:<10} {metric_key:<25} {value:<15.6f} {running:<10}")
                
                if metric_key == 'pool_liquid_level':
                    pool_count += 1
                elif metric_key == 'pump_flow_rate':
                    flow_count += 1
            
            print(f"\n统计:")
            print(f"  - pool_liquid_level: {pool_count}条")
            print(f"  - pump_flow_rate: {flow_count}条")
            
            # 查询总数
            cur.execute(sql.replace('LIMIT 20', ''), {
                'station_id': station_id,
                'device_id': device_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            total_rows = cur.fetchall()
            total_pool = sum(1 for row in total_rows if row[2] == 'pool_liquid_level')
            total_flow = sum(1 for row in total_rows if row[2] == 'pump_flow_rate')
            
            print(f"\n总数:")
            print(f"  - pool_liquid_level: {total_pool:,}条")
            print(f"  - pump_flow_rate: {total_flow:,}条")
            
            if total_pool == 0:
                print(f"\n❌ 问题确认：SQL 查询没有返回 pool_liquid_level 数据！")
                print(f"   可能原因：")
                print(f"   1. pool_liquid_level 数据不在泵站1")
                print(f"   2. pool_liquid_level 数据的时间范围不匹配")
                print(f"   3. pool_liquid_level 数据的 station_id 不是1")
            else:
                print(f"\n✅ SQL 查询正常返回 pool_liquid_level 数据")


if __name__ == "__main__":
    try:
        # 初始化
        config_dir = project_root / "configs"
        settings = load_settings(config_dir)
        init_database(settings)
        
        # 1. 检查 pool_liquid_level 数据可用性
        pool_data = check_pool_data_availability()
        
        # 2. 测试 DataLoader SQL 查询
        test_data_loader_sql()
        
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

