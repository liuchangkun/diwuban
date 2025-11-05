#!/usr/bin/env python3
"""
测试 v_fact_measurements_with_label 视图

用途：
  演示视图的使用方法和查询性能
  
执行方式：
  python scripts/test/test_display_label_view.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg
import yaml
from datetime import datetime, timedelta


def get_db_config():
    """从 database.yaml 读取数据库配置"""
    config_file = project_root / "configs" / "database.yaml"
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return {
        "host": config.get("host", "localhost"),
        "port": config.get("port", 5432),
        "dbname": config.get("dbname", "pump_station_optimization"),
        "user": config.get("user", "postgres"),
        "password": config.get("password"),
    }


def test_view_structure():
    """测试1：查看视图结构"""
    print("\n" + "=" * 60)
    print("【测试1】查看视图结构")
    print("=" * 60)
    
    conn_params = get_db_config()
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            # 查询视图字段
            cur.execute("""
                SELECT 
                    column_name, 
                    data_type,
                    col_description('v_fact_measurements_with_label'::regclass, ordinal_position) AS description
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'v_fact_measurements_with_label'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            
            print(f"\n✅ 视图包含 {len(columns)} 个字段：\n")
            
            # 分组显示字段
            print("【原始字段】（来自 fact_measurements）")
            for col_name, col_type, description in columns[:13]:
                desc = description if description else ""
                print(f"  - {col_name:20s} ({col_type:25s}) {desc}")
            
            print("\n【维度字段】（来自维度表）")
            for col_name, col_type, description in columns[13:20]:
                desc = description if description else ""
                print(f"  - {col_name:20s} ({col_type:25s}) {desc}")
            
            print("\n【组合标识符】（核心字段）")
            col_name, col_type, description = columns[20]
            desc = description if description else ""
            print(f"  - {col_name:20s} ({col_type:25s})")
            if desc:
                print(f"    {desc[:100]}...")


def test_view_query():
    """测试2：查询视图数据"""
    print("\n" + "=" * 60)
    print("【测试2】查询视图数据")
    print("=" * 60)
    
    conn_params = get_db_config()
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            # 查询记录数量
            cur.execute("SELECT COUNT(*) FROM v_fact_measurements_with_label")
            count = cur.fetchone()[0]
            
            print(f"\n✅ 视图包含 {count} 条记录")
            
            if count > 0:
                # 查询前10条记录
                cur.execute("""
                    SELECT 
                        display_label,
                        ts_bucket,
                        value,
                        unit,
                        quality_status
                    FROM v_fact_measurements_with_label
                    ORDER BY ts_bucket DESC
                    LIMIT 10
                """)
                rows = cur.fetchall()
                
                print("\n前10条记录：")
                print(f"{'组合标识符':<50s} {'时间':<25s} {'值':<10s} {'单位':<10s} {'质量':<5s}")
                print("-" * 100)
                for row in rows:
                    display_label, ts_bucket, value, unit, quality_status = row
                    ts_str = ts_bucket.strftime("%Y-%m-%d %H:%M:%S") if ts_bucket else "N/A"
                    print(f"{display_label:<50s} {ts_str:<25s} {value:<10.2f} {unit:<10s} {quality_status:<5d}")
            else:
                print("\n⚠️  视图当前无数据（fact_measurements 表为空）")
                print("\n💡 提示：可以运行数据导入脚本来填充数据")


def test_view_filter():
    """测试3：测试过滤查询"""
    print("\n" + "=" * 60)
    print("【测试3】测试过滤查询")
    print("=" * 60)
    
    conn_params = get_db_config()
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            # 测试按 display_label 过滤
            print("\n【查询示例1】按组合标识符过滤（LIKE '%1#泵%'）")
            cur.execute("""
                SELECT display_label, COUNT(*) AS count
                FROM v_fact_measurements_with_label
                WHERE display_label LIKE '%1#泵%'
                GROUP BY display_label
                ORDER BY count DESC
            """)
            rows = cur.fetchall()
            
            if rows:
                print(f"✅ 找到 {len(rows)} 个匹配的设备：")
                for display_label, count in rows:
                    print(f"  - {display_label}: {count} 条记录")
            else:
                print("⚠️  无匹配记录")
            
            # 测试按泵站和设备过滤
            print("\n【查询示例2】按泵站和设备名称过滤")
            cur.execute("""
                SELECT display_label, COUNT(*) AS count
                FROM v_fact_measurements_with_label
                WHERE station_name = '二期供水泵房'
                  AND device_name LIKE '%1#泵%'
                GROUP BY display_label
                ORDER BY count DESC
            """)
            rows = cur.fetchall()
            
            if rows:
                print(f"✅ 找到 {len(rows)} 个匹配的指标：")
                for display_label, count in rows:
                    print(f"  - {display_label}: {count} 条记录")
            else:
                print("⚠️  无匹配记录")
            
            # 测试按指标类型过滤
            print("\n【查询示例3】按指标类型过滤（频率相关）")
            cur.execute("""
                SELECT display_label, COUNT(*) AS count
                FROM v_fact_measurements_with_label
                WHERE metric_display LIKE '%频率%'
                GROUP BY display_label
                ORDER BY count DESC
            """)
            rows = cur.fetchall()
            
            if rows:
                print(f"✅ 找到 {len(rows)} 个频率相关指标：")
                for display_label, count in rows:
                    print(f"  - {display_label}: {count} 条记录")
            else:
                print("⚠️  无匹配记录")


def test_view_performance():
    """测试4：测试查询性能"""
    print("\n" + "=" * 60)
    print("【测试4】测试查询性能")
    print("=" * 60)
    
    conn_params = get_db_config()
    
    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            # 测试简单查询性能
            print("\n【性能测试1】简单查询（LIMIT 100）")
            cur.execute("""
                EXPLAIN ANALYZE
                SELECT * FROM v_fact_measurements_with_label
                LIMIT 100
            """)
            explain_result = cur.fetchall()
            
            # 提取执行时间
            for line in explain_result:
                if "Execution Time" in line[0]:
                    print(f"✅ {line[0]}")
            
            # 测试带时间范围的查询性能
            print("\n【性能测试2】带时间范围过滤的查询")
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
            
            cur.execute("""
                EXPLAIN ANALYZE
                SELECT display_label, COUNT(*) 
                FROM v_fact_measurements_with_label
                WHERE ts_bucket >= %s AND ts_bucket < %s
                GROUP BY display_label
            """, (start_time, end_time))
            explain_result = cur.fetchall()
            
            # 提取执行时间
            for line in explain_result:
                if "Execution Time" in line[0]:
                    print(f"✅ {line[0]}")
            
            # 测试带设备过滤的查询性能
            print("\n【性能测试3】带设备ID过滤的查询")
            cur.execute("""
                EXPLAIN ANALYZE
                SELECT display_label, AVG(value) AS avg_value
                FROM v_fact_measurements_with_label
                WHERE device_id = 1
                GROUP BY display_label
            """)
            explain_result = cur.fetchall()
            
            # 提取执行时间
            for line in explain_result:
                if "Execution Time" in line[0]:
                    print(f"✅ {line[0]}")


def test_view_examples():
    """测试5：实际使用示例"""
    print("\n" + "=" * 60)
    print("【测试5】实际使用示例")
    print("=" * 60)
    
    print("\n以下是一些实际使用示例的 SQL 语句：\n")
    
    examples = [
        ("查询所有测量数据（带标识符）", """
SELECT * FROM v_fact_measurements_with_label 
WHERE ts_bucket >= '2025-10-01' AND ts_bucket < '2025-10-02'
ORDER BY ts_bucket;
        """),
        
        ("按组合标识符过滤", """
SELECT * FROM v_fact_measurements_with_label 
WHERE display_label LIKE '%1#泵%'
ORDER BY ts_bucket DESC
LIMIT 100;
        """),
        
        ("按泵站和设备查询", """
SELECT display_label, ts_bucket, value, unit
FROM v_fact_measurements_with_label 
WHERE station_name = '二期供水泵房'
  AND device_name LIKE '%1#泵%'
  AND ts_bucket >= NOW() - INTERVAL '1 hour'
ORDER BY ts_bucket DESC;
        """),
        
        ("统计每个设备的测量数据量", """
SELECT display_label, COUNT(*) AS measurement_count
FROM v_fact_measurements_with_label 
WHERE ts_bucket >= NOW() - INTERVAL '1 day'
GROUP BY display_label
ORDER BY measurement_count DESC;
        """),
        
        ("查询特定指标的最新值", """
SELECT 
    display_label,
    ts_bucket,
    value,
    unit
FROM v_fact_measurements_with_label 
WHERE metric_key = 'pump_frequency'
ORDER BY ts_bucket DESC
LIMIT 10;
        """),
    ]
    
    for i, (title, sql) in enumerate(examples, 1):
        print(f"【示例{i}】{title}")
        print(sql)


def main():
    """主函数"""
    
    print("=" * 60)
    print("🧪 测试 v_fact_measurements_with_label 视图")
    print("=" * 60)
    
    try:
        # 执行所有测试
        test_view_structure()
        test_view_query()
        test_view_filter()
        test_view_performance()
        test_view_examples()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

