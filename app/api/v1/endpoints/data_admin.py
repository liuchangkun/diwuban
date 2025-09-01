from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.adapters.db.gateway import get_conn
from app.api.middleware import DatabaseLoggingMixin
from app.core.config.loader_new import load_settings
from app.models import DeviceSummary, StationSummary
from app.models.metric import MetricInfo
from app.services.data_import import DataImportService

router = APIRouter()
settings = load_settings(Path("configs"))
logger = structlog.get_logger("api.data.admin")


@router.get("/stations", response_model=List[StationSummary])
async def get_stations(request: Request) -> List[StationSummary]:
    """
    获取所有泵站的概览信息
    """
    query_start_time = time.time()

    logger.info(
        "泵站概览查询开始",
        client_ip=request.client.host if request.client else "unknown",
    )

    try:
        stations: List[StationSummary] = []
        sql = """
        WITH last_ts AS (
            SELECT d.station_id, MAX(fm.ts_raw) AS last_data_time
            FROM public.fact_measurements fm
            JOIN public.dim_devices d ON d.id = fm.device_id
            GROUP BY d.station_id
        )
        SELECT v.station_id,
               v.station_name AS name,
               NULL::text AS region,
               'active'::text AS status,
               NULL::numeric AS capacity,
               COUNT(DISTINCT v.device_id) AS device_count,
               lt.last_data_time
        FROM public.station_device_rated_params_view v
        LEFT JOIN last_ts lt ON lt.station_id = v.station_id
        GROUP BY v.station_id, v.station_name, lt.last_data_time
        ORDER BY v.station_id
        """

        sql_exec_time = time.time()
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                sql_duration = (time.time() - sql_exec_time) * 1000
                DatabaseLoggingMixin.log_sql_execution(
                    sql=sql, duration_ms=sql_duration
                )
                rows = cur.fetchall()
                logger.info(
                    "泵站数据查询完成",
                    stations_count=len(rows),
                    duration_ms=round(sql_duration, 2),
                )
                for row in rows:
                    (
                        station_id,
                        name,
                        region,
                        status,
                        capacity,
                        device_count,
                        last_data_time,
                    ) = row
                    stations.append(
                        StationSummary(
                            station_id=str(station_id),
                            name=name,
                            region=region,
                            status=status,
                            device_count=device_count,
                            capacity=capacity,
                            last_data_time=last_data_time,
                        )
                    )
        total_duration = (time.time() - query_start_time) * 1000
        logger.info(
            "泵站概览查询成功",
            stations_returned=len(stations),
            total_duration_ms=round(total_duration, 2),
        )
        return stations
    except Exception as e:
        total_duration = (time.time() - query_start_time) * 1000
        logger.error(
            "泵站概览查询失败",
            error=str(e),
            duration_ms=round(total_duration, 2),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"泵站查询失败: {str(e)}")


@router.get("/stations/{station_id}/devices", response_model=List[DeviceSummary])
async def get_station_devices(station_id: str, request: Request) -> List[DeviceSummary]:
    """
    获取指定泵站的设备信息（彻底方案）
    - 返回 station_name（JOIN station）
    - rated_power 优先取 device_rated_params.param_key='rated_power' 的 value_numeric，其次回退 device.rated_power
    - 兼容当前前端结构
    """
    query_start_time = time.time()
    logger.info(
        "泵站设备查询开始",
        station_id=station_id,
        client_ip=request.client.host if request.client else "unknown",
    )
    try:
        devices: List[DeviceSummary] = []
        sql = """
        SELECT
            v.device_id,
            v.device_name AS name,
            v.device_type AS type,
            v.pump_type,
            'active'::text AS status,
            MAX(CASE WHEN v.rated_param_key = 'rated_power' THEN v.rated_value_numeric END) AS rated_power,
            v.station_name,
            (
                SELECT MAX(fm.ts_raw) FROM public.fact_measurements fm WHERE fm.device_id = v.device_id
            ) AS last_data_time
        FROM public.station_device_rated_params_view v
        WHERE v.station_id = %s::bigint
        GROUP BY v.device_id, v.device_name, v.device_type, v.pump_type, v.station_name
        ORDER BY v.device_id
        """
        sql_exec_time = time.time()
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (station_id,))
                sql_duration = (time.time() - sql_exec_time) * 1000
                DatabaseLoggingMixin.log_sql_execution(
                    sql=sql, params=(station_id,), duration_ms=sql_duration
                )
                rows = cur.fetchall()
                logger.info(
                    "设备数据查询完成",
                    station_id=station_id,
                    devices_count=len(rows),
                    duration_ms=round(sql_duration, 2),
                )
                for row in rows:
                    (
                        device_id,
                        name,
                        device_type,
                        pump_type,
                        status,
                        rated_power,
                        station_name,
                        last_data_time,
                    ) = row
                    devices.append(
                        DeviceSummary(
                            device_id=str(device_id),
                            station_id=str(station_id),
                            name=name,
                            type=device_type,
                            pump_type=pump_type,
                            status=status,
                            rated_power=rated_power,
                            last_data_time=last_data_time,
                            station_name=station_name,
                        )
                    )
        total_duration = (time.time() - query_start_time) * 1000
        logger.info(
            "泵站设备查询成功",
            station_id=station_id,
            devices_returned=len(devices),
            total_duration_ms=round(total_duration, 2),
        )
        return devices
    except Exception as e:
        total_duration = (time.time() - query_start_time) * 1000
        logger.error(
            "泵站设备查询失败",
            station_id=station_id,
            error=str(e),
            duration_ms=round(total_duration, 2),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"设备查询失败: {str(e)}")


@router.get("/stations/{station_id}/statistics")
async def get_station_statistics(
    station_id: str,
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
) -> Dict[str, Any]:
    """获取泵站运行统计信息"""
    try:
        start_time = datetime.now() - timedelta(hours=hours)
        sql = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT fm.device_id) as active_devices,
            AVG(CASE WHEN m.metric_key = 'pump_active_power' THEN fm.value END) as avg_power,
            SUM(CASE WHEN m.metric_key = 'pump_active_power' THEN fm.value END) as total_power,
            AVG(CASE WHEN m.metric_key = 'main_pipeline_flow_rate' THEN fm.value END) as avg_flow_rate,
            SUM(CASE WHEN m.metric_key = 'main_pipeline_flow_rate' THEN fm.value END) as total_flow_rate,
            MIN(fm.ts_raw) as data_start,
            MAX(fm.ts_raw) as data_end
        FROM public.fact_measurements fm
        JOIN public.dim_metric_config m ON m.id = fm.metric_id
        JOIN public.dim_devices d ON d.id = fm.device_id
        WHERE d.station_id = %s AND fm.ts_raw >= %s
        """
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (station_id, start_time))
                result = cur.fetchone()
                if result:
                    return {
                        "station_id": station_id,
                        "time_range_hours": hours,
                        "total_records": result[0],
                        "active_devices": result[1],
                        "avg_power_kw": round(float(result[2]), 2) if result[2] else 0,
                        "total_power_kw": (
                            round(float(result[3]), 2) if result[3] else 0
                        ),
                        "avg_flow_rate_m3h": (
                            round(float(result[4]), 2) if result[4] else 0
                        ),
                        "total_flow_rate_m3h": (
                            round(float(result[5]), 2) if result[5] else 0
                        ),
                        "data_start": result[6].isoformat() if result[6] else None,
                        "data_end": result[7].isoformat() if result[7] else None,
                        "energy_consumption_kwh": (
                            round(float(result[3]) * hours, 2) if result[3] else 0
                        ),
                    }
                else:
                    return {"station_id": station_id, "message": "指定时间范围内无数据"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")


@router.get("/metrics", response_model=List[MetricInfo])
async def get_metrics_catalog() -> List[MetricInfo]:
    """返回固定的指标清单（用于前端指标多选器）。

    字段来源 dim_metric_config：
    - id, metric_key
    - unit（优先 unit_display 回退 unit）
    - unit_display, value_type, fixed_decimals, valid_min, valid_max
    """
    try:
        with get_conn(settings) as conn:
            sql = """
                SELECT id,
                       metric_key,
                       COALESCE(NULLIF(unit_display, ''), unit) AS unit,
                       unit_display,
                       value_type,
                       fixed_decimals,
                       valid_min,
                       valid_max
                FROM public.dim_metric_config
                ORDER BY metric_key
                """
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            result: List[MetricInfo] = []
            for r in rows:
                result.append(
                    MetricInfo(
                        id=int(r[0]),
                        metric_key=str(r[1]),
                        unit=r[2],
                        unit_display=r[3],
                        value_type=r[4],
                        fixed_decimals=r[5],
                        valid_min=float(r[6]) if r[6] is not None else None,
                        valid_max=float(r[7]) if r[7] is not None else None,
                    )
                )
            return result
    except Exception as e:
        logger.exception("获取指标清单失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取指标清单失败: {str(e)}")


@router.get("/import-stats/{station_id}")
async def get_import_statistics(station_id: str) -> Dict[str, Any]:
    """获取数据导入统计信息"""
    try:
        service = DataImportService(settings)
        stats = await service.get_import_statistics(station_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入统计查询失败: {str(e)}")
