from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from datetime import datetime as _dt

import numpy as np
from sklearn.mixture import GaussianMixture

from app.adapters.db.gateway import get_conn
import logging

_act = logging.getLogger(__name__)


def _fit_gmm_threshold(
    values: np.ndarray,
) -> Optional[tuple[float, float, float, float, float]]:
    """用 GMM(2) 在 [0,1] 上拟合 PF，返回(阈值, m1, m2, w1, w2)。样本<50返回None（降低要求从200→50）。"""
    x = values[np.isfinite(values)]
    x = x[(x >= 0.0) & (x <= 1.0)]
    if x.size < 50:  # 降低最小数据量要求（从200→50）
        return None
    x = x.reshape(-1, 1)
    try:
        gmm = GaussianMixture(
            n_components=2, covariance_type="full", random_state=42, max_iter=200
        )
        gmm.fit(x)
        means = np.sort(gmm.means_.ravel())
        covs = gmm.covariances_.reshape(-1)
        weights = gmm.weights_.ravel()
        # 数值解两高斯加权密度相等点：w1*N(m1,s1)=w2*N(m2,s2)
        m1, m2 = means[0], means[1]
        s1, s2 = np.sqrt(covs[0]), np.sqrt(covs[1])
        w1, w2 = weights[0], weights[1]
        # 近似解：在两均值之间用二分搜索找到密度相等点
        lo, hi = float(min(m1, m2)), float(max(m1, m2))
        for _ in range(60):
            mid = (lo + hi) / 2.0
            p1 = (
                w1
                * (1.0 / (s1 * np.sqrt(2 * np.pi)))
                * np.exp(-0.5 * ((mid - m1) / s1) ** 2)
            )
            p2 = (
                w2
                * (1.0 / (s2 * np.sqrt(2 * np.pi)))
                * np.exp(-0.5 * ((mid - m2) / s2) ** 2)
            )
            if p1 > p2:
                lo = mid
            else:
                hi = mid
        thr = (lo + hi) / 2.0
        thr = float(max(0.0, min(1.0, thr)))
        return (thr, float(m1), float(m2), float(w1), float(w2))
    except Exception:
        return None


def run_running_thresholds_b(
    settings,
    start: Optional[str],
    end: Optional[str],
    station_id: Optional[int],
    device_id: Optional[int],
    method: str = "gmm_bimodal",
    version: str = "vB_shadow",
) -> Dict[str, Any]:
    """
    使用GMM算法计算设备运行阈值（方案B），存入影子表。

    功能说明：
    - 从 fact_measurements 读取功率因数数据（quality_status=0）
    - 使用 mv_device_running_1s 表过滤稳态数据（running=1）
    - 使用GMM双峰拟合计算PF阈值，失败时回退到分位数方法
    - 结果存入 device_running_thresholds_shadow 表

    注意：
    - 只会为有稳态数据的设备计算阈值
    - 如果设备没有稳态数据（running=1），将被跳过
    - 当前数据中，只有设备3和设备5有稳态数据

    参数：
        settings: 系统配置
        start: 开始时间（ISO8601格式），None时自动从fact_measurements查询
        end: 结束时间（ISO8601格式），None时自动从fact_measurements查询
        station_id: 站点ID过滤（可选）
        device_id: 设备ID过滤（可选）
        method: 计算方法（默认"gmm_bimodal"）
        version: 版本标识（默认"vB_shadow"）

    返回：
        Dict[str, Any]: 执行摘要
        {
            "window": {"start": str, "end": str},
            "filters": {"station_id": int|None, "device_id": int|None},
            "method": str,
            "version": str,
            "inserted": int,  # 插入的设备数量
            "samples": List[Dict],  # 前5个设备的样本数据
        }

    异常：
        无显式异常抛出，所有错误通过日志记录并返回空结果

    示例：
        >>> from app.core.config import load_settings
        >>> from pathlib import Path
        >>> settings = load_settings(Path("configs"))
        >>> result = run_running_thresholds_b(
        ...     settings,
        ...     start="2025-05-31T18:00:00Z",
        ...     end="2025-05-31T20:00:00Z",
        ... )
        >>> print(result["inserted"])
        2  # 只有设备3和设备5有稳态数据
    """
    _act.info(
        "[流程-开始] [运行阈值生成B]",
        extra={
            "extra_data": {
                "start": start,
                "end": end,
                "station_id": station_id,
                "device_id": device_id,
                "method": method,
                "version": version,
            }
        },
    )

    result: Dict[str, Any] = {
        "window": {"start": start, "end": end},
        "filters": {"station_id": station_id, "device_id": device_id},
        "method": method,
        "version": version,
        "inserted": 0,
        "samples": [],
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 自动窗口
            if not start or not end:
                _act.info("[数据库-查询] [时间范围查询]")
                cur.execute(
                    "SELECT MIN(ts_bucket), MAX(ts_bucket) FROM public.fact_measurements"
                )
                row = cur.fetchone() or (None, None)
                if not start and row[0] is not None:
                    start = row[0].isoformat()
                if not end and row[1] is not None:
                    end = row[1].isoformat()
                _act.info(
                    "[数据库-查询] [时间范围已获取]",
                    extra={"extra_data": {"start": start, "end": end}},
                )
            if not start or not end:
                _act.warning(
                    "[流程-跳过] [时间窗口无效]",
                    extra={"extra_data": {"start": start, "end": end}},
                )
                return result

            s_dt = _dt.fromisoformat(start.replace("Z", "+00:00"))
            e_dt = _dt.fromisoformat(end.replace("Z", "+00:00"))

            _act.info(
                "[流程-阶段] [时间窗口确定]",
                extra={
                    "extra_data": {
                        "start_ts": s_dt.isoformat(),
                        "end_ts": e_dt.isoformat(),
                        "duration_hours": (e_dt - s_dt).total_seconds() / 3600,
                    }
                },
            )

            # 读取 PF 样本（质量=0 且稳态），按设备汇总
            # 使用 mv_device_running_1s 表进行稳态过滤（running=1）
            cur.execute(
                "SELECT id FROM public.dim_metric_config WHERE metric_key IN ('pump_power_factor','power_factor') LIMIT 1"
            )
            row = cur.fetchone()
            pf_id = int(row[0]) if row and row[0] is not None else None

            if pf_id is None:
                _act.warning(
                    "[流程-跳过] [功率因数指标缺失]",
                    extra={"extra_data": {"pf_id": pf_id}},
                )
                return result

            # 先检查 mv_device_running_1s 表是否有数据
            cur.execute("SELECT COUNT(*) FROM public.mv_device_running_1s WHERE running = 1")
            running_count = cur.fetchone()[0]

            if running_count > 0:
                # 有稳态数据，使用 mv_device_running_1s 表进行过滤
                _act.info(
                    "[数据库-查询] [功率因数数据加载] 使用 mv_device_running_1s 表进行稳态过滤",
                    extra={
                        "extra_data": {
                            "pf_id": pf_id,
                            "steady_state_source": "mv_device_running_1s",
                            "running_count": running_count,
                        }
                    },
                )
                cur.execute(
                    """
                    SELECT f.device_id, f.value::float8 AS pf
                    FROM public.fact_measurements f
                    WHERE f.metric_id = %(pf_id)s
                      AND f.ts_bucket >= %(start)s AND f.ts_bucket < %(end)s
                      AND (%(station_id)s::bigint IS NULL OR f.station_id=%(station_id)s::bigint)
                      AND (%(device_id)s::bigint IS NULL OR f.device_id=%(device_id)s::bigint)
                      AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                      AND EXISTS (
                        SELECT 1 FROM public.mv_device_running_1s r
                        WHERE r.station_id=f.station_id
                          AND r.device_id=f.device_id
                          AND r.ts_bucket=f.ts_bucket
                          AND r.running = 1
                      )
                    """,
                    {
                        "pf_id": pf_id,
                        "start": s_dt,
                        "end": e_dt,
                        "station_id": station_id,
                        "device_id": device_id,
                    },
                )
            else:
                # mv_device_running_1s 表为空，回退到不过滤稳态的策略
                _act.warning(
                    "[数据库-查询] [功率因数数据加载] mv_device_running_1s 表为空，回退到不过滤稳态",
                    extra={
                        "extra_data": {
                            "pf_id": pf_id,
                            "steady_state_source": "none",
                            "fallback": True,
                        }
                    },
                )
                cur.execute(
                    """
                    SELECT f.device_id, f.value::float8 AS pf
                    FROM public.fact_measurements f
                    WHERE f.metric_id = %(pf_id)s
                      AND f.ts_bucket >= %(start)s AND f.ts_bucket < %(end)s
                      AND (%(station_id)s::bigint IS NULL OR f.station_id=%(station_id)s::bigint)
                      AND (%(device_id)s::bigint IS NULL OR f.device_id=%(device_id)s::bigint)
                      AND COALESCE(f.quality_status,0)=0 AND f.value IS NOT NULL
                    """,
                    {
                        "pf_id": pf_id,
                        "start": s_dt,
                        "end": e_dt,
                        "station_id": station_id,
                        "device_id": device_id,
                    },
                )

            rows = cur.fetchall() or []
            _act.info(
                "[数据库-查询] [数据加载完成]",
                extra={"extra_data": {"rows_count": len(rows)}},
            )
            if not rows:
                _act.warning(
                    "[流程-跳过] [无可用数据]",
                    extra={"extra_data": {"reason": "功率因数数据为空"}},
                )
                return result

            import collections

            by_dev: Dict[int, list[float]] = collections.defaultdict(list)
            for d, v in rows:
                if v is None:
                    continue
                try:
                    x = float(v)
                except Exception:
                    continue
                if x < 0.0 or x > 1.0:
                    continue
                by_dev[int(d)].append(x)

            _act.info(
                "[流程-阶段] [数据分组完成]",
                extra={
                    "extra_data": {"devices_count": len(by_dev), "total_rows": len(rows)}
                },
            )

            # 稳态数据统计日志
            devices_with_data = list(by_dev.keys())
            steady_state_data_per_device = {dev: len(arr) for dev, arr in by_dev.items()}
            _act.info(
                "[流程-阶段] [稳态数据统计]",
                extra={
                    "extra_data": {
                        "devices_with_steady_state": len(devices_with_data),
                        "devices_with_steady_state_list": devices_with_data,
                        "steady_state_data_per_device": steady_state_data_per_device,
                    }
                },
            )

            # 创建影子表（迁移已提供，这里兜底）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.device_running_thresholds_shadow (
                  device_id bigint NOT NULL REFERENCES public.dim_devices(id),
                  method text NOT NULL,
                  version text NOT NULL,
                  pf_min double precision NULL,
                  pf_max double precision NULL,
                  computed_at timestamptz NOT NULL DEFAULT now(),
                  remark text NULL,
                  PRIMARY KEY (device_id, method, version)
                )
                """
            )

            inserted = 0
            samples: list[dict[str, Any]] = []

            for dev, arr in by_dev.items():
                pf_values = np.asarray(arr, dtype=float)

                # 设备处理开始日志
                _act.info(
                    f"[设备处理] [设备ID={dev}] 开始处理",
                    extra={
                        "extra_data": {
                            "device_id": dev,
                            "data_count": len(arr),
                            "data_min": float(pf_values.min()),
                            "data_max": float(pf_values.max()),
                            "data_mean": float(pf_values.mean()),
                        }
                    },
                )

                gmm_res = _fit_gmm_threshold(pf_values)
                # 参数：健康度阈值与滞回带
                DELTA_M = 0.05
                MIN_W = 0.10
                CLIP_LO, CLIP_HI = 0.10, 0.95
                HYST_C = 2.0
                MIN_BAND = 0.01

                def _robust_band(vals: np.ndarray) -> float:
                    if vals.size == 0:
                        return MIN_BAND
                    med = float(np.median(vals))
                    mad = float(np.median(np.abs(vals - med)))
                    band = max(MIN_BAND, HYST_C * mad)
                    return float(band)

                if gmm_res is None:
                    # Fallback：用分位作为影子输出，避免空洞
                    p05 = (
                        float(np.quantile(pf_values, 0.05)) if pf_values.size else None
                    )
                    p95 = (
                        float(np.quantile(pf_values, 0.95)) if pf_values.size else None
                    )
                    pf_min, pf_max = p05, p95
                    src = "fallback_robust(no_gmm)"
                else:
                    thr, m1, m2, w1, w2 = gmm_res
                    delta = abs(m2 - m1)
                    min_w = min(w1, w2)
                    ok = (
                        delta >= DELTA_M
                        and min_w >= MIN_W
                        and CLIP_LO <= thr <= CLIP_HI
                        and min(m1, m2) <= thr <= max(m1, m2)
                    )
                    if not ok:
                        # 回退：稳健分位
                        p05 = (
                            float(np.quantile(pf_values, 0.05))
                            if pf_values.size
                            else None
                        )
                        p95 = (
                            float(np.quantile(pf_values, 0.95))
                            if pf_values.size
                            else None
                        )
                        pf_min, pf_max = p05, p95
                        src = f"fallback_robust(delta={delta:.3f},min_w={min_w:.2f},thr={thr:.3f})"
                    else:
                        # 使用 GMM 阈值 + 滞回带
                        band = _robust_band(pf_values)
                        off_thr = max(0.0, min(1.0, thr - band))
                        on_thr = max(0.0, min(1.0, thr + band))
                        pf_min = float(min(off_thr, on_thr))
                        pf_max = float(max(off_thr, on_thr))
                        src = f"gmm_bimodal(m1={m1:.3f},m2={m2:.3f},w1={w1:.2f},w2={w2:.2f},band={band:.3f})"

                cur.execute(
                    """
                    INSERT INTO public.device_running_thresholds_shadow(
                      device_id, method, version, pf_min, pf_max, computed_at, remark
                    ) VALUES (%s,%s,%s,%s,%s, now(), %s)
                    ON CONFLICT (device_id, method, version) DO UPDATE
                      SET pf_min=EXCLUDED.pf_min, pf_max=EXCLUDED.pf_max, computed_at=now(), remark=EXCLUDED.remark
                    """,
                    (dev, method, version, pf_min, pf_max, src),
                )
                inserted += 1

                # 设备处理完成日志
                _act.info(
                    f"[设备处理] [设备ID={dev}] 处理完成",
                    extra={
                        "extra_data": {
                            "device_id": dev,
                            "method": "gmm" if gmm_res is not None and (gmm_res is not None and "gmm_bimodal" in src) else "fallback",
                            "pf_min": pf_min,
                            "pf_max": pf_max,
                            "remark": src,
                        }
                    },
                )

                if len(samples) < 5:
                    samples.append(
                        {
                            "device_id": dev,
                            "pf_min": pf_min,
                            "pf_max": pf_max,
                            "src": src,
                        }
                    )

            result["inserted"] = inserted
            result["samples"] = samples

            _act.info(
                "[流程-完成] [运行阈值生成B]",
                extra={
                    "extra_data": {
                        "inserted": inserted,
                        "devices_count": len(by_dev),
                        "samples_count": len(samples),
                    }
                },
            )

        # 提交事务，确保数据持久化
        conn.commit()

    return result
