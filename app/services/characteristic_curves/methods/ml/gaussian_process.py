"""
高斯过程回归拟合方法 (app.services.characteristic_curves.methods.ml.gaussian_process)

使用 sklearn.gaussian_process.GaussianProcessRegressor 实现高斯过程回归。

适用场景: 中小规模数据、需要不确定性估计的场景
适用曲线: 所有曲线类型 (qh, qp, qeta)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/03_机器学习方法.md
"""

from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MLGaussianProcessMethod(BaseMethod):
    """高斯过程回归拟合方法

    算法原理:
        高斯过程是一种概率模型，定义在函数空间上的分布。
        f(x) ~ GP(m(x), k(x, x'))
        其中 m(x) 是均值函数，k(x, x') 是协方差（核）函数。
        预测时不仅给出预测值，还提供不确定性估计（置信区间）。

    优点:
        - 提供不确定性量化（置信区间）
        - 自动平滑
        - 适合中小规模数据
        - 无需指定模型形式

    缺点:
        - 计算复杂度 O(n³)，不适合大数据
        - 超参数敏感

    适用曲线: 所有 (qh, qp, qeta)

    Attributes:
        method_id: 'ml_gaussian_process'
        method_name: '高斯过程回归'
        applicable_curves: ['qh', 'qp', 'qeta']
    """

    method_id = "ml_gaussian_process"
    method_name = "高斯过程回归"
    applicable_curves = ["qh", "qp", "qeta"]

    def __init__(
        self,
        length_scale: float = 1.0,
        noise_level: float = 0.1,
        n_restarts_optimizer: int = 10,
    ) -> None:
        """初始化高斯过程方法

        Args:
            length_scale: RBF核的长度尺度，控制平滑程度
            noise_level: 噪声水平，用于WhiteKernel
            n_restarts_optimizer: 优化器重启次数
        """
        super().__init__(method_name="高斯过程回归", method_id="ml_gaussian_process")
        self.length_scale = length_scale
        self.noise_level = noise_level
        self.n_restarts_optimizer = n_restarts_optimizer
        self._model: Optional[GaussianProcessRegressor] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行高斯过程拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（扬程H/功率P/效率η）
            constraints: 物理约束参数（ML方法不直接使用）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 重塑数据为2D数组
        X_reshaped = X.reshape(-1, 1)

        # 定义核函数: 常数核 * RBF核 + 白噪声核
        kernel = (
            ConstantKernel(1.0, constant_value_bounds=(1e-3, 1e3))
            * RBF(length_scale=self.length_scale, length_scale_bounds=(1e-2, 1e2))
            + WhiteKernel(noise_level=self.noise_level, noise_level_bounds=(1e-5, 1e1))
        )

        # 创建并训练模型
        self._model = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=self.n_restarts_optimizer,
            random_state=42,
            normalize_y=True,  # 归一化目标值
        )
        self._model.fit(X_reshaped, y)

        # 计算预测值和标准差
        y_pred, y_std = self._model.predict(X_reshaped, return_std=True)

        # 计算评估指标
        metrics = self._calculate_metrics(y, y_pred)

        # 获取质量等级
        quality_grade = self._get_quality_grade(metrics["r_squared"])

        # 创建预测函数（支持返回标准差）
        model = self._model

        def predict_func(
            x: np.ndarray, return_std: bool = False
        ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
            x_arr = np.atleast_1d(x).reshape(-1, 1)
            if return_std:
                return model.predict(x_arr, return_std=True)
            return model.predict(x_arr)

        return MethodResult(
            method_id=self.method_id,
            coefficients={
                "kernel_params": str(self._model.kernel_),
                "log_marginal_likelihood": float(
                    self._model.log_marginal_likelihood_value_
                ),
            },
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula="Gaussian Process Regression (kernel-based)",
            metadata={
                "model_type": "GaussianProcessRegressor",
                "quality_grade": quality_grade,
                "mean_std": float(np.mean(y_std)),
                "max_std": float(np.max(y_std)),
                "kernel": str(self._model.kernel_),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用训练好的模型进行预测

        Args:
            X: 自变量数组
            params: 参数字典（ML方法不使用）

        Returns:
            np.ndarray: 预测值数组
        """
        if self._model is None:
            raise ValueError("模型尚未训练，请先调用 fit() 方法")

        X_reshaped = np.atleast_1d(X).reshape(-1, 1)
        return self._model.predict(X_reshaped)

