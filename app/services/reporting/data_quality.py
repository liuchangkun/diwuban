from __future__ import annotations

# ruff: noqa: E402  # 顶部存在模块级文档字符串与 __future__ 导致 E402 误报，临时忽略（后续统一导入规范时再移除）


"""
数据质量报表（services.reporting.data_quality）
- 消费 ingest 过程产生的 perf.ndjson（ingest.copy.batch）与数据库事实表
- 输出覆盖率/缺口/越界统计，并从 perf.ndjson 归纳 p95 批耗时与行速率

事件字段对齐：
- ingest.copy.batch（perf）：batch_cost_ms, rows_per_sec
- align.merge.window（root）：affected_rows, rows_input, rows_deduped, rows_merged, dedup_ratio, sql_cost_ms
"""


import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.adapters.db.gateway import get_conn
from app.core.config.loader import Settings


def generate_report(
    settings: Settings,
    start_utc: datetime,
    end_utc: datetime,
    run_dir: Path | None = None,
    expected_interval_seconds: int = 1,
    top_k: int = 100,
    group_by: str = "metric",
) -> Dict[str, Any]:
    """生成数据质量报表。

    参数：
    - settings：配置（用于数据库连接）
    - start_utc/end_utc：统计窗口（UTC）
    - run_dir：可选；若提供且存在 perf.ndjson，则归纳 ingest.copy.batch 的 p95 指标
    - expected_interval_seconds：期望入库间隔（秒），用于覆盖率与缺口检测
    - top_k：各统计中选取 Top-K 分组
    - group_by：分组键；metric|device|station|batch|source

    返回：
    - JSON 结构，包含 window/params/coverage_top/histogram_hourly/coverage_rate/gaps_top
      /outliers_agg/quantiles/zero_const 与 perf（如 run_dir 存在）

    示例：
    - generate_report(cfg, start, end, run_dir=Path('logs/runs/2025.../..'))
    - 返回对象可写入 reports/data_quality_report.json（本函数已在有 run_dir 时自动输出）
    """
    out: Dict[str, Any] = {
        "window": {
            "start": start_utc.isoformat(),
            "end": end_utc.isoformat(),
        },
        "params": {
            "expected_interval_seconds": expected_interval_seconds,
            "top_k": top_k,
            "group_by": group_by,
        },
    }

    def _grp_expr(alias: str = "f") -> Tuple[str, str]:
        if group_by == "metric":
            return ("metric_id", f"{alias}.metric_id")
        if group_by == "device":
            return ("device_id", f"{alias}.device_id")
        if group_by == "station":
            return ("station_id", f"{alias}.station_id")
        if group_by == "batch":
            # 'batch=xxxx' 在第二段
            return (
                "batch",
                f"split_part(split_part({alias}.source_hint, '|', 2), '=', 2)",
            )
        if group_by == "source":
            # 文件（含相对路径）在第一段
            return ("source", f"split_part({alias}.source_hint, '|', 1)")
        # 默认 metric
        return ("metric_id", f"{alias}.metric_id")

    grp_key, grp_sql = _grp_expr("f")

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 基础覆盖统计（TopK）
            cur.execute(
                f"""
                WITH base AS (
                  SELECT {grp_sql} AS grp,
                         min(ts_bucket) AS ts_min,
                         max(ts_bucket) AS ts_max,
                         count(*) AS rows
                  FROM public.fact_measurements f
                  WHERE ts_bucket >= %s AND ts_bucket < %s
                  GROUP BY {grp_sql}
                )
                SELECT grp, ts_min, ts_max, rows
                FROM base
                ORDER BY rows DESC
                LIMIT %s
                """,
                (start_utc, end_utc, top_k),
            )
            out["coverage_top"] = [
                {
                    grp_key: r[0],
                    "ts_min": str(r[1]),
                    "ts_max": str(r[2]),
                    "rows": int(r[3]),
                }
                for r in cur.fetchall()
            ]

            # 覆盖直方图（按小时）- 仅 TopK 分组
            cur.execute(
                f"""
                WITH tops AS (
                  SELECT {grp_sql} AS grp, count(*) AS rows
                  FROM public.fact_measurements f
                  WHERE ts_bucket >= %s AND ts_bucket < %s
                  GROUP BY {grp_sql}
                  ORDER BY rows DESC
                  LIMIT %s
                )
                SELECT t.grp,
                       date_trunc('hour', f.ts_bucket) AS bucket,
                       count(*) AS rows
                FROM public.fact_measurements f
                JOIN tops t ON t.grp = {grp_sql}
                WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                GROUP BY t.grp, date_trunc('hour', f.ts_bucket)
                ORDER BY t.grp, bucket
                """,
                (start_utc, end_utc, top_k, start_utc, end_utc),
            )
            out["histogram_hourly"] = [
                {grp_key: r[0], "bucket": str(r[1]), "rows": int(r[2])}
                for r in cur.fetchall()
            ]

            # 覆盖率与缺口（基于 expected_interval_seconds）- 仅 TopK 分组
            cur.execute(
                f"""
                WITH tops AS (
                  SELECT {grp_sql} AS grp, count(*) AS rows
                  FROM public.fact_measurements f
                  WHERE ts_bucket >= %s AND ts_bucket < %s
                  GROUP BY {grp_sql}
                  ORDER BY rows DESC
                  LIMIT %s
                ), seq AS (
                  SELECT f.{grp_key} AS grp, f.ts_bucket AS ts,
                         lag(f.ts_bucket) OVER (PARTITION BY f.{grp_key} ORDER BY f.ts_bucket) AS prev
                  FROM public.fact_measurements f
                  JOIN tops t ON t.grp = f.{grp_key}
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                )
                SELECT t.grp,
                       min(s.ts) AS ts_min,
                       max(s.ts) AS ts_max,
                       count(*) AS rows,
                       sum(CASE WHEN s.prev IS NOT NULL AND EXTRACT(EPOCH FROM (s.ts - s.prev)) > %s THEN EXTRACT(EPOCH FROM (s.ts - s.prev)) ELSE 0 END) AS gap_seconds
                FROM seq s
                JOIN tops t ON t.grp = s.grp
                GROUP BY t.grp
                ORDER BY rows DESC
                """,
                (
                    start_utc,
                    end_utc,
                    top_k,
                    start_utc,
                    end_utc,
                    expected_interval_seconds * 1.5,
                ),
            )
            cov_rows = cur.fetchall()
            out["coverage_rate"] = []
            for r in cov_rows:
                grp, ts_min, ts_max, rows_count, gap_seconds = r
                if ts_min and ts_max:
                    total_span = max(1, int((ts_max - ts_min).total_seconds()) + 1)
                    expected = max(
                        1, math.ceil(total_span / max(1, expected_interval_seconds))
                    )
                else:
                    expected = rows_count
                rate = round(min(1.0, rows_count / expected), 4) if expected else 1.0
                out["coverage_rate"].append(
                    {
                        grp_key: grp,
                        "rows": int(rows_count),
                        "expected_rows": int(expected),
                        "coverage_rate": rate,
                        "gap_seconds_sum": int(gap_seconds or 0),
                    }
                )

            # 缺口明细 TopK（按 gap 秒数排序）
            cur.execute(
                f"""
                WITH seq AS (
                  SELECT {grp_sql} AS grp, f.ts_bucket AS ts,
                         lag(f.ts_bucket) OVER (PARTITION BY {grp_sql} ORDER BY f.ts_bucket) AS prev
                  FROM public.fact_measurements f
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                )
                SELECT grp,
                       prev AS gap_start,
                       ts   AS gap_end,
                       EXTRACT(EPOCH FROM (ts - prev)) AS gap_seconds
                FROM seq
                WHERE prev IS NOT NULL AND EXTRACT(EPOCH FROM (ts - prev)) > %s
                ORDER BY gap_seconds DESC
                LIMIT %s
                """,
                (start_utc, end_utc, expected_interval_seconds * 1.5, top_k),
            )
            out["gaps_top"] = [
                {
                    grp_key: r[0],
                    "gap_start": str(r[1]),
                    "gap_end": str(r[2]),
                    "gap_seconds": int(r[3]),
                }
                for r in cur.fetchall()
            ]

            # 越界聚合（按配置 min/max）
            cur.execute(
                f"""
                WITH totals AS (
                  SELECT {grp_sql} AS grp, count(*) AS rows
                  FROM public.fact_measurements f
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                  GROUP BY {grp_sql}
                ), viol AS (
                  SELECT {grp_sql} AS grp, count(*) AS outliers
                  FROM public.fact_measurements f
                  JOIN public.dim_metric_config c ON c.id = f.metric_id
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                    AND ((c.valid_min IS NOT NULL AND f.value < c.valid_min) OR (c.valid_max IS NOT NULL AND f.value > c.valid_max))
                  GROUP BY {grp_sql}
                )
                SELECT t.grp, t.rows, COALESCE(v.outliers, 0) AS outliers
                FROM totals t LEFT JOIN viol v ON v.grp = t.grp
                ORDER BY outliers DESC
                LIMIT %s
                """,
                (start_utc, end_utc, start_utc, end_utc, top_k),
            )
            out["outliers_agg"] = [
                {
                    grp_key: r[0],
                    "rows": int(r[1]),
                    "outliers": int(r[2]),
                    "outlier_ratio": round((r[2] / r[1]) if r[1] else 0.0, 6),
                }
                for r in cur.fetchall()
            ]

            # 分位数（p01/p50/p95）
            cur.execute(
                f"""
                SELECT {grp_sql} AS grp,
                       percentile_disc(0.01) WITHIN GROUP (ORDER BY f.value) AS p01,
                       percentile_disc(0.5)  WITHIN GROUP (ORDER BY f.value) AS p50,
                       percentile_disc(0.95) WITHIN GROUP (ORDER BY f.value) AS p95
                FROM public.fact_measurements f
                WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                GROUP BY {grp_sql}
                ORDER BY grp
                LIMIT %s
                """,
                (start_utc, end_utc, top_k),
            )
            out["quantiles"] = [
                {
                    grp_key: r[0],
                    "p01": float(r[1]) if r[1] is not None else None,
                    "p50": float(r[2]) if r[2] is not None else None,
                    "p95": float(r[3]) if r[3] is not None else None,
                }
                for r in cur.fetchall()
            ]

            # 零值/常值检测（TopK）
            cur.execute(
                f"""
                WITH totals AS (
                  SELECT {grp_sql} AS grp, count(*) AS rows
                  FROM public.fact_measurements f
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                  GROUP BY {grp_sql}
                ), zeros AS (
                  SELECT {grp_sql} AS grp, sum(CASE WHEN f.value = 0 THEN 1 ELSE 0 END) AS zeros
                  FROM public.fact_measurements f
                  WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                  GROUP BY {grp_sql}
                ), consts AS (
                  SELECT t.grp AS grp, max(cnt) AS max_same
                  FROM (
                    SELECT {grp_sql} AS grp, value, count(*) AS cnt
                    FROM public.fact_measurements f
                    WHERE f.ts_bucket >= %s AND f.ts_bucket < %s
                    GROUP BY {grp_sql}, value
                  ) t
                  GROUP BY t.grp
                )
                SELECT t.grp, t.rows, COALESCE(z.zeros,0) AS zeros, COALESCE(c.max_same,0) AS max_same
                FROM totals t
                LEFT JOIN zeros z ON z.grp = t.grp
                LEFT JOIN consts c ON c.grp = t.grp
                ORDER BY (COALESCE(z.zeros,0)::float/t.rows) DESC
                LIMIT %s
                """,
                (start_utc, end_utc, start_utc, end_utc, start_utc, end_utc, top_k),
            )
            out["zero_const"] = [
                {
                    grp_key: r[0],
                    "rows": int(r[1]),
                    "zero_ratio": round((r[2] / r[1]) if r[1] else 0.0, 6),
                    "const_ratio": round((r[3] / r[1]) if r[1] else 0.0, 6),
                }
                for r in cur.fetchall()
            ]

    # perf 摘要（如有 run_dir）
    if run_dir:
        perf_path = Path(run_dir) / "perf.ndjson"
        parse_errors = 0
        perf_rows: List[Dict[str, Any]] = []
        if perf_path.exists():
            try:
                with perf_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            if (
                                '"event":"ingest.copy.batch"' in line
                                or '"event": "ingest.copy.batch"' in line
                            ):
                                perf_rows.append(json.loads(line))
                        except Exception:
                            parse_errors += 1
            except Exception:
                parse_errors += 1

            # 统计 p95（批耗时与行速率）
            def _p95(a: List[float]) -> float:
                if not a:
                    return 0.0
                arr: List[float] = sorted(a)
                idx = max(0, int(len(arr) * 0.95) - 1)
                return float(arr[idx])

            costs: List[float] = [
                float(r.get("extra", {}).get("batch_cost_ms", 0.0)) for r in perf_rows
            ]
            rps: List[float] = [
                float(r.get("extra", {}).get("rows_per_sec", 0.0)) for r in perf_rows
            ]
            out["perf"] = {
                "batches": len(perf_rows),
                "batch_cost_ms_p95": int(_p95(costs)),
                "rows_per_sec_p95": round(_p95(rps), 2),
                "parse_errors": parse_errors,
            }
        else:
            # 缺失 perf.ndjson：提供默认结构并记录事件
            out["perf"] = {
                "batches": 0,
                "batch_cost_ms_p95": 0,
                "rows_per_sec_p95": 0.0,
                "parse_errors": 0,
                "missing": True,
            }
            try:
                logging.getLogger("root").warning(
                    "perf.ndjson missing",
                    extra={
                        "event": "data_report.perf.missing",
                        "extra": {"run_dir": str(run_dir)},
                    },
                )
            except Exception:
                pass

    # 输出
    if run_dir:
        out_dir = Path(run_dir) / ".." / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        # 从 env.json 读取 run_id 作为文件名后缀
        run_id: str | None = None
        try:
            env_path = Path(run_dir) / "env.json"
            if env_path.exists():
                env_obj = json.loads(env_path.read_text(encoding="utf-8"))
                run_id = str(env_obj.get("run_id")) if env_obj.get("run_id") else None
        except Exception:
            run_id = None
        fname = (
            f"data_quality_report.{run_id}.json"
            if run_id
            else "data_quality_report.json"
        )
        out_path = out_dir / fname
        out_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 生成成功事件
        try:
            logging.getLogger("root").info(
                "data quality report generated",
                extra={
                    "event": "data_report.generated",
                    "extra": {
                        "run_id": run_id,
                        "window_start": out["window"]["start"],
                        "window_end": out["window"]["end"],
                        "report_path": str(out_path),
                        "groups_count": len(out.get("coverage_top", [])),
                    },
                },
            )
        except Exception:
            pass
    return out
