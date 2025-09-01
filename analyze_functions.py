#!/usr/bin/env python3
"""
分析数据库函数详细信息
"""

import psycopg

def analyze_functions():
    conn_params = {
        "host": "localhost",
        "dbname": "pump_station_optimization", 
        "user": "postgres",
    }
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            print("=== 数据库函数详细分析 ===\n")
            
            # 获取所有函数的详细信息
            cur.execute("""
                SELECT 
                    n.nspname as schema_name, 
                    p.proname as function_name,
                    pg_get_function_arguments(p.oid) as arguments,
                    pg_get_function_result(p.oid) as return_type,
                    COALESCE(obj_description(p.oid, 'pg_proc'), '') as description
                FROM pg_proc p 
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname IN ('public', 'reporting', 'monitoring', 'api')
                ORDER BY n.nspname, p.proname
            """)
            
            functions = cur.fetchall()
            
            current_schema = None
            for schema, func_name, args, return_type, desc in functions:
                if schema != current_schema:
                    print(f"\n=== {schema.upper()} SCHEMA 函数 ===")
                    current_schema = schema
                
                print(f"\n函数: {func_name}")
                print(f"参数: {args if args else '无参数'}")
                print(f"返回: {return_type}")
                if desc.strip():
                    print(f"描述: {desc}")
                else:
                    print("描述: 无")
                
                # 对于核心函数，显示函数定义
                if func_name in ['safe_upsert_measurement', 'safe_upsert_measurement_local', 
                               'get_measurements', 'upsert_measurements_json']:
                    try:
                        cur.execute("""
                            SELECT pg_get_functiondef(oid) 
                            FROM pg_proc p
                            JOIN pg_namespace n ON p.pronamespace = n.oid
                            WHERE n.nspname = %s AND p.proname = %s
                        """, (schema, func_name))
                        
                        func_def = cur.fetchone()
                        if func_def:
                            definition = func_def[0]
                            # 只显示函数签名部分，不显示完整实现
                            lines = definition.split('\n')
                            signature_lines = []
                            for line in lines:
                                signature_lines.append(line)
                                if 'RETURNS' in line or 'AS $' in line:
                                    break
                            print(f"定义: {' '.join(signature_lines[:3])}")
                    except Exception as e:
                        print(f"获取定义失败: {e}")
                
                print("-" * 60)
            
            # 分析视图
            print(f"\n=== 数据库视图详细分析 ===\n")
            cur.execute("""
                SELECT schemaname, viewname, definition 
                FROM pg_views 
                WHERE schemaname IN ('public', 'reporting', 'monitoring', 'api')
                ORDER BY schemaname, viewname
            """)
            
            views = cur.fetchall()
            current_schema = None
            
            for schema, view_name, definition in views:
                if schema != current_schema:
                    print(f"\n=== {schema.upper()} SCHEMA 视图 ===")
                    current_schema = schema
                
                print(f"\n视图: {view_name}")
                # 显示视图定义的前几行
                def_lines = definition.split('\n')[:5]
                print(f"定义预览: {' '.join(def_lines)}")
                print("-" * 60)
            
            # 分析存储过程使用的核心逻辑
            print(f"\n=== 核心业务逻辑分析 ===\n")
            
            # 检查时间对齐约束
            cur.execute("""
                SELECT conname, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = 'public.fact_measurements'::regclass
                AND contype = 'c'
            """)
            
            constraints = cur.fetchall()
            print("时间对齐约束:")
            for name, definition in constraints:
                print(f"  {name}: {definition}")
            
            # 检查索引
            print(f"\n索引结构:")
            cur.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'fact_measurements' 
                AND schemaname = 'public'
            """)
            
            indexes = cur.fetchall()
            for idx_name, idx_def in indexes:
                print(f"  {idx_name}")
                print(f"    {idx_def}")

if __name__ == "__main__":
    analyze_functions()