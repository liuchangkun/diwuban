#!/usr/bin/env python3
"""
将public.metrics_presence_per_second_device转换为分区表
"""

from pathlib import Path
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings


def main():
    settings = load_settings(Path("configs"))

    # 先检查表是否存在
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 检查所有包含metrics的表
            cur.execute(
                """
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE tablename LIKE '%metrics%'
            """
            )
            tables = cur.fetchall()
            print(f"包含metrics的表: {tables}")

            # 检查表是否存在
            cur.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename = 'metrics_presence_per_second_device'
                )
            """
            )
            exists = cur.fetchone()[0]
            if not exists:
                print("❌ public schema中表不存在")
                # 检查reporting schema中是否有表
                cur.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM pg_tables
                        WHERE schemaname = 'reporting'
                        AND tablename = 'metrics_presence_per_second_device'
                    )
                """
                )
                reporting_exists = cur.fetchone()[0]
                if reporting_exists:
                    print("✅ 发现表在reporting schema中，需要移动到public schema")
                    # 移动表到public schema
                    cur.execute(
                        "ALTER TABLE reporting.metrics_presence_per_second_device SET SCHEMA public"
                    )
                    print("✅ 表已移动到public schema")
                else:
                    print("❌ 表在任何schema中都不存在，需要先创建")
                    return

            cur.execute(
                "SELECT COUNT(*) FROM public.metrics_presence_per_second_device"
            )
            count = cur.fetchone()[0]
            print(f"当前表中有 {count} 行数据")

            # 检查表类型
            cur.execute(
                """
                SELECT c.relkind,
                       CASE
                           WHEN c.relkind = 'p' THEN 'partitioned table'
                           WHEN c.relkind = 'r' THEN 'regular table'
                           ELSE 'other'
                       END as table_type
                FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'public' AND c.relname = 'metrics_presence_per_second_device'
            """
            )
            result = cur.fetchone()
            if result:
                print(f"表类型: {result[1]}")
                if result[0] == "p":
                    print("✅ 表已经是分区表")
                    return

    # 读取SQL脚本
    sql_content = Path("scripts/sql/convert_to_partitioned_table.sql").read_text(
        encoding="utf-8"
    )

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_content)
        conn.commit()
        print("✅ 分区表转换完成")


if __name__ == "__main__":
    main()
