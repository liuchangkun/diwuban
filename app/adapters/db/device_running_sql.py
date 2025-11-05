from __future__ import annotations

"""
设备运行状态 SQL 片段与DB操作封装（app.adapters.db.device_running_sql）

职责（最小可用）：
- 读取阈值快照与 grace_hold_secs
- 解析设备所属站点、默认设备集合（全部泵，排除总管，且已配置阈值）
- 计算设备全量时间窗（最早/最晚 ts_bucket）
- 基于数据库函数 fn_running_state_1s 生成逐秒状态，并批量 UPSERT 到 fact_measurements
- 写入前确保周分区存在

注意：
- 写入采用“仅值变化更新”以降低 WAL 与表膨胀：WHERE fact_measurements.value IS DISTINCT FROM EXCLUDED.value
- 所有时间均使用 timestamptz（UTC 秒对齐）
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import time
import logging

_act = logging.getLogger(__name__)


@dataclass(frozen=True)
class SliceStats:
    total_secs: int
    run_secs: int
    stop_secs: int
    hold_secs: int


def get_device_running_metric_id(cur) -> int:
    _act.info("[数据库-查询] [设备运行指标ID查询]")
    sql = "SELECT id FROM public.dim_metric_config WHERE metric_key='device_running'"

    cur.execute(sql)
    row = cur.fetchone()
    if not row:
        _act.error("[数据库-错误] [设备运行指标未找到]")
        raise RuntimeError("未找到 dim_metric_config.metric_key='device_running'")

    metric_id = int(row[0])
    _act.info(
        "[数据库-查询] [设备运行指标ID已获取]",
        extra={"extra_data": {"metric_id": metric_id}},
    )
    return metric_id


def get_station_id(cur, device_id: int) -> int:
    sql = "SELECT station_id FROM public.dim_devices WHERE id=%s"

    cur.execute(sql, (device_id,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"未找到设备 device_id={device_id}")
    return int(row[0])


def list_default_device_ids(cur) -> List[int]:
    """默认设备集合：全部泵类设备（排除 main_pipeline），且在阈值表存在配置。"""
    sql = """
        SELECT d.id
        FROM public.dim_devices d
        JOIN public.device_running_thresholds t ON t.device_id = d.id
        WHERE COALESCE(NULLIF(d.type,''),'') NOT IN ('main_pipeline','clear_water_pool','other')
          AND COALESCE(d.is_active, TRUE) = TRUE
        ORDER BY d.id
        """
    cur.execute(sql)
    return [int(r[0]) for r in cur.fetchall() or []]


def get_full_time_window(cur, device_id: int) -> Optional[Tuple[datetime, datetime]]:
    sql = "SELECT MIN(ts_bucket) AS mn, MAX(ts_bucket) AS mx FROM public.fact_measurements WHERE device_id=%s"
    cur.execute(sql, (device_id,))
    row = cur.fetchone()
    if not row or row[0] is None or row[1] is None:
        return None
    return row[0], row[1]


def get_thresholds_snapshot(cur, device_id: int) -> Dict[str, Any]:
    sql = "SELECT row_to_json(t) FROM public.device_running_thresholds t WHERE t.device_id=%s"
    cur.execute(sql, (device_id,))
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else {}


def get_grace_hold_secs(cur, device_id: int) -> int:
    sql = "SELECT COALESCE(grace_hold_secs,0) FROM public.device_running_thresholds WHERE device_id=%s"
    cur.execute(sql, (device_id,))
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def ensure_fact_weekly_partitions(conn, start_ts: datetime, end_ts: datetime) -> None:
    """调用网关内部工具，确保目标周分区存在（幂等）。

    若 fact_measurements 不是分区表，或不支持该操作，忽略即可。
    """
    try:
        from app.adapters.db.gateway import _ensure_fact_weekly_partitions
    except Exception:
        return
    try:
        _ensure_fact_weekly_partitions(conn, start_ts, end_ts)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        # 非分区表或其他环境不支持，直接忽略。
        return


def aggregate_slice_counts(
    cur, station_id: int, device_id: int, start_ts: datetime, end_ts: datetime
) -> SliceStats:
    """对单段窗口，统计逐秒判定的计数（总秒/运行/停机/hold）。"""
    sql = """
        SELECT COUNT(*)::bigint               AS total_secs,
               SUM(CASE WHEN s.is_running THEN 1 ELSE 0 END)::bigint AS run_secs,
               SUM(CASE WHEN NOT s.is_running THEN 1 ELSE 0 END)::bigint AS stop_secs,
               SUM(CASE WHEN s.source='hold' THEN 1 ELSE 0 END)::bigint AS hold_secs
        FROM public.fn_running_state_1s(%s,%s,%s,%s) AS s
        """
    params = (station_id, device_id, start_ts, end_ts)
    t0 = time.perf_counter()
    cur.execute(sql, params)
    total_ms = (time.perf_counter() - t0) * 1000
    row = cur.fetchone() or (0, 0, 0, 0)
    stats = SliceStats(
        int(row[0] or 0), int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)
    )
    return stats


def aggregate_counts_by_day(
    cur, station_id: int, device_id: int, start_ts: datetime, end_ts: datetime
) -> List[Dict[str, Any]]:
    """
    按日统计运行判定计数：返回 [{"date": "YYYY-MM-DD", "total_secs":..., "run_secs":..., "stop_secs":..., "hold_secs":...}, ...]
    用于 completion_audit.group_consistency 的按日聚合。
    """
    sql = """
        SELECT date_trunc('day', s.ts_bucket)::date AS d,
               COUNT(*)::bigint AS total_secs,
               SUM(CASE WHEN s.is_running THEN 1 ELSE 0 END)::bigint AS run_secs,
               SUM(CASE WHEN NOT s.is_running THEN 1 ELSE 0 END)::bigint AS stop_secs,
               SUM(CASE WHEN s.source='hold' THEN 1 ELSE 0 END)::bigint AS hold_secs
        FROM public.fn_running_state_1s(%s,%s,%s,%s) AS s
        GROUP BY 1
        ORDER BY 1
        """
    params = (station_id, device_id, start_ts, end_ts)
    t0 = time.perf_counter()
    cur.execute(sql, params)
    rows = cur.fetchall() or []
    total_ms = (time.perf_counter() - t0) * 1000
    return [
        {
            "date": str(r[0]),
            "total_secs": int(r[1] or 0),
            "run_secs": int(r[2] or 0),
            "stop_secs": int(r[3] or 0),
            "hold_secs": int(r[4] or 0),
        }
        for r in rows
    ]


def upsert_device_running_slice(
    conn,
    station_id: int,
    device_id: int,
    metric_id: int,
    start_ts: datetime,
    end_ts: datetime,
) -> int:
    """将一个时间段内的逐秒运行判定写入 fact_measurements。

    返回：数据库驱动的 rowcount（注意：包含 INSERT/UPDATE 影响行数，可能与总秒数不同）。
    """
    ensure_fact_weekly_partitions(conn, start_ts, end_ts)

    sql = """
        INSERT INTO public.fact_measurements(id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint)
        SELECT (
          CASE WHEN pg_get_serial_sequence('public.fact_measurements','id') IS NOT NULL THEN
            nextval(pg_get_serial_sequence('public.fact_measurements','id'))
          ELSE
            abs(('x' || substr(md5(
              %(station_id)s::text || '-' || %(device_id)s::text || '-' || %(metric_id)s::text || '-' || s.ts_bucket::text
            ), 1, 16))::bit(64)::bigint)
          END
        ), %(station_id)s, %(device_id)s, %(metric_id)s,
               s.ts_bucket, s.ts_bucket,
               CASE WHEN s.is_running THEN 1 ELSE 0 END,
               'derived:device_running'
        FROM public.fn_running_state_1s(%(station_id)s, %(device_id)s, %(start)s, %(end)s) AS s
        ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
        DO UPDATE SET value = EXCLUDED.value, source_hint = EXCLUDED.source_hint, ts_raw = EXCLUDED.ts_raw
        WHERE public.fact_measurements.value IS DISTINCT FROM EXCLUDED.value
        """
    params = {
        "station_id": station_id,
        "device_id": device_id,
        "metric_id": metric_id,
        "start": start_ts,
        "end": end_ts,
    }

    t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        affected = cur.rowcount if cur.rowcount is not None else 0
    total_ms = (time.perf_counter() - t0) * 1000
    return int(affected or 0)



def upsert_mv_running_phase_slice(
    conn,
    station_id: int,
    device_id: int,
    start_ts: datetime,
    end_ts: datetime,
) -> int:
    """
    将一个时间段内的逐秒运行/相位写入 mv_device_running_1s（1s基准）。
    返回：窗口内该设备的总秒数（近似作为影响行数）。
    说明：底层调用存储过程 sp_refresh_mv_running_phase，过程内负责幂等UPSERT。
    """
    # 调用过程
    with conn.cursor() as cur:
        cur.execute(
            "CALL public.sp_refresh_mv_running_phase(%s,%s,%s,%s)",
            (station_id, device_id, start_ts, end_ts),
        )
    # 简单统计窗口秒数作为影响数量参考
    secs = int(max(0, (end_ts - start_ts).total_seconds()))
    return secs
