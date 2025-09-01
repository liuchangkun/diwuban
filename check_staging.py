#!/usr/bin/env python3
"""检查staging数据和时间范围"""

import psycopg

def check_staging_data():
    try:
        conn = psycopg.connect('host=localhost dbname=pump_station_optimization user=postgres')
        cur = conn.cursor()

        # 检查staging表中的时间范围
        cur.execute('SELECT MIN("DataTime"), MAX("DataTime") FROM staging_raw')
        time_range = cur.fetchone()
        print(f'staging_raw 时间范围: {time_range[0]} 到 {time_range[1]}')

        # 查看一些样本数据
        cur.execute('SELECT "DataTime", "DataValue", station_name, device_name, metric_key FROM staging_raw LIMIT 5')
        samples = cur.fetchall()
        print('\n样本数据:')
        for sample in samples:
            print(f'  时间: {sample[0]}, 值: {sample[1]}, 泵站: {sample[2]}, 设备: {sample[3]}, 指标: {sample[4]}')
            
        # 检查时间格式
        cur.execute('SELECT DISTINCT LEFT("DataTime", 10) as date_part FROM staging_raw ORDER BY date_part LIMIT 10')
        dates = cur.fetchall()
        print('\n数据日期范围:')
        for date in dates:
            print(f'  {date[0]}')

        conn.close()
        
    except Exception as e:
        print(f"检查数据失败: {e}")

if __name__ == "__main__":
    check_staging_data()