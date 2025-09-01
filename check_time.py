#!/usr/bin/env python3
"""检查staging数据时间格式"""

import psycopg
from datetime import datetime

def check_time_data():
    try:
        conn = psycopg.connect('host=localhost dbname=pump_station_optimization user=postgres')
        cur = conn.cursor()

        # 检查staging表中的数据时区和格式
        cur.execute('SELECT "DataTime", station_name, device_name, metric_key FROM staging_raw ORDER BY "DataTime" LIMIT 3')
        samples = cur.fetchall()
        print('staging_raw 样本数据:')
        for sample in samples:
            print(f'  {sample}')

        # 检查是否能解析时间
        sample_time = samples[0][0] if samples else None
        if sample_time:
            print(f'\n样本时间字符串: "{sample_time}"')
            try:
                parsed = datetime.fromisoformat(sample_time)
                print(f'解析后的时间: {parsed}')
                print(f'时区信息: {parsed.tzinfo}')
            except Exception as e:
                print(f'时间解析失败: {e}')
                
        # 检查staging表总数
        cur.execute('SELECT COUNT(*) FROM staging_raw')
        total = cur.fetchone()[0]
        print(f'\nstaging_raw 总行数: {total}')
        
        # 检查时间范围覆盖
        cur.execute("""
            SELECT 
                MIN("DataTime") as min_time,
                MAX("DataTime") as max_time,
                COUNT(*) as count
            FROM staging_raw 
            WHERE "DataTime" >= '2025-02-28 00:00:00' 
            AND "DataTime" <= '2025-02-28 23:59:59'
        """)
        window_data = cur.fetchone()
        print(f'时间窗口 2025-02-28 内的数据: {window_data[2]} 行')
        print(f'窗口内时间范围: {window_data[0]} 到 {window_data[1]}')

        conn.close()
        
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == "__main__":
    check_time_data()