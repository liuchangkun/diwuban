"""
梯度提升拟合方法 (app.services.characteristic_curves.methods.ml.gradient_boost)

使用 sklearn.ensemble.GradientBoostingRegressor 实现梯度提升回归。

适用场景: 大数据量（>1000点）、复杂非线性关系
适用曲线: 所有曲线类型 (qh, qp, qeta)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/03_机器学习方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.models import MethodResult


class MLGradientBoostMethod(BaseMethod):
    """梯度提升拟合方法

    算法原理:
        梯度提升是一种集成学习方法，通过迭代训练弱学习器（决策树），
        每轮训练的目标是拟合前一轮的残差，最终将所有弱学习器加权组合。

    优点:
        - 对复杂非线性关系有很好的拟合能力
        - 对异常值有一定鲁棒性
        - 支持特征重要性评估

    缺点:
        - 训练时间较长
        - 模型不可解释（黑盒）
        - 可能过拟合

    适用曲线: 所有 (qh, qp, qeta)

    Attributes:
        method_id: 'ml_gradient_boost'
        method_name: '梯度提升'
        applicable_curves: ['qh', 'qp', 'qeta']
        min_data_points: 100 (建议1000+以获得最佳效果)
    """

    method_id = "ml_gradient_boost"
    method_name = "梯度提升"
    applicable_curves = ["qh", "qp", "qeta"]
    min_data_points = 100  # 最小数据点数，建议1000+

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 3,
        learning_rate: float = 0.1,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
    ) -> None:
        """初始化梯度提升方法

        Args:
            n_estimators: 树的数量，默认100
            max_depth: 树的最大深度，默认3
            learning_rate: 学习率，默认0.1
            min_samples_split: 分裂所需最小样本数，默认5
            min_samples_leaf: 叶节点最小样本数，默认2
        """
        super().__init__(method_name="梯度提升", method_id="ml_gradient_boost")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self._model: Optional[GradientBoostingRegressor] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行梯度提升拟合

        Args:
            X: 自变量数组（流量Q）
            y: 因变量数组（扬程H/功率P/效率η）
            constraints: 物理约束参数（ML方法不直接使用，仅后验验证）
            **kwargs: 其他参数

        Returns:
            MethodResult: 拟合结果
        """
        # 数据量检查
        if len(X) < self.min_data_points:
            self._logger.warning(
                f"数据量不足: {len(X)} < {self.min_data_points}，结果可能不稳定"
            )

        # 重塑数据为2D数组
        X_reshaped = X.reshape(-1, 1)

        # 创建并训练模型
        self._model = GradientBoostingRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            random_state=42,
        )
        self._model.fit(X_reshaped, y)

        # 计算预测值
        y_pred = self._model.predict(X_reshaped)

        # 计算评估指标
        metrics = self._calculate_metrics(y, y_pred)

        # 获取质量等级
        quality_grade = self._get_quality_grade(metrics["r_squared"])

        # 创建预测函数（闭包捕获模型）
        model = self._model

        def predict_func(x: np.ndarray) -> np.ndarray:
            x_arr = np.atleast_1d(x).reshape(-1, 1)
            return model.predict(x_arr)

        return MethodResult(
            method_id=self.method_id,
            coefficients={
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
            },
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula="Gradient Boosting Regressor (ensemble model)",
            metadata={
                "model_type": "GradientBoostingRegressor",
                "quality_grade": quality_grade,
                "n_features": 1,
                "training_score": float(self._model.score(X_reshaped, y)),
            },
        )

    def predict(self, X: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        """使用训练好的模型进行预测

        Args:
            X: 自变量数组
            params: 参数字典（ML方法不使用，模型已内化参数）

        Returns:
            np.ndarray: 预测值数组
        """
        if self._model is None:
            raise ValueError("模型尚未训练，请先调用 fit() 方法")

        X_reshaped = np.atleast_1d(X).reshape(-1, 1)
        return self._model.predict(X_reshaped)

