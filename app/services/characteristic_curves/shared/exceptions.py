"""
异常类体系

定义特性曲线拟合系统的所有异常类。

版本: v2.7
更新日期: 2025-12-11
来源: 特性曲线开发/开发文档/03_核心模块/03_共用层.md 第0节
文件路径: app/services/characteristic_curves/shared/exceptions.py
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


# ==================== 核心异常 (文档权威定义 CF001-CF007) ====================

class InsufficientDataError(CurveFittingError):
    """数据不足异常

    当训练或验证数据点数不满足最小要求时抛出。

    Raises:
        当 actual_points < min_points 时

    处理策略:
        ❌ 不使用降级数据
        ✅ 记录错误日志，跳过该泵/泵组
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


class FrequencyQueryError(CurveFittingError):
    """频率查询异常

    当无法获取变频泵的运行频率时抛出。

    Raises:
        当 fact_measurements 查询返回空或None

    处理策略:
        ❌ 不使用default_freq=50.0降级
        ✅ 记录错误日志，标记该泵组合成失败
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
    """扬程超出范围异常

    当系统扬程超出所有泵的有效H范围时抛出。

    Raises:
        当 H_system > max(H_max) 或 H_system < min(H_min)

    处理策略:
        ❌ 不返回0流量作为降级
        ✅ 抛出异常，明确告知扬程超范围
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
    """修正模型训练失败异常

    当SystemCorrectionModel训练失败时抛出。

    Raises:
        当训练数据不足或模型拟合失败

    处理策略:
        ❌ 不使用默认α=1.0
        ✅ 抛出异常，记录详细训练失败原因
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
    """P0拟合重试耗尽异常

    当auto_trigger_p0重试次数超过最大限制时抛出。

    Raises:
        当 retry_count >= max_retries

    处理策略:
        ✅ 防止死循环
        ✅ 明确告知需要人工检查数据
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
    """曲线一致性异常（v2.3新增）

    当同构泵组的曲线参数差异超出阈值时抛出。

    Raises:
        当同型号泵归一化后的H0或K参数差异过大时抛出

    场景:
        - 同构泵组P2阶段前置检查
        - 曲线一致性验证失败
    """

    error_code = "CF006"

    def __init__(
        self,
        message: str,
        pump_ids: List[int] = None,
        parameter: str = "",
        deviation: float = 0.0,
        threshold: float = 0.0,
        details: Dict[str, Any] = None
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
    """单泵曲线缺失异常【v2.4新增 P42修复】

    当泵组处理时发现单泵曲线未注册时抛出。

    场景:
        - P2泵组处理前置检查
        - 单泵曲线未完成P0拟合

    Attributes:
        missing_pump_ids: 缺失曲线的泵ID列表
    """

    error_code = "CF007"

    def __init__(
        self,
        message: str,
        missing_pump_ids: List[int] = None,
        details: Dict[str, Any] = None
    ):
        super().__init__(message, details)
        self.missing_pump_ids = missing_pump_ids or []

    def to_log_format(self) -> str:
        return (
            f"[{self.error_code}] {self.message} | "
            f"missing_pumps={self.missing_pump_ids}"
        )


class DataExtractionError(CurveFittingError):
    """数据提取异常（v2.6新增）

    当从数据库提取训练数据失败时抛出。

    Raises:
        - 数据库查询失败
        - 提取的数据为空
        - 数据格式不符合要求

    处理策略:
        ❌ 不使用空数据或默认数据降级
        ✅ 抛出异常，记录详细错误原因
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


# ==================== 向后兼容的辅助异常类 ====================

class DataError(CurveFittingError):
    """数据相关异常基类（向后兼容）"""
    pass


class DataNotFoundError(DataError):
    """数据不存在异常（向后兼容）"""
    error_code: str = "CF008"


class DataInsufficientError(InsufficientDataError):
    """数据量不足异常（向后兼容，建议使用InsufficientDataError）"""

    def __init__(
        self,
        message: str,
        required: int,
        actual: int,
        device_id: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            actual_points=actual,
            min_points=required,
            device_id=device_id
        )


class DataQualityError(DataError):
    """数据质量异常（异常值过多、缺失率过高等）"""
    error_code: str = "CF010"


# ==================== 参数异常 ====================

class ParameterError(CurveFittingError):
    """参数相关异常"""
    pass


class ParameterMissingError(ParameterError):
    """参数缺失异常（设备额定参数缺失）"""

    def __init__(
        self,
        message: str,
        missing_params: List[str],
        **kwargs
    ):
        self.missing_params = missing_params
        super().__init__(message, **kwargs)


# ==================== 拟合异常 ====================

class FittingError(CurveFittingError):
    """拟合相关异常"""
    pass


class FittingFailedError(FittingError):
    """拟合失败异常（所有方法都失败）"""
    pass


# ==================== 验证异常 ====================

class ValidationError(CurveFittingError):
    """验证相关异常"""
    pass


class ConstraintViolationError(ValidationError):
    """约束违反异常"""

    def __init__(
        self,
        message: str,
        violated_constraints: List[dict],
        **kwargs
    ):
        self.violated_constraints = violated_constraints
        super().__init__(message, **kwargs)


# ==================== P0 新增异常(设计文档3.4节) ====================


class TimeWindowSplitError(CurveFittingError):
    """时间窗口分割失败异常

    错误代码: CF016
    阶段: 零零1 TIME_WINDOW_SPLIT
    """
    error_code: str = "CF016"


class DataCleaningError(DataError):
    """数据清洗失败异常

    错误代码: CF017
    阶段: 零零4 DATA_CLEAN
    """
    error_code: str = "CF017"


class SteadyStateDetectionError(CurveFittingError):
    """稳态检测失败异常

    错误代码: CF018
    阶段: 零零5 STEADY_STATE_DETECT
    """
    error_code: str = "CF018"


class NormalizationError(CurveFittingError):
    """数据归一化失败异常

    错误代码: CF019
    阶段: 零零7 FREQ_NORMALIZE 或零零8 DATA_NORMALIZE
    """
    error_code: str = "CF019"


class FittingFailureError(FittingError):
    """拟合失败异常(重命名,与设计文档一致)

    错误代码: CF011
    阶段: 零零10 CURVE_FIT
    """
    error_code: str = "CF011"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, details)


class ValidationFailureError(ValidationError):
    """验证失败异常

    错误代码: CF012
    阶段: 零零11 RESULT_VALIDATE
    """
    error_code: str = "CF012"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, details)


class VisualizationError(CurveFittingError):
    """可视化生成失败异常

    错误代码: CF013
    阶段: 图片生成阶段
    """
    error_code: str = "CF013"


class StorageError(CurveFittingError):
    """存储失败异常

    错误代码: CF014
    阶段: 零零13 RESULT_STORE
    """
    error_code: str = "CF014"


class DatabaseConnectionError(CurveFittingError):
    """数据库连接失败异常

    错误代码: CF015
    """
    error_code: str = "CF015"
