#!/usr/bin/env python3
"""
数据库结构检查脚本
使用项目的数据库配置直接查询数据库结构
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path('.').absolute()))

try:
    from app.core.config.loader_new import load_settings
    from app.adapters.db.gateway import get_conn
    
    def check_database():
        """检查数据库结构"""
        settings = load_settings(Path('configs'))
        
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 1. 查看所有表
                print("=== 数据库中的所有表 ===")
                cur.execute("""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                for table_name, table_type in tables:
                    print(f"{table_type}: {table_name}")
                
                # 2. 查看所有视图
                print("\n=== 数据库中的所有视图 ===")
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                views = cur.fetchall()
                for (view_name,) in views:
                    print(f"VIEW: {view_name}")
                
                # 3. 检查主要表结构
                print("\n=== 检查主要表是否存在 ===")
                main_tables = ['operation_data', 'fact_measurements', 'dim_devices', 'dim_metric_config', 'station', 'device']
                
                for table in main_tables:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                    exists = cur.fetchone()[0]
                    print(f"表 {table}: {'存在' if exists else '不存在'}")
                
                # 4. 如果operation_data表存在，查看其结构
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'operation_data'
                    )
                """)
                if cur.fetchone()[0]:
                    print("\n=== operation_data 表结构 ===")
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = 'operation_data'
                        ORDER BY ordinal_position
                    """)
                    columns = cur.fetchall()
                    for col_name, data_type, is_nullable in columns:
                        print(f"  {col_name}: {data_type} ({'NULL' if is_nullable == 'YES' else 'NOT NULL'})")
                
                # 5. 查看一些示例数据
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'operation_data'
                    )
                """)
                if cur.fetchone()[0]:
                    print("\n=== operation_data 示例数据 ===")
                    cur.execute("SELECT * FROM operation_data LIMIT 3")
                    rows = cur.fetchall()
                    if rows:
                        # 获取列名
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'operation_data'
                            ORDER BY ordinal_position
                        """)
                        column_names = [row[0] for row in cur.fetchall()]
                        print(f"列名: {column_names}")
                        for i, row in enumerate(rows):
                            print(f"示例 {i+1}: {row}")
                    else:
                        print("表中无数据")

    if __name__ == "__main__":
        check_database()

except Exception as e:
    print(f"错误: {e}")
    print("请确保数据库连接配置正确")