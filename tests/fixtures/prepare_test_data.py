#!/usr/bin/env python3
"""
测试数据准备脚本

功能：
1. 创建测试用的维度数据（泵站、设备、指标）
2. 生成测试用的事实数据（fact_measurements）
3. 刷新物化视图（mv_device_running_1s）
4. 初始化计算参数（calculation_parameters）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def prepare_dimension_data(conn):
    """准备维度数据"""
    print("\n" + "="*80)
    print("1. 准备维度数据")
    print("="*80)
    
    with conn.cursor() as cur:
        # 1.1 创建测试泵站
        print("\n1.1 创建测试泵站...")
        cur.execute("""
            INSERT INTO dim_stations (id, station_name, location, created_at)
            VALUES (999, '测试泵站', '测试地点', NOW())
            ON CONFLICT (id) DO UPDATE SET
                station_name = EXCLUDED.station_name,
                location = EXCLUDED.location
        """)
        print("  ✅ 测试泵站创建成功 (ID=999)")
        
        # 1.2 创建测试设备
        print("\n1.2 创建测试设备...")
        test_devices = [
            (105, 999, '测试泵1', 'pump'),
            (106, 999, '测试泵2', 'pump'),
            (107, 999, '测试泵3', 'pump'),
            (108, 999, '测试总管', 'main_pipeline'),
        ]
        
        for device_id, station_id, device_name, device_type in test_devices:
            cur.execute("""
                INSERT INTO dim_devices (id, station_id, device_name, device_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    station_id = EXCLUDED.station_id,
                    device_name = EXCLUDED.device_name,
                    device_type = EXCLUDED.device_type
            """, (device_id, station_id, device_name, device_type))
            print(f"  ✅ 设备创建成功: {device_name} (ID={device_id})")
        
        # 1.3 确保指标存在
        print("\n1.3 确保指标存在...")
        test_metrics = [
            ('pump_flow_rate', '泵流量', 'm³/h'),
            ('pump_active_power', '泵有功功率', 'kW'),
            ('pump_frequency', '泵频率', 'Hz'),
            ('pump_cumulative_flow', '泵累计流量', 'm³'),
            ('main_pipeline_flow_rate', '总管流量', 'm³/h'),
        ]
        
        for metric_key, metric_name, unit in test_metrics:
            cur.execute("""
                INSERT INTO dim_metrics (metric_key, metric_name, unit, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (metric_key) DO NOTHING
            """, (metric_key, metric_name, unit))
        
        print(f"  ✅ {len(test_metrics)} 个指标已确保存在")
        
        conn.commit()
        print("\n✅ 维度数据准备完成")


def prepare_fact_data(conn):
    """准备事实数据（fact_measurements）"""
    print("\n" + "="*80)
    print("2. 准备事实数据")
    print("="*80)
    
    with conn.cursor() as cur:
        # 2.1 获取 metric_id
        print("\n2.1 获取 metric_id...")
        cur.execute("""
            SELECT id, metric_key FROM dim_metrics
            WHERE metric_key IN (
                'pump_flow_rate', 'pump_active_power', 'pump_frequency',
                'pump_cumulative_flow', 'main_pipeline_flow_rate'
            )
        """)
        metric_ids = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  ✅ 获取到 {len(metric_ids)} 个 metric_id")
        
        # 2.2 生成测试数据（最近1小时）
        print("\n2.2 生成测试数据（最近1小时）...")
        
        # 删除旧的测试数据
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        cur.execute("""
            DELETE FROM fact_measurements
            WHERE device_id IN (105, 106, 107, 108)
            AND ts_bucket >= %s AND ts_bucket <= %s
        """, (start_time, end_time))
        print(f"  ✅ 删除旧测试数据: {cur.rowcount} 条")
        
        # 生成新数据
        records = []
        current_time = start_time
        cumulative_flow = 0.0
        
        while current_time <= end_time:
            # 总管流量（200-300 m³/h）
            main_flow = random.uniform(200, 300)
            
            # 3台泵的数据
            for device_id in [105, 106, 107]:
                # 功率（40-50 kW）
                power = random.uniform(40, 50)
                # 频率（45-50 Hz）
                frequency = random.uniform(45, 50)
                # 累计流量（递增）
                cumulative_flow += random.uniform(0.05, 0.1)
                
                records.append((
                    device_id, metric_ids['pump_active_power'],
                    current_time, power, 0
                ))
                records.append((
                    device_id, metric_ids['pump_frequency'],
                    current_time, frequency, 0
                ))
                records.append((
                    device_id, metric_ids['pump_cumulative_flow'],
                    current_time, cumulative_flow, 0
                ))
            
            # 总管流量
            records.append((
                108, metric_ids['main_pipeline_flow_rate'],
                current_time, main_flow, 0
            ))
            
            current_time += timedelta(seconds=1)
        
        # 批量插入
        print(f"\n2.3 批量插入数据（{len(records)} 条）...")
        cur.executemany("""
            INSERT INTO fact_measurements (device_id, metric_id, ts_bucket, value, quality_code)
            VALUES (%s, %s, %s, %s, %s)
        """, records)
        
        conn.commit()
        print(f"  ✅ 插入成功: {len(records)} 条记录")
        print("\n✅ 事实数据准备完成")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("测试数据准备脚本")
    print("="*80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        # 1. 准备维度数据
        prepare_dimension_data(conn)
        
        # 2. 准备事实数据
        prepare_fact_data(conn)
    
    print("\n" + "="*80)
    print("✅ 测试数据准备完成！")
    print("="*80)
    print("\n下一步：")
    print("  1. 刷新物化视图: python tests/fixtures/refresh_materialized_views.py")
    print("  2. 初始化参数: python tests/fixtures/init_calculation_parameters.py")
    print("  3. 运行测试: pytest tests/unit/services/calculation/ -v")
    print()


if __name__ == "__main__":
    main()

