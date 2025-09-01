from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.adapters.db import get_conn
from app.adapters.db.gateway import (
    get_device_metrics_by_time_range,
    get_station_devices_metrics_by_time_range,
)
from app.core.config.loader_new import load_settings
from app.schemas.data import TimeSeriesResponse

router = APIRouter()
settings = load_settings(Path("configs"))
logger = structlog.get_logger("api.data.timeseries")


# 辅助函数：递归将对象转换为可 JSON 序列化的基本类型
# - Decimal -> float
# - datetime/date -> ISO 字符串
# - dict/list/tuple -> 递归处理
# 这样可以避免 format=wide 直接透传 metrics_data 时包含 Decimal 导致 FastAPI/JSON 序列化失败
# 注意：保留 None；其他类型原样返回（由 FastAPI 进一步处理）
def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return datetime.combine(obj, datetime.min.time()).isoformat()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


@router.get("/measurements", response_model=TimeSeriesResponse)
async def get_measurements(
    request: Request,
    station_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> TimeSeriesResponse:
    # 已废弃端点：为避免与新端点重复，统一返回 410，并提示替代接口
    raise HTTPException(
        status_code=410,
        detail=(
            "该端点已废弃，请使用 /api/v1/data/stations/{station_id}/measurements 或 "
            "/api/v1/data/devices/{device_id}/measurements 或 /api/v1/data/stations/{station_id}/raw"
        ),
    )

    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")

    try:
        with get_conn(settings) as conn:
            data: List[Dict[str, Any]] = []
            if device_id:
                # 单设备：调用数据库时间范围函数
                with conn.cursor() as cur:
                    # 说明：数据库函数目前不支持 offset 参数，这里采用“函数内部 limit = offset+limit”+ 外层 OFFSET/LIMIT 策略
                    # 首先以 probe 查询获取 total_count（避免当页为空时无法读取 total）
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(total_records), 0)
                        FROM public.get_device_metrics_by_time_range(%(device_id)s, %(start_ts)s, %(end_ts)s, %(probe_limit)s)
                        """,
                        {
                            "device_id": int(device_id),
                            "start_ts": start_time,
                            "end_ts": end_time,
                            "probe_limit": 1,
                        },
                    )
                    total = int(cur.fetchone()[0] or 0)

                    # 分页查询：内部 limit = offset+limit，外层 OFFSET/LIMIT
                    cur.execute(
                        """
                        SELECT record_timestamp, metrics_data, total_records
                        FROM public.get_device_metrics_by_time_range(%(device_id)s, %(start_ts)s, %(end_ts)s, %(inner_limit)s)
                        OFFSET %(offset)s LIMIT %(limit)s
                        """,
                        {
                            "device_id": int(device_id),
                            "start_ts": start_time,
                            "end_ts": end_time,
                            "inner_limit": int(offset) + int(limit),
                            "offset": int(offset),
                            "limit": int(limit),
                        },
                    )
                    rows_raw = cur.fetchall()
                for ts, metrics, _total in rows_raw:
                    flow = (metrics.get("main_pipeline_flow_rate", {}) or {}).get(
                        "value"
                    )
                    pressure = (
                        metrics.get("main_pipeline_outlet_pressure", {}) or {}
                    ).get("value")
                    power = (metrics.get("pump_active_power", {}) or {}).get("value")
                    freq = (metrics.get("pump_frequency", {}) or {}).get("value")
                    pump_q = (metrics.get("pump_flow_rate", {}) or {}).get("value")
                    pump_h = (metrics.get("pump_head", {}) or {}).get("value")
                    data.append(
                        {
                            "timestamp": ts.isoformat() if ts else None,
                            "device_id": device_id,
                            "device_name": None,
                            "flow_rate": float(flow) if flow is not None else None,
                            "pressure": (
                                float(pressure) if pressure is not None else None
                            ),
                            "power": float(power) if power is not None else None,
                            "frequency": float(freq) if freq is not None else None,
                            "pump_flow_rate": (
                                float(pump_q) if pump_q is not None else None
                            ),
                            "pump_head": float(pump_h) if pump_h is not None else None,
                            "pump_voltage_a": None,
                            "pump_voltage_b": None,
                            "pump_voltage_c": None,
                            "pump_current_a": None,
                            "pump_current_b": None,
                            "pump_current_c": None,
                            "pump_power_factor": None,
                        }
                    )
                # total_count：使用上面的 probe 查询结果 total
                return TimeSeriesResponse(
                    data=data,
                    total_count=total,
                    query_time_ms=0.0,
                    has_more=(offset + limit) < total,
                )
            elif station_id:
                # 站点：调用站点维度时间范围函数（小窗）
                with get_conn(settings) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT record_timestamp, metrics_data, total_records
                            FROM public.get_station_devices_metrics_by_time_range(%(station_id)s, %(start_ts)s, %(end_ts)s, %(limit)s)
                            """,
                            {
                                "station_id": int(station_id),
                                "start_ts": start_time,
                                "end_ts": end_time,
                                "limit": int(limit),
                            },
                        )
                        rows_raw = cur.fetchall()
                for ts, metrics, _total in rows_raw:
                    for dev, dev_metrics in (metrics or {}).items():
                        flow = (
                            dev_metrics.get("main_pipeline_flow_rate", {}) or {}
                        ).get("value")
                        pressure = (
                            dev_metrics.get("main_pipeline_outlet_pressure", {}) or {}
                        ).get("value")
                        power = (dev_metrics.get("pump_active_power", {}) or {}).get(
                            "value"
                        )
                        freq = (dev_metrics.get("pump_frequency", {}) or {}).get(
                            "value"
                        )
                        pump_q = (dev_metrics.get("pump_flow_rate", {}) or {}).get(
                            "value"
                        )
                        pump_h = (dev_metrics.get("pump_head", {}) or {}).get("value")
                        data.append(
                            {
                                "timestamp": ts.isoformat() if ts else None,
                                "device_id": str(dev),
                                "device_name": None,
                                "flow_rate": float(flow) if flow is not None else None,
                                "pressure": (
                                    float(pressure) if pressure is not None else None
                                ),
                                "power": float(power) if power is not None else None,
                                "frequency": float(freq) if freq is not None else None,
                                "pump_flow_rate": (
                                    float(pump_q) if pump_q is not None else None
                                ),
                                "pump_head": (
                                    float(pump_h) if pump_h is not None else None
                                ),
                                "pump_voltage_a": None,
                                "pump_voltage_b": None,
                                "pump_voltage_c": None,
                                "pump_current_a": None,
                                "pump_current_b": None,
                                "pump_current_c": None,
                                "pump_power_factor": None,
                            }
                        )
                return TimeSeriesResponse(
                    data=data,
                    total_count=len(data),
                    query_time_ms=0.0,
                    has_more=False,
                )
            else:
                raise HTTPException(
                    status_code=400, detail="必须提供 station_id 或 device_id 之一"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("时间范围函数调用失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.get("/stations/{station_id}/measurements", response_model=TimeSeriesResponse)
async def get_station_measurements(
    request: Request,
    station_id: int,
    start_time: datetime = Query(..., description="开始时间（UTC或本地时间，建议UTC）"),
    end_time: datetime = Query(..., description="结束时间（必须大于开始时间）"),
    device_ids: Optional[List[int]] = Query(None, description="设备ID列表（可选）"),
    metric_ids: Optional[List[int]] = Query(None, description="指标ID列表（可选）"),
    granularity: str = Query("auto", description="粒度：auto|hourly|daily"),
    limit: int = Query(1000, ge=1, le=10000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> TimeSeriesResponse:
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    try:
        with get_conn(settings) as conn:
            rows = get_station_devices_metrics_by_time_range(
                conn=conn,
                station_id=station_id,
                start_utc=start_time,
                end_utc=end_time,
                device_ids=device_ids,
                metric_ids=metric_ids,
                granularity=granularity,
            )
            dev_ids = sorted({r["device_id"] for r in rows})
            met_ids = sorted({r["metric_id"] for r in rows})
            devices_map: Dict[int, str] = {}
            metrics_map: Dict[int, Dict[str, Optional[str]]] = {}
            if dev_ids:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, name FROM public.dim_devices WHERE id = ANY(%s)",
                        (dev_ids,),
                    )
                    for d_id, d_name in cur.fetchall():
                        devices_map[int(d_id)] = d_name
            if met_ids:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, metric_key,
                               COALESCE(NULLIF(unit_display,''), unit) AS unit
                        FROM public.dim_metric_config WHERE id = ANY(%s)
                        """,
                        (met_ids,),
                    )
                    for m_id, m_key, m_unit in cur.fetchall():
                        metrics_map[int(m_id)] = {"metric_key": m_key, "unit": m_unit}
        from app.utils.data_mapping import map_metrics_meta

        data = map_metrics_meta(
            rows, devices_map, metrics_map, offset=offset, limit=limit
        )
        return TimeSeriesResponse(
            data=data,
            metadata={
                "station_id": station_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "granularity": granularity,
                "device_ids": dev_ids,
                "metric_ids": met_ids,
            },
            total_count=len(rows),
            query_time_ms=0.0,
            has_more=(offset + limit) < len(rows),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("泵站汇总指标查询失败", station_id=station_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/measurements", response_model=TimeSeriesResponse)
async def get_device_measurements(
    request: Request,
    device_id: int,
    start_time: datetime = Query(..., description="开始时间（UTC或本地时间，建议UTC）"),
    end_time: datetime = Query(..., description="结束时间（必须大于开始时间）"),
    metric_ids: Optional[List[int]] = Query(None, description="指标ID列表（可选）"),
    granularity: str = Query("auto", description="粒度：auto|hourly|daily"),
    limit: int = Query(1000, ge=1, le=10000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> TimeSeriesResponse:
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    try:
        with get_conn(settings) as conn:
            rows = get_device_metrics_by_time_range(
                conn=conn,
                device_id=device_id,
                start_utc=start_time,
                end_utc=end_time,
                metric_ids=metric_ids,
                granularity=granularity,
            )
            dev_ids = sorted({r["device_id"] for r in rows})
            met_ids = sorted({r["metric_id"] for r in rows})
            devices_map: Dict[int, str] = {}
            metrics_map: Dict[int, Dict[str, Optional[str]]] = {}
            if dev_ids:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, name FROM public.dim_devices WHERE id = ANY(%s)",
                        (dev_ids,),
                    )
                    for d_id, d_name in cur.fetchall():
                        devices_map[int(d_id)] = d_name
            if met_ids:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, metric_key,
                               COALESCE(NULLIF(unit_display,''), unit) AS unit
                        FROM public.dim_metric_config WHERE id = ANY(%s)
                        """,
                        (met_ids,),
                    )
                    for m_id, m_key, m_unit in cur.fetchall():
                        metrics_map[int(m_id)] = {"metric_key": m_key, "unit": m_unit}
        from app.utils.data_mapping import map_metrics_meta

        data = map_metrics_meta(
            rows, devices_map, metrics_map, offset=offset, limit=limit
        )
        return TimeSeriesResponse(
            data=data,
            metadata={
                "device_id": device_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "granularity": granularity,
                "metric_ids": met_ids,
            },
            total_count=len(rows),
            query_time_ms=0.0,
            has_more=(offset + limit) < len(rows),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("设备汇总指标查询失败", device_id=device_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stations/{station_id}/raw", response_model=TimeSeriesResponse)
async def get_station_raw(
    request: Request,
    station_id: int,
    start_time: datetime = Query(..., description="开始时间（UTC或本地时间，建议UTC）"),
    end_time: datetime = Query(..., description="结束时间（必须大于开始时间）"),
    limit: int = Query(1000, ge=1, le=10000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    format: str = Query("wide", description="返回格式：wide|long"),
) -> TimeSeriesResponse:
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    if format not in {"wide", "long"}:
        raise HTTPException(status_code=400, detail="format 仅支持 wide/long")
    try:
        data: List[Dict[str, Any]] = []
        with get_conn(settings) as conn:
            # 先探针 total
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(total_records), 0)
                    FROM public.get_station_devices_metrics_by_time_range(%(station_id)s, %(start_ts)s, %(end_ts)s, %(probe_limit)s)
                    """,
                    {
                        "station_id": int(station_id),
                        "start_ts": start_time,
                        "end_ts": end_time,
                        "probe_limit": 1,
                    },
                )
                total = int(cur.fetchone()[0] or 0)
            # 拉取当前页（函数内扩大 limit，外层做 OFFSET/LIMIT）
            with get_conn(settings) as conn2:
                with conn2.cursor() as cur:
                    cur.execute(
                        """
                        SELECT record_timestamp, metrics_data, total_records
                        FROM public.get_station_devices_metrics_by_time_range(%(station_id)s, %(start_ts)s, %(end_ts)s, %(inner_limit)s)
                        OFFSET %(offset)s LIMIT %(limit)s
                        """,
                        {
                            "station_id": int(station_id),
                            "start_ts": start_time,
                            "end_ts": end_time,
                            "inner_limit": int(offset) + int(limit),
                            "offset": int(offset),
                            "limit": int(limit),
                        },
                    )
                    rows_raw = cur.fetchall()
        # 根据 format 构造 data（与前端预期保持一致）
        if format == "wide":
            # 宽表：透传 record_timestamp + metrics_data（递归转为 JSON 可序列化）
            data = [
                {
                    "record_timestamp": (ts.isoformat() if ts else None),
                    "metrics_data": _to_jsonable(metrics or {}),
                }
                for ts, metrics, _t in rows_raw
            ]
        else:
            # 长表：展平成 {ts, metric, value}
            # 兼容两种结构：
            # 1) 扁平：{ "设备名_指标": 数值 }
            # 2) 分层：{ "设备名": { "指标": 数值或{value:数值} } }
            data = []
            for ts, metrics, _t in rows_raw:
                metrics = metrics or {}
                for k, v in metrics.items():
                    if isinstance(v, dict) and not ("value" in v and len(v) <= 3):
                        # 分层场景：k=设备名，v=该设备下的指标字典
                        for subk, subv in (v or {}).items():
                            val = subv.get("value") if isinstance(subv, dict) else subv
                            try:
                                val = float(val) if val is not None else None
                            except Exception:
                                val = None
                            ts_str = ts.isoformat() if ts else None
                            metric_label = f"{k}_{subk}"
                            data.append(
                                {
                                    "ts": ts_str,
                                    "timestamp": ts_str,  # 兼容旧前端
                                    "metric": metric_label,
                                    "metric_key": metric_label,  # 兼容旧前端
                                    "value": val,
                                }
                            )
                    else:
                        # 扁平或 {value:x}
                        val = v.get("value") if isinstance(v, dict) else v
                        try:
                            val = float(val) if val is not None else None
                        except Exception:
                            val = None
                        data.append(
                            {
                                "ts": ts.isoformat() if ts else None,
                                "metric": k,
                                "value": val,
                            }
                        )

        return TimeSeriesResponse(
            data=data,
            metadata={
                "station_id": station_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "format": format,
            },
            total_count=total,
            query_time_ms=0.0,
            has_more=(offset + limit) < total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("站点原始数据查询失败", station_id=station_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/raw", response_model=TimeSeriesResponse)
async def get_device_raw(
    request: Request,
    device_id: int,
    start_time: datetime = Query(..., description="开始时间（UTC或本地时间，建议UTC）"),
    end_time: datetime = Query(..., description="结束时间（必须大于开始时间）"),
    limit: int = Query(1000, ge=1, le=10000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    format: str = Query("wide", description="返回格式：wide|long"),
) -> TimeSeriesResponse:
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    if format not in {"wide", "long"}:
        raise HTTPException(status_code=400, detail="format 仅支持 wide/long")
    try:
        data: List[Dict[str, Any]] = []
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # total 探针
                cur.execute(
                    """
                    SELECT COALESCE(MAX(total_records), 0)
                    FROM public.get_device_metrics_by_time_range(%(device_id)s, %(start_ts)s, %(end_ts)s, %(probe_limit)s)
                    """,
                    {
                        "device_id": int(device_id),
                        "start_ts": start_time,
                        "end_ts": end_time,
                        "probe_limit": 1,
                    },
                )
                total = int(cur.fetchone()[0] or 0)
            # 当前页
            with get_conn(settings) as conn2:
                with conn2.cursor() as cur:
                    cur.execute(
                        """
                        SELECT record_timestamp, metrics_data, total_records
                        FROM public.get_device_metrics_by_time_range(%(device_id)s, %(start_ts)s, %(end_ts)s, %(inner_limit)s)
                        OFFSET %(offset)s LIMIT %(limit)s
                        """,
                        {
                            "device_id": int(device_id),
                            "start_ts": start_time,
                            "end_ts": end_time,
                            "inner_limit": int(offset) + int(limit),
                            "offset": int(offset),
                            "limit": int(limit),
                        },
                    )
                    rows_raw = cur.fetchall()
        # 与站点 raw 统一：
        if format == "wide":
            # 直接透传 record_timestamp + metrics_data（递归转为 JSON 可序列化，避免 Decimal/日期对象导致序列化失败）
            data = [
                {
                    "record_timestamp": (ts.isoformat() if ts else None),
                    "metrics_data": _to_jsonable(metrics or {}),
                }
                for ts, metrics, _t in rows_raw
            ]
        else:
            # 长表：展平成 {ts, metric, value}；兼容扁平与分层
            data = []
            for ts, metrics, _t in rows_raw:
                metrics = metrics or {}
                for k, v in metrics.items():
                    if isinstance(v, dict) and not ("value" in v and len(v) <= 3):
                        for subk, subv in (v or {}).items():
                            val = subv.get("value") if isinstance(subv, dict) else subv
                            try:
                                val = float(val) if val is not None else None
                            except Exception:
                                val = None
                            data.append(
                                {
                                    "ts": ts.isoformat() if ts else None,
                                    "metric": f"{k}_{subk}",
                                    "value": val,
                                }
                            )
                    else:
                        val = v.get("value") if isinstance(v, dict) else v
                        try:
                            val = float(val) if val is not None else None
                        except Exception:
                            val = None
                        data.append(
                            {
                                "ts": ts.isoformat() if ts else None,
                                "metric": k,
                                "value": val,
                            }
                        )

        return TimeSeriesResponse(
            data=data,
            metadata={
                "device_id": device_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "format": format,
            },
            total_count=total,
            query_time_ms=0.0,
            has_more=(offset + limit) < total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("设备原始数据查询失败", device_id=device_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
