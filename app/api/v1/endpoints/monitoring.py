"""
系统监控 API 端点（app.api.v1.endpoints.monitoring）

提供系统健康检查和状态监控功能：
- 数据库连接检查
- 连接池状态监控
- 服务可用性检查
- 系统性能指标
- 设备状态监控
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.adapters.db import get_pool_stats, is_initialized
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings

router = APIRouter()

# 加载配置
settings = load_settings(Path("configs"))


class DeviceStatus(BaseModel):
    """设备状态模型"""

    device_id: int
    name: str
    type: str
    station_id: int
    station_name: str
    status: str
    rated_power: Optional[float] = None
    last_data_time: Optional[datetime] = None
    current_flow_rate: Optional[float] = None
    current_pressure: Optional[float] = None
    current_power: Optional[float] = None
    efficiency: Optional[float] = None
    warning_count: int = 0
    error_count: int = 0


class DevicesResponse(BaseModel):
    """设备列表响应模型"""

    devices: List[DeviceStatus]
    total_count: int
    online_count: int
    offline_count: int
    warning_count: int


@router.get("/health")
def system_health_check() -> Dict[str, Any]:
    """
    系统健康检查

    返回系统整体的健康状态和关键指标。
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "services": {},
    }

    try:
        # 1. 数据库连接检查
        db_health = check_database_health()
        health_status["checks"]["database"] = db_health

        # 2. 连接池状态检查
        pool_health = check_connection_pool_health()
        health_status["checks"]["connection_pool"] = pool_health

        # 3. 服务可用性检查
        services_health = check_services_availability()
        health_status["services"] = services_health

        # 4. 数据质量检查
        data_quality = check_data_quality()
        health_status["checks"]["data_quality"] = data_quality

        # 判断整体健康状态
        if not all(
            check.get("healthy", False) for check in health_status["checks"].values()
        ):
            health_status["status"] = "unhealthy"
        elif any(
            check.get("warning", False) for check in health_status["checks"].values()
        ):
            health_status["status"] = "warning"

        return health_status

    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


@router.get("/db-health")
def db_health_check() -> Dict[str, Any]:
    """
    数据库健康检查

    检查数据库连接和基本操作。
    """
    return check_database_health()


@router.get("/pool-stats")
def connection_pool_stats() -> Dict[str, Any]:
    """
    连接池统计信息

    返回连接池的详细统计数据。
    """
    try:
        return {
            "pool_initialized": is_initialized(),
            "pool_stats": get_pool_stats(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接池状态查询失败: {str(e)}")


@router.get("/performance")
def system_performance() -> Dict[str, Any]:
    """
    系统性能指标

    返回系统的关键性能指标。
    """
    try:
        start_time = time.time()

        # 测试数据库查询性能
        db_response_time = measure_db_response_time()

        # 获取数据统计
        data_stats = get_data_statistics()

        total_time = (time.time() - start_time) * 1000

        return {
            "api_response_time_ms": round(total_time, 2),
            "database_response_time_ms": db_response_time,
            "data_statistics": data_stats,
            "connection_pool": get_pool_stats(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"性能指标查询失败: {str(e)}")


@router.get("/devices", response_model=DevicesResponse)
def get_devices(
    station_id: Optional[int] = Query(None, description="按泵站ID筛选"),
    status: Optional[str] = Query(
        None, description="按状态筛选 (online/offline/warning)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> DevicesResponse:
    """
    获取设备列表和状态信息

    提供设备的实时状态监控，包括：
    - 设备基本信息
    - 运行状态
    - 最新测量数据
    - 告警统计
    """
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 构建查询条件
                where_conditions = []
                params = []

                if station_id:
                    where_conditions.append("d.station_id = %s")
                    params.append(station_id)

                where_clause = (
                    " AND ".join(where_conditions) if where_conditions else "1=1"
                )

                # 查询设备列表和最新数据（从 v_fully_adaptive_data 取近24小时每个指标的最新值）
                query = f"""
                    WITH latest_values AS (
                        SELECT DISTINCT ON (device_id, metric_key)
                            device_id,
                            timestamp,
                            metric_key,
                            value
                        FROM v_fully_adaptive_data
                        WHERE timestamp > NOW() - INTERVAL '24 hours'
                        ORDER BY device_id, metric_key, timestamp DESC
                    ), pivot AS (
                        SELECT
                            device_id,
                            MAX(timestamp) AS last_data_time,
                            MAX(CASE WHEN metric_key = 'main_pipeline_flow_rate' THEN value END) AS flow_rate,
                            MAX(CASE WHEN metric_key = 'main_pipeline_pressure' THEN value END) AS pressure,
                            MAX(CASE WHEN metric_key = 'pump_active_power' THEN value END) AS power,
                            MAX(CASE WHEN metric_key = 'pump_frequency' THEN value END) AS frequency
                        FROM latest_values
                        GROUP BY device_id
                    )
                    SELECT
                        d.device_id,
                        d.name,
                        d.type,
                        d.station_id,
                        s.name as station_name,
                        d.rated_power,
                        p.last_data_time,
                        p.flow_rate,
                        p.pressure,
                        p.power,
                        p.frequency
                    FROM device d
                    JOIN station s ON d.station_id = s.station_id
                    LEFT JOIN pivot p ON d.device_id = p.device_id
                    WHERE {where_clause}
                    ORDER BY d.device_id
                    LIMIT %s OFFSET %s
                """

                params.extend([limit, offset])
                cur.execute(query, params)
                rows = cur.fetchall()

                # 查询总数
                count_query = f"""
                    SELECT COUNT(*)
                    FROM device d
                    JOIN station s ON d.station_id = s.station_id
                    WHERE {where_clause}
                """
                cur.execute(count_query, params[:-2])  # 不包括limit和offset
                total_count = cur.fetchone()[0]

                # 构建设备列表
                devices = []
                online_count = 0
                offline_count = 0
                warning_count = 0

                for row in rows:
                    (
                        device_id,
                        name,
                        device_type,
                        station_id,
                        station_name,
                        rated_power,
                        last_data_time,
                        flow_rate,
                        pressure,
                        power,
                        frequency,
                    ) = row

                    # 判断设备状态
                    if last_data_time:
                        time_since_last = datetime.now() - last_data_time
                        if time_since_last.total_seconds() < 3600:  # 1小时内有数据
                            device_status = "online"
                            online_count += 1
                        else:
                            device_status = "warning"
                            warning_count += 1
                    else:
                        device_status = "offline"
                        offline_count += 1

                    # 计算效率（简单示例）
                    efficiency = None
                    if power and rated_power and rated_power > 0:
                        efficiency = round((power / rated_power) * 100, 1)

                    # 应用状态筛选
                    if status and device_status != status:
                        continue

                    device = DeviceStatus(
                        device_id=device_id,
                        name=name,
                        type=device_type,
                        station_id=station_id,
                        station_name=station_name,
                        status=device_status,
                        rated_power=rated_power,
                        last_data_time=last_data_time,
                        current_flow_rate=flow_rate,
                        current_pressure=pressure,
                        current_power=power,
                        efficiency=efficiency,
                        warning_count=0,  # 可以后续扩展告警统计
                        error_count=0,
                    )
                    devices.append(device)

                return DevicesResponse(
                    devices=devices,
                    total_count=total_count,
                    online_count=online_count,
                    offline_count=offline_count,
                    warning_count=warning_count,
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备状态查询失败: {str(e)}")


@router.get("/devices/{device_id}")
def get_device_detail(device_id: int) -> Dict[str, Any]:
    """
    获取设备详细信息

    包括设备的详细状态、历史数据趋势等。
    """
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 查询设备基本信息
                cur.execute(
                    """
                    SELECT 
                        d.device_id,
                        d.name,
                        d.type,
                        d.station_id,
                        s.name as station_name,
                        d.rated_power
                    FROM device d
                    JOIN station s ON d.station_id = s.station_id
                    WHERE d.device_id = %s
                """,
                    (device_id,),
                )

                device_info = cur.fetchone()
                if not device_info:
                    raise HTTPException(
                        status_code=404, detail=f"设备 {device_id} 不存在"
                    )

                # 查询最近24小时的数据趋势
                cur.execute(
                    """
                    SELECT 
                        timestamp,
                        flow_rate,
                        pressure,
                        power,
                        frequency
                    FROM operation_data
                    WHERE device_id = %s
                        AND timestamp > NOW() - INTERVAL '24 hours'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """,
                    (device_id,),
                )

                recent_data = cur.fetchall()

                # 计算统计信息
                if recent_data:
                    flow_rates = [r[1] for r in recent_data if r[1] is not None]
                    pressures = [r[2] for r in recent_data if r[2] is not None]
                    powers = [r[3] for r in recent_data if r[3] is not None]

                    stats = {
                        "avg_flow_rate": (
                            round(sum(flow_rates) / len(flow_rates), 2)
                            if flow_rates
                            else None
                        ),
                        "avg_pressure": (
                            round(sum(pressures) / len(pressures), 2)
                            if pressures
                            else None
                        ),
                        "avg_power": (
                            round(sum(powers) / len(powers), 2) if powers else None
                        ),
                        "data_points": len(recent_data),
                    }
                else:
                    stats = {
                        "avg_flow_rate": None,
                        "avg_pressure": None,
                        "avg_power": None,
                        "data_points": 0,
                    }

                return {
                    "device_info": {
                        "device_id": device_info[0],
                        "name": device_info[1],
                        "type": device_info[2],
                        "station_id": device_info[3],
                        "station_name": device_info[4],
                        "rated_power": device_info[5],
                    },
                    "recent_statistics": stats,
                    "recent_data": [
                        {
                            "timestamp": row[0].isoformat(),
                            "flow_rate": row[1],
                            "pressure": row[2],
                            "power": row[3],
                            "frequency": row[4],
                        }
                        for row in recent_data
                    ],
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备详情查询失败: {str(e)}")


def check_database_health() -> Dict[str, Any]:
    """检查数据库健康状态"""
    start_time = time.time()

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 测试基本连接
                cur.execute("SELECT 1")
                result = cur.fetchone()

                if result and result[0] == 1:
                    response_time = (time.time() - start_time) * 1000

                    # 检查表存在
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_name IN ('station', 'device', 'operation_data')
                    """
                    )
                    table_count = cur.fetchone()[0]

                    return {
                        "healthy": True,
                        "response_time_ms": round(response_time, 2),
                        "required_tables_present": table_count >= 3,
                        "connection_successful": True,
                        "message": "数据库连接正常",
                    }
                else:
                    return {"healthy": False, "error": "数据库查询返回异常结果"}

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000,
        }


def check_connection_pool_health() -> Dict[str, Any]:
    """检查连接池健康状态"""
    try:
        pool_initialized = is_initialized()
        pool_stats = get_pool_stats() if pool_initialized else {}

        if pool_initialized:
            # 检查连接池是否正常
            active_connections = pool_stats.get("active_connections", 0)
            max_connections = pool_stats.get("max_connections", 10)

            utilization = (
                active_connections / max_connections if max_connections > 0 else 0
            )

            return {
                "healthy": True,
                "initialized": True,
                "utilization_percentage": round(utilization * 100, 2),
                "warning": utilization > 0.8,  # 警告阈值 80%
                "stats": pool_stats,
            }
        else:
            return {
                "healthy": False,
                "initialized": False,
                "message": "连接池未初始化，使用直连模式",
            }

    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_services_availability() -> Dict[str, Any]:
    """检查服务可用性"""
    services = {}

    try:
        # 检查曲线拟合服务
        from app.services.curve_fitting import CurveFittingService

        _ = CurveFittingService(settings)  # 仅验证可用性，避免未使用变量
        services["curve_fitting"] = {"available": True, "class": "CurveFittingService"}
    except Exception as e:
        services["curve_fitting"] = {"available": False, "error": str(e)}

    try:
        # 检查优化服务
        from app.services.optimization import OptimizationService

        _ = OptimizationService(settings)  # 仅验证可用性，避免未使用变量
        services["optimization"] = {"available": True, "class": "OptimizationService"}
    except Exception as e:
        services["optimization"] = {"available": False, "error": str(e)}

    try:
        # 检查数据导入服务
        from app.services.data_import import DataImportService

        _ = DataImportService(settings)  # 仅验证可用性，避免未使用变量
        services["data_import"] = {"available": True, "class": "DataImportService"}
    except Exception as e:
        services["data_import"] = {"available": False, "error": str(e)}

    return services


def check_data_quality() -> Dict[str, Any]:
    """检查数据质量"""
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 检查最近 24 小时的数据
                recent_time = datetime.now() - timedelta(hours=24)

                cur.execute(
                    """
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT station_id) as stations,
                           COUNT(DISTINCT device_id) as devices,
                           MIN(timestamp) as oldest_data,
                           MAX(timestamp) as newest_data
                    FROM operation_data
                    WHERE timestamp >= %s
                """,
                    (recent_time,),
                )

                result = cur.fetchone()

                if result:
                    total_records, stations, devices, oldest, newest = result

                    # 数据新鲜度检查（最新数据不超过 1 小时）
                    data_freshness = True
                    if newest:
                        time_since_last = datetime.now() - newest
                        data_freshness = time_since_last.total_seconds() < 3600  # 1小时

                    return {
                        "healthy": total_records > 0 and data_freshness,
                        "warning": not data_freshness,
                        "total_records_24h": total_records,
                        "active_stations": stations,
                        "active_devices": devices,
                        "oldest_data": oldest.isoformat() if oldest else None,
                        "newest_data": newest.isoformat() if newest else None,
                        "data_fresh": data_freshness,
                    }
                else:
                    return {"healthy": False, "message": "最近 24 小时无数据"}

    except Exception as e:
        return {"healthy": False, "error": str(e)}


def measure_db_response_time() -> float:
    """测量数据库响应时间"""
    start_time = time.time()

    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM operation_data LIMIT 1")
                cur.fetchone()

        return round((time.time() - start_time) * 1000, 2)

    except Exception:
        return -1  # 表示失败


def get_data_statistics() -> Dict[str, Any]:
    """获取数据统计信息"""
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 基本统计
                cur.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM station) as total_stations,
                        (SELECT COUNT(*) FROM device) as total_devices,
                        (SELECT COUNT(*) FROM operation_data) as total_records
                """
                )

                stats = cur.fetchone()

                return {
                    "total_stations": stats[0] if stats else 0,
                    "total_devices": stats[1] if stats else 0,
                    "total_operation_records": stats[2] if stats else 0,
                }

    except Exception as e:
        return {"error": str(e)}
