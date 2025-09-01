#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将“字典型”映射文件转换为“标准 schema（stations/devices/metrics/files）”。
- 输入：旧版 data_mapping.json（顶层为站点名 -> 设备名 -> 指标key: [files]）
- 输出：标准 schema 的 JSON 文件（stations 数组）

用法：
  python scripts/tools/convert_mapping_to_standard.py config/data_mapping.json config/data_mapping.v2.json

说明：
- 仅处理 value 为“字符串数组”的键作为指标 files，其他键（如 type/pump_type）作为元数据：
  * device.type 若存在：取字符串或数组第一个元素
  * 其他元数据忽略（不影响导入流程）
- 不更改原始文件；输出为新文件。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _as_str_list(v: Any) -> List[str] | None:
    if isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v):
        return [x.strip() for x in v]
    return None


def _as_first_str(v: Any) -> str | None:
    if isinstance(v, str) and v.strip():
        return v.strip()
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str) and x.strip():
                return x.strip()
    return None


def convert_dict_schema_to_standard(data: Dict[str, Any]) -> Dict[str, Any]:
    stations_out: List[Dict[str, Any]] = []
    # 顶层：站点名
    for station_name, station_val in (data or {}).items():
        if not isinstance(station_val, dict):
            continue
        station_obj: Dict[str, Any] = {"name": str(station_name)}
        devices_out: List[Dict[str, Any]] = []
        # 第二层：设备名
        for device_name, device_val in station_val.items():
            if not isinstance(device_val, dict):
                continue
            device_obj: Dict[str, Any] = {"name": str(device_name)}
            # 提取设备类型（可选）
            dev_type = None
            if "type" in device_val:
                dev_type = _as_first_str(device_val.get("type"))
            if dev_type:
                device_obj["type"] = dev_type
            # 指标列表
            metrics_out: List[Dict[str, Any]] = []
            for k, v in device_val.items():
                if k in ("type", "pump_type"):
                    continue
                files = _as_str_list(v)
                if files:
                    metrics_out.append({"key": str(k), "files": files})
            if metrics_out:
                device_obj["metrics"] = metrics_out
                devices_out.append(device_obj)
        if devices_out:
            station_obj["devices"] = devices_out
            stations_out.append(station_obj)
    return {"stations": stations_out}


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "用法: python scripts/tools/convert_mapping_to_standard.py <输入旧版JSON> <输出新版JSON>"
        )
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = json.loads(src.read_text(encoding="utf-8"))
    converted = convert_dict_schema_to_standard(data)
    dst.write_text(
        json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已生成: {dst}")
    # 简要统计
    stations = converted.get("stations", [])
    total_metrics = 0
    total_files = 0
    for s in stations:
        for d in s.get("devices", []) or []:
            for m in d.get("metrics", []) or []:
                total_metrics += 1
                total_files += len(m.get("files", []) or [])
    print(f"站点: {len(stations)} 指标条目: {total_metrics} 文件数: {total_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
