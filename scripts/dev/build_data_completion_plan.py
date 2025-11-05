from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

REPORTS = Path("reports")
DEP_MATRIX = max(REPORTS.glob("dependency_matrix_*.csv"))
START = "2025-01-01 00:00:00+08"
END = "2025-02-28 14:09:59+08"

P0_DEPS = ["pump_inlet_pressure", "pump_outlet_pressure"]
P1_DEPS = ["main_pipeline_flow_rate", "pump_flow_rate"]
P2_DEPS = ["pump_frequency", "pump_active_power"]

# load matrix
rows: List[Dict[str,str]] = list(csv.DictReader(DEP_MATRIX.open("r", encoding="utf-8")))

# Aggregate by metric/device
from collections import defaultdict

by_metric_device: Dict[Tuple[str,int,int], Dict[str,int]] = defaultdict(lambda: {"secs_total":0,"secs_match_all":0,"secs_match_all_running":0})
methods_by_metric: Dict[str, set] = defaultdict(set)
for r in rows:
    key = (r["metric_key"], int(r["station_id"]), int(r["device_id"]))
    by_metric_device[key]["secs_total"] = int(r.get("secs_total",0) or 0)
    # keep max across methods for availability signal
    by_metric_device[key]["secs_match_all"] = max(by_metric_device[key]["secs_match_all"], int(r.get("secs_match_all",0) or 0))
    by_metric_device[key]["secs_match_all_running"] = max(by_metric_device[key]["secs_match_all_running"], int(r.get("secs_match_all_running",0) or 0))
    methods_by_metric[r["metric_key"]].add(r["method_id"])

# a) High priority completion targets
p0_targets = []
p1_targets = []
p2_targets = []
for (metric, sid, did), v in by_metric_device.items():
    # If secs_match_all == 0 for metrics that depend on P0 deps, mark device as needing P0
    if any(x in metric for x in ["head","pressure"]):
        if v["secs_match_all"] == 0:
            p0_targets.append({"station_id":sid, "device_id":did, "metric":metric})
    # Heuristic for P1/P2 consumers
    if "flow" in metric:
        if v["secs_match_all"] == 0:
            p1_targets.append({"station_id":sid, "device_id":did, "metric":metric})
    if any(x in metric for x in ["frequency","power","torque","speed","efficiency"]):
        if v["secs_match_all"] == 0:
            p2_targets.append({"station_id":sid, "device_id":did, "metric":metric})

# b) Pilot windows: deps_available>0 but running=0 (适合验证 filter_running 影响)
pilots = []
for (metric, sid, did), v in by_metric_device.items():
    if v["secs_match_all"] >= 3600 and v["secs_match_all_running"] == 0:
        pilots.append({
            "station_id": sid,
            "device_id": did,
            "metric": metric,
            "start_time": "2025-02-28 02:00:00+08",
            "end_time": "2025-02-28 04:00:00+08"
        })
# take Top-N
pilots = pilots[:20]

# c) Phase suggestion
summary = {
    "phases": [
        {
            "name": "phase-1",
            "goal": "试点设备/时段（预期成功率 ≥20%）",
            "criteria": "依赖交集≥10%，或 pilots 列表中的设备/窗口（关闭运行过滤）",
            "actions": [
                {"cmd": "python -m app.cli.main missing-metrics:compute --start '2025-02-28 02:00:00+08' --end '2025-02-28 04:00:00+08' --window-hours 1 --concurrency 2 --no-filter-running --no-filter-quality --dry-run"}
            ]
        },
        {
            "name": "phase-2",
            "goal": "扩大范围（预期成功率 ≥10%）",
            "actions": [
                {"cmd": "python -m app.cli.main presence:compute --start '2025-01-01 00:00:00+08' --end '2025-02-28 23:59:59+08' --rebuild"},
                {"cmd": "python -m app.cli.main missing-metrics:compute --start '2025-01-01 00:00:00+08' --end '2025-02-28 14:09:59+08' --window-hours 1 --concurrency 2 --no-filter-quality --dry-run"}
            ]
        },
        {
            "name": "phase-3",
            "goal": "全量覆盖（预期成功率 ≥5%）",
            "actions": [
                {"cmd": "python -m app.cli.main missing-metrics:compute --start '2025-01-01 00:00:00+08' --end '2025-02-28 14:09:59+08' --window-hours 1 --concurrency 3 --dry-run"}
            ]
        }
    ]
}

plan = {
    "time_range": {"start": START, "end": END},
    "priorities": {
        "P0": {"dependencies": P0_DEPS, "targets": p0_targets},
        "P1": {"dependencies": P1_DEPS, "targets": p1_targets},
        "P2": {"dependencies": P2_DEPS, "targets": p2_targets}
    },
    "pilot_windows": pilots,
    "summary": summary
}

(REPORTS / "data_completion_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

# write markdown companion
lines = [
    "# 数据补齐与试点计划",
    f"时间范围：{START} ~ {END}",
    "",
    "## 高优先级（P0/P1/P2）",
    f"- P0 依赖：{', '.join(P0_DEPS)}",
    f"- P1 依赖：{', '.join(P1_DEPS)}",
    f"- P2 依赖：{', '.join(P2_DEPS)}",
    "",
    "### P0 目标（示例 Top-20）",
]
for t in p0_targets[:20]:
    lines.append(f"- ({t['station_id']},{t['device_id']}) {t['metric']}")
lines.extend(["", "### 试点窗口（Top-20）"])
for p in pilots:
    lines.append(f"- ({p['station_id']},{p['device_id']}) {p['metric']} {p['start_time']} ~ {p['end_time']}")

(REPORTS / "data_completion_plan.md").write_text("\n".join(lines), encoding="utf-8")

print("OK build_data_completion_plan")

