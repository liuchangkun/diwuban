"""
数学拟合方法子包 (app.services.characteristic_curves.methods.math)

本模块包含所有数学类拟合方法的实现，包括：
- 多项式方法 (polynomial.py)
- 统计方法 (statistical.py)
- 样条方法 (spline.py)
- 核方法 (kernel.py)
- 有理函数方法 (rational.py)
- 局部方法 (local.py)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/01_数学方法.md
"""

from .polynomial import (
    MathPoly2Method,
    MathPoly3Method,
    register_polynomial_methods,
)
from .statistical import (
    MathStatGaussianMethod,
    register_statistical_methods,
)
from .spline import (
    MathSplineCubicMethod,
    MathSplineBsplineMethod,
    register_spline_methods,
)
from .kernel import (
    MathKernelRbfMethod,
    register_kernel_methods,
)
from .rational import (
    MathRationalPadeMethod,
    register_rational_methods,
)
from .local import (
    MathLocalLowessMethod,
    register_local_methods,
)

__all__ = [
    # 多项式方法
    "MathPoly2Method",
    "MathPoly3Method",
    "register_polynomial_methods",
    # 统计方法
    "MathStatGaussianMethod",
    "register_statistical_methods",
    # 样条方法
    "MathSplineCubicMethod",
    "MathSplineBsplineMethod",
    "register_spline_methods",
    # 核方法
    "MathKernelRbfMethod",
    "register_kernel_methods",
    # 有理函数方法
    "MathRationalPadeMethod",
    "register_rational_methods",
    # 局部方法
    "MathLocalLowessMethod",
    "register_local_methods",
]


def register_all_math_methods() -> None:
    """注册所有数学方法到 MethodRegistry"""
    register_polynomial_methods()
    register_statistical_methods()
    register_spline_methods()
    register_kernel_methods()
    register_rational_methods()
    register_local_methods()

