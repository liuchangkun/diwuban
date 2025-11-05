from __future__ import annotations

"""
设备运行状态批处理作业（app.services.device_running_job）

职责（最小可用）：
- 设备集合解析（默认=全部泵类设备，排除 main_pipeline，且阈值已配置）
- 时间窗解析（未传参=全量时间），按“周/日”切片，跨段以 grace_hold_secs 秒 overlap 承接前态
- 借助数据库函数 fn_running_state_1s 逐秒判定；单条 INSERT…SELECT 批量 UPSERT 到 fact_measurements（device_running=0/1）
- 追踪层写入 completion_runs/steps（记录 thresholds_snapshot 与段级统计），避免逐秒审计爆量
- 性能：仅值变化更新（IS DISTINCT FROM）、段级提交、小并发（编排层控制）

注意：
- 全部时间均为 timestamptz（UTC）；fn_running_state_1s 为闭区间 [start, end]
- 事实层仅落 0/1；最小段长等防抖在只读层处理
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Any
import time
import logging

_act = logging.getLogger("activity")


from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings, load_settings
from app.core.time_utils import format_for_display
from app.adapters.db.device_running_sql import (
    get_station_id,
    list_default_device_ids,
    get_full_time_window,
    get_thresholds_snapshot,
    get_grace_hold_secs,
    aggregate_slice_counts,
    aggregate_counts_by_day,
    upsert_mv_running_phase_slice,
)


@dataclass(frozen=True)
class JobConfig:
    """
    作业配置（可由外部配置覆盖）。
    - slice_granularity: 切片粒度 'week' | 'day'
    - max_device_concurrency: 设备并发（编排层使用，本实现串行）
    - update_only_when_changed: 仅值变化更新（由 SQL 负责，默认 True）
    - force_recompute: 强制重算（预留，当前不启用跳过策略）
    - audit_granularity: 审计聚合粒度 'day' | 'week'（本实现写 steps 的 residual_stats）
    """

    slice_granularity: str = "week"
    max_device_concurrency: int = 2
    update_only_when_changed: bool = True
    force_recompute: bool = False
    audit_granularity: str = "day"


class DeviceRunningJob:
    """设备运行状态计算与落库作业。"""

    def __init__(self, settings: Settings, config: Optional[JobConfig] = None) -> None:
        self.settings = settings
        self.config = config or JobConfig()

    # --------------------------- 内部：时间切片 ---------------------------
    def _week_floor(self, ts: datetime) -> datetime:
        ts_utc = ts.astimezone(timezone.utc)
        dow = ts_utc.weekday()  # 0=Mon
        floored = datetime(
            ts_utc.year, ts_utc.month, ts_utc.day, tzinfo=timezone.utc
        ) - timedelta(days=dow)
        return floored.replace(hour=0, minute=0, second=0, microsecond=0)

    def _week_ceil(self, ts: datetime) -> datetime:
        start = self._week_floor(ts)
        return start + timedelta(days=7)

    def _iter_slices(
        self, start: datetime, end: datetime
    ) -> Iterable[Tuple[datetime, datetime]]:
        if self.config.slice_granularity == "day":
            cur = start
            while cur < end:
                nxt = min(cur + timedelta(days=1), end)
                yield cur, nxt
                cur = nxt
        else:  # week
            cur = max(self._week_floor(start), start)
            while cur < end:
                nxt = min(self._week_ceil(cur), end)
                yield cur, nxt
                cur = nxt

    # --------------------------- 设备/窗口解析 ---------------------------
    def resolve_devices(self) -> List[int]:
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                return list_default_device_ids(cur)

    def resolve_window(
        self, device_id: int, start_ts: Optional[datetime], end_ts: Optional[datetime]
    ) -> Optional[Tuple[datetime, datetime]]:
        if start_ts and end_ts:
            return start_ts, end_ts
        with get_conn(self.settings) as conn:

            with conn.cursor() as cur:
                return get_full_time_window(cur, device_id)


    # --------------------------- 主流程：单设备 ---------------------------
    def run_for_device(
        self, device_id: int, start_ts: Optional[datetime], end_ts: Optional[datetime]
    ) -> None:
        t_job0 = time.perf_counter()
        _act.info(
            "[流程-开始] [设备运行状态计算]",
            extra={
                "extra_data": {
                    "device_id": device_id,
                    "start_ts": format_for_display(start_ts, self.settings) if start_ts else None,
                    "end_ts": format_for_display(end_ts, self.settings) if end_ts else None,
                }
            },
        )

        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:

                station_id = get_station_id(cur, device_id)
                win = self.resolve_window(device_id, start_ts, end_ts)
                # 清理异常的调试代码（此前存在错误的 try/except 段）
                # 解析窗口与阈值
                if not win:
                    return
                overall_start, overall_end = win
                thr_snapshot = get_thresholds_snapshot(cur, device_id)
                grace = get_grace_hold_secs(cur, device_id)
                _act.info(
                    "[流程-阶段] [时间窗口解析]",
                    extra={
                        "extra_data": {
                            "device_id": device_id,
                            "window_start": format_for_display(overall_start, self.settings),
                            "window_end": format_for_display(overall_end, self.settings),
                            "grace_hold_secs": grace,
                        }
                    },
                )

                if not win:
                    return
                overall_start, overall_end = win
                thr_snapshot = get_thresholds_snapshot(cur, device_id)
                grace = get_grace_hold_secs(cur, device_id)

        # 运行级：completion_runs（先建壳，最终回填统计）
        run_id: Optional[int] = None
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO public.completion_runs(
                      station_id, device_id, start_ts, end_ts,
                      code_version, imputation_version,
                      config_snapshot, thresholds_snapshot,
                      rows_read, duration_ms, steps_total,
                      rerun_policy, idempotency_key, status_reason
                    ) VALUES (
                      %s, %s, %s, %s,
                      %s, %s,
                      %s::jsonb, %s::jsonb,
                      %s, %s, %s,
                      %s, %s, %s
                    ) RETURNING run_id
                    """
                cfg_snap = {
                    "slice_granularity": self.config.slice_granularity,
                    "update_only_when_changed": self.config.update_only_when_changed,
                    "force_recompute": self.config.force_recompute,
                    "audit_granularity": self.config.audit_granularity,
                }
                params = (
                    station_id,
                    device_id,
                    overall_start,
                    overall_end,
                    "device_running:v1",
                    "running:v1",
                    cfg_snap,
                    thr_snapshot,
                    0,
                    0,
                    0,
                    "append",
                    f"run_device_{device_id}_{int(time.time())}",
                    "ok",
                )
                t0 = time.perf_counter()
                cur.execute(
                    sql,
                    (
                        params[0],
                        params[1],
                        params[2],
                        params[3],
                        params[4],
                        params[5],
                        json_dumps(params[6]),
                        json_dumps(params[7]),
                        params[8],
                        params[9],
                        params[10],
                        params[11],
                        params[12],
                        params[13],
                    ),
                )
                run_id = int(cur.fetchone()[0])
                conn.commit()

        # 步骤级：切片统计 + UPSERT 事实
        steps_total = 0
        total_rows_read = 0
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:

                station_id = get_station_id(cur, device_id)
                for s, e in self._iter_slices(overall_start, overall_end):
                    # overlap：以 grace_hold_secs 秒向前扩，避免边界误判
                    s_overlap = max(overall_start, s - timedelta(seconds=max(0, grace)))
                    # 1) 统计
                    stats = aggregate_slice_counts(
                        cur, station_id, device_id, s_overlap, e
                    )
                    # 2) UPSERT 事实层
                    affected = upsert_mv_running_phase_slice(
                        conn, station_id, device_id, s_overlap, e
                    )
                    conn.commit()
                    # 3) 写 steps（段级审计）
                    steps_total += 1
                    total_rows_read += stats.total_secs
                    insert_step_sql = """
                        INSERT INTO public.completion_steps(
                          run_id, device_id, metric_id,
                          gap_start_ts, gap_end_ts, gap_len_sec,
                          residual_stats, step_duration_ms, rows_considered
                        ) VALUES (
                          %s, %s, %s,
                          %s, %s, %s,
                          %s::jsonb, %s, %s
                        )
                        """

                    residual = {
                        "slice_start": s.isoformat(),
                        "slice_end": e.isoformat(),
                        "overlap_start": s_overlap.isoformat(),
                        "stats": {
                            "total_secs": stats.total_secs,
                            "run_secs": stats.run_secs,
                            "stop_secs": stats.stop_secs,
                            "hold_secs": stats.hold_secs,
                        },
                        "affected_rows": affected,
                    }
                    t1 = time.perf_counter()
                    cur.execute(
                        insert_step_sql,
                        (
                            run_id,
                            device_id,
                            None,
                            s,
                            e,
                            int((e - s).total_seconds()),
                            json_dumps(residual),
                            int((time.perf_counter() - t1) * 1000),
                            stats.total_secs,
                        ),
                    )
                    conn.commit()
        # 审计级：按日聚合写入 completion_audit（每个 run 一条，按日统计置于 group_consistency）
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                station_id = get_station_id(cur, device_id)
                per_day = aggregate_counts_by_day(
                    cur, station_id, device_id, overall_start, overall_end
                )
                audit_json = {"per_day": per_day}
                ins_audit_sql = """
                    INSERT INTO public.completion_audit(
                      run_id, group_consistency, thresholds_snapshot_ref
                    ) VALUES (
                      %s, %s::jsonb, %s
                    )
                    ON CONFLICT (run_id)
                    DO UPDATE SET group_consistency = EXCLUDED.group_consistency,
                                  thresholds_snapshot_ref = EXCLUDED.thresholds_snapshot_ref,
                                  audit_time = now()
                    """
                cur.execute(
                    ins_audit_sql, (run_id, json_dumps(audit_json), "device_running:v1")
                )
                conn.commit()

        # 回填 runs 汇总
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                upd_sql = "UPDATE public.completion_runs SET rows_read=%s, duration_ms=%s, steps_total=%s WHERE run_id=%s"
                run_cost_ms = int((time.perf_counter() - t_job0) * 1000)
                cur.execute(
                    upd_sql, (total_rows_read, run_cost_ms, steps_total, run_id)
                )
                conn.commit()
        _act.info(
            "[流程-完成] [设备运行状态计算]",
            extra={
                "extra_data": {
                    "device_id": device_id,
                    "steps_total": steps_total,
                    "rows_read": total_rows_read,
                    "duration_ms": run_cost_ms,
                }
            },
        )


    # --------------------------- 批处理入口 ---------------------------
    def run(
        self,
        device_ids: Optional[List[int]] = None,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
    ) -> None:
        if device_ids is None:
            device_ids = self.resolve_devices()
        t_batch0 = time.perf_counter()
        _act.info(
            "[流程-开始] [批量设备运行状态计算]",
            extra={
                "extra_data": {
                    "device_count": len(device_ids) if device_ids else 0,
                    "start_ts": format_for_display(start_ts, self.settings) if start_ts else None,
                    "end_ts": format_for_display(end_ts, self.settings) if end_ts else None,
                }
            },
        )

        pass
        if not device_ids:
            return
        conc = max(1, int(self.config.max_device_concurrency))
        if conc == 1 or len(device_ids) == 1:
            for did in device_ids:
                try:
                    self.run_for_device(did, start_ts, end_ts)
                except Exception:
                    pass
            _act.info(
                "[流程-完成] [批量设备运行状态计算]",
                extra={
                    "extra_data": {
                        "device_count": len(device_ids) if device_ids else 0,
                        "duration_ms": int((time.perf_counter() - t_batch0) * 1000),
                    }
                },
            )

            return
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=conc, thread_name_prefix="devrun") as ex:
            futs = {

                ex.submit(self.run_for_device, did, start_ts, end_ts): did
                for did in device_ids
            }
            for fut in as_completed(futs):

                did = futs[fut]
                try:
                    fut.result()
                except Exception:
                    pass
        _act.info(
            "[流程-完成] [批量设备运行状态计算]",
            extra={
                "extra_data": {
                    "device_count": len(device_ids) if device_ids else 0,
                    "duration_ms": int((time.perf_counter() - t_batch0) * 1000),
                }
            },
        )



# --------------------------- CLI 入口（可独立运行） ---------------------------



def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main(argv: Optional[List[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="按周/日切片批量计算并落地 device_running（0/1）"
    )
    parser.add_argument(
        "--device-ids",
        type=str,
        default="",
        help="逗号分隔设备ID；缺省=全部泵类且已配置阈值的设备",
    )
    parser.add_argument("--start", type=str, default="", help="开始时间 ISO；缺省=全量")
    parser.add_argument("--end", type=str, default="", help="结束时间 ISO；缺省=全量")
    parser.add_argument(
        "--slice", type=str, choices=["week", "day"], default="week", help="切片粒度"
    )

    args = parser.parse_args(argv)
    settings = load_settings(Path("configs"))
    job = DeviceRunningJob(settings, JobConfig(slice_granularity=args.slice))

    device_ids: Optional[List[int]]
    if args.device_ids.strip():
        device_ids = [int(x) for x in args.device_ids.split(",") if x.strip()]
    else:
        device_ids = None

    def parse_ts(v: str) -> Optional[datetime]:
        v = (v or "").strip()
        if not v:
            return None
        return datetime.fromisoformat(v)

    start_ts = parse_ts(args.start)
    end_ts = parse_ts(args.end)

    job.run(device_ids=device_ids, start_ts=start_ts, end_ts=end_ts)


if __name__ == "__main__":
    main()
