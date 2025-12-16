"""
方法层模块 (app.services.characteristic_curves.methods)

本模块提供特性曲线拟合方法的核心组件：
- BaseMethod: 拟合方法抽象基类
- MethodRegistry: 方法注册表（线程安全单例）
- MethodBenchmark: 方法性能基准数据
- 数学方法子包 (mathematical/): 多项式、样条、核函数、有理函数、统计、局部方法
- 物理模型子包 (physical/): 泵特性方程、功率方程
- 机器学习子包 (machine_learning/): 梯度提升、随机森林、高斯过程
- 混合方法子包 (hybrid/): 物理约束多项式

版本: v1.3
更新日期: 2025-12-08
"""

from .base_method import (
    MIN_DATA_POINTS,
    MIN_EXTRACTION_POINTS,
    MIN_VALIDATION_POINTS,
    R2_EXCELLENT_THRESHOLD,
    R2_FAIR_THRESHOLD,
    R2_GOOD_THRESHOLD,
    BaseMethod,
)
from .method_registry import (
    DEFAULT_METHOD_BENCHMARKS,
    MethodBenchmark,
    MethodRegistry,
)

# 数学方法
from .mathematical import (
    MathPoly2Method,
    MathPoly3Method,
    MathStatGaussianMethod,
    MathSplineCubicMethod,
    MathSplineBsplineMethod,
    MathKernelRbfMethod,
    MathRationalPadeMethod,
    MathLocalLowessMethod,
    register_all_math_methods,
)

# 物理模型方法
from .physical import (
    PhysicsPumpCharMethod,
    PhysicsPowerEqMethod,
    register_all_physics_methods,
)

# 机器学习方法
from .machine_learning import (
    MLGradientBoostMethod,
    MLRandomForestMethod,
    MLGaussianProcessMethod,
)

# 混合方法
from .hybrid import (
    HybridPhysicsPolyMethod,
)

__all__ = [
    # 基类
    "BaseMethod",
    # 注册表
    "MethodRegistry",
    "MethodBenchmark",
    "DEFAULT_METHOD_BENCHMARKS",
    # 常量
    "MIN_DATA_POINTS",
    "MIN_EXTRACTION_POINTS",
    "MIN_VALIDATION_POINTS",
    "R2_EXCELLENT_THRESHOLD",
    "R2_GOOD_THRESHOLD",
    "R2_FAIR_THRESHOLD",
    # 数学方法
    "MathPoly2Method",
    "MathPoly3Method",
    "MathStatGaussianMethod",
    "MathSplineCubicMethod",
    "MathSplineBsplineMethod",
    "MathKernelRbfMethod",
    "MathRationalPadeMethod",
    "MathLocalLowessMethod",
    "register_all_math_methods",
    # 物理模型方法
    "PhysicsPumpCharMethod",
    "PhysicsPowerEqMethod",
    "register_all_physics_methods",
    # 机器学习方法
    "MLGradientBoostMethod",
    "MLRandomForestMethod",
    "MLGaussianProcessMethod",
    # 混合方法
    "HybridPhysicsPolyMethod",
]
