"""
计算审计追溯模块

提供计算结果的审计追溯功能，包括：
1. source_hint 生成（扩展格式）
2. 审计查询函数
3. 失败日志扩展记录

版本：v1.0
创建时间：2025-10-25
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import logging

from app.adapters.db import get_connection

logger = logging.getLogger(__name__)


def generate_source_hint(
    method_id: str,
    params_version: Optional[str] = None,
    priority: Optional[int] = None,
    duration_ms: Optional[float] = None
) -> str:
    """
    生成审计追溯的 source_hint
    
    Args:
        method_id: 计算方法ID
        params_version: 参数版本（可选，格式：YYYYMMDD）
        priority: 方法优先级（可选）
        duration_ms: 计算耗时（可选）
    
    Returns:
        格式化的 source_hint 字符串
        
    Examples:
        >>> generate_source_hint("pump_inlet_pressure_method_b")
        'calculation:pump_inlet_pressure_method_b'
        
        >>> generate_source_hint("pump_inlet_pressure_method_b", params_version="20251025", priority=90, duration_ms=12.5)
        'calculation:pump_inlet_pressure_method_b|params_version:20251025|priority:90|duration_ms:12'
    """
    parts = [f"calculation:{method_id}"]
    
    if params_version:
        parts.append(f"params_version:{params_version}")
    
    if priority is not None:
        parts.append(f"priority:{priority}")
    
    if duration_ms is not None:
        parts.append(f"duration_ms:{int(duration_ms)}")
    
    return "|".join(parts)


def parse_source_hint(source_hint: str) -> Dict[str, str]:
    """
    解析 source_hint 字符串
    
    Args:
        source_hint: source_hint 字符串
    
    Returns:
        解析后的字典
        
    Examples:
        >>> parse_source_hint("calculation:pump_inlet_pressure_method_b|params_version:20251025|priority:90")
        {'calculation': 'pump_inlet_pressure_method_b', 'params_version': '20251025', 'priority': '90'}
    """
    source_info = {}
    if source_hint:
        parts = source_hint.split('|')
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                source_info[key] = value
    return source_info


def log_calculation_failure_with_audit(
    station_id: int,
    device_id: int,
    metric_key: str,
    ts_second: datetime,
    attempted_methods: List[Dict],
    params_used: Dict[str, float],
    error_type: str,
    error_message: str
) -> None:
    """
    记录计算失败，包含完整审计信息
    
    Args:
        station_id: 泵站ID
        device_id: 设备ID
        metric_key: 指标键
        ts_second: 时间戳
        attempted_methods: 尝试的方法列表，每个方法包含：
            - method_id: 方法ID
            - priority: 优先级
            - failure_reason: 失败原因
            - missing_deps: 缺失依赖（可选）
            - error_message: 错误信息（可选）
        params_used: 使用的参数
        error_type: 错误类型
        error_message: 错误信息
    """
    error_details = {
        "attempted_methods": attempted_methods,
        "params_used": params_used,
        "execution_context": {
            "batch_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "device_id": device_id,
            "ts_second": ts_second.isoformat()
        }
    }
    
    query = """
        INSERT INTO calculation_failures_log (
            station_id, device_id, metric_key, ts_second,
            method_id, error_type, error_message, error_details, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    station_id, device_id, metric_key, ts_second,
                    attempted_methods[0]['method_id'] if attempted_methods else None,
                    error_type, error_message, json.dumps(error_details)
                ))
            conn.commit()
            
        logger.debug(
            f"记录计算失败审计信息: {metric_key}, device={device_id}, "
            f"attempted_methods={len(attempted_methods)}"
        )
    except Exception as e:
        logger.error(f"记录计算失败审计信息时出错: {e}")


def audit_calculation_result(
    device_id: int,
    metric_key: str,
    ts_second: datetime
) -> Dict[str, Any]:
    """
    审计追溯计算结果
    
    Args:
        device_id: 设备ID
        metric_key: 指标键
        ts_second: 时间戳
    
    Returns:
        审计信息字典，包含：
        - result: 计算结果信息
            - value: 计算值
            - source_hint: 原始source_hint
            - source_info: 解析后的source_hint
            - quality_meta: 质量元数据
            - inserted_at: 插入时间
        - failures: 失败记录列表
            - method_id: 方法ID
            - error_type: 错误类型
            - error_message: 错误信息
            - error_details: 详细错误信息
            - created_at: 创建时间
    """
    # 查询计算结果
    query_result = """
        SELECT fm.value, fm.source_hint, fm.quality_meta, fm.inserted_at
        FROM fact_measurements fm
        JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
        WHERE fm.device_id = %s
          AND dmc.metric_key = %s
          AND fm.ts_bucket = %s
    """
    
    # 查询失败日志
    query_failures = """
        SELECT method_id, error_type, error_message, error_details, created_at
        FROM calculation_failures_log
        WHERE device_id = %s
          AND metric_key = %s
          AND ts_second = %s
        ORDER BY created_at DESC
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查询结果
                cur.execute(query_result, (device_id, metric_key, ts_second))
                result = cur.fetchone()
                
                # 查询失败记录
                cur.execute(query_failures, (device_id, metric_key, ts_second))
                failures = cur.fetchall()
        
        # 解析 source_hint
        source_info = {}
        if result and result[1]:
            source_info = parse_source_hint(result[1])
        
        return {
            "result": {
                "value": float(result[0]) if result and result[0] is not None else None,
                "source_hint": result[1] if result else None,
                "source_info": source_info,
                "quality_meta": result[2] if result else None,
                "inserted_at": result[3] if result else None
            },
            "failures": [
                {
                    "method_id": f[0],
                    "error_type": f[1],
                    "error_message": f[2],
                    "error_details": f[3],
                    "created_at": f[4]
                }
                for f in failures
            ]
        }
    except Exception as e:
        logger.error(f"审计查询失败: {e}")
        return {
            "result": {
                "value": None,
                "source_hint": None,
                "source_info": {},
                "quality_meta": None,
                "inserted_at": None
            },
            "failures": []
        }


def audit_calculation_batch(
    device_id: int,
    metric_key: str,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    批量审计计算结果
    
    Args:
        device_id: 设备ID
        metric_key: 指标键
        start_time: 开始时间
        end_time: 结束时间
    
    Returns:
        批量审计信息，包含：
        - total_points: 总数据点数
        - calculated_points: 计算数据点数
        - imported_points: 导入数据点数
        - method_distribution: 方法分布统计
        - failure_count: 失败次数
    """
    # 查询计算结果统计
    query_stats = """
        SELECT
            COUNT(*) as total_points,
            COUNT(CASE WHEN fm.source_hint LIKE 'calculation:%%' THEN 1 END) as calculated_points,
            COUNT(CASE WHEN fm.source_hint LIKE 'imported_from_csv%%' OR fm.source_hint LIKE 'data/%%' THEN 1 END) as imported_points
        FROM fact_measurements fm
        JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
        WHERE fm.device_id = %s
          AND dmc.metric_key = %s
          AND fm.ts_bucket >= %s
          AND fm.ts_bucket < %s
    """

    # 查询方法分布
    query_methods = """
        SELECT fm.source_hint, COUNT(*) as count
        FROM fact_measurements fm
        JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
        WHERE fm.device_id = %s
          AND dmc.metric_key = %s
          AND fm.ts_bucket >= %s
          AND fm.ts_bucket < %s
          AND fm.source_hint LIKE 'calculation:%%'
        GROUP BY fm.source_hint
        ORDER BY count DESC
    """
    
    # 查询失败次数
    query_failures = """
        SELECT COUNT(*) as failure_count
        FROM calculation_failures_log
        WHERE device_id = %s
          AND metric_key = %s
          AND ts_second >= %s
          AND ts_second < %s
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查询统计
                cur.execute(query_stats, (device_id, metric_key, start_time, end_time))
                stats = cur.fetchone()
                
                # 查询方法分布
                cur.execute(query_methods, (device_id, metric_key, start_time, end_time))
                methods = cur.fetchall()
                
                # 查询失败次数
                cur.execute(query_failures, (device_id, metric_key, start_time, end_time))
                failures = cur.fetchone()
        
        # 解析方法分布
        method_distribution = {}
        for source_hint, count in methods:
            source_info = parse_source_hint(source_hint)
            method_id = source_info.get('calculation', 'unknown')
            method_distribution[method_id] = count
        
        return {
            "total_points": stats[0] if stats else 0,
            "calculated_points": stats[1] if stats else 0,
            "imported_points": stats[2] if stats else 0,
            "method_distribution": method_distribution,
            "failure_count": failures[0] if failures else 0
        }
    except Exception as e:
        logger.error(f"批量审计查询失败: {e}")
        return {
            "total_points": 0,
            "calculated_points": 0,
            "imported_points": 0,
            "method_distribution": {},
            "failure_count": 0
        }

