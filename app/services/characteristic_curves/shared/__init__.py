"""
特性曲线共用层模块 (app.services.characteristic_curves.shared)

本模块提供特性曲线拟合系统的共用组件：
- ResultStorage: 结果存储管理器
- CacheManager: 缓存管理器（LRU缓存）
- BatchProcessor: 批处理器
- ParameterOptimizer: 参数优化器
- HistoricalDataEvaluator: 历史数据评估器
- TimeWindowValidator: 时间窗口验证器
- ResultOutput: 结果输出器
- CurveRegistry: P2阶段曲线注册表（v1.0新增）
- 异常类: 统一异常定义（v1.0新增）

使用方式：
    from app.services.characteristic_curves.shared import ResultStorage, CacheManager
    from app.services.characteristic_curves.shared import CurveRegistry, CurveEntry
    from app.services.characteristic_curves.shared.exceptions import CurveFittingError
"""

from app.services.characteristic_curves.shared.batch_processor import BatchProcessor
from app.services.characteristic_curves.shared.cache_manager import CacheManager
from app.services.characteristic_curves.shared.historical_data_evaluator import (
    CURVE_METRICS,
    HistoricalDataEvaluator,
    TimeWindow,
    TimeWindowSplitResult,
)
from app.services.characteristic_curves.shared.parameter_optimizer import ParameterOptimizer
from app.services.characteristic_curves.shared.result_output import ResultOutput
from app.services.characteristic_curves.shared.result_storage import ResultStorage
from app.services.characteristic_curves.shared.time_window_splitter import TimeWindowSplitter

# v1.0新增：P2阶段曲线注册表
from app.services.characteristic_curves.shared.curve_registry import (
    CurveRegistry,
    CurveEntry,
)

# v1.0新增：统一异常定义
from app.services.characteristic_curves.shared.exceptions import (
    CurveFittingError,
    InsufficientDataError,
    DataExtractionError,
    FrequencyQueryError,
    HeadOutOfRangeError,
    CorrectionModelTrainingError,
    P0FittingRetryExhaustedError,
    CurveInconsistencyError,
    MissingCurveError,
    DataNotFoundError,
)

__all__ = [
    # 原有模块
    "ResultStorage",
    "CacheManager",
    "BatchProcessor",
    "ParameterOptimizer",
    "HistoricalDataEvaluator",
    "TimeWindow",
    "TimeWindowSplitResult",
    "TimeWindowSplitter",
    "ResultOutput",
    "CURVE_METRICS",
    # v1.0新增：曲线注册表
    "CurveRegistry",
    "CurveEntry",
    # v1.0新增：异常类
    "CurveFittingError",
    "InsufficientDataError",
    "DataExtractionError",
    "FrequencyQueryError",
    "HeadOutOfRangeError",
    "CorrectionModelTrainingError",
    "P0FittingRetryExhaustedError",
    "CurveInconsistencyError",
    "MissingCurveError",
    "DataNotFoundError",
]

