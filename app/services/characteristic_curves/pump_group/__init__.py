"""泵组特性曲线处理模块 (app.services.characteristic_curves.pump_group)

本模块提供泵组特性曲线的拟合、合成、修正、控制、异常检测等完整功能。

核心组件（直接拟合路径）：
- GroupMethodAdapter: 方法适配器（复用单泵方法）
- GroupCurveFitter: 泵组曲线拟合器（支持多种方法）
- GroupMethodSelector: 方法选择器（基于配置）
- GroupDataExtractor: 数据提取器

合成与修正组件：
- ParallelSynthesizer: 并联合成器（单泵曲线→泵组曲线）
- FrequencyDataProvider: 频率数据提供器
- SystemCorrectionModel: 系统修正模型
- SystemCurveProvider: 管网系统曲线提供器
- DerivedCurveGenerator: heta/peta曲线派生器

处理与执行组件：
- PumpGroupProcessor: 泵组处理器（统一入口）
- GroupCurveComparator: 曲线对比器
- DualMethodExecutor: 双方法执行器

验证与存储组件：
- GroupCurveValidator: 曲线结果验证器
- GroupCurveHistoryEvaluator: 历史曲线评估器
- GroupCurveStorage: 曲线结果存储器
- GroupCurveReportGenerator: 报告生成器
- CombinationValidator: 泵组合有效性验证器

控制策略组件（曲线10-15）：
- StartStopStrategy: 启停策略（曲线10）
- SwitchingTimingAnalyzer: 切换时机分析（曲线11）
- SwitchingProcessSimulator: 切换过程模拟（曲线12）
- CoordinationController: 协调控制（曲线15）
- StartupSequenceAnalyzer: 启停顺序影响分析

异常检测与分析组件：
- AnomalyDetector: 逆流/倒灌/气蚀异常检测
- FlowBalanceAnalyzer: 并联泵组抢流现象分析

数据结构（统一从 core.data_structures 导入）：
- GroupOperatingPoint: 泵组运行工况点
- DirectFitResult: 直接拟合结果
- CurveFitMethod: 曲线生成方式枚举

版本: v5.0
创建日期: 2025-12-13
更新日期: 2025-12-14
"""

# 直接拟合路径组件
from .group_curve_fitter import GroupCurveFitter
from .group_data_extractor import GroupDataExtractor
from .group_method_adapter import GroupMethodAdapter
from .group_method_selector import GroupMethodSelector

# 合成与修正组件
from .parallel_synthesizer import ParallelSynthesizer
from .frequency_data_provider import FrequencyDataProvider
from .system_correction_model import SystemCorrectionModel
from .system_curve_provider import SystemCurveProvider

# 处理与执行组件
from .pump_group_processor import PumpGroupProcessor
from .group_curve_comparator import GroupCurveComparator
from .dual_method_executor import DualMethodExecutor

# 验证与存储组件
from .group_curve_validator import GroupCurveValidator, ValidationResult
from .group_curve_history_evaluator import GroupCurveHistoryEvaluator, HistoryEvaluation
from .group_curve_storage import GroupCurveStorage
from .group_curve_report_generator import GroupCurveReportGenerator

# 控制策略组件
from .start_stop_strategy import StartStopStrategy
from .switching_timing_analyzer import SwitchingTimingAnalyzer
from .switching_process_simulator import SwitchingProcessSimulator
from .coordination_controller import CoordinationController
from .startup_sequence_analyzer import StartupSequenceAnalyzer

# 异常检测与分析组件
from .anomaly_detector import AnomalyDetector, AnomalyEvent, AnomalyDetectionResult
from .flow_balance_analyzer import FlowBalanceAnalyzer, FlowBalanceResult, FlowImbalanceLevel
from .combination_validator import CombinationValidator
from .derived_curve_generator import DerivedCurveGenerator

# 数据结构从统一位置导出（方便外部使用）
from app.services.characteristic_curves.core.data_structures import (
    GroupOperatingPoint,
    DirectFitResult,
    CurveFitMethod,
)

__all__ = [
    # 直接拟合路径组件
    "GroupCurveFitter",
    "GroupDataExtractor",
    "GroupMethodAdapter",
    "GroupMethodSelector",
    # 合成与修正组件
    "ParallelSynthesizer",
    "FrequencyDataProvider",
    "SystemCorrectionModel",
    "SystemCurveProvider",
    "DerivedCurveGenerator",
    # 处理与执行组件
    "PumpGroupProcessor",
    "GroupCurveComparator",
    "DualMethodExecutor",
    # 验证与存储组件
    "GroupCurveValidator",
    "ValidationResult",
    "GroupCurveHistoryEvaluator",
    "HistoryEvaluation",
    "GroupCurveStorage",
    "GroupCurveReportGenerator",
    "CombinationValidator",
    # 控制策略组件
    "StartStopStrategy",
    "SwitchingTimingAnalyzer",
    "SwitchingProcessSimulator",
    "CoordinationController",
    "StartupSequenceAnalyzer",
    # 异常检测与分析组件
    "AnomalyDetector",
    "AnomalyEvent",
    "AnomalyDetectionResult",
    "FlowBalanceAnalyzer",
    "FlowBalanceResult",
    "FlowImbalanceLevel",
    # 数据结构
    "GroupOperatingPoint",
    "DirectFitResult",
    "CurveFitMethod",
]
