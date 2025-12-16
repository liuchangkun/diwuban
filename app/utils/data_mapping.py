"""
数据映射与适配工具（公共复用）
- 设备与指标元数据查询（id→name/key/unit）
- 将数据库函数/报表函数结果适配为 API 扁平结构
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def map_metrics_meta(
    rows: Iterable[Dict[str, Any]],
    devices_map: Dict[int, str],
    metrics_map: Dict[int, Dict[str, Optional[str]]],
    offset: int = 0,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    将网关/数据库函数返回的聚合行，映射为前端友好的扁平结构。
    期望 row 字段：ts, station_id, device_id, metric_id, cnt/avg_value/min_value/max_value/sum_value
    """
    data: List[Dict[str, Any]] = []
    rows_list = list(rows)[offset : offset + limit]
    for r in rows_list:
        mmeta = metrics_map.get(int(r["metric_id"]), {})
        data.append(
            {
                "ts": r.get("ts"),
                "station_id": r.get("station_id"),
                "device_id": r.get("device_id"),
                "device_name": (
                    devices_map.get(int(r["device_id"]))
                    if r.get("device_id") is not None
                    else None
                ),
                "metric_id": r.get("metric_id"),
                "metric_key": mmeta.get("metric_key"),
                "unit": mmeta.get("unit"),
                "cnt": r.get("cnt"),
                "avg": r.get("avg_value"),
                "min": r.get("min_value"),
                "max": r.get("max_value"),
                "sum": r.get("sum_value"),
            }
        )
    return data
