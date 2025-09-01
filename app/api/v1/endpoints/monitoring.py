"""
系统监控 API 端点（app.api.v1.endpoints.monitoring）

提供系统健康检查和状态监控功能：
- 数据库连接检查
- 连接池状态监控
- 服务可用性检查
- 系统性能指标
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.core.config.loader import load_settings
from app.adapters.db import get_pool_stats, is_initialized
from app.adapters.db.gateway import get_conn

router = APIRouter()

# 加载配置
settings = load_settings(Path("configs"))


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
        "services": {}
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
        if not all(check.get("healthy", False) for check in health_status["checks"].values()):
            health_status["status"] = "unhealthy"
        elif any(check.get("warning", False) for check in health_status["checks"].values()):
            health_status["status"] = "warning"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
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
            "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"性能指标查询失败: {str(e)}")


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
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_name IN ('station', 'device', 'operation_data')
                    """)
                    table_count = cur.fetchone()[0]
                    
                    return {
                        "healthy": True,
                        "response_time_ms": round(response_time, 2),
                        "required_tables_present": table_count >= 3,
                        "connection_successful": True,
                        "message": "数据库连接正常"
                    }
                else:
                    return {
                        "healthy": False,
                        "error": "数据库查询返回异常结果"
                    }
    
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000
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
            
            utilization = active_connections / max_connections if max_connections > 0 else 0
            
            return {
                "healthy": True,
                "initialized": True,
                "utilization_percentage": round(utilization * 100, 2),
                "warning": utilization > 0.8,  # 警告阈值 80%
                "stats": pool_stats
            }
        else:
            return {
                "healthy": False,
                "initialized": False,
                "message": "连接池未初始化，使用直连模式"
            }
    
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }


def check_services_availability() -> Dict[str, Any]:
    """检查服务可用性"""
    services = {}
    
    try:
        # 检查曲线拟合服务
        from app.services.curve_fitting import CurveFittingService
        curve_service = CurveFittingService(settings)
        services["curve_fitting"] = {
            "available": True,
            "class": "CurveFittingService"
        }
    except Exception as e:
        services["curve_fitting"] = {
            "available": False,
            "error": str(e)
        }
    
    try:
        # 检查优化服务
        from app.services.optimization import OptimizationService
        opt_service = OptimizationService(settings)
        services["optimization"] = {
            "available": True,
            "class": "OptimizationService"
        }
    except Exception as e:
        services["optimization"] = {
            "available": False,
            "error": str(e)
        }
    
    try:
        # 检查数据导入服务
        from app.services.data_import import DataImportService
        import_service = DataImportService(settings)
        services["data_import"] = {
            "available": True,
            "class": "DataImportService"
        }
    except Exception as e:
        services["data_import"] = {
            "available": False,
            "error": str(e)
        }
    
    return services


def check_data_quality() -> Dict[str, Any]:
    """检查数据质量"""
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 检查最近 24 小时的数据
                recent_time = datetime.now() - timedelta(hours=24)
                
                cur.execute("""
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT station_id) as stations,
                           COUNT(DISTINCT device_id) as devices,
                           MIN(timestamp) as oldest_data,
                           MAX(timestamp) as newest_data
                    FROM operation_data
                    WHERE timestamp >= %s
                """, (recent_time,))
                
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
                        "data_fresh": data_freshness
                    }
                else:
                    return {
                        "healthy": False,
                        "message": "最近 24 小时无数据"
                    }
    
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }


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
                cur.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM station) as total_stations,
                        (SELECT COUNT(*) FROM device) as total_devices,
                        (SELECT COUNT(*) FROM operation_data) as total_records
                """)
                
                stats = cur.fetchone()
                
                return {
                    "total_stations": stats[0] if stats else 0,
                    "total_devices": stats[1] if stats else 0,
                    "total_operation_records": stats[2] if stats else 0
                }
    
    except Exception as e:
        return {
            "error": str(e)
        }
