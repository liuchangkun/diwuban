#!/usr/bin/env python3
"""
简单的数据库连接测试脚本
"""

import psycopg
from pathlib import Path

def test_connection():
    try:
        # 使用配置中的默认连接参数
        conn_params = {
            "host": "localhost",
            "dbname": "pump_station_optimization", 
            "user": "postgres",
        }
        
        print(f"尝试连接数据库: {conn_params}")
        
        with psycopg.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # 测试基本连接
                cur.execute("SELECT 1 as test")
                result = cur.fetchone()
                print(f"连接测试成功: {result}")
                
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
                
                # 查看表结构
                print("\n=== 查看数据库表结构 ===")
                cur.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname IN ('public', 'reporting', 'monitoring', 'api')
                    ORDER BY schemaname, tablename
                """)
                
                tables = cur.fetchall()
                for schema, table in tables:
                    print(f"{schema}.{table}")
                
                if tables:
                    # 查看第一个表的详细结构
                    first_schema, first_table = tables[0]
                    print(f"\n=== {first_schema}.{first_table} 表结构示例 ===")

                
                # 查看函数
                print("\n=== 数据库函数 ===")
                cur.execute("""
                    SELECT schemaname, functionname 
                    FROM pg_functions 
                    WHERE schemaname IN ('public', 'reporting', 'monitoring', 'api')
                    ORDER BY schemaname, functionname
                """)
                functions = cur.fetchall()
                for schema, func in functions[:10]:  # 只显示前10个
                    print(f"{schema}.{func}")
                if len(functions) > 10:
                    print(f"... 还有 {len(functions) - 10} 个函数")
                    
    except Exception as e:
        print(f"连接失败: {e}")
        print("请检查:")
        print("1. PostgreSQL服务是否运行")
        print("2. 数据库 'pump_station_optimization' 是否存在")
        print("3. 用户权限是否正确")
        return False
        
    return True

if __name__ == "__main__":
    test_connection()