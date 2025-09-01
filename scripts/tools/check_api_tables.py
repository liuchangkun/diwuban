#!/usr/bin/env python3
"""
简单的数据库结构查询脚本
专门查看API需要的表结构信息
"""

import psycopg
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(".").absolute()))


def check_api_tables():
    """检查API需要的表结构"""
    try:
        from app.core.config.loader_new import load_settings
        from app.adapters.db.gateway import make_dsn

        settings = load_settings(Path("configs"))
        dsn = make_dsn(settings)

        print("🔍 检查API相关的数据库表结构...\n")

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:

                # 1. 检查fact_measurements表结构
                print("📊 1. fact_measurements 表结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'fact_measurements'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type, nullable, default in columns:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"   - {col_name}: {data_type} {null_str}{default_str}")

                # 查看样本数据
                print("\n   样本数据:")
                cur.execute("SELECT * FROM fact_measurements LIMIT 2")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows, 1):
                        print(f"     记录{i}: {row}")
                else:
                    print("     无数据")

                # 2. 检查dim_devices表结构
                print("\n🔧 2. dim_devices 表结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'dim_devices'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type, nullable in columns:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"   - {col_name}: {data_type} {null_str}")

                # 查看样本数据
                print("\n   样本数据:")
                cur.execute("SELECT * FROM dim_devices LIMIT 2")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows, 1):
                        print(f"     记录{i}: {row}")

                # 3. 检查dim_stations表结构
                print("\n🏭 3. dim_stations 表结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'dim_stations'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type, nullable in columns:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"   - {col_name}: {data_type} {null_str}")

                # 查看样本数据
                print("\n   样本数据:")
                cur.execute("SELECT * FROM dim_stations LIMIT 2")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows, 1):
                        print(f"     记录{i}: {row}")

                # 4. 检查operation_data视图
                print("\n📋 4. operation_data 视图结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'operation_data'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type in columns:
                    print(f"   - {col_name}: {data_type}")

                # 查看样本数据
                print("\n   样本数据:")
                cur.execute("SELECT * FROM operation_data LIMIT 2")
                rows = cur.fetchall()
                if rows:
                    for i, row in enumerate(rows, 1):
                        print(f"     记录{i}: {row}")
                else:
                    print("     无数据")

                # 5. 检查station视图
                print("\n🏭 5. station 视图结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'station'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type in columns:
                    print(f"   - {col_name}: {data_type}")

                # 6. 检查device视图
                print("\n🔧 6. device 视图结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'device'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()
                for col_name, data_type in columns:
                    print(f"   - {col_name}: {data_type}")

        print("\n✅ 数据库表结构检查完成!")

    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    check_api_tables()
