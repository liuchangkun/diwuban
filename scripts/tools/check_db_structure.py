#!/usr/bin/env python3
"""
检查数据库结构
"""

import psycopg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(".").absolute()))
from app.core.config.loader_new import load_settings


def check_database():
    """检查数据库结构"""
    try:
        settings = load_settings(Path("configs"))
        # 使用make_dsn构建连接字符串
        from app.adapters.db.gateway import make_dsn

        dsn = make_dsn(settings)
        print("连接数据库...")

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 检查operation_data视图
                print("\n=== operation_data视图定义 ===")
                try:
                    cur.execute("SELECT pg_get_viewdef('operation_data', true)")
                    view_def = cur.fetchone()
                    if view_def:
                        print("当前operation_data视图定义:")
                        print(view_def[0])
                    else:
                        print("operation_data视图不存在")
                except Exception as e:
                    print(f"获取视图定义失败: {e}")

                # 检查fact_measurements表结构
                print("\n=== fact_measurements表结构 ===")
                cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'fact_measurements' ORDER BY ordinal_position"
                )
                for row in cur.fetchall():
                    print(f"  {row[0]}: {row[1]}")

                # 检查dim_devices表结构
                print("\n=== dim_devices表结构 ===")
                cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'dim_devices' ORDER BY ordinal_position"
                )
                for row in cur.fetchall():
                    print(f"  {row[0]}: {row[1]}")

                # 检查dim_metric_config表中有哪些指标
                print("\n=== 前20个指标配置 ===")
                cur.execute(
                    "SELECT id, metric_key, unit, unit_display FROM dim_metric_config ORDER BY id LIMIT 20"
                )
                for row in cur.fetchall():
                    print(f'  ID={row[0]}: {row[1]} ({row[2]}) [{row[3] or "N/A"}]')

                # 检查fact_measurements中的数据样本
                print("\n=== fact_measurements数据样本 ===")
                cur.execute(
                    """
                    SELECT f.station_id, f.device_id, f.metric_id, f.ts_raw, f.value, m.metric_key, m.unit_display
                    FROM fact_measurements f
                    JOIN dim_metric_config m ON f.metric_id = m.id
                    ORDER BY f.ts_raw DESC
                    LIMIT 10
                """
                )
                for row in cur.fetchall():
                    print(
                        f"  station_id={row[0]}, device_id={row[1]}, metric_id={row[2]}, ts={row[3]}, value={row[4]}, metric={row[5]}, unit={row[6]}"
                    )

    except Exception as e:
        print(f"检查数据库失败: {e}")


if __name__ == "__main__":
    check_database()
