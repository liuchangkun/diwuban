"""
机器学习拟合方法模块 (app.services.characteristic_curves.methods.ml)

本模块提供基于机器学习的曲线拟合方法。

包含方法:
- MLGradientBoostMethod: 梯度提升拟合方法
- MLRandomForestMethod: 随机森林拟合方法
- MLGaussianProcessMethod: 高斯过程回归方法

版本: v1.0
更新日期: 2025-12-08
"""

from app.services.characteristic_curves.methods.machine_learning.gradient_boost import (
    MLGradientBoostMethod,
)
from app.services.characteristic_curves.methods.machine_learning.random_forest import (
    MLRandomForestMethod,
)
from app.services.characteristic_curves.methods.machine_learning.gaussian_process import (
    MLGaussianProcessMethod,
)

__all__ = [
    "MLGradientBoostMethod",
    "MLRandomForestMethod",
    "MLGaussianProcessMethod",
]
