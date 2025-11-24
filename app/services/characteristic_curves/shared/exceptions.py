"""
特性曲线拟合系统 - 统一异常定义

版本: v2.6
创建日期: 2025-12-09
文件路径: app/services/characteristic_curves/shared/exceptions.py
来源: 03_共用层.md 第0章

原则: 宁可失败并明确告知，也不要使用不可靠的降级数据继续执行
"""

from typing import List, Dict, Any, Optional


class CurveFittingError(Exception):
    """曲线拟合基础异常类

    所有曲线拟合相关异常的基类，提供统一的错误码和日志格式。
    """

    error_code: str = "CF000"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_log_format(self) -> str:
        """格式化为日志输出"""
        return f"[{self.error_code}] {self.message} | details={self.details}"


class InsufficientDataError(CurveFittingError):
    """数据不足异常 (CF001)

    当训练或验证数据点数不满足最小要求时抛出。
    """

    error_code: str = "CF001"

    def __init__(
        self,
        message: str,
        actual_points: int,
        min_points: int,
        device_id: Optional[int] = None,
        stage: Optional[str] = None
    ):
        details = {
            "actual_points": actual_points,
            "min_points": min_points,
            "device_id": device_id,
            "stage": stage
        }
        super().__init__(message, details)
        self.actual_points = actual_points
        self.min_points = min_points
        self.device_id = device_id
        self.stage = stage


class DataExtractionError(CurveFittingError):
    """数据提取异常 (CF009)

    当从数据库提取训练数据失败时抛出。
    """

    error_code: str = "CF009"

    def __init__(
        self,
        message: str,
        device_id: Optional[int] = None,
        curve_type: Optional[str] = None,
        reason: Optional[str] = None
    ):
        details = {
            "device_id": device_id,
            "curve_type": curve_type,
            "reason": reason
        }
        super().__init__(message, details)
        self.device_id = device_id
        self.curve_type = curve_type
        self.reason = reason


class FrequencyQueryError(CurveFittingError):
    """频率查询异常 (CF002)

    当无法获取变频泵的运行频率时抛出。
    """

    error_code: str = "CF002"

    def __init__(
        self,
        message: str,
        pump_id: int,
        timestamp: Optional[str] = None
    ):
        details = {"pump_id": pump_id, "timestamp": timestamp}
        super().__init__(message, details)
        self.pump_id = pump_id
        self.timestamp = timestamp


class HeadOutOfRangeError(CurveFittingError):
    """扬程超出范围异常 (CF003)

    当系统扬程超出所有泵的有效H范围时抛出。
    """

    error_code: str = "CF003"

    def __init__(
        self,
        message: str,
        H_system: float,
        H_min: float,
        H_max: float,
        pump_id: Optional[int] = None
    ):
        details = {
            "H_system": H_system,
            "H_min": H_min,
            "H_max": H_max,
            "pump_id": pump_id
        }
        super().__init__(message, details)
        self.H_system = H_system
        self.H_min = H_min
        self.H_max = H_max


class CorrectionModelTrainingError(CurveFittingError):
    """修正模型训练失败异常 (CF004)

    当SystemCorrectionModel训练失败时抛出。
    """

    error_code: str = "CF004"

    def __init__(
        self,
        message: str,
        station_id: int,
        pump_ids: List[int],
        reason: str,
        actual_points: int = 0,
        min_points: int = 100
    ):
        details = {
            "station_id": station_id,
            "pump_ids": pump_ids,
            "reason": reason,
            "actual_points": actual_points,
            "min_points": min_points
        }
        super().__init__(message, details)
        self.station_id = station_id
        self.pump_ids = pump_ids
        self.reason = reason


class P0FittingRetryExhaustedError(CurveFittingError):
    """P0拟合重试耗尽异常 (CF005)

    当auto_trigger_p0重试次数超过最大限制时抛出。
    """

    error_code: str = "CF005"

    def __init__(
        self,
        message: str,
        pump_id: int,
        retry_count: int,
        max_retries: int,
        last_error: Optional[str] = None
    ):
        details = {
            "pump_id": pump_id,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "last_error": last_error
        }
        super().__init__(message, details)
        self.pump_id = pump_id
        self.retry_count = retry_count
        self.max_retries = max_retries


class CurveInconsistencyError(CurveFittingError):
    """曲线一致性异常 (CF006)

    当同构泵组的曲线参数差异超出阈值时抛出。
    """

    error_code: str = "CF006"

    def __init__(
        self,
        message: str,
        pump_ids: Optional[List[int]] = None,
        parameter: str = "",
        deviation: float = 0.0,
        threshold: float = 0.0,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.pump_ids = pump_ids or []
        self.parameter = parameter
        self.deviation = deviation
        self.threshold = threshold

    def to_log_format(self) -> str:
        return (
            f"[{self.error_code}] {self.message} | "
            f"pumps={self.pump_ids}, param={self.parameter}, "
            f"deviation={self.deviation:.2%}, threshold={self.threshold:.0%}"
        )


class MissingCurveError(CurveFittingError):
    """单泵曲线缺失异常 (CF007)

    当泵组处理时发现单泵曲线未注册时抛出。
    """

    error_code: str = "CF007"

    def __init__(
        self,
        message: str,
        missing_pump_ids: Optional[List[int]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.missing_pump_ids = missing_pump_ids or []

    def to_log_format(self) -> str:
        return (
            f"[{self.error_code}] {self.message} | "
            f"missing_pumps={self.missing_pump_ids}"
        )


class DataNotFoundError(CurveFittingError):
    """数据未找到异常 (CF008)

    当查询必需数据返回空时抛出。
    """

    error_code: str = "CF008"

    def __init__(
        self,
        message: str,
        query_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ):
        details = {
            "query_type": query_type,
            "entity_id": entity_id
        }
        super().__init__(message, details)
        self.query_type = query_type
        self.entity_id = entity_id

