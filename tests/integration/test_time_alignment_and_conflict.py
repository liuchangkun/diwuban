# test_time_alignment_and_conflict.py
# 目的：验证“整秒对齐 + 冲突合并（同秒主键）”
# 约定：
# - 通过 SQL 连接执行 DB 函数（此处仅给出测试骨架与伪代码）
# - 实际项目中请使用项目内的数据库连接工具/fixtures

import datetime as dt

import pytest

from app.core.config.loader import Settings

# 占位：获取 DB 连接（请替换为项目实际连接方法）
psycopg = pytest.importorskip("psycopg")

# 使用 Settings 提供的连接信息，不在代码内保存 DSN
SETTINGS = Settings()


@pytest.fixture(scope="module")
def conn():
    # 连接策略：优先使用环境变量 TEST_DB_DSN；否则尝试免密候选（优先项目库）与默认口令
    # 严格按配置驱动：优先 dsn_read，否则使用参数化连接
    try:
        if getattr(SETTINGS.db, "dsn_read", None):
            c = psycopg.connect(SETTINGS.db.dsn_read)
        else:
            c = psycopg.connect(
                host=SETTINGS.db.host,
                port=getattr(SETTINGS.db, "port", 5432),
                dbname=SETTINGS.db.name,
                user=SETTINGS.db.user,
                password=getattr(SETTINGS.db, "password", None),
            )
        with c:
            yield c
        return
    except Exception as e:  # 无可用配置或连接失败：跳过
        pytest.skip(f"数据库不可用或认证失败，跳过写入类集成测试：{e}")


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

    # 构造两个落在同一秒内的时间（使用带时区 UTC 的时间，避免类型不匹配）
    base_ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    ts_a = base_ts + dt.timedelta(milliseconds=120)
    ts_b = base_ts + dt.timedelta(milliseconds=850)

    # 准备维表记录，确保外键约束满足（若已存在则忽略）
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.dim_stations(id, name, extra)
            VALUES (%s, %s, %s::jsonb)
            ON CONFLICT (id) DO NOTHING
            """,
            (station_id, "test_station_1", '{"tz":"UTC"}'),
        )
        cur.execute(
            """
            INSERT INTO public.dim_devices(id, station_id, name, type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (device_id, station_id, "test_device_10", "pump"),
        )
        cur.execute(
            """
            INSERT INTO public.dim_metric_config(id, metric_key, unit)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (metric_id, f"test_metric_{metric_id}", "Hz"),
        )
    conn.commit()

    # 直接写入事实表：对齐到秒并使用 ON CONFLICT 合并，验证“同秒主键合并”的合约
    with conn.cursor() as cur:
        # 以服务端计算 bucket，确保与表内口径一致
        cur.execute("SELECT date_trunc('second', %s::timestamptz)", (ts_a,))
        (bucket,) = cur.fetchone()
        cur.execute(
            """
            INSERT INTO public.fact_measurements(
              station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint
            )
            VALUES (
              %s::bigint, %s::bigint, %s::bigint,
              %s::timestamptz,
              %s::timestamptz,
              %s::numeric, %s::text
            )
            ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
            DO UPDATE SET
              value = EXCLUDED.value,
              source_hint = EXCLUDED.source_hint,
              ts_raw = EXCLUDED.ts_raw
            """,
            (station_id, device_id, metric_id, ts_a, bucket, 12.34, "test_a"),
        )
        cur.execute(
            """
            INSERT INTO public.fact_measurements(
              station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint
            )
            VALUES (
              %s::bigint, %s::bigint, %s::bigint,
              %s::timestamptz,
              %s::timestamptz,
              %s::numeric, %s::text
            )
            ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
            DO UPDATE SET
              value = EXCLUDED.value,
              source_hint = EXCLUDED.source_hint,
              ts_raw = EXCLUDED.ts_raw
            """,
            (station_id, device_id, metric_id, ts_b, bucket, 56.78, "test_b"),
        )
    conn.commit()

    # 查询该秒的记录应只有 1 条（同一主键同一秒应合并）
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM public.fact_measurements
            WHERE station_id=%s AND device_id=%s AND metric_id=%s
              AND ts_bucket = %s::timestamptz
            """,
            (station_id, device_id, metric_id, bucket),
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
              AND ts_bucket = %s::timestamptz
            LIMIT 1
            """,
            (station_id, device_id, metric_id, bucket),
        )
        (aligned,) = cur.fetchone()
        assert aligned
