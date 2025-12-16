#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成数据库字典文档"""

import psycopg2
import sys
from datetime import datetime

def generate_dictionary():
    """生成数据库字典"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )
    
    cursor = conn.cursor()
    
    # 创建Markdown文档
    output_file = "docs/database_dictionary.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 文档头部
        f.write("# 数据库字典\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("**数据库**: pump_station_optimization\n\n")
        f.write("---\n\n")
        
        # 目录
        f.write("## 目录\n\n")
        f.write("- [核心参数表](#核心参数表)\n")
        f.write("- [维度表](#维度表)\n")
        f.write("- [事实表](#事实表)\n")
        f.write("- [配置表](#配置表)\n")
        f.write("- [日志表](#日志表)\n")
        f.write("- [视图](#视图)\n\n")
        f.write("---\n\n")
        
        # 核心参数表
        f.write("## 核心参数表\n\n")
        
        param_tables = [
            'global_default_rated_params',
            'device_rated_params',
            'calculation_parameters'
        ]
        
        for table in param_tables:
            write_table_section(cursor, f, table)
        
        # 维度表
        f.write("## 维度表\n\n")
        
        dim_tables = [
            'dim_stations',
            'dim_devices',
            'dim_metric_config'
        ]
        
        for table in dim_tables:
            write_table_section(cursor, f, table)
        
        # 事实表
        f.write("## 事实表\n\n")
        
        fact_tables = [
            'fact_measurements'
        ]
        
        for table in fact_tables:
            write_table_section(cursor, f, table)
        
        # 配置表
        f.write("## 配置表\n\n")
        
        config_tables = [
            'calculation_method_registry',
            'metric_calculation_order',
            'metric_quality_rules',
            'quality_code_dict'
        ]
        
        for table in config_tables:
            write_table_section(cursor, f, table)
        
        # 日志表
        f.write("## 日志表\n\n")
        
        log_tables = [
            'calculation_failures_log',
            'completion_audit',
            'completion_failures',
            'completion_runs',
            'completion_steps',
            'optimization_history',
            'quality_diagnosis_log',
            'quality_profile_log'
        ]
        
        for table in log_tables:
            write_table_section(cursor, f, table)
    
    cursor.close()
    conn.close()
    
    print(f"数据库字典已生成: {output_file}")

def write_table_section(cursor, f, table):
    """写入表的章节"""
    # 获取表注释
    cursor.execute(f"""
        SELECT obj_description('{table}'::regclass, 'pg_class');
    """)
    result = cursor.fetchone()
    table_comment = result[0] if result and result[0] else "无注释"
    
    # 获取字段信息
    cursor.execute(f"""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default,
            col_description('{table}'::regclass, ordinal_position) AS column_comment
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = '{table}'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()
    
    # 写入表名
    f.write(f"### {table}\n\n")
    
    # 写入表注释
    f.write(f"**表注释**:\n\n")
    f.write(f"```\n{table_comment}\n```\n\n")
    
    # 写入字段表格
    f.write("**字段列表**:\n\n")
    f.write("| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |\n")
    f.write("|--------|----------|------|--------|------|\n")
    
    for col in columns:
        col_name = col[0]
        col_type = col[1]
        col_length = col[2]
        col_nullable = "是" if col[3] == "YES" else "否"
        col_default = col[4] if col[4] else "-"
        col_comment = col[5] if col[5] else "-"
        
        # 处理数据类型
        if col_length:
            col_type = f"{col_type}({col_length})"
        
        # 处理默认值（截断过长的默认值）
        if len(col_default) > 50:
            col_default = col_default[:47] + "..."
        
        # 处理注释（截断过长的注释）
        if len(col_comment) > 100:
            col_comment = col_comment[:97] + "..."
        
        # 转义Markdown特殊字符
        col_comment = col_comment.replace("|", "\\|")
        col_default = col_default.replace("|", "\\|")
        
        f.write(f"| {col_name} | {col_type} | {col_nullable} | {col_default} | {col_comment} |\n")
    
    f.write("\n---\n\n")

if __name__ == "__main__":
    try:
        generate_dictionary()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

