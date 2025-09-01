#!/usr/bin/env python3
"""
检查视图的列名结构
"""

import psycopg2
import os


def check_view_columns():
    """检查视图的列名"""

    conn_config = {
        "host": "localhost",
        "port": 5432,
        "database": "pump_station_optimization",
        "user": "postgres",
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }

    try:
        with psycopg2.connect(**conn_config) as conn:
            with conn.cursor() as cur:

                # 1. 查看所有视图
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                )
                views = cur.fetchall()
                print("📊 当前数据库中的视图:")
                for view in views:
                    print(f"  - {view[0]}")

                # 2. 检查每个视图的列结构
                for view in views:
                    view_name = view[0]
                    print(f"\n🔍 检查视图 '{view_name}' 的列结构:")

                    cur.execute(
                        f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = '{view_name}' AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """
                    )
                    columns = cur.fetchall()

                    for col_name, data_type, nullable in columns:
                        print(
                            f"  📝 {col_name} ({data_type}) {'NULL' if nullable == 'YES' else 'NOT NULL'}"
                        )

                    # 查看视图的前几行数据
                    print(f"\n📋 视图 '{view_name}' 的示例数据:")
                    try:
                        cur.execute(f"SELECT * FROM {view_name} LIMIT 3")
                        rows = cur.fetchall()
                        if rows:
                            # 获取列名
                            col_names = [desc[0] for desc in cur.description]
                            print(f"  列名: {col_names}")
                            for i, row in enumerate(rows, 1):
                                print(f"  行{i}: {row}")
                        else:
                            print("  视图无数据")
                    except Exception as e:
                        print(f"  ❌ 查询视图数据失败: {e}")

                # 3. 也检查一下operation_data表的结构作为对比
                print("\n🔍 检查 'operation_data' 表的列结构:")
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'operation_data' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()

                for col_name, data_type, nullable in columns:
                    print(
                        f"  📝 {col_name} ({data_type}) {'NULL' if nullable == 'YES' else 'NOT NULL'}"
                    )

    except Exception as e:
        print(f"❌ 查询失败: {e}")


if __name__ == "__main__":
    check_view_columns()
