import pytest
import sys
from pathlib import Path

# 确保可以导入 app 包
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import app.services.reporting.presence_writer as pw


class DummyCursor:
    def __init__(self, record_calls):
        self.record_calls = record_calls
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.record_calls.append((sql, tuple(params) if params is not None else None))

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return []


class DummyConn:
    def __init__(self, record_calls):
        self.record_calls = record_calls
        self.closed = False

    def cursor(self):
        return DummyCursor(self.record_calls)


def test_ensure_partitions_noop_on_hypertable():
    calls = []
    conn = DummyConn(calls)
    ts = datetime(2025, 2, 27, 19, 55, tzinfo=timezone.utc)

    # run（DummyCursor.fetchone() 返回 (1,) 会使 is_ht=True → 应当直接 no-op）
    pw.ensure_partitions(conn, ts)

    # assert：Hypertable 环境下不应调用 ensure_mpps_partitions()
    assert not any(
        sql.strip().startswith("SELECT public.ensure_mpps_partitions(")
        for sql, params in calls
    ), f"expected no ensure_mpps_partitions call on hypertable, calls={calls}"


def test_upsert_window_calls_ensure_and_executes_sql(monkeypatch):
    calls = []
    conn = DummyConn(calls)

    ensured = {"called": False, "ts": None}

    def fake_ensure(conn_arg, ts):
        ensured["called"] = True
        ensured["ts"] = ts

    monkeypatch.setattr(pw, "ensure_partitions", fake_ensure)

    # Patch file read to avoid dependency on real SQL files
    last_sql_path = {"path": None}

    def fake_read_text(self, encoding="utf-8"):
        last_sql_path["path"] = str(self)
        return "SELECT 1"

    monkeypatch.setattr(pw.Path, "read_text", fake_read_text, raising=False)

    start = datetime(2025, 2, 27, 19, 55, tzinfo=timezone.utc)
    end = start + timedelta(minutes=5)

    # run without device（新实现统一走 sync_presence_from_cagg.sql，始终4参数）
    affected = pw.upsert_window(conn, start, end, station_id=None, device_id=None)

    # assertions
    assert ensured["called"] and ensured["ts"] == start
    assert any("SET LOCAL statement_timeout" in sql for sql, _ in calls)
    assert any(sql.strip() == "SELECT 1" for sql, _ in calls)
    assert affected == 0

    # run with device（同样4参数）
    calls.clear()
    affected2 = pw.upsert_window(conn, start, end, station_id=1, device_id=101)
    select_calls = [c for c in calls if c[0].strip() == "SELECT 1"]
    assert select_calls, f"no SELECT 1 executed, calls={calls}"
    assert select_calls[0][1] == (start, end, 1, 101)
    assert affected2 == 0
