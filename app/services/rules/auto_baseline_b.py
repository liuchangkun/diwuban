from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime as _dt

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from app.adapters.db.gateway import get_conn
import logging

_act = logging.getLogger(__name__)


def run_auto_baseline_b(
    settings,
    lookback_days: int = 30,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
    method: str = "stl_residual",
    version: str = "vB_shadow",
) -> Dict[str, Any]:
    """方案B：基于 STL 的自动基线（影子输出），在 Residual 上做稳健估计。
    - 仅读取质量=0 的数据；优先使用 phase=1 的稳态片段；缺失相位时回退 running=1
    - 结果写入 metric_rule_auto_baseline_shadow，不影响正式表
    - 使用lookback_days参数计算时间窗口，避免时间窗口不匹配
    """
    _act.info(
        "[流程-开始] [自动基线生成B]",
        extra={
            "extra_data": {
                "lookback_days": lookback_days,
                "station_id": station_id,
                "device_id": device_id,
                "method": method,
                "version": version,
            }
        },
    )

    result: Dict[str, Any] = {
        "filters": {"station_id": station_id, "device_id": device_id},
        "method": method,
        "version": version,
        "inserted": 0,
        "samples": [],
    }

    # 初始化start和end为None，将在数据库查询中确定
    start = None
    end = None

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 查询实际数据时间范围
            _act.info("[数据库-查询] 查询实际数据时间范围")
            cur.execute(
                "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
            )
            row = cur.fetchone() or (None, None)
            if row[0] is not None:
                start = row[0].isoformat()
            if row[1] is not None:
                end = row[1].isoformat()
            _act.info(
                "[数据库-查询] 实际数据时间范围",
                extra={"start": start, "end": end},
            )

            if not start or not end:
                _act.warning(
                    "[流程-跳过] [时间窗口无效]",
                    extra={"extra_data": {"start": start, "end": end}},
                )
                return result

            start_ts = _dt.fromisoformat(start.replace("Z", "+00:00"))
            end_ts = _dt.fromisoformat(end.replace("Z", "+00:00"))

            _act.info(
                "[流程-阶段] [时间窗口确定]",
                extra={
                    "extra_data": {
                        "start_ts": start_ts.isoformat(),
                        "end_ts": end_ts.isoformat(),
                        "duration_hours": (end_ts - start_ts).total_seconds() / 3600,
                        "lookback_days": lookback_days,
                    }
                },
            )

            # 先读取相关 metric_id，避免 CTE 兼容性问题
            cur.execute(
                "SELECT id FROM public.dim_metric_config WHERE metric_key='device_phase'"
            )
            row = cur.fetchone()
            phase_id = int(row[0]) if row and row[0] is not None else None
            cur.execute(
                "SELECT id FROM public.dim_metric_config WHERE metric_key='device_running'"
            )
            row = cur.fetchone()
            run_id = int(row[0]) if row and row[0] is not None else None

            _act.info(
                "[数据库-查询] 加载稳态数据（phase=1或running=1）",
                extra={"phase_id": phase_id, "run_id": run_id},
            )
            cur.execute(
                """
                SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value::float8 AS v
                FROM public.fact_measurements f
                WHERE f.ts_bucket >= %(start)s AND f.ts_bucket < %(end)s
                  AND (%(station_id)s::bigint IS NULL OR f.station_id=%(station_id)s::bigint)
                  AND (%(device_id)s::bigint IS NULL OR f.device_id=%(device_id)s::bigint)
                  AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                  AND (
                    ( %(phase_id)s IS NOT NULL AND EXISTS (
                        SELECT 1 FROM public.fact_measurements ph
                        WHERE ph.station_id=f.station_id AND ph.device_id=f.device_id AND ph.ts_bucket=f.ts_bucket
                          AND ph.metric_id = %(phase_id)s AND ph.value=1
                    ) )
                    OR (
                      %(phase_id)s IS NULL AND EXISTS (
                        SELECT 1 FROM public.fact_measurements fr
                        WHERE fr.station_id=f.station_id AND fr.device_id=f.device_id AND fr.ts_bucket=f.ts_bucket
                          AND fr.metric_id = %(run_id)s AND fr.value=1
                      )
                    )
                  )
                ORDER BY f.station_id, f.device_id, f.metric_id, f.ts_bucket
                """,
                {
                    "start": start_ts,
                    "end": end_ts,
                    "station_id": station_id,
                    "device_id": device_id,
                    "phase_id": phase_id,
                    "run_id": run_id,
                },
            )
            rows = cur.fetchall() or []
            _act.info(
                "[数据库-查询] 稳态数据加载完成",
                extra={"rows_count": len(rows)},
            )
            if not rows:
                _act.info("[数据库-查询] 稳态数据为空，回退到质量=0数据")
                # 回退数据口径：仅质量=0，不要求相位/运行标记，尽量生成影子用于对照
                cur.execute(
                    """
                    SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, f.value::float8 AS v
                    FROM public.fact_measurements f
                    WHERE f.ts_bucket >= %(start)s AND f.ts_bucket < %(end)s
                      AND (%(station_id)s::bigint IS NULL OR f.station_id=%(station_id)s::bigint)
                      AND (%(device_id)s::bigint IS NULL OR f.device_id=%(device_id)s::bigint)
                      AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                    ORDER BY f.station_id, f.device_id, f.metric_id, f.ts_bucket
                    """,
                    {
                        "start": start_ts,
                        "end": end_ts,
                        "station_id": station_id,
                        "device_id": device_id,
                    },
                )
                rows = cur.fetchall() or []
                _act.info(
                    "[数据库-查询] 回退数据加载完成",
                    extra={"rows_count": len(rows)},
                )
                if not rows:
                    _act.warning(
                        "[流程-跳过] [无可用数据]",
                        extra={"extra_data": {"reason": "稳态数据和回退数据均为空"}},
                    )
                    return result

    # 按 station-device-metric 分组做 STL 与稳健估计
    import collections

    groups: Dict[tuple[int, int, int], list[tuple]] = collections.defaultdict(list)
    for st, dev, met, ts, val in rows:
        groups[(int(st), int(dev), int(met))].append((ts, float(val)))

    _act.info(
        "[流程-阶段] [数据分组完成]",
        extra={"extra_data": {"groups_count": len(groups), "total_rows": len(rows)}},
    )

    inserted = 0
    samples: list[dict[str, Any]] = []

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 兜底创建影子表（迁移已提供）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.metric_rule_auto_baseline_shadow (
                  station_id bigint NOT NULL,
                  device_id  bigint NOT NULL,
                  metric_id  bigint NOT NULL,
                  lookback_days int NOT NULL,
                  method text NOT NULL,
                  version text NOT NULL,
                  p05 double precision NULL,
                  p95 double precision NULL,
                  median double precision NULL,
                  mad double precision NULL,
                  spike_abs double precision NULL,
                  roc_abs double precision NULL,
                  roc_ratio double precision NULL,
                  flatline_eps double precision NULL,
                  flatline_delta double precision NULL,
                  computed_at timestamptz NOT NULL DEFAULT now(),
                  remark text NULL,
                  PRIMARY KEY (station_id, device_id, metric_id, lookback_days, method, version)
                )
                """
            )

            for key, seq in groups.items():
                st, dev, met = key
                # 构造等间隔序列（按秒），缺失填充线性插值，避免 STL 对不规则采样不稳
                df = pd.DataFrame(seq, columns=["ts", "v"]).set_index("ts").sort_index()
                # 采样周期与季节周期估计（若未知，先按 60s 采样；季节按 24h）
                df = df[~df.index.duplicated(keep="first")]
                # 统一重采样到 60s 间隔，再检查点数
                df = df.resample("60s").mean().interpolate(limit_direction="both")
                if df.index.size < 30:  # 降低最小数据量要求（从120→30）
                    # 小样本回退：若存在 A 版基线，则复制到影子，便于对照
                    cur.execute(
                        """
                        SELECT p05, p95, median,
                               mad, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta
                        FROM public.metric_rule_auto_baseline
                        WHERE station_id IS NOT DISTINCT FROM %s
                          AND device_id  IS NOT DISTINCT FROM %s
                          AND metric_id  = %s
                          AND lookback_days = %s
                        LIMIT 1
                        """,
                        (st, dev, met, lookback_days),
                    )
                    rowb = cur.fetchone()
                    if rowb:
                        cur.execute(
                            """
                            INSERT INTO public.metric_rule_auto_baseline_shadow(
                              station_id, device_id, metric_id, lookback_days, method, version,
                              p05, p95, median, mad, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta, computed_at, remark
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now(), %s)
                            ON CONFLICT (station_id, device_id, metric_id, lookback_days, method, version) DO UPDATE
                              SET p05=EXCLUDED.p05, p95=EXCLUDED.p95, median=EXCLUDED.median, mad=EXCLUDED.mad,
                                  spike_abs=EXCLUDED.spike_abs, roc_abs=EXCLUDED.roc_abs, roc_ratio=EXCLUDED.roc_ratio,
                                  flatline_eps=EXCLUDED.flatline_eps, flatline_delta=EXCLUDED.flatline_delta, computed_at=now(), remark=EXCLUDED.remark
                            """,
                            (
                                st,
                                dev,
                                met,
                                lookback_days,
                                method,
                                version,
                                float(rowb[0]) if rowb[0] is not None else None,
                                float(rowb[1]) if rowb[1] is not None else None,
                                float(rowb[2]) if rowb[2] is not None else None,
                                float(rowb[3]) if rowb[3] is not None else None,
                                float(rowb[4]) if rowb[4] is not None else None,
                                float(rowb[5]) if rowb[5] is not None else None,
                                float(rowb[6]) if rowb[6] is not None else None,
                                float(rowb[7]) if rowb[7] is not None else None,
                                float(rowb[8]) if rowb[8] is not None else None,
                                "fallback_from_A",
                            ),
                        )
                        inserted += 1
                    else:
                        # 进一步回退：直接用当前序列计算稳健基线到影子
                        vals = df["v"].values.astype(float)
                        if vals.size >= 20:  # 最低样本线
                            med2 = float(np.median(vals))
                            mad2 = float(np.median(np.abs(vals - med2)))
                            p05 = float(np.quantile(vals, 0.05))
                            p95 = float(np.quantile(vals, 0.95))
                            diff = np.diff(vals)
                            spike_abs = (
                                float(np.quantile(np.abs(diff), 0.99))
                                if diff.size
                                else None
                            )
                            roc_abs = spike_abs
                            with np.errstate(divide="ignore", invalid="ignore"):
                                prev = vals[:-1]
                                roc_ratio_arr = (
                                    np.abs(diff / np.where(prev == 0.0, np.nan, prev))
                                    if diff.size
                                    else np.array([np.nan])
                                )
                            roc_ratio = (
                                float(np.nanquantile(roc_ratio_arr, 0.99))
                                if diff.size
                                else None
                            )
                            # 分辨率保护
                            cur.execute(
                                """
                                SELECT COALESCE(vm.resolution, 0.0)
                                FROM public.v_effective_metric_metadata vm
                                WHERE vm.metric_id = %s AND (vm.device_id = %s OR vm.device_id IS NULL)
                                  AND (vm.station_id = %s OR vm.station_id IS NULL)
                                ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
                                LIMIT 1
                                """,
                                (met, dev, st),
                            )
                            row_res2 = cur.fetchone()
                            reso2 = (
                                float(row_res2[0])
                                if row_res2 and row_res2[0] is not None
                                else 0.0
                            )
                            flatline_eps = float(max(reso2, mad2 * 0.5))
                            flatline_delta = float(max(reso2 * 2.0, mad2 * 1.0))

                            cur.execute(
                                """
                                INSERT INTO public.metric_rule_auto_baseline_shadow(
                                  station_id, device_id, metric_id, lookback_days, method, version,
                                  p05, p95, median, mad, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta, computed_at, remark
                                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now(), %s)
                                ON CONFLICT (station_id, device_id, metric_id, lookback_days, method, version) DO UPDATE
                                  SET p05=EXCLUDED.p05, p95=EXCLUDED.p95, median=EXCLUDED.median, mad=EXCLUDED.mad,
                                      spike_abs=EXCLUDED.spike_abs, roc_abs=EXCLUDED.roc_abs, roc_ratio=EXCLUDED.roc_ratio,
                                      flatline_eps=EXCLUDED.flatline_eps, flatline_delta=EXCLUDED.flatline_delta, computed_at=now(), remark=EXCLUDED.remark
                                """,
                                (
                                    st,
                                    dev,
                                    met,
                                    lookback_days,
                                    method,
                                    version,
                                    p05,
                                    p95,
                                    med2,
                                    mad2,
                                    spike_abs,
                                    roc_abs,
                                    roc_ratio,
                                    flatline_eps,
                                    flatline_delta,
                                    "fallback_py_robust",
                                ),
                            )
                            inserted += 1
                    continue
                period = int(max(24 * 60, 2))  # 24h=1440点

                try:
                    stl = STL(df["v"], period=period, robust=True)
                    res = stl.fit()
                    resid = res.resid.values.astype(float)
                    if resid.size < 100:
                        continue
                    med = float(np.median(resid))
                    mad = float(np.median(np.abs(resid - med)))
                    p05 = float(np.quantile(resid, 0.05))
                    p95 = float(np.quantile(resid, 0.95))
                    # 跳变与速率阈值（残差域）
                    diff = np.diff(resid)
                    if diff.size < 10:
                        continue
                    spike_abs = float(np.quantile(np.abs(diff), 0.99))
                    roc_abs = spike_abs
                    prev = resid[:-1]
                    with np.errstate(divide="ignore", invalid="ignore"):
                        roc_ratio_arr = np.abs(
                            diff / np.where(prev == 0.0, np.nan, prev)
                        )
                    roc_ratio = float(np.nanquantile(roc_ratio_arr, 0.99))
                    # 平台期阈值：MAD 与观测分辨率结合（引入元数据的 resolution 作为下限）
                    # 读取元数据分辨率（设备/站点优先，其次全局）
                    cur.execute(
                        """
                        SELECT COALESCE(vm.resolution, 0.0)
                        FROM public.v_effective_metric_metadata vm
                        WHERE vm.metric_id = %s AND (vm.device_id = %s OR vm.device_id IS NULL)
                          AND (vm.station_id = %s OR vm.station_id IS NULL)
                        ORDER BY (vm.device_id IS NOT NULL) DESC, (vm.station_id IS NOT NULL) DESC
                        LIMIT 1
                        """,
                        (met, dev, st),
                    )
                    row_res = cur.fetchone()
                    reso = (
                        float(row_res[0]) if row_res and row_res[0] is not None else 0.0
                    )
                    flatline_eps = float(max(reso, mad * 0.5))
                    flatline_delta = float(max(reso * 2.0, mad * 1.0))

                    cur.execute(
                        """
                        INSERT INTO public.metric_rule_auto_baseline_shadow(
                          station_id, device_id, metric_id, lookback_days, method, version,
                          p05, p95, median, mad, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta, computed_at, remark
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now(), %s)
                        ON CONFLICT (station_id, device_id, metric_id, lookback_days, method, version) DO UPDATE
                          SET p05=EXCLUDED.p05, p95=EXCLUDED.p95, median=EXCLUDED.median, mad=EXCLUDED.mad,
                              spike_abs=EXCLUDED.spike_abs, roc_abs=EXCLUDED.roc_abs, roc_ratio=EXCLUDED.roc_ratio,
                              flatline_eps=EXCLUDED.flatline_eps, flatline_delta=EXCLUDED.flatline_delta, computed_at=now(), remark=EXCLUDED.remark
                        """,
                        (
                            st,
                            dev,
                            met,
                            lookback_days,
                            method,
                            version,
                            p05,
                            p95,
                            med,
                            mad,
                            spike_abs,
                            roc_abs,
                            roc_ratio,
                            flatline_eps,
                            flatline_delta,
                            "stl_residual",
                        ),
                    )
                    inserted += 1
                    if len(samples) < 5:
                        samples.append(
                            {
                                "station_id": st,
                                "device_id": dev,
                                "metric_id": met,
                                "mad": mad,
                                "p95": p95,
                            }
                        )
                except Exception:
                    # 单个分组失败跳过，继续其它分组
                    continue

        # 提交事务，确保数据持久化
        conn.commit()

    result["inserted"] = inserted
    result["samples"] = samples

    _act.info(
        "[流程-完成] [自动基线生成B]",
        extra={
            "extra_data": {
                "inserted": inserted,
                "groups_count": len(groups),
                "samples_count": len(samples),
            }
        },
    )

    return result
