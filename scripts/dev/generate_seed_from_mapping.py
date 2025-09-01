#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 config/data_mapping.json 生成维表与映射快照的 SQL 脚本（不直接写库）。
输出：scripts/dev/seed_from_mapping.sql
严格遵循文档约束：
- 以 data_mapping.json 作为唯一配置来源；禁止从 CSV 文件名/路径反推语义（仅作 source_hint）
- dim_devices.type=type[0]；若 type != 'pump'，pump_type=null
- 为出现过的 metric_key 生成 dim_metric_config（缺省单位按规则映射，未知项留空）
- 为每个(站点,设备,metric_key)生成 dim_mapping_items 快照，source_hint='data_mapping.json'
运行：python scripts/dev/generate_seed_from_mapping.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set

ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "config" / "data_mapping.json"
OUT_SQL = ROOT / "scripts" / "dev" / "seed_from_mapping.sql"

ALLOWED_DEVICE_TYPES = {"pump", "main_pipeline"}
ALLOWED_PUMP_TYPES = {"variable_frequency", "soft_start"}

# 已知 metric 的默认单位（可按需扩展/调整）
DEFAULT_UNITS = {
    "frequency": ("Hz", "Hz"),
    "voltage_a": ("V", "V"),
    "voltage_b": ("V", "V"),
    "voltage_c": ("V", "V"),
    "current_a": ("A", "A"),
    "current_b": ("A", "A"),
    "current_c": ("A", "A"),
    "power": ("kW", "kW"),  # 如源为 W，可后续统一换算
    "kwh": ("kWh", "kWh"),
    "power_factor": ("", ""),
    "pressure": ("MPa", "MPa"),  # 或 kPa，需保持一致
    "flow_rate": ("m3/h", "m3/h"),  # 或 L/s，需保持一致
    "cumulative_flow": ("m3", "m3"),
}


def load_mapping() -> Dict[str, Dict[str, Dict[str, Any]]]:
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_all_metric_keys(mapping: Dict[str, Dict[str, Dict[str, Any]]]) -> Set[str]:
    keys: Set[str] = set()
    for station_name, devices in mapping.items():
        if not isinstance(devices, dict):
            continue
        for device_name, attrs in devices.items():
            if not isinstance(attrs, dict):
                continue
            for key in attrs.keys():
                if key in ("type", "pump_type"):
                    continue
                keys.add(key)
    return keys


def sql_quote(s: str) -> str:
    return s.replace("'", "''")


def gen_sql(mapping: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    lines: list[str] = []
    ap = lines.append
    ap("-- Auto-generated from config/data_mapping.json")
    ap("SET client_encoding TO 'UTF8';")
    ap("-- Do not edit manually. UTF-8, LF newlines.")
    ap("\\set ON_ERROR_STOP 1")
    ap("BEGIN;")

    # 1) 站点 upsert（按 name）
    for station_name in mapping.keys():
        s = sql_quote(station_name)
        ap(
            """
INSERT INTO public.dim_stations(name)
SELECT '{name}'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_stations WHERE name='{name}'
);
            """.strip().format(
                name=s
            )
        )

    # 2) 设备 upsert（type/pump_type 来自映射；非 pump 的 pump_type=null）
    for station_name, devices in mapping.items():
        s_name = sql_quote(station_name)
        for device_name, attrs in (devices or {}).items():
            if not isinstance(attrs, dict):
                continue
            dev_type_list = attrs.get("type") or []
            dev_type_raw = dev_type_list[0] if dev_type_list else ""
            dev_type = (dev_type_raw or "").strip().lower()
            if dev_type not in ALLOWED_DEVICE_TYPES:
                # 尽量容错：将大小写/驼峰写法归一（如 Main_pipeline → main_pipeline）
                if dev_type_raw and dev_type_raw.strip().lower() == "main_pipeline":
                    dev_type = "main_pipeline"
                else:
                    dev_type = dev_type  # 保持原状（若为空将导致 NOT NULL/CK 失败，提示修正 mapping）
            pump_type_list = attrs.get("pump_type") or []
            pump_type_raw = pump_type_list[0] if pump_type_list else None
            pump_type_norm = (
                (pump_type_raw or "").strip().lower()
                if pump_type_raw is not None
                else None
            )
            pump_type = (
                pump_type_norm
                if (dev_type == "pump" and pump_type_norm in ALLOWED_PUMP_TYPES)
                else None
            )
            d_name = sql_quote(device_name)
            ap(
                """
WITH s AS (
  SELECT id FROM public.dim_stations WHERE name='{s_name}' LIMIT 1
)
INSERT INTO public.dim_devices(station_id, name, type, pump_type)
SELECT s.id, '{d_name}', '{dev_type}', {pump_type_sql}
FROM s
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_devices d WHERE d.station_id=s.id AND d.name='{d_name}'
);
                """.strip().format(
                    s_name=s_name,
                    d_name=d_name,
                    dev_type=sql_quote(dev_type),
                    pump_type_sql=(
                        "NULL"
                        if pump_type is None
                        else "'{}'".format(sql_quote(pump_type))
                    ),
                )
            )

    # 3) 指标配置（去重）
    all_keys = sorted(collect_all_metric_keys(mapping))
    if all_keys:
        ap("-- dim_metric_config upsert")
        for key in all_keys:
            unit, unit_display = DEFAULT_UNITS.get(key, ("", ""))
            ap(
                """
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, decimals_policy)
SELECT '{k}', '{u}', '{ud}', 'as_is'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config m WHERE m.metric_key='{k}'
);
                """.strip().format(
                    k=sql_quote(key), u=sql_quote(unit), ud=sql_quote(unit_display)
                )
            )

    # 4) 映射快照（为每个站点-设备-指标）
    for station_name, devices in mapping.items():
        s_name = sql_quote(station_name)
        for device_name, attrs in (devices or {}).items():
            if not isinstance(attrs, dict):
                continue
            d_name = sql_quote(device_name)
            metric_keys: Iterable[str] = [
                k for k in attrs.keys() if k not in ("type", "pump_type")
            ]
            for k in metric_keys:
                kq = sql_quote(k)
                ap(
                    """
INSERT INTO public.dim_mapping_items(mapping_hash, station_name, device_name, metric_key, source_hint)
SELECT md5('{s_name}'||'|'||'{d_name}'||'|'||'{kq}')::text, '{s_name}', '{d_name}', '{kq}', 'data_mapping.json'
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_mapping_items WHERE station_name='{s_name}' AND device_name='{d_name}' AND metric_key='{kq}'
);
                    """.strip().format(
                        s_name=s_name, d_name=d_name, kq=kq
                    )
                )

    ap("COMMIT;")
    return "\n".join(lines) + "\n"


def main() -> int:
    mapping = load_mapping()
    sql = gen_sql(mapping)
    OUT_SQL.write_text(sql, encoding="utf-8", newline="\n")
    print(f"[ok] generated: {OUT_SQL.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
