from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import os
import csv
import math

from app.adapters.db.gateway import get_conn

import logging

_act = logging.getLogger(__name__)


@dataclass
class Stat:
    n: int
    mean: float | None = None
    p50: float | None = None
    p90: float | None = None
    max: float | None = None


def _stats(vals: List[float]) -> Dict[str, Any]:
    try:
        import numpy as np  # 已在项目中安装
    except Exception:
        # 简易统计回退
        if not vals:
            return {"n": 0}
        arr = sorted(vals)
        n = len(arr)
        p50 = arr[n // 2]
        p90 = arr[max(0, int(math.ceil(n * 0.9)) - 1)]
        return {
            "n": n,
            "mean": sum(arr) / n,
            "p50": p50,
            "p90": p90,
            "max": arr[-1],
        }
    if not vals:
        return {"n": 0}
    a = np.array(vals, dtype=float)
    return {
        "n": int(a.size),
        "mean": float(np.mean(a)),
        "p50": float(np.quantile(a, 0.5)),
        "p90": float(np.quantile(a, 0.9)),
        "max": float(np.max(a)),
    }


def _absdiff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    try:
        return abs(float(a) - float(b))
    except Exception:
        return None


def run_rules_diff_report(
    settings,
    method: str = "stl_residual",
    version: str = "vB_shadow",
    out_dir: Optional[str] = None,
    top_k: int = 20,
) -> Dict[str, Any]:
    """
    生成 A 表与 B 影子表的差异报告：
    - 基线层：metric_rule_auto_baseline_shadow vs metric_rule_auto_baseline
    - 规则层：metric_quality_rules_shadow vs metric_quality_rules
    - 若 out_dir 提供，则导出两份 CSV 详情
    """
    _act.info(
        "[流程-开始] [规则差异报告生成]",
        extra={"extra_data": {"method": method, "version": version, "top_k": top_k}},
    )

    result: Dict[str, Any] = {
        "method": method,
        "version": version,
        "baseline": {},
        "quality_rules": {},
        "csv_files": [],
    }

    baseline_rows: List[Tuple] = []
    rule_rows: List[Tuple] = []

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 计数
            cur.execute(
                "SELECT COUNT(*) FROM public.metric_rule_auto_baseline_shadow WHERE method=%s AND version=%s",
                (method, version),
            )
            total_shadow = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM public.metric_rule_auto_baseline")
            total_a = int(cur.fetchone()[0])

            # join 详情
            cur.execute(
                (
                    "SELECT s.lookback_days, s.station_id, s.device_id, s.metric_id, "
                    " s.p05, a.p05, s.p95, a.p95, s.median, a.median, s.mad, a.mad, "
                    " s.spike_abs, a.spike_abs, s.roc_abs, a.roc_abs, s.roc_ratio, a.roc_ratio, "
                    " s.flatline_eps, a.flatline_eps, s.flatline_delta, a.flatline_delta "
                    " FROM public.metric_rule_auto_baseline_shadow s "
                    " JOIN public.metric_rule_auto_baseline a "
                    " USING (station_id, device_id, metric_id, lookback_days) "
                    " WHERE s.method=%s AND s.version=%s"
                ),
                (method, version),
            )
            baseline_rows = cur.fetchall() or []

            # 规则层
            cur.execute(
                "SELECT COUNT(*) FROM public.metric_quality_rules_shadow WHERE method=%s AND version=%s",
                (method, version),
            )
            qr_total_shadow = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM public.metric_quality_rules")
            qr_total_a = int(cur.fetchone()[0])

            cur.execute(
                (
                    "SELECT s.station_id, s.device_id, s.metric_id, "
                    " s.value_min, r.value_min, s.value_max, r.value_max, "
                    " s.spike_abs, r.spike_abs, s.roc_abs, r.roc_abs, s.roc_ratio, r.roc_ratio, "
                    " s.flatline_eps, r.flatline_eps, s.flatline_delta, r.flatline_delta "
                    " FROM public.metric_quality_rules_shadow s "
                    " JOIN public.metric_quality_rules r USING (station_id, device_id, metric_id) "
                    " WHERE s.method=%s AND s.version=%s"
                ),
                (method, version),
            )
            rule_rows = cur.fetchall() or []

    # 汇总统计
    def build_stats_for_baseline(rows: List[Tuple]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "total_shadow": total_shadow,
            "total_a": total_a,
            "join_rows": len(rows),
        }
        idx = {
            "p05": (4, 5),
            "p95": (6, 7),
            "median": (8, 9),
            "mad": (10, 11),
            "spike_abs": (12, 13),
            "roc_abs": (14, 15),
            "roc_ratio": (16, 17),
            "flatline_eps": (18, 19),
            "flatline_delta": (20, 21),
        }
        for name, (i_b, i_a) in idx.items():
            vals = []
            for r in rows:
                d = _absdiff(r[i_b], r[i_a])
                if d is not None:
                    vals.append(d)
            stats[name] = _stats(vals)
        return stats

    def build_stats_for_rules(rows: List[Tuple]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "total_shadow": qr_total_shadow,
            "total_a": qr_total_a,
            "join_rows": len(rows),
        }
        idx = {
            "value_min": (3, 4),
            "value_max": (5, 6),
            "spike_abs": (7, 8),
            "roc_abs": (9, 10),
            "roc_ratio": (11, 12),
            "flatline_eps": (13, 14),
            "flatline_delta": (15, 16),
        }
        for name, (i_b, i_a) in idx.items():
            vals = []
            for r in rows:
                d = _absdiff(r[i_b], r[i_a])
                if d is not None:
                    vals.append(d)
            stats[name] = _stats(vals)
        return stats

    result["baseline"] = build_stats_for_baseline(baseline_rows)
    result["quality_rules"] = build_stats_for_rules(rule_rows)

    # 可选导出 CSV 详情
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        base_csv = os.path.join(out_dir, "baseline_diff_details.csv")
        qr_csv = os.path.join(out_dir, "quality_rules_diff_details.csv")
        # baseline CSV
        with open(base_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "lookback_days",
                    "station_id",
                    "device_id",
                    "metric_id",
                    # pairs + diff
                    "p05_b",
                    "p05_a",
                    "p05_diff",
                    "p95_b",
                    "p95_a",
                    "p95_diff",
                    "median_b",
                    "median_a",
                    "median_diff",
                    "mad_b",
                    "mad_a",
                    "mad_diff",
                    "spike_abs_b",
                    "spike_abs_a",
                    "spike_abs_diff",
                    "roc_abs_b",
                    "roc_abs_a",
                    "roc_abs_diff",
                    "roc_ratio_b",
                    "roc_ratio_a",
                    "roc_ratio_diff",
                    "flatline_eps_b",
                    "flatline_eps_a",
                    "flatline_eps_diff",
                    "flatline_delta_b",
                    "flatline_delta_a",
                    "flatline_delta_diff",
                ]
            )
            for r in baseline_rows:
                row = [r[0], r[1], r[2], r[3]]
                pairs = [
                    (r[4], r[5]),
                    (r[6], r[7]),
                    (r[8], r[9]),
                    (r[10], r[11]),
                    (r[12], r[13]),
                    (r[14], r[15]),
                    (r[16], r[17]),
                    (r[18], r[19]),
                    (r[20], r[21]),
                ]
                for (b, a) in pairs:
                    row.extend([b, a, _absdiff(b, a)])
                w.writerow(row)
        # rules CSV
        with open(qr_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "station_id",
                    "device_id",
                    "metric_id",
                    "value_min_b",
                    "value_min_a",
                    "value_min_diff",
                    "value_max_b",
                    "value_max_a",
                    "value_max_diff",
                    "spike_abs_b",
                    "spike_abs_a",
                    "spike_abs_diff",
                    "roc_abs_b",
                    "roc_abs_a",
                    "roc_abs_diff",
                    "roc_ratio_b",
                    "roc_ratio_a",
                    "roc_ratio_diff",
                    "flatline_eps_b",
                    "flatline_eps_a",
                    "flatline_eps_diff",
                    "flatline_delta_b",
                    "flatline_delta_a",
                    "flatline_delta_diff",
                ]
            )
            for r in rule_rows:
                pairs = [
                    (r[3], r[4]),
                    (r[5], r[6]),
                    (r[7], r[8]),
                    (r[9], r[10]),
                    (r[11], r[12]),
                    (r[13], r[14]),
                    (r[15], r[16]),
                ]
                row = [r[0], r[1], r[2]]
                for (b, a) in pairs:
                    row.extend([b, a, _absdiff(b, a)])
                w.writerow(row)
        result["csv_files"].extend([base_csv, qr_csv])

    # Top-K 差异（便于快速定位明显差异项）
    def topk(rows: List[Tuple], pair_idx: Tuple[int, int], keys_idx: Tuple[int, ...], k: int):
        scored = []
        for r in rows:
            d = _absdiff(r[pair_idx[0]], r[pair_idx[1]])
            if d is not None:
                scored.append((d,) + tuple(r[i] for i in keys_idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:k]

    result["top"] = {
        "baseline": {
            "p95": topk(baseline_rows, (6, 7), (1, 2, 3), top_k),
            "mad": topk(baseline_rows, (10, 11), (1, 2, 3), top_k),
        },
        "quality_rules": {
            "value_max": topk(rule_rows, (5, 6), (0, 1, 2), top_k),
            "flatline_eps": topk(rule_rows, (13, 14), (0, 1, 2), top_k),
        },
    }

    return result

