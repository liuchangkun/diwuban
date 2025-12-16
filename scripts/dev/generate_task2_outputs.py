from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import sys
import os

# ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection

REPORTS_DIR = Path("reports")
START = "2025-01-01 00:00:00+08"
END = "2025-02-28 14:09:59+08"


def _pick_report(filter_running: bool) -> Path:
    files = sorted(REPORTS_DIR.glob("missing_metrics_full_*.json"))
    cand: List[Tuple[Path, bool]] = []
    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            fr = bool(obj.get("summary", {}).get("filter_running"))
            if fr == filter_running:
                cand.append((p, fr))
        except Exception:
            continue
    if not cand:
        raise RuntimeError(f"no report for filter_running={filter_running}")
    # latest
    return cand[-1][0]


@dataclass
class WindowRecord:
    station_id: int
    device_id: int
    hour: str
    metric_key: str
    success: int
    failure_reason: str


def build_success_heatmap(report_path: Path, out_csv: Path) -> None:
    obj = json.loads(report_path.read_text(encoding="utf-8"))
    metrics: List[str] = obj["plan"]["metrics"]
    rows: List[WindowRecord] = []
    for item in obj.get("results", []):
        sid = int(item["station_id"])
        did = int(item["device_id"])
        hour = item["start"]  # window start
        res = item.get("result", {})
        ok_set = set(res.get("metrics_calculated", []) or [])
        errs = res.get("errors", []) or []
        err_map: Dict[str, str] = {}
        for e in errs:
            # format: "metric: reason"
            if ":" in e:
                k, v = e.split(":", 1)
                err_map[k.strip()] = v.strip()
        for m in metrics:
            if m in ok_set:
                rows.append(WindowRecord(sid, did, hour, m, 1, ""))
            else:
                rows.append(WindowRecord(sid, did, hour, m, 0, err_map.get(m, "unknown")))
    # write csv
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station_id","device_id","hour","metric_key","success_rate","failure_reason"])
        for r in rows:
            w.writerow([r.station_id, r.device_id, r.hour, r.metric_key, r.success, r.failure_reason])


def build_method_availability_matrix(dep_matrix_csv: Path, out_csv: Path) -> None:
    # input columns: metric_key,method_id,station_id,device_id,secs_total,secs_match_all,secs_match_all_running
    with dep_matrix_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station_id","device_id","metric_key","method_id","deps_available_secs","deps_available_running_secs","coverage_rate"])
        for r in rows:
            secs_total = int(r.get("secs_total", 0) or 0)
            secs_match_all = int(r.get("secs_match_all", 0) or 0)
            secs_match_all_running = int(r.get("secs_match_all_running", 0) or 0)
            coverage = (secs_match_all / secs_total) if secs_total > 0 else 0.0
            w.writerow([
                int(r["station_id"]), int(r["device_id"]), r["metric_key"], r["method_id"],
                secs_match_all, secs_match_all_running, f"{coverage:.6f}"
            ])


def _collect_unique_deps(conn: psycopg.Connection) -> Dict[str, List[str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT metric_key, COALESCE(dependencies, '{}'::text[])
        FROM calculation_method_registry
        WHERE is_enabled = TRUE
        """
    )
    dep_map: Dict[str, List[str]] = {}
    for metric_key, deps in cur.fetchall():
        dep_map.setdefault(metric_key, [])
        for d in (deps or []):
            if d not in dep_map[metric_key]:
                dep_map[metric_key].append(d)
    return dep_map


def _dep_presence_counts(conn: psycopg.Connection, deps: List[str]) -> Dict[str, Dict[str, int]]:
    # returns {dep: {"secs": n, "secs_running": n}}
    out: Dict[str, Dict[str, int]] = {}
    if not deps:
        return out
    cur = conn.cursor()
    # total secs per dep
    cur.execute(
        """
        SELECT %(dep)s AS dep, COUNT(*) AS secs
        FROM metrics_presence_per_second_device
        WHERE ts_second >= %(start)s AND ts_second <= %(end)s
          AND available_metrics @> %(arr)s
        """,
        {"start": START, "end": END, "dep": "__placeholder__", "arr": []},
    )
    # We'll loop per dep to avoid giant arrays
    for d in deps:
        cur.execute(
            """
            SELECT COUNT(*) FROM metrics_presence_per_second_device
            WHERE ts_second >= %(start)s AND ts_second <= %(end)s
              AND available_metrics @> %(arr)s
            """,
            {"start": START, "end": END, "arr": [d]},
        )
        secs = int(cur.fetchone()[0] or 0)
        cur.execute(
            """
            SELECT COUNT(*)
            FROM metrics_presence_per_second_device p
            JOIN mv_device_running_1s r
              ON p.station_id=r.station_id AND p.device_id=r.device_id AND p.ts_second=r.ts_bucket
            WHERE p.ts_second >= %(start)s AND p.ts_second <= %(end)s
              AND p.available_metrics @> %(arr)s
            """,
            {"start": START, "end": END, "arr": [d]},
        )
        secs_run = int(cur.fetchone()[0] or 0)
        out[d] = {"secs": secs, "secs_running": secs_run}
    return out


def build_failure_reasons_detail(fr_true_path: Path, dep_map: Dict[str, List[str]], dep_presence: Dict[str, Dict[str, int]], out_json: Path) -> None:
    obj = json.loads(fr_true_path.read_text(encoding="utf-8"))
    # aggregate from per-window errors
    agg: Dict[str, Dict[str, Any]] = {}
    for item in obj.get("results", []):
        res = item.get("result", {})
        errs = res.get("errors", []) or []
        for e in errs:
            if ":" in e:
                k, v = e.split(":", 1)
                metric, reason = k.strip(), v.strip()
                d = agg.setdefault(metric, {})
                entry = d.setdefault(reason, {"missing_deps": [], "count": 0, "affected_windows": 0})
                entry["count"] += 1
                entry["affected_windows"] += 1
    # infer missing_deps via presence (which deps never present across the range)
    for metric, reasons in agg.items():
        deps = dep_map.get(metric, [])
        missing = [d for d in deps if dep_presence.get(d, {}).get("secs_running", 0) == 0]
        for rname, entry in reasons.items():
            entry["missing_deps"] = missing
    out_json.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    settings = load_settings(Path("configs"))
    init_database(settings)

    # 1) pick reports
    rpt_true = _pick_report(True)
    try:
        rpt_false = _pick_report(False)
    except Exception:
        rpt_false = None

    # 2) success heatmap (only when no-filter-running report is present)
    if rpt_false is not None:
        heatmap_csv = REPORTS_DIR / "success_heatmap.no_filter_running.csv"
        build_success_heatmap(rpt_false, heatmap_csv)

    # 3) method availability matrix (transform from dependency_matrix_*.csv)
    dep_csv = max(REPORTS_DIR.glob("dependency_matrix_*.csv"))
    matrix_csv = REPORTS_DIR / "method_availability_matrix.csv"
    build_method_availability_matrix(dep_csv, matrix_csv)

    # 4) failure reasons (use filter_running=True report for“真实运行画像” + presence推断缺失依赖)
    with get_connection() as conn:
        dep_map = _collect_unique_deps(conn)
        all_deps = sorted({d for lst in dep_map.values() for d in lst})
        dep_presence = _dep_presence_counts(conn, all_deps)
    failure_json = REPORTS_DIR / "failure_reasons_detail.json"
    build_failure_reasons_detail(rpt_true, dep_map, dep_presence, failure_json)

    # 5) markdown summary (partial if no rpt_false)
    a = json.loads(rpt_true.read_text(encoding="utf-8"))
    def metric_success(d: Dict[str, Any]) -> Dict[str,int]:
        return {k:int(v) for k,v in (d.get("per_metric_success_tasks") or {}).items()}
    ms_true = metric_success(a)

    md = [
        "# Task2 对比摘要",
        f"- filter_running=True: windows={a['summary']['windows']}, success_tasks={a['summary'].get('success_tasks')}"
    ]
    if rpt_false is not None:
        b = json.loads(rpt_false.read_text(encoding="utf-8"))
        ms_false = metric_success(b)
        md.extend([
            f"- filter_running=False: windows={b['summary']['windows']}, success_tasks={b['summary'].get('success_tasks')}",
            "",
            "## 指标级成功窗口（对比）",
        ])
        all_metrics = sorted(set(ms_true.keys()) | set(ms_false.keys()))
        for m in all_metrics:
            md.append(f"- {m}: true={ms_true.get(m,0)} | false={ms_false.get(m,0)}")
    (REPORTS_DIR / "task2_compare_summary.md").write_text("\n".join(md), encoding="utf-8")

    print("OK generate_task2_outputs (partial=" + str(rpt_false is None) + ")")

if __name__ == "__main__":
    main()

