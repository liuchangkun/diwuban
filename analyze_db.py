#!/usr/bin/env python3
"""
详细的数据库结构查看脚本
"""

import psycopg
from pathlib import Path

def analyze_database():
    try:
        # 使用配置中的默认连接参数
        conn_params = {
            "host": "localhost",
            "dbname": "pump_station_optimization", 
            "user": "postgres",
        }
        
        print(f"连接数据库: {conn_params}")
        
        with psycopg.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # 获取数据库基本信息
                cur.execute("""
                    SELECT current_database(), current_user, 
                           current_setting('TimeZone'), version()
                """)
                db_info = cur.fetchone()
                if db_info:
                    dbname, user, tz, version = db_info
                    print(f"数据库: {dbname}")
                    print(f"用户: {user}")
                    print(f"时区: {tz}")
                    print(f"版本: {version.split(' ')[0] if version else 'Unknown'}")
                
                # 查看核心业务表的结构
                core_tables = ['dim_stations', 'dim_devices', 'dim_metric_config', 'dim_mapping_items', 'fact_measurements']
                
                for table_name in core_tables:
                    print(f"\n=== public.{table_name} 表结构 ===")
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    
                    columns = cur.fetchall()
                    if columns:
                        for col in columns:
                            name, dtype, nullable, default = col
                            default_str = f" DEFAULT {default}" if default else ""
                            nullable_str = "NULL" if nullable == 'YES' else "NOT NULL"
                            print(f"  {name:20} {dtype:15} {nullable_str:8} {default_str}")
                    else:
                        print(f"  表 {table_name} 不存在")
                
                # 查看数据库函数
                print(f"\n=== 数据库函数 ===")
                cur.execute("""
                    SELECT n.nspname as schema_name, p.proname as function_name
                    FROM pg_proc p 
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname IN ('public', 'reporting', 'monitoring', 'api')
                    ORDER BY n.nspname, p.proname
                """)
                functions = cur.fetchall()
                current_schema = None
                for schema, func in functions:
                    if schema != current_schema:
                        print(f"\n  [{schema}]")
                        current_schema = schema
                    print(f"    {func}")
                
                # 查看视图
                print(f"\n=== 数据库视图 ===")
                cur.execute("""
                    SELECT schemaname, viewname 
                    FROM pg_views 
                    WHERE schemaname IN ('public', 'reporting', 'monitoring', 'api')
                    ORDER BY schemaname, viewname
                """)
                views = cur.fetchall()
                current_schema = None
                for schema, view in views:
                    if schema != current_schema:
                        print(f"\n  [{schema}]")
                        current_schema = schema
                    print(f"    {view}")
                
                # 查看分区表统计
                print(f"\n=== fact_measurements 分区统计 ===")
                cur.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename LIKE 'fact_measurements_%'
                    ORDER BY tablename
                """)
                partitions = cur.fetchall()
                
                # 按年周分组统计
                weeks = {}
                for schema, table in partitions:
                    if '_p' not in table:  # 这是周分区主表
                        week = table.replace('fact_measurements_', '')
                        weeks[week] = 0
                
                # 统计每周的子分区数
                for schema, table in partitions:
                    if '_p' in table:  # 这是子分区
                        week = table.split('_p')[0].replace('fact_measurements_', '')
                        if week in weeks:
                            weeks[week] += 1
                
                print(f"总分区数: {len(partitions)}")
                print(f"周分区数: {len(weeks)}")
                for week in sorted(weeks.keys())[-10:]:  # 显示最近10周
                    print(f"  {week}: {weeks[week]} 个子分区")
                
                # 查看各表的数据量
                print(f"\n=== 核心表数据量 ===")
                for table_name in ['dim_stations', 'dim_devices', 'dim_metric_config', 'dim_mapping_items']:
                    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cur.fetchone()[0]
                    print(f"  {table_name:20} {count:>8} 条记录")
                
                # 查看fact_measurements总数据量（从父表查询）
                try:
                    cur.execute("SELECT COUNT(*) FROM fact_measurements")
                    count = cur.fetchone()[0]
                    print(f"  {'fact_measurements':20} {count:>8} 条记录")
                except Exception as e:
                    print(f"  fact_measurements: 查询失败 ({e})")
                    
    except Exception as e:
        print(f"连接失败: {e}")
        return False
        
    return True

if __name__ == "__main__":
    analyze_database()