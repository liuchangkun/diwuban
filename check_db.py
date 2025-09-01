#!/usr/bin/env python3
"""简单的数据库连接和表结构检查脚本"""

import psycopg

def check_database():
    try:
        # 连接数据库
        conn = psycopg.connect('host=localhost dbname=pump_station_optimization user=postgres')
        cur = conn.cursor()
        
        # 检查表
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables = cur.fetchall()
        
        print("数据库连接成功！")
        print(f"数据库中的表 ({len(tables)} 个):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查dim_stations表是否存在
        table_names = [t[0] for t in tables]
        if 'dim_stations' in table_names:
            cur.execute("SELECT COUNT(*) FROM dim_stations")
            count = cur.fetchone()[0]
            print(f"\ndim_stations 表存在，包含 {count} 条记录")
        else:
            print("\n⚠️  dim_stations 表不存在")
        
        # 检查其他核心表
        core_tables = ['dim_devices', 'dim_metric_config', 'fact_measurements']
        for table in core_tables:
            if table in table_names:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"{table} 表存在，包含 {count} 条记录")
            else:
                print(f"⚠️  {table} 表不存在")
        
        conn.close()
        
    except Exception as e:
        print(f"数据库检查失败: {e}")

if __name__ == "__main__":
    check_database()