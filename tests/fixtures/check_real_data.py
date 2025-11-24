#!/usr/bin/env python3
"""
检查真实数据库中的数据情况

功能：
1. 检查 dim_stations 表中的真实泵站
2. 检查 dim_devices 表中的真实设备
3. 检查 fact_measurements 表中的真实数据
4. 检查 mv_device_running_1s 物化视图
5. 生成测试数据配置建议
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def check_stations(conn):
    """检查真实泵站数据"""
    print("\n" + "="*80)
    print("1. 检查真实泵站数据")
    print("="*80)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, extra
            FROM dim_stations
            ORDER BY id
            LIMIT 10
        """)
        
        stations = cur.fetchall()
        if stations:
            print(f"\n找到 {len(stations)} 个泵站:")
            print("-"*80)
            for station_id, name, extra in stations:
                print(f"  ID={station_id:<5} 名称={name:<20} 额外信息={extra}")
            print("-"*80)
            return [s[0] for s in stations]
        else:
            print("  ⚠️ 没有找到泵站数据")
            return []


def check_devices(conn, station_ids):
    """检查真实设备数据"""
    print("\n" + "="*80)
    print("2. 检查真实设备数据")
    print("="*80)
    
    with conn.cursor() as cur:
        if station_ids:
            cur.execute("""
                SELECT id, station_id, name, type
                FROM dim_devices
                WHERE station_id = ANY(%s)
                ORDER BY station_id, id
                LIMIT 20
            """, (station_ids,))
        else:
            cur.execute("""
                SELECT id, station_id, name, type
                FROM dim_devices
                ORDER BY station_id, id
                LIMIT 20
            """)
        
        devices = cur.fetchall()
        if devices:
            print(f"\n找到 {len(devices)} 个设备:")
            print("-"*80)
            for device_id, station_id, name, device_type in devices:
                print(f"  ID={device_id:<5} 泵站ID={station_id:<5} 名称={name:<20} 类型={device_type}")
            print("-"*80)
            return [d[0] for d in devices]
        else:
            print("  ⚠️ 没有找到设备数据")
            return []


def check_fact_measurements(conn, device_ids):
    """检查真实测量数据"""
    print("\n" + "="*80)
    print("3. 检查真实测量数据")
    print("="*80)
    
    with conn.cursor() as cur:
        if device_ids:
            # 先检查是否有任何数据
            cur.execute("""
                SELECT
                    fm.device_id,
                    dmc.metric_key,
                    COUNT(*) as count,
                    MIN(fm.ts_bucket) as min_ts,
                    MAX(fm.ts_bucket) as max_ts
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE fm.device_id = ANY(%s)
                GROUP BY fm.device_id, dmc.metric_key
                ORDER BY fm.device_id, dmc.metric_key
                LIMIT 50
            """, (device_ids[:5],))  # 只检查前5个设备
            
            results = cur.fetchall()
            if results:
                print(f"\n找到 {len(results)} 个设备-指标组合（所有历史数据）:")
                print("-"*80)
                for device_id, metric_key, count, min_ts, max_ts in results:
                    print(f"  设备ID={device_id:<5} 指标={metric_key:<30} 记录数={count:<10} 时间范围={min_ts} ~ {max_ts}")
                print("-"*80)
                return True
            else:
                print("  ⚠️ 没有找到任何测量数据")
                return False
        else:
            print("  ⚠️ 没有设备ID，跳过检查")
            return False


def check_mv_device_running(conn, device_ids):
    """检查 mv_device_running_1s 物化视图"""
    print("\n" + "="*80)
    print("4. 检查 mv_device_running_1s 物化视图")
    print("="*80)
    
    with conn.cursor() as cur:
        # 检查物化视图是否存在
        cur.execute("""
            SELECT matviewname FROM pg_matviews
            WHERE schemaname = 'public' AND matviewname = 'mv_device_running_1s'
        """)
        
        if cur.fetchone() is None:
            print("  ⚠️ 物化视图不存在")
            return False
        
        print("  ✅ 物化视图存在")
        
        if device_ids:
            # 检查数据
            cur.execute("""
                SELECT
                    device_id,
                    COUNT(*) as total_count,
                    SUM(running) as running_count,
                    MIN(ts_bucket) as min_ts,
                    MAX(ts_bucket) as max_ts
                FROM mv_device_running_1s
                WHERE device_id = ANY(%s)
                GROUP BY device_id
                ORDER BY device_id
                LIMIT 10
            """, (device_ids[:5],))
            
            results = cur.fetchall()
            if results:
                print(f"\n找到 {len(results)} 个设备的运行状态数据（最近7天）:")
                print("-"*80)
                for device_id, total, running, min_ts, max_ts in results:
                    running_rate = (running / total * 100) if total > 0 else 0
                    print(f"  设备ID={device_id:<5} 总记录={total:<10} 运行记录={running:<10} 运行率={running_rate:.1f}% 时间范围={min_ts} ~ {max_ts}")
                print("-"*80)
                return True
            else:
                print("  ⚠️ 最近7天没有找到运行状态数据")
                return False
        else:
            print("  ⚠️ 没有设备ID，跳过检查")
            return False


def generate_test_config(conn):
    """生成测试数据配置建议"""
    print("\n" + "="*80)
    print("5. 生成测试数据配置建议")
    print("="*80)
    
    with conn.cursor() as cur:
        # 查找有完整数据的设备
        cur.execute("""
            WITH device_metrics AS (
                SELECT
                    fm.device_id,
                    dmc.metric_key,
                    COUNT(*) as count
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE fm.ts_bucket >= NOW() - INTERVAL '7 days'
                AND dmc.metric_key IN (
                    'pump_active_power', 'pump_frequency',
                    'pump_cumulative_flow', 'main_pipeline_flow_rate'
                )
                GROUP BY fm.device_id, dmc.metric_key
            )
            SELECT
                device_id,
                COUNT(DISTINCT metric_key) as metric_count,
                SUM(count) as total_records
            FROM device_metrics
            GROUP BY device_id
            HAVING COUNT(DISTINCT metric_key) >= 2
            ORDER BY metric_count DESC, total_records DESC
            LIMIT 5
        """)
        
        results = cur.fetchall()
        if results:
            print("\n推荐用于测试的设备（有完整数据）:")
            print("-"*80)
            for device_id, metric_count, total_records in results:
                print(f"  设备ID={device_id:<5} 指标数={metric_count:<5} 总记录数={total_records}")
            print("-"*80)
            
            # 生成配置代码
            print("\n建议的测试配置（添加到 conftest.py）:")
            print("-"*80)
            print("```python")
            print("# 真实数据配置")
            print(f"TEST_DEVICE_IDS = {[r[0] for r in results]}")
            print("TEST_TIME_RANGE = (")
            print("    datetime.now() - timedelta(days=1),  # 最近1天")
            print("    datetime.now()")
            print(")")
            print("```")
            print("-"*80)
        else:
            print("  ⚠️ 没有找到有完整数据的设备")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("检查真实数据库数据")
    print("="*80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        # 1. 检查泵站
        station_ids = check_stations(conn)
        
        # 2. 检查设备
        device_ids = check_devices(conn, station_ids)
        
        # 3. 检查测量数据
        has_measurements = check_fact_measurements(conn, device_ids)
        
        # 4. 检查物化视图
        has_mv = check_mv_device_running(conn, device_ids)
        
        # 5. 生成配置建议
        if has_measurements:
            generate_test_config(conn)
    
    print("\n" + "="*80)
    print("✅ 数据检查完成！")
    print("="*80)
    print()


if __name__ == "__main__":
    main()

