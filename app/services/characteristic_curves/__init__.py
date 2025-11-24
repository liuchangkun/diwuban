"""
特性曲线拟合服务模块 (app.services.characteristic_curves)

本模块提供水泵特性曲线的拟合、验证和管理功能。

核心功能：
- 曲线拟合：支持多种拟合方法（多项式、物理模型、机器学习等）
- 结果验证：物理约束验证、统计检验
- 版本管理：拟合结果的版本控制和历史追踪
- 缓存管理：内存LRU缓存提高性能

模块结构：
- models: 核心数据结构（FitResult, ValidationResult等）
- shared: 共用组件（ResultStorage, CacheManager等）
- methods: 拟合方法实现
- curves: 曲线模块（QHCurve, QPCurve, QEtaCurve）
- constraints: 约束验证模块
- preprocessing: 数据预处理模块
- output: 结果输出模块

使用方式：
    from app.services.characteristic_curves import CurveFittingPipeline
    from app.services.characteristic_curves.models import FitResult, ValidationResult

设计原则：
- 顺序执行：禁止并发拟合多个设备
- 类型安全：完整的类型注解
- 日志规范：统一的日志格式
"""

from app.services.characteristic_curves.models import (
    FitResult,
    ValidationResult,
    EvaluationReport,
    MethodResult,
    CurveType,
    FitStatus,
    ValidationStatus,
)

__all__ = [
    # 核心数据结构
    "FitResult",
    "ValidationResult",
    "EvaluationReport",
    "MethodResult",
    # 类型定义
    "CurveType",
    "FitStatus",
    "ValidationStatus",
]

