#!/usr/bin/env python3
"""
查看视图的详细定义
"""

import psycopg
from pathlib import Path
import sys

def check_views():
    """检查视图定义"""
    try:
        conn_str = "host=localhost dbname=pump_station_optimization user=postgres"
        
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                
                print('🔍 查看 operation_data 视图定义：')
                cur.execute("""
                    SELECT pg_get_viewdef('operation_data'::regclass, true)
                """)
                view_def = cur.fetchone()[0]
                print(view_def)
                
                print('\n🔍 查看 device 视图定义：')
                cur.execute("""
                    SELECT pg_get_viewdef('device'::regclass, true)
                """)
                view_def = cur.fetchone()[0]
                print(view_def)
                
                print('\n🔍 查看 station 视图定义：')
                cur.execute("""
                    SELECT pg_get_viewdef('station'::regclass, true)
                """)
                view_def = cur.fetchone()[0]
                print(view_def)
                
                print('\n📊 查看 operation_data 视图的示例数据：')
                cur.execute("SELECT * FROM operation_data LIMIT 5")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows):
                        print(f"   行{i+1}: {row}")
                else:
                    print('   视图为空')
                    
                print('\n📊 查看 device 视图的示例数据：')
                cur.execute("SELECT * FROM device LIMIT 5")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows):
                        print(f"   行{i+1}: {row}")
                else:
                    print('   视图为空')
                    
                print('\n📊 查看 station 视图的示例数据：')
                cur.execute("SELECT * FROM station LIMIT 5")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows):
                        print(f"   行{i+1}: {row}")
                else:
                    print('   视图为空')
                    
                # 检查数据
                print('\n📈 检查数据量：')
                cur.execute("SELECT COUNT(*) FROM operation_data")
                count = cur.fetchone()[0]
                print(f"   operation_data 视图记录数: {count}")
                
                cur.execute("SELECT COUNT(*) FROM fact_measurements")
                count = cur.fetchone()[0]
                print(f"   fact_measurements 表记录数: {count}")
                
                cur.execute("SELECT COUNT(*) FROM device")
                count = cur.fetchone()[0]
                print(f"   device 视图记录数: {count}")
                
                cur.execute("SELECT COUNT(*) FROM station")
                count = cur.fetchone()[0]
                print(f"   station 视图记录数: {count}")
                        
    except Exception as e:
        print(f"❌ 查询失败: {e}")

if __name__ == "__main__":
    check_views()