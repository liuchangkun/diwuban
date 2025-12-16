# -*- coding: utf-8 -*-
"""
数据库注释完整性分析脚本

分析所有表、视图、函数的注释情况
"""
import psycopg
import yaml
from pathlib import Path
import json

# 读取数据库配置
config_path = Path("configs/database.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

# 连接数据库
conn_str = f"host={db_config['host']} port={db_config['port']} dbname={db_config['dbname']} user={db_config['user']} password={db_config['password']}"

results = {
    'tables': [],
    'views': [],
    'functions': [],
    'summary': {}
}

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        print("=" * 100)
        print("1. 分析所有用户表")
        print("=" * 100)
        
        # 获取所有用户表（排除分区表和系统表）
        cur.execute("""
            SELECT 
                t.schemaname,
                t.tablename,
                obj_description((t.schemaname || '.' || t.tablename)::regclass, 'pg_class') as table_comment,
                (SELECT count(*) 
                 FROM pg_attribute a 
                 WHERE a.attrelid = (t.schemaname || '.' || t.tablename)::regclass 
                 AND a.attnum > 0 
                 AND NOT a.attisdropped) as column_count
            FROM pg_tables t
            WHERE t.schemaname = 'public'
            AND t.tablename NOT LIKE '_hyper_%'
            AND t.tablename NOT LIKE 'pg_%'
            ORDER BY t.tablename
        """)
        
        tables = cur.fetchall()
        print(f"\n找到 {len(tables)} 张用户表")
        
        for schema, table_name, table_comment, col_count in tables:
            print(f"\n【表】{table_name}")
            print(f"  字段数: {col_count}")
            print(f"  表注释: {table_comment or '❌ 缺失'}")
            
            # 获取该表的所有字段及其注释
            cur.execute("""
                SELECT 
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                    a.attnotnull as not_null,
                    col_description((%(schema)s || '.' || %(table)s)::regclass, a.attnum) as column_comment
                FROM pg_attribute a
                WHERE a.attrelid = (%(schema)s || '.' || %(table)s)::regclass
                AND a.attnum > 0
                AND NOT a.attisdropped
                ORDER BY a.attnum
            """, {'schema': schema, 'table': table_name})
            
            columns = cur.fetchall()
            columns_without_comment = []
            
            for col_name, data_type, not_null, col_comment in columns:
                if not col_comment:
                    columns_without_comment.append(col_name)
            
            if columns_without_comment:
                print(f"  ⚠️  缺少注释的字段 ({len(columns_without_comment)}/{col_count}): {', '.join(columns_without_comment[:5])}")
                if len(columns_without_comment) > 5:
                    print(f"      ... 还有 {len(columns_without_comment) - 5} 个字段")
            else:
                print(f"  ✅ 所有字段都有注释")
            
            results['tables'].append({
                'name': table_name,
                'table_comment': table_comment,
                'column_count': col_count,
                'columns_without_comment': columns_without_comment,
                'columns': [{'name': c[0], 'type': c[1], 'not_null': c[2], 'comment': c[3]} for c in columns]
            })
        
        print("\n" + "=" * 100)
        print("2. 分析所有视图")
        print("=" * 100)
        
        # 获取所有视图
        cur.execute("""
            SELECT 
                schemaname,
                viewname,
                obj_description((schemaname || '.' || viewname)::regclass, 'pg_class') as view_comment
            FROM pg_views
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        
        views = cur.fetchall()
        print(f"\n找到 {len(views)} 个视图")
        
        for schema, view_name, view_comment in views:
            print(f"\n【视图】{view_name}")
            print(f"  视图注释: {view_comment or '❌ 缺失'}")
            
            # 获取视图的字段
            cur.execute("""
                SELECT 
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                    col_description((%(schema)s || '.' || %(view)s)::regclass, a.attnum) as column_comment
                FROM pg_attribute a
                WHERE a.attrelid = (%(schema)s || '.' || %(view)s)::regclass
                AND a.attnum > 0
                AND NOT a.attisdropped
                ORDER BY a.attnum
            """, {'schema': schema, 'view': view_name})
            
            columns = cur.fetchall()
            columns_without_comment = [c[0] for c in columns if not c[2]]
            
            if columns_without_comment:
                print(f"  ⚠️  缺少注释的字段 ({len(columns_without_comment)}/{len(columns)}): {', '.join(columns_without_comment[:5])}")
            else:
                print(f"  ✅ 所有字段都有注释")
            
            results['views'].append({
                'name': view_name,
                'view_comment': view_comment,
                'columns_without_comment': columns_without_comment,
                'columns': [{'name': c[0], 'type': c[1], 'comment': c[2]} for c in columns]
            })
        
        print("\n" + "=" * 100)
        print("3. 分析所有函数")
        print("=" * 100)
        
        # 获取所有用户函数
        cur.execute("""
            SELECT 
                n.nspname as schema_name,
                p.proname as function_name,
                pg_get_function_arguments(p.oid) as arguments,
                pg_get_function_result(p.oid) as return_type,
                obj_description(p.oid, 'pg_proc') as function_comment
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public'
            AND p.prokind = 'f'
            ORDER BY p.proname
        """)
        
        functions = cur.fetchall()
        print(f"\n找到 {len(functions)} 个函数")
        
        for schema, func_name, args, ret_type, func_comment in functions:
            print(f"\n【函数】{func_name}({args})")
            print(f"  返回类型: {ret_type}")
            print(f"  函数注释: {func_comment or '❌ 缺失'}")
            
            results['functions'].append({
                'name': func_name,
                'arguments': args,
                'return_type': ret_type,
                'comment': func_comment
            })
        
        print("\n" + "=" * 100)
        print("4. 总结")
        print("=" * 100)
        
        # 统计
        tables_without_comment = [t for t in results['tables'] if not t['table_comment']]
        tables_with_missing_columns = [t for t in results['tables'] if t['columns_without_comment']]
        views_without_comment = [v for v in results['views'] if not v['view_comment']]
        views_with_missing_columns = [v for v in results['views'] if v['columns_without_comment']]
        functions_without_comment = [f for f in results['functions'] if not f['comment']]
        
        print(f"\n表统计：")
        print(f"  总数: {len(results['tables'])}")
        print(f"  缺少表注释: {len(tables_without_comment)}")
        print(f"  有字段缺少注释: {len(tables_with_missing_columns)}")
        
        print(f"\n视图统计：")
        print(f"  总数: {len(results['views'])}")
        print(f"  缺少视图注释: {len(views_without_comment)}")
        print(f"  有字段缺少注释: {len(views_with_missing_columns)}")
        
        print(f"\n函数统计：")
        print(f"  总数: {len(results['functions'])}")
        print(f"  缺少函数注释: {len(functions_without_comment)}")
        
        results['summary'] = {
            'total_tables': len(results['tables']),
            'tables_without_comment': len(tables_without_comment),
            'tables_with_missing_columns': len(tables_with_missing_columns),
            'total_views': len(results['views']),
            'views_without_comment': len(views_without_comment),
            'views_with_missing_columns': len(views_with_missing_columns),
            'total_functions': len(results['functions']),
            'functions_without_comment': len(functions_without_comment)
        }

# 保存结果到 JSON 文件
output_path = Path("reports/database_comments_analysis.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n✅ 分析完成，结果已保存到: {output_path}")

