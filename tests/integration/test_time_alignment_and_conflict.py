# test_time_alignment_and_conflict.py
# 目的：验证“整秒对齐 + 冲突合并（同秒主键）”
# 约定：
# - 通过 SQL 连接执行 DB 函数（此处仅给出测试骨架与伪代码）
# - 实际项目中请使用项目内的数据库连接工具/fixtures

import os
import datetime as dt
import pytest

# 占位：获取 DB 连接（请替换为项目实际连接方法）
import psycopg

DB_DSN = os.environ.get(
    "TEST_DB_DSN", "postgresql://postgres:postgres@localhost:5432/postgres"
)


@pytest.fixture(scope="module")
def conn():
    with psycopg.connect(DB_DSN) as c:
        yield c


@pytest.fixture
def cleanup(conn):
    # 清理目标时间窗口内的测试数据
    with conn.cursor() as cur:
        cur.execute(
            "SELECT api.delete_measurements_by_filter(ARRAY[1], now()-interval '1 hour', now()+interval '1 hour')"
        )
    conn.commit()
    yield
    with conn.cursor() as cur:
        cur.execute(
            "SELECT api.delete_measurements_by_filter(ARRAY[1], now()-interval '1 hour', now()+interval '1 hour')"
        )
    conn.commit()


def test_time_alignment_to_second_and_conflict_merge(conn, cleanup):
    station_id, device_id, metric_id = 1, 10, 101

    # 构造两个落在同一秒内的本地时间（含毫秒）
    base_ts = dt.datetime.utcnow().replace(microsecond=0)  # 整秒基准（UTC）
    ts_local_a = base_ts + dt.timedelta(milliseconds=120)
    ts_local_b = base_ts + dt.timedelta(milliseconds=850)

    with conn.cursor() as cur:
        # 使用本地时间接口写入（由 DB 侧按站点 tz 转 UTC 并对齐到秒）
        cur.execute(
            "SELECT public.safe_upsert_measurement_local(%s,%s,%s,%s,%s,%s)",
            (station_id, device_id, metric_id, ts_local_a, 12.34, "test_a"),
        )
        cur.execute(
            "SELECT public.safe_upsert_measurement_local(%s,%s,%s,%s,%s,%s)",
            (station_id, device_id, metric_id, ts_local_b, 56.78, "test_b"),
        )
    conn.commit()

    # 查询该秒的记录应只有 1 条（同一主键同一秒应合并）
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM public.fact_measurements
            WHERE station_id=%s AND device_id=%s AND metric_id=%s
              AND ts_bucket = date_trunc('second', %s AT TIME ZONE 'UTC')
            """,
            (station_id, device_id, metric_id, base_ts),
        )
        (count,) = cur.fetchone()
        assert count == 1

    # 校验 ts_bucket 已对齐到整秒
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT (date_trunc('second', ts_bucket) = ts_bucket) AS aligned
            FROM public.fact_measurements
            WHERE station_id=%s AND device_id=%s AND metric_id=%s
              AND ts_bucket = date_trunc('second', %s AT TIME ZONE 'UTC')
            LIMIT 1
            """,
            (station_id, device_id, metric_id, base_ts),
        )
        (aligned,) = cur.fetchone()
        assert aligned
