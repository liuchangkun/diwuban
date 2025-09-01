#!/usr/bin/env python3
"""
数据库实际结构检查脚本
直接连接数据库查看当前的表、视图和数据结构
"""

import psycopg
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path('.').absolute()))

def check_database():
    """检查数据库结构"""
    try:
        # 直接使用配置中的数据库连接信息
        conn_str = "host=localhost dbname=pump_station_optimization user=postgres"
        
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                
                print('📋 1. 查看所有表：')
                cur.execute("""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_type, table_name
                """)
                tables = cur.fetchall()
                for table_name, table_type in tables:
                    print(f"   {table_type}: {table_name}")
                
                print('\n🔍 2. 查看所有视图：')
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                views = cur.fetchall()
                for (view_name,) in views:
                    print(f"   VIEW: {view_name}")
                
                # 检查主要数据表
                data_tables = ['operation_data', 'fact_measurements', 'device', 'station', 'dim_devices', 'dim_metric_config']
                
                print('\n📊 3. 检查主要数据表是否存在：')
                for table in data_tables:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                    exists = cur.fetchone()[0]
                    print(f"   {table}: {'✅ 存在' if exists else '❌ 不存在'}")
                
                # 查看实际存在的主要表的结构
                print('\n🔍 4. 查看存在的主要表结构：')
                for table in data_tables:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                    if cur.fetchone()[0]:
                        print(f'\n   表 {table} 的字段结构：')
                        cur.execute("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        columns = cur.fetchall()
                        for col_name, data_type, nullable, default in columns:
                            null_str = "NULL" if nullable == "YES" else "NOT NULL"
                            default_str = f" DEFAULT {default}" if default else ""
                            print(f"     {col_name}: {data_type} {null_str}{default_str}")
                
                # 查看一些示例数据
                print('\n📈 5. 查看示例数据：')
                
                # 检查哪个表包含运行数据
                if any(table in [t[0] for t in tables] for table in ['fact_measurements']):
                    print('   从 fact_measurements 表查看示例数据：')
                    cur.execute("SELECT * FROM fact_measurements LIMIT 3")
                    rows = cur.fetchall()
                    if rows:
                        # 获取列名
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' AND table_name = 'fact_measurements'
                            ORDER BY ordinal_position
                        """)
                        col_names = [row[0] for row in cur.fetchall()]
                        print(f"     列名: {col_names}")
                        for i, row in enumerate(rows):
                            print(f"     行{i+1}: {row}")
                    else:
                        print('     表为空')
                        
                elif any(table in [t[0] for t in tables] for table in ['operation_data']):
                    print('   从 operation_data 表查看示例数据：')
                    cur.execute("SELECT * FROM operation_data LIMIT 3")
                    rows = cur.fetchall()
                    if rows:
                        # 获取列名
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' AND table_name = 'operation_data'
                            ORDER BY ordinal_position
                        """)
                        col_names = [row[0] for row in cur.fetchall()]
                        print(f"     列名: {col_names}")
                        for i, row in enumerate(rows):
                            print(f"     行{i+1}: {row}")
                    else:
                        print('     表为空')
                        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("请确保：")
        print("1. PostgreSQL 服务正在运行")
        print("2. 数据库 'pump_station_optimization' 存在")
        print("3. 用户 'postgres' 有访问权限")

if __name__ == "__main__":
    check_database()