"""
数据查询 API 端点（app.api.v1.endpoints.data）

提供泵站运行数据的查询接口：
- 时序数据查询
- 设备信息查询
- 泵站状态查询
- 数据统计和聚合
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path

from app.core.config.loader import load_settings
from app.models import (
    TimeSeriesQuery,
    TimeSeriesResponse,
    StationSummary,
    DeviceSummary,
    DataExportRequest,
)
from app.adapters.db.gateway import get_conn
from app.services.data_import import DataImportService

router = APIRouter()

# 加载配置
settings = load_settings(Path("configs"))


@router.get("/measurements", response_model=TimeSeriesResponse)
async def get_measurements(
    station_id: Optional[str] = Query(None, description="泵站ID"),
    device_id: Optional[str] = Query(None, description="设备ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(1000, ge=1, le=10000, description="数据数量限制"),
    offset: int = Query(0, ge=0, description="数据偏移量")
) -> TimeSeriesResponse:
    """
    查询测量数据
    
    返回指定条件下的泵站运行数据。
    """
    try:
        # 设置默认时间范围（最近 24 小时）
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()
        
        # 构建查询 SQL
        sql_parts = [
            "SELECT timestamp, device_id, flow_rate, pressure, power, frequency",
            "FROM operation_data",
            "WHERE timestamp BETWEEN %s AND %s"
        ]
        params = [start_time, end_time]
        
        if station_id:
            sql_parts.append("AND station_id = %s")
            params.append(station_id)
        
        if device_id:
            sql_parts.append("AND device_id = %s")
            params.append(device_id)
        
        sql_parts.extend([
            "ORDER BY timestamp DESC",
            f"LIMIT {limit} OFFSET {offset}"
        ])
        
        query_sql = " ".join(sql_parts)
        
        # 执行查询
        data = []
        total_count = 0
        
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 获取数据
                cur.execute(query_sql, params)
                
                for row in cur.fetchall():
                    timestamp, dev_id, flow_rate, pressure, power, frequency = row
                    data.append({
                        "timestamp": timestamp.isoformat(),
                        "device_id": dev_id,
                        "flow_rate": float(flow_rate) if flow_rate else None,
                        "pressure": float(pressure) if pressure else None,
                        "power": float(power) if power else None,
                        "frequency": float(frequency) if frequency else None
                    })
                
                # 获取总数
                count_sql = query_sql.replace(
                    "SELECT timestamp, device_id, flow_rate, pressure, power, frequency",
                    "SELECT COUNT(*)"
                ).replace(f"LIMIT {limit} OFFSET {offset}", "")
                
                cur.execute(count_sql, params[:-0])  # 除去 LIMIT/OFFSET 参数
                total_count = cur.fetchone()[0]
        
        return TimeSeriesResponse(
            data=data,
            metadata={
                "station_id": station_id,
                "device_id": device_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit,
                "offset": offset
            },
            total_count=total_count,
            has_more=offset + len(data) < total_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据查询失败: {str(e)}")


@router.get("/stations", response_model=List[StationSummary])
async def get_stations() -> List[StationSummary]:
    """
    获取所有泵站的概览信息
    """
    try:
        stations = []
        
        sql = """
        SELECT s.station_id, s.name, s.region, s.status, s.capacity,
               COUNT(d.device_id) as device_count,
               MAX(od.timestamp) as last_data_time
        FROM station s
        LEFT JOIN device d ON s.station_id = d.station_id
        LEFT JOIN operation_data od ON s.station_id = od.station_id
        GROUP BY s.station_id, s.name, s.region, s.status, s.capacity
        ORDER BY s.station_id
        """
        
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                
                for row in cur.fetchall():
                    station_id, name, region, status, capacity, device_count, last_data_time = row
                    
                    station = StationSummary(
                        station_id=station_id,
                        name=name,
                        region=region,
                        status=status,
                        device_count=device_count,
                        capacity=capacity,
                        last_data_time=last_data_time
                    )
                    stations.append(station)
        
        return stations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"泵站查询失败: {str(e)}")


@router.get("/stations/{station_id}/devices", response_model=List[DeviceSummary])
async def get_station_devices(station_id: str) -> List[DeviceSummary]:
    """
    获取指定泵站的设备信息
    """
    try:
        devices = []
        
        sql = """
        SELECT d.device_id, d.name, d.type, d.pump_type, d.status, d.rated_power,
               MAX(od.timestamp) as last_data_time
        FROM device d
        LEFT JOIN operation_data od ON d.device_id = od.device_id
        WHERE d.station_id = %s
        GROUP BY d.device_id, d.name, d.type, d.pump_type, d.status, d.rated_power
        ORDER BY d.device_id
        """
        
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (station_id,))
                
                for row in cur.fetchall():
                    device_id, name, device_type, pump_type, status, rated_power, last_data_time = row
                    
                    device = DeviceSummary(
                        device_id=device_id,
                        station_id=station_id,
                        name=name,
                        type=device_type,
                        pump_type=pump_type,
                        status=status,
                        rated_power=rated_power,
                        last_data_time=last_data_time
                    )
                    devices.append(device)
        
        return devices
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备查询失败: {str(e)}")


@router.get("/stations/{station_id}/statistics")
async def get_station_statistics(
    station_id: str,
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）")
) -> Dict[str, Any]:
    """
    获取泵站运行统计信息
    """
    try:
        start_time = datetime.now() - timedelta(hours=hours)
        
        sql = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT device_id) as active_devices,
            AVG(power) as avg_power,
            SUM(power) as total_power,
            AVG(flow_rate) as avg_flow_rate,
            SUM(flow_rate) as total_flow_rate,
            MIN(timestamp) as data_start,
            MAX(timestamp) as data_end
        FROM operation_data
        WHERE station_id = %s AND timestamp >= %s
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
                        "total_power_kw": round(float(result[3]), 2) if result[3] else 0,
                        "avg_flow_rate_m3h": round(float(result[4]), 2) if result[4] else 0,
                        "total_flow_rate_m3h": round(float(result[5]), 2) if result[5] else 0,
                        "data_start": result[6].isoformat() if result[6] else None,
                        "data_end": result[7].isoformat() if result[7] else None,
                        "energy_consumption_kwh": round(float(result[3]) * hours, 2) if result[3] else 0
                    }
                else:
                    return {
                        "station_id": station_id,
                        "message": "指定时间范围内无数据"
                    }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")


@router.get("/import-stats/{station_id}")
async def get_import_statistics(station_id: str) -> Dict[str, Any]:
    """
    获取数据导入统计信息
    """
    try:
        service = DataImportService(settings)
        stats = await service.get_import_statistics(station_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入统计查询失败: {str(e)}")
