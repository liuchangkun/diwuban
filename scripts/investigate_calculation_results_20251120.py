#!/usr/bin/env python3
"""
调查计算结果异常
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import init_database, get_connection
from app.core.config.loader import load_settings

def main():
    # 初始化
    settings = load_settings(Path(__file__).parent.parent / "config")
    init_database(settings)
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        print('='*100)
        print('问题1: 检查pump_flow_rate数据量')
        print('='*100)
        
        # 检查pump_flow_rate的数据量分布
        cur.execute('''
            SELECT device_id, COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_flow_rate')
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id
            ORDER BY device_id
        ''')
        print('\npump_flow_rate数据量（按设备）:')
        for row in cur.fetchall():
            print(f'  设备{row[0]}: {row[1]:,}条')

        # 检查pump_inlet_pressure的数据量分布
        cur.execute('''
            SELECT device_id, COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_inlet_pressure')
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id
            ORDER BY device_id
        ''')
        print('\npump_inlet_pressure数据量（按设备）:')
        for row in cur.fetchall():
            print(f'  设备{row[0]}: {row[1]:,}条')
        
        print('\n' + '='*100)
        print('问题2: 检查pump_head是否有重复数据')
        print('='*100)
        
        # 检查pump_head的数据量和source_hint分布
        cur.execute('''
            SELECT device_id,
                   SPLIT_PART(source_hint, ':', 1) as method_id,
                   COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_head')
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id, SPLIT_PART(source_hint, ':', 1)
            ORDER BY device_id, method_id
        ''')
        print('\npump_head数据量（按设备和方法）:')
        for row in cur.fetchall():
            print(f'  设备{row[0]}, {row[1]}: {row[2]:,}条')

        # 检查是否有重复的时间戳
        cur.execute('''
            SELECT device_id, ts_bucket, COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_head')
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id, ts_bucket
            HAVING COUNT(*) > 1
            LIMIT 10
        ''')
        duplicates = cur.fetchall()
        if duplicates:
            print('\n⚠️ 发现重复时间戳:')
            for row in duplicates:
                print(f'  设备{row[0]}, {row[1]}: {row[2]}条重复')
        else:
            print('\n✅ 未发现重复时间戳')
        
        print('\n' + '='*100)
        print('问题3: 检查设备5的running状态')
        print('='*100)
        
        # 检查设备5的running状态分布（从fact_measurements获取）
        cur.execute('''
            SELECT
                CASE WHEN value > 0 THEN 1 ELSE 0 END as running_status,
                COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'running')
              AND device_id = 5
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY running_status
            ORDER BY running_status
        ''')
        print('\n设备5的running状态分布:')
        for row in cur.fetchall():
            print(f'  running={row[0]}: {row[1]:,}条')
        
        # 检查设备5的pump_flow_rate计算结果
        cur.execute('''
            SELECT SPLIT_PART(source_hint, ':', 1) as method_id,
                   COUNT(*) as count,
                   AVG(value) as avg_flow,
                   MIN(value) as min_flow,
                   MAX(value) as max_flow
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_flow_rate')
              AND device_id = 5
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY SPLIT_PART(source_hint, ':', 1)
            ORDER BY method_id
        ''')
        print('\n设备5的pump_flow_rate计算结果（按方法）:')
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]:,}条, 平均={row[2]:.2f}, 最小={row[3]:.2f}, 最大={row[4]:.2f}')
        
        print('\n' + '='*100)
        print('问题4: 检查pump_flow_rate的过滤条件')
        print('='*100)
        
        # 检查每个设备的running=1数据量
        cur.execute('''
            SELECT device_id, COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'running')
              AND value > 0
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id
            ORDER BY device_id
        ''')
        print('\n各设备running=1的数据量:')
        for row in cur.fetchall():
            print(f'  设备{row[0]}: {row[1]:,}条')
        
        # 检查pump_inlet_pressure的过滤条件（需要pump_flow_rate > 0）
        cur.execute('''
            SELECT device_id, COUNT(*) as count
            FROM fact_measurements
            WHERE metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_flow_rate')
              AND value > 0
              AND ts_bucket BETWEEN '2025-10-22 16:00:00' AND '2025-10-23 15:20:00'
            GROUP BY device_id
            ORDER BY device_id
        ''')
        print('\n各设备pump_flow_rate > 0的数据量:')
        for row in cur.fetchall():
            print(f'  设备{row[0]}: {row[1]:,}条')

if __name__ == '__main__':
    main()

