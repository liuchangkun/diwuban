"""
共用层模块 (app.services.characteristic_curves.shared)

本模块提供所有曲线模块共用的组件：
- exceptions: 异常类体系
- utils: 通用工具函数
- constants: 常量定义

版本: v2.1
更新日期: 2025-12-10
"""

from .exceptions import (
    CurveFittingError,
    DataError,
    DataNotFoundError,
    DataInsufficientError,
    DataQualityError,
    DataExtractionError,
    ParameterError,
    ParameterMissingError,
    FittingError,
    FittingFailedError,
    ValidationError,
    ConstraintViolationError,
    # P0新增异常
    TimeWindowSplitError,
    DataCleaningError,
    SteadyStateDetectionError,
    NormalizationError,
    FittingFailureError,
    ValidationFailureError,
    VisualizationError,
    StorageError,
    DatabaseConnectionError,
)

# P0新增模块
from .data_extractor import DataExtractor
from .curve_point_generator import CurvePointGenerator
from .method_selector import MethodSelector
from .time_window_validator import TimeWindowValidator
from .result_storage import ResultStorage
from .cache_manager import CacheManager
from .time_window_splitter import TimeWindowSplitter
from .historical_data_evaluator import HistoricalDataEvaluator
from .batch_processor import BatchProcessor
from .parameter_optimizer import ParameterOptimizer
from .performance_monitor import PerformanceMonitor

__all__ = [
    # 异常类
    "CurveFittingError",
    "DataError",
    "DataNotFoundError",
    "DataInsufficientError",
    "DataQualityError",
    "DataExtractionError",
    "ParameterError",
    "ParameterMissingError",
    "FittingError",
    "FittingFailedError",
    "ValidationError",
    "ConstraintViolationError",
    # P0新增异常
    "TimeWindowSplitError",
    "DataCleaningError",
    "SteadyStateDetectionError",
    "NormalizationError",
    "FittingFailureError",
    "ValidationFailureError",
    "VisualizationError",
    "StorageError",
    "DatabaseConnectionError",
    # P0新增模块
    "DataExtractor",
    "CurvePointGenerator",
    "MethodSelector",
    "TimeWindowValidator",
    "ResultStorage",
    "CacheManager",
    "TimeWindowSplitter",
    "HistoricalDataEvaluator",
    "BatchProcessor",
    "ParameterOptimizer",
    "PerformanceMonitor",
]
