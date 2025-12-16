"""
特性曲线拟合服务模块 (app.services.characteristic_curves)

本模块提供水泵特性曲线的拟合、验证和管理功能。

核心功能：
- 曲线拟合：支持多种拟合方法（多项式、物理模型、机器学习等）
- 结果验证：物理约束验证、统计检验
- 版本管理：拟合结果的版本控制和历史追踪
- 缓存管理：内存LRU缓存提高性能

模块结构：
- core: 核心数据结构（FitResult, ValidationResult等）
- shared: 共用组件（ResultStorage, CacheManager等）
- methods: 拟合方法实现
- curves: 曲线模块（QHCurve, QPCurve, QEtaCurve）
- constraints: 约束验证模块
- preprocessing: 数据预处理模块
- output: 结果输出模块
- pipeline: 主管道（CurveFittingPipeline）

使用方式（v2.6推荐 - 依赖注入）：
    from app.services.characteristic_curves.pipeline import CurveFittingPipeline
    from app.services.characteristic_curves.shared import ResultStorage, CacheManager
    from app.services.characteristic_curves.methods import MethodRegistry
    from app.services.characteristic_curves.core.data_structures import FitResult
    
    # 创建共用组件
    registry = MethodRegistry()
    storage = ResultStorage()
    cache = CacheManager(max_size=1000, ttl_seconds=3600)
    
    # 创建管道（显式依赖注入）
    pipeline = CurveFittingPipeline(
        method_registry=registry,
        result_storage=storage,
        cache_manager=cache
    )
    
    # 执行拟合
    result = pipeline.fit(device_id=1, curve_type='qh', ...)

使用方式（向后兼容 - 自动创建）：
    from app.services.characteristic_curves.pipeline import CurveFittingPipeline
    
    # 简化方式（组件会自动创建）
    pipeline = CurveFittingPipeline()
    result = pipeline.fit(device_id=1, curve_type='qh', ...)

设计原则：
- 依赖注入：共用层组件通过构造函数注入（v2.6新增）
- 顺序执行：禁止并发拟合多个设备
- 类型安全：完整的类型注解
- 日志规范：统一的日志格式
- 向后兼容：支持旧代码无缝升级
"""

from app.services.characteristic_curves.core.data_structures import (
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
