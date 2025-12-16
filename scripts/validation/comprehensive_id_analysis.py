#!/usr/bin/env python3
"""
综合ID关联分析脚本

用途：全面分析 dim_stations.id、dim_devices.id、dim_metric_config.id 和 metric_key 的关联关系
作者：AI
创建日期：2025-10-30
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def analyze_foreign_keys() -> Dict[str, Any]:
    """分析所有外键约束"""
    print("=" * 80)
    print("1. 数据库外键约束分析")
    print("=" * 80)
    print()
    
    # 查询所有外键约束
    query = """
    SELECT 
        tc.table_schema,
        tc.table_name,
        kcu.column_name,
        ccu.table_schema AS foreign_table_schema,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        rc.update_rule,
        rc.delete_rule,
        tc.constraint_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    JOIN information_schema.referential_constraints AS rc
        ON rc.constraint_name = tc.constraint_name
        AND rc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND (
            (ccu.table_name = 'dim_stations' AND ccu.column_name = 'id')
            OR (ccu.table_name = 'dim_devices' AND ccu.column_name = 'id')
            OR (ccu.table_name = 'dim_metric_config' AND ccu.column_name = 'id')
            OR (ccu.table_name = 'dim_metric_config' AND ccu.column_name = 'metric_key')
        )
    ORDER BY ccu.table_name, ccu.column_name, tc.table_name;
    """
    
    results = {
        'dim_stations.id': [],
        'dim_devices.id': [],
        'dim_metric_config.id': [],
        'dim_metric_config.metric_key': []
    }
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
            for row in rows:
                (table_schema, table_name, column_name, 
                 foreign_table_schema, foreign_table_name, foreign_column_name,
                 update_rule, delete_rule, constraint_name) = row
                
                key = f"{foreign_table_name}.{foreign_column_name}"
                
                fk_info = {
                    'table': f"{table_schema}.{table_name}",
                    'column': column_name,
                    'constraint_name': constraint_name,
                    'update_rule': update_rule,
                    'delete_rule': delete_rule
                }
                
                if key in results:
                    results[key].append(fk_info)
    
    # 打印结果
    for key, fks in results.items():
        print(f"\n### 引用 {key} 的外键（共 {len(fks)} 个）")
        print("-" * 80)
        
        if not fks:
            print("  ⚠️  未找到外键约束")
            continue
        
        cascade_count = sum(1 for fk in fks if fk['update_rule'] == 'CASCADE')
        print(f"  ON UPDATE CASCADE: {cascade_count}/{len(fks)} ({cascade_count/len(fks)*100:.1f}%)")
        print()
        
        for fk in fks:
            status = "✅" if fk['update_rule'] == 'CASCADE' else "❌"
            print(f"  {status} {fk['table']}.{fk['column']}")
            print(f"     约束名: {fk['constraint_name']}")
            print(f"     ON UPDATE: {fk['update_rule']}, ON DELETE: {fk['delete_rule']}")
            print()
    
    return results


def analyze_table_relationships() -> Dict[str, Any]:
    """分析表之间的关联关系（包括记录数量）"""
    print("=" * 80)
    print("2. 表关联关系和数据统计")
    print("=" * 80)
    print()
    
    tables_to_check = [
        'dim_stations',
        'dim_devices',
        'dim_metric_config',
        'device_rated_params',
        'device_running_thresholds',
        'fact_measurements',
        'fact_device_status',
        'fact_pump_efficiency',
        'fact_pump_performance',
        'fact_system_metrics'
    ]
    
    stats = {}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in tables_to_check:
                try:
                    # 获取记录数量
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    
                    # 获取表的列信息
                    cur.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """, (table,))
                    columns = cur.fetchall()
                    
                    # 检查是否有相关的ID列
                    related_columns = []
                    for col_name, col_type in columns:
                        if any(keyword in col_name for keyword in ['station_id', 'device_id', 'metric_id', 'metric_key']):
                            related_columns.append((col_name, col_type))
                    
                    stats[table] = {
                        'count': count,
                        'related_columns': related_columns
                    }
                    
                    print(f"### {table}")
                    print(f"  记录数量: {count:,}")
                    if related_columns:
                        print(f"  关联列: {', '.join([f'{col}({dtype})' for col, dtype in related_columns])}")
                    print()
                    
                except Exception as e:
                    print(f"  ❌ 查询失败: {e}")
                    print()
    
    return stats


def check_orphaned_records() -> Dict[str, List[Any]]:
    """检查孤立记录（外键引用不存在的ID）"""
    print("=" * 80)
    print("3. 孤立记录检查")
    print("=" * 80)
    print()
    
    orphaned = {}
    
    checks = [
        {
            'name': 'dim_devices.station_id',
            'query': """
                SELECT id, station_id, name 
                FROM dim_devices 
                WHERE station_id NOT IN (SELECT id FROM dim_stations)
            """
        },
        {
            'name': 'device_rated_params.device_id',
            'query': """
                SELECT device_id 
                FROM device_rated_params 
                WHERE device_id NOT IN (SELECT id FROM dim_devices)
            """
        },
        {
            'name': 'device_running_thresholds.device_id',
            'query': """
                SELECT device_id 
                FROM device_running_thresholds 
                WHERE device_id NOT IN (SELECT id FROM dim_devices)
            """
        },
        {
            'name': 'fact_measurements.device_id',
            'query': """
                SELECT DISTINCT device_id 
                FROM fact_measurements 
                WHERE device_id NOT IN (SELECT id FROM dim_devices)
                LIMIT 10
            """
        }
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for check in checks:
                try:
                    cur.execute(check['query'])
                    rows = cur.fetchall()
                    
                    if rows:
                        orphaned[check['name']] = rows
                        print(f"❌ {check['name']}: 发现 {len(rows)} 条孤立记录")
                        for row in rows[:5]:  # 只显示前5条
                            print(f"   {row}")
                        if len(rows) > 5:
                            print(f"   ... 还有 {len(rows) - 5} 条")
                    else:
                        print(f"✅ {check['name']}: 无孤立记录")
                    print()
                except Exception as e:
                    print(f"❌ {check['name']}: 检查失败 - {e}")
                    print()
    
    return orphaned


def check_id_duplicates() -> Dict[str, Any]:
    """检查ID重复"""
    print("=" * 80)
    print("4. ID重复检查")
    print("=" * 80)
    print()
    
    duplicates = {}
    
    tables = ['dim_stations', 'dim_devices', 'dim_metric_config']
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"""
                    SELECT id, COUNT(*) as cnt 
                    FROM {table} 
                    GROUP BY id 
                    HAVING COUNT(*) > 1
                """)
                rows = cur.fetchall()
                
                if rows:
                    duplicates[table] = rows
                    print(f"❌ {table}: 发现 {len(rows)} 个重复ID")
                    for id_val, cnt in rows:
                        print(f"   ID={id_val} 出现 {cnt} 次")
                else:
                    print(f"✅ {table}: 无重复ID")
                print()
    
    return duplicates


def verify_cascade_updates() -> Dict[str, Any]:
    """验证CASCADE更新是否正常工作（通过检查ID一致性）"""
    print("=" * 80)
    print("5. CASCADE更新验证")
    print("=" * 80)
    print()
    
    results = {}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 验证 dim_devices.station_id 与 dim_stations.id 的一致性
            cur.execute("""
                SELECT d.station_id, COUNT(*) as device_count
                FROM dim_devices d
                GROUP BY d.station_id
                ORDER BY d.station_id
            """)
            device_stations = cur.fetchall()
            
            print("### dim_devices.station_id 分布")
            for station_id, count in device_stations:
                cur.execute("SELECT name FROM dim_stations WHERE id = %s", (station_id,))
                station = cur.fetchone()
                if station:
                    print(f"  ✅ station_id={station_id} ({station[0]}): {count} 个设备")
                else:
                    print(f"  ❌ station_id={station_id}: {count} 个设备（泵站不存在！）")
            print()
            
            results['device_stations'] = device_stations
    
    return results


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "综合ID关联分析报告" + " " * 38 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行各项分析
    fk_results = analyze_foreign_keys()
    table_stats = analyze_table_relationships()
    orphaned = check_orphaned_records()
    duplicates = check_id_duplicates()
    cascade_results = verify_cascade_updates()
    
    # 生成总结报告
    print("=" * 80)
    print("总结报告")
    print("=" * 80)
    print()
    
    # 统计外键配置
    total_fks = sum(len(fks) for fks in fk_results.values())
    cascade_fks = sum(
        sum(1 for fk in fks if fk['update_rule'] == 'CASCADE')
        for fks in fk_results.values()
    )
    
    print(f"✅ 外键总数: {total_fks}")
    print(f"✅ CASCADE配置: {cascade_fks}/{total_fks} ({cascade_fks/total_fks*100:.1f}%)")
    print()
    
    # 孤立记录
    if orphaned:
        print(f"⚠️  发现孤立记录: {len(orphaned)} 个表")
        for table, records in orphaned.items():
            print(f"   - {table}: {len(records)} 条")
    else:
        print("✅ 无孤立记录")
    print()
    
    # ID重复
    if duplicates:
        print(f"❌ 发现ID重复: {len(duplicates)} 个表")
        for table, dups in duplicates.items():
            print(f"   - {table}: {len(dups)} 个重复ID")
    else:
        print("✅ 无ID重复")
    print()
    
    print("=" * 80)
    print("分析完成")
    print("=" * 80)


if __name__ == "__main__":
    main()

