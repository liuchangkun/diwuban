from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.config.loader import Settings


def _validate_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    stations = data.get("stations")
    if not isinstance(stations, list) or not stations:
        errors.append("缺少 stations 列表或格式不正确")
        return {"errors": errors, "warnings": warnings}
    for si, s in enumerate(stations):
        name = (s or {}).get("name")
        if not name:
            errors.append(f"stations[{si}] 缺少 name")
        devices = (s or {}).get("devices")
        if not isinstance(devices, list) or not devices:
            errors.append(f"stations[{si}] 缺少 devices 列表")
            continue
        for di, d in enumerate(devices):
            dname = (d or {}).get("name")
            if not dname:
                errors.append(f"stations[{si}].devices[{di}] 缺少 name")
            metrics = (d or {}).get("metrics")
            if not isinstance(metrics, list) or not metrics:
                errors.append(f"stations[{si}].devices[{di}] 缺少 metrics 列表")
                continue
            for mi, m in enumerate(metrics):
                key = (m or {}).get("key")
                files = (m or {}).get("files")
                if not key:
                    errors.append(
                        f"stations[{si}].devices[{di}].metrics[{mi}] 缺少 key"
                    )
                if not isinstance(files, list) or not files:
                    errors.append(
                        f"stations[{si}].devices[{di}].metrics[{mi}] 缺少 files 列表"
                    )
                else:
                    for fi, f in enumerate(files):
                        if not isinstance(f, str) or not f.strip():
                            errors.append(
                                f"stations[{si}].devices[{di}].metrics[{mi}].files[{fi}] 不是有效的字符串路径"
                            )
    return {"errors": errors, "warnings": warnings}


def check_mapping_paths(settings: Settings, mapping_path: Path) -> Dict[str, Any]:
    """只读一致性检查：
    - 结构检查：stations/devices/metrics/files/key/name 必填项
    - 路径是否带 data/ 前缀（建议移除，路径应为相对 base_dir）
    - 严格规则下（base_dir + 相对路径）文件是否存在
    - 给出修正建议（不修改任何文件）
    - 统计缺陷（路径类）按站点/设备/指标聚类的计数
    返回报告字典，CLI 负责渲染。
    """
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    base_dir = Path(settings.ingest.base_dir)

    schema_report = _validate_schema(data)

    found: List[Dict[str, Any]] = []
    group_station: Dict[str, Dict[str, int]] = {}
    group_device: Dict[str, Dict[str, int]] = {}
    group_metric: Dict[str, Dict[str, int]] = {}

    stations = data.get("stations") or []
    for s in stations:
        station_name = str((s or {}).get("name") or "").strip()
        for d in (s or {}).get("devices", []) or []:
            device_name = str((d or {}).get("name") or "").strip()
            for m in (d or {}).get("metrics", []) or []:
                metric_key = str((m or {}).get("key") or "").strip()
                for p in (m or {}).get("files", []) or []:
                    if not isinstance(p, str):
                        continue
                    p_norm = p.replace("\\", "/").strip()
                    if not p_norm:
                        continue
                    has_data_prefix = p_norm.startswith("data/")
                    strict_path = base_dir / Path(p)
                    exists_strict = strict_path.exists()
                    suggestion = None
                    expected_path = None
                    if has_data_prefix:
                        rel = p_norm[len("data/") :]
                        expected_path = base_dir / rel
                        suggestion = (
                            f"将映射中的路径从 '{p}' 改为 '{rel}'（相对 base_dir）"
                        )
                    item = {
                        "station": station_name,
                        "device": device_name,
                        "metric_key": metric_key,
                        "path": p,
                        "has_data_prefix": has_data_prefix,
                        "strict_full_path": str(strict_path),
                        "exists_under_strict_rule": exists_strict,
                        "expected_full_path": (
                            str(expected_path) if expected_path else None
                        ),
                        "suggestion": suggestion,
                    }
                    found.append(item)
                    # 聚类统计（路径类缺陷）
                    st = station_name or "<未命名站点>"
                    dv = device_name or "<未命名设备>"
                    mk = metric_key or "<未命名指标>"
                    # station 维度
                    agg = group_station.setdefault(
                        st, {"paths": 0, "missing_files": 0, "with_data_prefix": 0}
                    )
                    agg["paths"] += 1
                    if not exists_strict:
                        agg["missing_files"] += 1
                    if has_data_prefix:
                        agg["with_data_prefix"] += 1
                    # device 维度（key 采用 station|device）
                    dev_key = f"{st}|{dv}"
                    agg = group_device.setdefault(
                        dev_key, {"paths": 0, "missing_files": 0, "with_data_prefix": 0}
                    )
                    agg["paths"] += 1
                    if not exists_strict:
                        agg["missing_files"] += 1
                    if has_data_prefix:
                        agg["with_data_prefix"] += 1
                    # metric 维度（key 采用 station|device|metric）
                    met_key = f"{st}|{dv}|{mk}"
                    agg = group_metric.setdefault(
                        met_key, {"paths": 0, "missing_files": 0, "with_data_prefix": 0}
                    )
                    agg["paths"] += 1
                    if not exists_strict:
                        agg["missing_files"] += 1
                    if has_data_prefix:
                        agg["with_data_prefix"] += 1

    # 扁平化聚类结果，便于阅读
    def _flat_station() -> List[Dict[str, Any]]:
        return [
            {"station": k, **v}
            for k, v in sorted(
                group_station.items(),
                key=lambda x: (-x[1]["missing_files"], -x[1]["with_data_prefix"]),
            )
        ]

    def _flat_device() -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for k, v in group_device.items():
            st, dv = k.split("|", 1)
            out.append({"station": st, "device": dv, **v})
        return sorted(out, key=lambda x: (-x["missing_files"], -x["with_data_prefix"]))

    def _flat_metric() -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for k, v in group_metric.items():
            st, dv, mk = k.split("|", 2)
            out.append({"station": st, "device": dv, "metric_key": mk, **v})
        return sorted(out, key=lambda x: (-x["missing_files"], -x["with_data_prefix"]))

    report = {
        "base_dir": str(base_dir),
        "total_paths": len(found),
        "with_data_prefix": sum(1 for x in found if x["has_data_prefix"]),
        "exists_under_strict_rule": sum(
            1 for x in found if x["exists_under_strict_rule"]
        ),
        "schema": schema_report,
        "items": found,
        "group_by_station": _flat_station(),
        "group_by_device": _flat_device(),
        "group_by_metric": _flat_metric(),
    }
    return report
