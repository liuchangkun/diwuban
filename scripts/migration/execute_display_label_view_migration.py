#!/usr/bin/env python3
"""
执行 display_label 视图迁移脚本

用途：
  解决 Windows psql 编码问题，使用 Python 执行 SQL 迁移脚本

执行方式：
  python scripts/migration/execute_display_label_view_migration.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg
import yaml


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


def execute_migration():
    """执行迁移脚本"""

    # 读取 SQL 文件
    sql_file = project_root / "scripts" / "sql" / "migrations" / "056_add_fact_measurements_display_label_view.sql"

    print(f"📄 读取迁移脚本：{sql_file}")

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print(f"✅ 脚本读取成功（{len(sql_content)} 字符）")

    # 移除 psql 特定的元命令（\echo）
    import re
    sql_content = re.sub(r'\\echo.*\n', '', sql_content)

    print(f"✅ 清理 psql 元命令后：{len(sql_content)} 字符")

    # 获取数据库连接参数
    conn_params = get_db_config()

    print(f"\n🔌 连接数据库：{conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}")

    # 执行 SQL
    try:
        with psycopg.connect(**conn_params, autocommit=False) as conn:
            with conn.cursor() as cur:
                print("\n🚀 开始执行迁移脚本...")
                print("=" * 60)

                # 执行 SQL（psycopg3 会自动处理 UTF-8 编码）
                cur.execute(sql_content)

                # 提交事务
                conn.commit()

                print("=" * 60)
                print("✅ 迁移脚本执行成功")
                
                # 验证视图是否创建成功
                print("\n🔍 验证视图是否创建成功...")
                
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.views 
                        WHERE table_schema = 'public' 
                        AND table_name = 'v_fact_measurements_with_label'
                    )
                """)
                view_exists = cur.fetchone()[0]
                
                if view_exists:
                    print("✅ 视图 v_fact_measurements_with_label 创建成功")
                    
                    # 获取视图字段数量
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'v_fact_measurements_with_label'
                    """)
                    column_count = cur.fetchone()[0]
                    print(f"✅ 视图包含 {column_count} 个字段")
                else:
                    print("❌ 视图创建失败")
                    return False
                
                # 验证索引是否创建成功
                print("\n🔍 验证索引是否创建成功...")
                
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'fact_measurements' 
                        AND indexname = 'idx_fm_station_device_metric'
                    )
                """)
                index_exists = cur.fetchone()[0]
                
                if index_exists:
                    print("✅ 索引 idx_fm_station_device_metric 创建成功")
                else:
                    print("❌ 索引创建失败")
                    return False
                
                return True
                
    except Exception as e:
        print(f"\n❌ 迁移脚本执行失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_view():
    """测试视图是否正常工作"""

    print("\n" + "=" * 60)
    print("🧪 测试视图功能")
    print("=" * 60)

    conn_params = get_db_config()
    
    try:
        with psycopg.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # 测试1：查询视图结构
                print("\n【测试1】查询视图字段列表")
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'v_fact_measurements_with_label'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                print(f"✅ 视图包含 {len(columns)} 个字段：")
                for col_name, col_type in columns:
                    print(f"   - {col_name}: {col_type}")
                
                # 测试2：查询视图数据（如果有数据）
                print("\n【测试2】查询视图数据")
                cur.execute("""
                    SELECT COUNT(*) FROM v_fact_measurements_with_label
                """)
                row_count = cur.fetchone()[0]
                
                if row_count > 0:
                    print(f"✅ 视图包含 {row_count} 条记录")
                    
                    # 查询前5条记录
                    cur.execute("""
                        SELECT 
                            display_label,
                            station_name,
                            device_name,
                            metric_display,
                            ts_bucket,
                            value
                        FROM v_fact_measurements_with_label
                        ORDER BY ts_bucket DESC
                        LIMIT 5
                    """)
                    rows = cur.fetchall()
                    
                    print("\n前5条记录：")
                    for row in rows:
                        print(f"   - {row[0]}: {row[5]} (时间: {row[4]})")
                else:
                    print("⚠️  视图当前无数据（fact_measurements 表为空）")
                
                # 测试3：测试 JOIN 性能
                print("\n【测试3】测试 JOIN 性能")
                cur.execute("""
                    EXPLAIN ANALYZE
                    SELECT display_label, COUNT(*) 
                    FROM v_fact_measurements_with_label
                    GROUP BY display_label
                """)
                explain_result = cur.fetchall()
                
                print("✅ 查询计划：")
                for line in explain_result:
                    print(f"   {line[0]}")
                
                return True
                
    except Exception as e:
        print(f"\n❌ 视图测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    
    print("=" * 60)
    print("🚀 执行 display_label 视图迁移")
    print("=" * 60)
    
    # 执行迁移
    if not execute_migration():
        print("\n❌ 迁移失败")
        sys.exit(1)
    
    # 测试视图
    if not test_view():
        print("\n❌ 视图测试失败")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ 迁移和测试全部完成")
    print("=" * 60)
    print("\n使用示例：")
    print("  SELECT * FROM v_fact_measurements_with_label LIMIT 10;")
    print("\n性能建议：")
    print("  - 查询时必须包含时间范围过滤")
    print("  - 优先使用 station_id、device_id、metric_id 过滤")
    print("")


if __name__ == "__main__":
    main()

