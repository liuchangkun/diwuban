from __future__ import annotations

import json
from pathlib import Path

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection, cleanup_database


def q(sql: str, *args):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def main() -> int:
    settings = load_settings(Path("configs"))
    init_database(settings)

    checks: dict[str, object] = {}

    # 1) 关键对象存在性（public）
    checks["public.metrics_presence_per_second_device"] = bool(
        q(
            "select to_regclass('public.metrics_presence_per_second_device') is not null"
        )[0][0]
    )

    # 2) 错误引用应不存在（reporting.metrics_presence_per_second_device）
    checks["reporting.metrics_presence_per_second_device_absent"] = bool(
        q("select to_regclass('reporting.metrics_presence_per_second_device') is null")[
            0
        ][0]
    )

    # 3) 核心事实表与最近分区是否存在（取最新 1 张分区名）
    rows = q(
        """
        select inhrelid::regclass::text
        from pg_inherits
        where inhparent = 'public.fact_measurements'::regclass
        order by inhrelid::text desc
        limit 1
        """
    )
    checks["fact_measurements_latest_partition"] = rows[0][0] if rows else None

    # 4) 主键存在性（fact_measurements）
    rows = q(
        """
        select indexrelid::regclass::text
        from pg_index i
        join pg_class c on c.oid=i.indrelid
        where c.relname='fact_measurements' and i.indisprimary
        """
    )
    checks["fact_measurements_pk_exists"] = bool(rows)

    # 5) presence 表列清单与近 1 天数据量（不作为失败条件）
    cols = q(
        """
        select column_name
        from information_schema.columns
        where table_schema='public' and table_name='metrics_presence_per_second_device'
        order by ordinal_position
        """
    )
    presence_columns = [r[0] for r in cols]
    checks["presence_columns"] = presence_columns

    ts_candidates = [
        "ts_second",
        "ts_bucket",
        "ts",
        "record_timestamp",
        "timestamp",
        "event_time",
        "time",
    ]
    ts_col = next((c for c in ts_candidates if c in presence_columns), None)
    if ts_col:
        rows = q(
            f"""
            select count(*)::bigint
            from public.metrics_presence_per_second_device
            where {ts_col} > now() - interval '1 day'
            """
        )
        checks["presence_count_1d"] = int(rows[0][0])
    else:
        checks["presence_count_1d"] = None

    print("CHECKS=" + json.dumps(checks, ensure_ascii=False))
    cleanup_database()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
