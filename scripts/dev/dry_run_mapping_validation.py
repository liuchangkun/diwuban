#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
干跑（dry-run）校验：基于 config/data_mapping.json 生成将要写入的维度/映射概览，不对数据库进行任何写入。
- 输出：站点数量、设备数量、去重后的 metric_key 数量；每个站点/设备的 metric_key 概览
- 约束：
  * 严禁从 CSV 文件名/路径反推出站点/设备/指标语义（仅用于 source_hint）
  * dim_devices.type 取 data_mapping.json 的 type[0]
  * dim_devices.pump_type 取 pump_type[0]；若 type != 'pump' 则为 None
用法：
  python scripts/dev/dry_run_mapping_validation.py
可选：设置环境变量 DRY_RUN_LIMIT（默认显示前 10 条详细映射）
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "config" / "data_mapping.json"


def load_mapping() -> Dict:
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect(mapping: Dict) -> Tuple[int, int, int, List[Tuple[str, str, str]]]:
    stations = list(mapping.keys())
    mapping_rows: List[Tuple[str, str, str]] = []
    metrics_set = set()
    device_count = 0
    for station_name, devices in mapping.items():
        if not isinstance(devices, dict):
            continue
        for device_name, attrs in devices.items():
            device_count += 1
            # 采集 metric_key（除 type/pump_type 外）
            for key, value in (attrs or {}).items():
                if key in ("type", "pump_type"):
                    continue
                metrics_set.add(key)
                mapping_rows.append((station_name, device_name, key))
    return len(stations), device_count, len(metrics_set), mapping_rows


def device_type(attrs: Dict) -> Tuple[str, str | None]:
    t = (attrs or {}).get("type") or []
    p = (attrs or {}).get("pump_type") or []
    type_val = t[0] if t else ""
    pump_type_val = p[0] if p else None
    if type_val != "pump":
        pump_type_val = None
    return type_val, pump_type_val


def main() -> int:
    limit = int(os.getenv("DRY_RUN_LIMIT", "10"))
    data = load_mapping()
    s_cnt, d_cnt, m_cnt, rows = collect(data)

    print("[dry-run] 站点数:", s_cnt)
    print("[dry-run] 设备数:", d_cnt)
    print("[dry-run] 指标(metric_key)数:", m_cnt)
    print("[dry-run] 示例映射（前 %d 条）：" % limit)
    for i, (s, d, k) in enumerate(rows[:limit], 1):
        attrs = data.get(s, {}).get(d, {})
        t, pt = device_type(attrs)
        print(
            f"  {i:02d}. station='{s}' device='{d}' type='{t}' pump_type='{pt}' metric_key='{k}'"
        )

    # 规则提示
    print(
        "\n[contract] 仅以 data_mapping.json 定义维度/指标；禁止从 CSV 文件名/路径推断语义。"
    )
    print("[contract] dim_devices.type=type[0]；非 pump 的 pump_type=null。")
    print(
        "[contract] 推荐先完成 dim_* 与 dim_mapping_items，再加载 CSV 并调用 safe_upsert_* 对齐入库。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
