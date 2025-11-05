from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

import time
import logging
import psycopg

from app.adapters.db.gateway import get_conn, make_dsn
from app.core.config.loader_new import load_settings
from app.core.time_utils import format_for_display


_act = logging.getLogger("activity")


# 统一对外时间格式：使用 app.core.time_utils.format_for_display
# 已删除重复的 _fmt_local 函数，直接使用统一的时间格式化函数


@dataclass
class PresenceWindow:
    start: datetime
    end: datetime
    station_name: Optional[str] = None


def _floor_day(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)


def _ceil_day(dt: datetime) -> datetime:
    base = _floor_day(dt)
    if dt == base:
        return dt
    return base + timedelta(days=1)


def iter_day_slices(
    start: datetime, end: datetime, days: int = 1
) -> Iterable[tuple[datetime, datetime]]:
    i = start
    while i < end:
        j = min(i + timedelta(days=days), end)
        yield i, j
        i = j


def iter_minute_slices(
    start: datetime, end: datetime, minutes: int = 1
) -> Iterable[tuple[datetime, datetime]]:
    i = start
    while i < end:
        j = min(i + timedelta(minutes=minutes), end)
        yield i, j
        i = j


def detect_full_or_incremental(conn: psycopg.Connection) -> tuple[datetime, datetime]:
    _act.info("[流程-开始] [检测全量或增量模式]")
    """返回 [start,end) UTC 窗口。
    - 若目标表为空：min(ts_bucket) ~ max(ts_bucket)
    - 否则：max(ts_second)+1s ~ max(ts_bucket)
    """
    # no-op logger removed
    with conn.cursor() as cur:
        cur.execute(
            "SELECT min(ts_bucket), max(ts_bucket), count(*) FROM public.fact_measurements"
        )
        row = cur.fetchone()
        if not row or not row[0] or not row[1]:
            raise RuntimeError("fact_measurements 无数据")
        fmin, fmax, fcnt = row
        cur.execute(
            "SELECT max(ts_second), count(*) FROM public.metrics_presence_per_second_device"
        )
        mrow = cur.fetchone() or (None, 0)
        mmax, mpres = mrow
        # no-op removed
        if mmax is None:
            s, e = fmin, fmax
        else:
            s, e = (mmax + timedelta(seconds=1)), fmax
        # 秒级对齐，统一半开区间 [start, end)
        s = s.replace(microsecond=0)
        e = e.replace(microsecond=0)
        return (s, e)


def ensure_partitions(conn: psycopg.Connection, ts: datetime) -> None:
    """确保指定时间戳对应的分区存在；若已存在则不重复创建。

    优先使用轻量存在性检查（to_regclass）判断对应周分区是否已存在；
    若不存在，再调用 public.ensure_mpps_partitions(ts) 创建按周 RANGE + 16 份 HASH 子分区。
    """
    # no-op logger removed
    try:
        with conn.cursor() as cur:
            # Hypertable 环境下无需分区，直接 no-op
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema='public' AND hypertable_name='metrics_presence_per_second_device')"
            )
            is_ht = bool(cur.fetchone()[0])
            if is_ht:
                return
            # 计算与数据库函数一致的周分区父表名，如 public.mpps_w_202536
            cur.execute(
                "SELECT 'public.mpps_w_' || to_char(date_trunc('week', %s AT TIME ZONE 'UTC'), 'IYYYIW')",
                (ts,),
            )
            parent: str = cur.fetchone()[0]

            # 轻量检查：若父分区已存在则跳过创建
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", (parent,))
            exists = bool(cur.fetchone()[0])
            if exists:
                return

            # 后备：确保分区管理函数存在再调用
            cur.execute(
                "SELECT to_regprocedure('public.ensure_mpps_partitions(timestamptz)') IS NOT NULL"
            )
            fn_exists = bool(cur.fetchone()[0])
            if not fn_exists:
                return

            # 创建所需分区
            cur.execute("SELECT public.ensure_mpps_partitions(%s)", (ts,))
    except Exception:
        pass


def list_station_devices(conn: psycopg.Connection, station_name: str) -> list[str]:
    """获取站点下的设备名称列表（不依赖 active 字段，保持兼容）。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.name
            FROM public.dim_devices d
            JOIN public.dim_stations s ON s.id = d.station_id
            WHERE s.name = %s
            ORDER BY d.name
            """,
            (station_name,),
        )
        rows = cur.fetchall() or []
        return [r[0] for r in rows]


def _upsert_device_slice(
    settings,
    start: datetime,
    end: datetime,
    station_id: int,
    device_id: int,
) -> int:
    """单设备单片窗口写入（独立连接，使用 ID 过滤）。

    返回影响行数；异常由调用方捕获并记录。
    """
    # 修复2：子线程绕过连接池，独立直连，避免连接池统计并发错乱
    dsn = make_dsn(settings)
    # 使用 psycopg3 连接上下文：成功退出自动 commit，异常自动 rollback
    with psycopg.connect(
        dsn,
        connect_timeout=int(settings.db.timeouts.connect_timeout_seconds()),
    ) as conn:
        # 统一设置语句超时（与 gateway 保持一致）
        try:
            with conn.cursor() as cur:
                cur.execute(settings.db.timeouts.statement_timeout_sql())
        except Exception:
            pass
        return upsert_window(conn, start, end, station_id, device_id)


def upsert_window(
    conn: psycopg.Connection,
    start: datetime,
    end: datetime,
    station_id: Optional[int],
    device_id: Optional[int] = None,
) -> int:
    """执行一个窗口 UPSERT，返回影响行数。"""
    # 写入前确保分区存在（使用窗口起点即可触发当周分区创建）
    ensure_partitions(conn, start)
    # 小窗口下优先按设备切片调用 per_device SQL 以显著缩小扫描范围
    params: tuple[object, ...]
    # 统一使用从 CAgg 同步的 SQL，实现“仅变更更新”。
    sql_path = Path("scripts/sql/sync_presence_from_cagg.sql")
    sql = sql_path.read_text(encoding="utf-8")
    params = (start, end, station_id, device_id)

    with conn.cursor() as cur:
        # 设置有限语句/锁等待超时，避免长时间阻塞；LOCAL 仅本事务生效
        cur.execute("SET LOCAL statement_timeout = '60s'")
        cur.execute("SET LOCAL lock_timeout = '5s'")
        # 提升聚合与数组操作内存，减少磁盘临时文件
        cur.execute("SET LOCAL work_mem = '128MB'")
        cur.execute(sql, params)
        affected = cur.rowcount if cur.rowcount is not None else 0
    return affected


def run_presence_compute(
    station_name: Optional[str] = None,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    batch_days: int = 1,
    rolling_days: int = 7,
    minutes_per_batch: int = 5,
    device_concurrency: int = 2,
) -> dict:
    """对 presence 表进行批量 UPSERT（自适应切片 + 受控并发）。

    - 统一窗口语义：[start, end) 半开区间
    - 动态自适应切片：以目标片耗时为反馈，自动调整下一片时长
    - 设备级受控并发：当指定 station_name 时，按设备并发执行 per-device SQL
    """
    settings = load_settings(Path("configs"))
    t0_perf = time.perf_counter()
    try:
        _act.info(
            "进入 presence 计算阶段",
            extra={
                "extra_data": {
                    "阶段": "presence",
                    "站点": station_name,
                    "站点ID": station_id,
                    "设备ID": device_id,
                    "开始": (format_for_display(start, settings) if start else None),
                    "结束": (format_for_display(end, settings) if end else None),
                    "批天数": batch_days,
                    "滚动天数": rolling_days,
                    "每批分钟": minutes_per_batch,
                    "设备并发": device_concurrency,
                }
            },
        )
    except Exception:
        pass

    # no-op logger removed
    summary: dict = {
        "station_name": station_name,
        "batch_days": batch_days,
        "rolling_days": rolling_days,
        "slices": [],
        "affected_total": 0,
    }
    with get_conn(settings) as conn:
        # 计算窗口
        if start is None or end is None:
            s, e = detect_full_or_incremental(conn)
        else:
            s, e = start, end
        # 秒级对齐与边界保护
        s = s.replace(microsecond=0)
        e = e.replace(microsecond=0)
        if s >= e:
            summary.update(
                {
                    "status": "ok",
                    "message": "already up-to-date",
                    "affected_total": 0,
                }
            )
            return summary

        # 关键上下文：设备数
        with conn.cursor() as cur:
            dev_scope = None
            # 统一从 ID 推导设备范围统计
            if device_id:
                cur.execute("SELECT 1")
                dev_scope = 1
            elif station_id:
                cur.execute(
                    "SELECT count(*) FROM public.dim_devices WHERE station_id=%s AND COALESCE(is_active, TRUE)=TRUE AND COALESCE(NULLIF(type,''),'') NOT IN ('clear_water_pool','other')",
                    (station_id,),
                )
                dev_scope = int(cur.fetchone()[0])
            elif station_name:
                cur.execute(
                    "SELECT count(*) FROM public.dim_devices d JOIN public.dim_stations s ON s.id=d.station_id WHERE s.name=%s AND COALESCE(d.is_active, TRUE)=TRUE AND COALESCE(NULLIF(d.type,''),'') NOT IN ('clear_water_pool','other')",
                    (station_name,),
                )
                dev_scope = int(cur.fetchone()[0])

        # 按设备循环范围（当指定站点时启用）
        devices: list[tuple[int, int]] = []
        # 优先按显式 ID 做设备范围
        with conn.cursor() as cur:
            if device_id:
                if not station_id:
                    cur.execute(
                        "SELECT station_id FROM public.dim_devices WHERE id=%s",
                        (device_id,),
                    )
                    row = cur.fetchone()
                    station_id = int(row[0]) if row else None
                devices = [(int(station_id), int(device_id))] if station_id else []
            elif station_id:
                cur.execute(
                    "SELECT %s, id FROM public.dim_devices WHERE station_id=%s AND COALESCE(is_active, TRUE)=TRUE AND COALESCE(NULLIF(type,''),'') NOT IN ('clear_water_pool','other') ORDER BY id",
                    (station_id, station_id),
                )
                devices = [(int(r[0]), int(r[1])) for r in (cur.fetchall() or [])]
            elif station_name:
                # 兼容旧接口：由名称解析为 ID 范围
                cur.execute(
                    """
                    SELECT s.id AS station_id, d.id AS device_id
                    FROM public.dim_devices d
                    JOIN public.dim_stations s ON s.id=d.station_id
                    WHERE s.name=%s
                      AND COALESCE(d.is_active, TRUE)=TRUE
                      AND COALESCE(NULLIF(d.type,''),'') NOT IN ('clear_water_pool','other')
                    ORDER BY d.id
                    """,
                    (station_name,),
                )
                devices = [(int(r[0]), int(r[1])) for r in (cur.fetchall() or [])]

    # 取消固定切片器，采用自适应切片
    total = 0
    i = s
    # 初始步长：最多 60s，避免第一片过大；尊重传入 minutes_per_batch 的更小值
    step_secs = min(60, max(1, int(minutes_per_batch) * 60))
    # 自适应目标与边界
    TARGET = 20  # 目标片耗时（秒）
    MIN_STEP = 15
    MAX_STEP = max(60, int(minutes_per_batch) * 60)  # 不超过传入期望的上限

    while i < e:
        j = min(i + timedelta(seconds=step_secs), e)
        t0_dt = datetime.now(timezone.utc)
        slice_total = 0

        if devices:
            # 设备级并发（独立连接），受控并发上限
            max_workers = max(1, int(device_concurrency))
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                fut_map = {ex.submit(_upsert_device_slice, settings, i, j, sid, did): (sid, did) for (sid, did) in devices}
                for fut in as_completed(fut_map):
                    dev = fut_map[fut]
                    try:
                        affected = fut.result()
                    except Exception:
                        affected = 0
                    summary["slices"].append(
                        {
                            "start": format_for_display(i, settings),
                            "end": format_for_display(j, settings),
                            "station_id": dev[0],
                            "device_id": dev[1],
                            "affected": affected,
                        }
                    )
                    try:
                        _act.info(
                            "presence 切片(按设备)",
                            extra={
                                "extra_data": {
                                    "阶段": "presence",
                                    "切片开始": format_for_display(i, settings),
                                    "切片结束": format_for_display(j, settings),
                                    "站点ID": dev[0],
                                    "设备ID": dev[1],
                                    "受影响行数": affected,
                                }
                            },
                        )
                    except Exception:
                        pass

                    slice_total += affected
        else:
            # 全站或全量：保持单条 SQL 避免跨站设备名冲突
            with get_conn(settings) as _conn0:
                # 全站或全量：station_id 为 NULL；device_id 为 NULL
                affected = upsert_window(_conn0, i, j, None, None)
                # 显式提交：get_conn 不负责提交事务
                try:
                    _conn0.commit()
                except Exception:
                    pass
                try:
                    _act.info(
                        "presence 切片(全站/全量)",
                        extra={
                            "extra_data": {
                                "阶段": "presence",
                                "切片开始": format_for_display(i, settings),
                                "切片结束": format_for_display(j, settings),
                                "受影响行数": affected,
                            }
                        },
                    )
                except Exception:
                    pass

                # 显式提交：get_conn 不负责提交事务
                try:
                    _conn0.commit()
                except Exception:
                    pass
            summary["slices"].append(
                {"start": format_for_display(i, settings), "end": format_for_display(j, settings), "affected": affected}
            )
            slice_total += affected
        t1 = datetime.now(timezone.utc)
        dur = (t1 - t0_dt).total_seconds()
        # 自适应调整下一片步长
        old_step = step_secs
        if dur > TARGET and step_secs > MIN_STEP:
            step_secs = max(MIN_STEP, int(step_secs / 2))
        elif dur < TARGET / 2 and step_secs < MAX_STEP:
            step_secs = min(MAX_STEP, int(step_secs * 2))

        total += slice_total
        i = j

    summary["affected_total"] = total
    dur_ms = int((time.perf_counter() - t0_perf) * 1000)
    try:
        _act.info("完成 presence 计算阶段", extra={"extra_data": {"阶段": "presence", "切片数": len(summary.get("slices", [])), "总影响行数": summary.get("affected_total", 0), "耗时ms": dur_ms}})
    except Exception:
        pass
    return summary
