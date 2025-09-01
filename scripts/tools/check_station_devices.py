#!/usr/bin/env python3
"""
检查泵站设备分布情况，为创建泵站综合视图做准备
"""

import psycopg
from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').absolute()))
from app.core.config.loader_new import load_settings

def check_station_devices():
    """检查泵站设备分布情况"""
    try:
        settings = load_settings(Path('configs'))
        from app.adapters.db.gateway import make_dsn
        dsn = make_dsn(settings)
        print('🔍 检查泵站设备分布情况...')
        print(f'📍 连接数据库: {settings.db.host}/{settings.db.name}')

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 1. 检查所有设备的基本信息
                print("\n📋 所有设备基本信息:")
                cur.execute("""
                    SELECT 
                        d.id,
                        d.name,
                        d.type,
                        d.pump_type,
                        d.station_id,
                        s.name as station_name,
                        COUNT(DISTINCT m.metric_key) as metric_count,
                        COUNT(f.id) as data_count
                    FROM dim_devices d
                    LEFT JOIN station s ON d.station_id = s.station_id
                    LEFT JOIN fact_measurements f ON d.id = f.device_id AND f.value IS NOT NULL
                    LEFT JOIN dim_metric_config m ON f.metric_id = m.id
                    GROUP BY d.id, d.name, d.type, d.pump_type, d.station_id, s.name
                    ORDER BY d.station_id, d.type, d.id
                """)
                
                devices = cur.fetchall()
                current_station = None
                for device in devices:
                    device_id, device_name, device_type, pump_type, station_id, station_name, metric_count, data_count = device
                    if current_station != station_id:
                        current_station = station_id
                        print(f"\n🏭 泵站 {station_id} ({station_name}):")
                    
                    type_info = f"{device_type}"
                    if pump_type:
                        type_info += f" ({pump_type})"
                    
                    print(f"  设备{device_id:2}: {device_name:20} | {type_info:15} | {metric_count:3}个指标 | {data_count:,}条数据")
                
                # 2. 检查每个泵站的指标前缀分布
                print("\n🔍 各泵站指标前缀分布:")
                cur.execute("""
                    SELECT 
                        d.station_id,
                        s.name as station_name,
                        CASE 
                            WHEN m.metric_key LIKE 'pump%' THEN 'pump'
                            WHEN m.metric_key LIKE 'main_pipeline%' THEN 'main_pipeline'
                            ELSE SPLIT_PART(m.metric_key, '_', 1)
                        END as prefix,
                        COUNT(DISTINCT m.metric_key) as metric_count,
                        COUNT(f.id) as total_data
                    FROM dim_devices d
                    LEFT JOIN station s ON d.station_id = s.station_id
                    LEFT JOIN fact_measurements f ON d.id = f.device_id AND f.value IS NOT NULL
                    LEFT JOIN dim_metric_config m ON f.metric_id = m.id
                    WHERE m.metric_key IS NOT NULL
                    GROUP BY d.station_id, s.name, 
                        CASE 
                            WHEN m.metric_key LIKE 'pump%' THEN 'pump'
                            WHEN m.metric_key LIKE 'main_pipeline%' THEN 'main_pipeline'
                            ELSE SPLIT_PART(m.metric_key, '_', 1)
                        END
                    ORDER BY d.station_id, total_data DESC
                """)
                
                station_metrics = cur.fetchall()
                current_station = None
                for row in station_metrics:
                    station_id, station_name, prefix, metric_count, total_data = row
                    if current_station != station_id:
                        current_station = station_id
                        print(f"\n🏭 泵站 {station_id} ({station_name}) 指标分布:")
                    
                    print(f"  {prefix:15}: {metric_count:3}个指标, {total_data:,}条数据")
                
                # 3. 找出数据最丰富的泵站
                print("\n🎯 各泵站数据统计:")
                cur.execute("""
                    SELECT 
                        d.station_id,
                        s.name as station_name,
                        COUNT(DISTINCT d.id) as device_count,
                        COUNT(DISTINCT CASE WHEN d.type = 'pump' THEN d.id END) as pump_count,
                        COUNT(DISTINCT CASE WHEN d.type = 'main_pipeline' THEN d.id END) as pipeline_count,
                        COUNT(DISTINCT m.metric_key) as total_metrics,
                        COUNT(DISTINCT CASE WHEN m.metric_key LIKE 'pump%' THEN m.metric_key END) as pump_metrics,
                        COUNT(DISTINCT CASE WHEN m.metric_key LIKE 'main_pipeline%' THEN m.metric_key END) as pipeline_metrics,
                        COUNT(f.id) as total_data
                    FROM dim_devices d
                    LEFT JOIN station s ON d.station_id = s.station_id
                    LEFT JOIN fact_measurements f ON d.id = f.device_id AND f.value IS NOT NULL
                    LEFT JOIN dim_metric_config m ON f.metric_id = m.id
                    GROUP BY d.station_id, s.name
                    ORDER BY total_data DESC, total_metrics DESC
                """)
                
                station_stats = cur.fetchall()
                for row in station_stats:
                    station_id, station_name, device_count, pump_count, pipeline_count, total_metrics, pump_metrics, pipeline_metrics, total_data = row
                    print(f"  泵站{station_id} ({station_name}):")
                    print(f"    设备: {device_count}个 (水泵:{pump_count}, 总管:{pipeline_count})")
                    print(f"    指标: {total_metrics}个 (pump:{pump_metrics}, main_pipeline:{pipeline_metrics})")
                    print(f"    数据: {total_data:,}条")
                
                return station_stats
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    check_station_devices()