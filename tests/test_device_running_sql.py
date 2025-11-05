from __future__ import annotations

"""
 device_running_sql  SQL     
  WHERE value IS DISTINCT FROM EXCLUDED.value      
"""

from app.adapters.db.device_running_sql import upsert_device_running_slice


def test_conflict_update_clause_contains_is_distinct_from(monkeypatch):
    #     
    captured = {}

    class DummyCur:
        rowcount = 0

        def __enter__(self):  # 支持 with 语法
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):  # type: ignore[no-untyped-def]
            captured["sql"] = sql

    class DummyConn:
        def cursor(self):  # type: ignore[no-untyped-def]
            return DummyCur()

    def nop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.adapters.db.device_running_sql.ensure_fact_weekly_partitions", nop
    )

    conn = DummyConn()
    upsert_device_running_slice(
        conn,
        station_id=1,
        device_id=2,
        metric_id=64,
        start_ts=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        end_ts=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    assert (
        "WHERE public.fact_measurements.value IS DISTINCT FROM EXCLUDED.value"
        in captured.get("sql", "")
    )
