#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证数据库注释是否正确添加"""

import psycopg2
import sys

def verify_comments():
    """验证数据库注释"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )
    
    cursor = conn.cursor()
    
    print("=" * 80)
    print("验证表注释")
    print("=" * 80)
    
    tables_to_check = [
        'device_rated_params',
        'calculation_parameters',
        'fact_measurements',
        'global_default_rated_params',
        'dim_stations',
        'dim_devices',
        'dim_metric_config'
    ]
    
    for table in tables_to_check:
        cursor.execute(f"""
            SELECT obj_description('{table}'::regclass, 'pg_class');
        """)
        result = cursor.fetchone()
        comment = result[0] if result and result[0] else "❌ 无注释"
        
        # 只显示前200个字符
        comment_preview = comment[:200] + "..." if len(comment) > 200 else comment
        print(f"\n表: {table}")
        print(f"注释: {comment_preview}")
        print(f"长度: {len(comment)} 字符")
    
    print("\n" + "=" * 80)
    print("验证字段注释")
    print("=" * 80)
    
    fields_to_check = [
        ('global_default_rated_params', 'param_key'),
        ('global_default_rated_params', 'default_value'),
        ('fact_measurements', 'quality_codes'),
        ('calculation_parameters', 'param_name'),
        ('calculation_parameters', 'is_optimizable'),
        ('dim_stations', 'is_active'),
        ('dim_devices', 'is_active')
    ]
    
    for table, column in fields_to_check:
        cursor.execute(f"""
            SELECT col_description('{table}'::regclass, 
                (SELECT ordinal_position FROM information_schema.columns 
                 WHERE table_name = '{table}' AND column_name = '{column}'));
        """)
        result = cursor.fetchone()
        comment = result[0] if result and result[0] else "❌ 无注释"
        
        print(f"\n字段: {table}.{column}")
        print(f"注释: {comment}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)

if __name__ == "__main__":
    try:
        verify_comments()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

