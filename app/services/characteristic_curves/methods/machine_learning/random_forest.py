"""
随机森林拟合方法 (app.services.characteristic_curves.methods.ml.random_forest)

使用 sklearn.ensemble.RandomForestRegressor 实现随机森林回归。

适用场景: 中等规模数据、需要鲁棒性的场景
适用曲线: 所有曲线类型 (qh, qp, qeta)

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/05_拟合方法/03_机器学习方法.md
"""

from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.services.characteristic_curves.methods.base_method import BaseMethod
from app.services.characteristic_curves.core.data_structures import MethodResult


class MLRandomForestMethod(BaseMethod):
    """随机森林拟合方法

    算法原理:
        随机森林是Bagging集成方法，训练多棵决策树，
        每棵树使用随机子集（Bootstrap采样）训练，
        最终预测值为所有树预测的平均值。

    优点:
        - 鲁棒性强，对噪声和异常值不敏感
        - 不易过拟合
        - 可以评估特征重要性
        - 训练可并行化

    缺点:
        - 模型不可解释（黑盒）
        - 内存占用较大

    适用曲线: 所有 (qh, qp, qeta)

    Attributes:
        method_id: 'ml_random_forest'
        method_name: '随机森林'
        applicable_curves: ['qh', 'qp', 'qeta']
    """

    method_id = "ml_random_forest"
    method_name = "随机森林"
    applicable_curves = ["qh", "qp", "qeta"]

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
    ) -> None:
        """初始化随机森林方法

        Args:
            n_estimators: 树的数量，默认100
            max_depth: 树的最大深度，默认10
            min_samples_split: 分裂所需最小样本数，默认5
            min_samples_leaf: 叶节点最小样本数，默认2
        """
        super().__init__(method_name="随机森林", method_id="ml_random_forest")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self._model: Optional[RandomForestRegressor] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MethodResult:
        """执行随机森林拟合

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

        # 创建并训练模型
        self._model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            random_state=42,
            n_jobs=-1,  # 使用所有CPU核心
        )
        self._model.fit(X_reshaped, y)

        # 计算预测值
        y_pred = self._model.predict(X_reshaped)

        # 计算评估指标
        metrics = self._calculate_metrics(y, y_pred)

        # 获取质量等级
        quality_grade = self._get_quality_grade(metrics["r_squared"])

        # 创建预测函数
        model = self._model

        def predict_func(x: np.ndarray) -> np.ndarray:
            x_arr = np.atleast_1d(x).reshape(-1, 1)
            return model.predict(x_arr)

        # 特征重要性（单特征情况下为1.0）
        feature_importance = self._model.feature_importances_.tolist()

        return MethodResult(
            method_id=self.method_id,
            coefficients={
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "feature_importance": feature_importance,
            },
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            mape=metrics["mape"],
            predict_func=predict_func,
            formula="Random Forest Regressor (ensemble model)",
            metadata={
                "model_type": "RandomForestRegressor",
                "quality_grade": quality_grade,
                "n_features": 1,
                "oob_score": None,  # 需要设置oob_score=True才能获取
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

