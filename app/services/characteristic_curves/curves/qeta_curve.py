"""
Q-η曲线处理器 (app.services.characteristic_curves.curves.qeta_curve)

流量-效率曲线的专用处理器。

版本: v1.0
更新日期: 2025-12-08
参考文档: 特性曲线开发/开发文档/04_曲线模块/03_QEta曲线.md

物理特性:
- 单调性: 单峰 (先增后减)
- 效率范围: η ∈ [0, 100%]
- 最佳效率点: BEP (Best Efficiency Point)
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    FitResult,
    MonotonicityType,
)


class QEtaCurve(BaseCurve):
    """Q-η曲线处理器

    流量-效率曲线，物理约束为单峰特性。

    使用方式:
        curve = QEtaCurve()
        result = curve.fit(Q_values, eta_values)
    """

    curve_type = CurveType.QETA
    monotonicity = MonotonicityType.UNIMODAL
    recommended_methods = ["math_stat_gaussian", "math_poly_3", "math_poly_4"]

    def __init__(
        self,
        storage: Optional[Any] = None,
        cache: Optional[Any] = None,
        batch_processor: Optional[Any] = None,
        parameter_optimizer: Optional[Any] = None,
        historical_evaluator: Optional[Any] = None,
    ) -> None:
        """初始化Q-η曲线处理器

        Args:
            storage: 结果存储器实例
            cache: 缓存管理器实例
            batch_processor: 批处理器实例
            parameter_optimizer: 参数优化器实例
            historical_evaluator: 历史数据评估器实例
        """
        # 调用父类构造函数,传递依赖组件
        super().__init__(
            storage=storage,
            cache=cache,
            batch_processor=batch_processor,
            parameter_optimizer=parameter_optimizer,
            historical_evaluator=historical_evaluator
        )

    def _init_submodules(self) -> None:
        """初始化子模块"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def extract_data(
        self, device_id: int, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """提取Q-η数据

        从 fact_measurements 表提取流量和效率数据。
        效率在数据库中为百分比(0-100),提取后转为小数(0-1)。

        Args:
            device_id: 设备ID
            start_time: 起始时间
            end_time: 结束时间

        Returns:
            DataFrame: 包含 ts, Q, eta 列的数据
        """
        from app.adapters.db import get_connection

        sql = """
            SELECT
                fm.ts,
                MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) AS Q,
                MAX(CASE WHEN mc.metric_key = 'pump_efficiency' THEN fm.value END) AS eta
            FROM fact_measurements fm
            JOIN dim_metric_config mc ON fm.metric_id = mc.id
            WHERE fm.device_id = %s
              AND fm.ts BETWEEN %s AND %s
              AND mc.metric_key IN ('pump_flow_rate', 'pump_efficiency')
            GROUP BY fm.ts
            HAVING MAX(CASE WHEN mc.metric_key = 'pump_flow_rate' THEN fm.value END) IS NOT NULL
               AND MAX(CASE WHEN mc.metric_key = 'pump_efficiency' THEN fm.value END) IS NOT NULL
            ORDER BY fm.ts
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (device_id, start_time, end_time))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]

        data = pd.DataFrame(rows, columns=columns)

        # 效率从百分比(0-100)转为小数(0-1)
        if not data.empty and 'eta' in data.columns:
            data['eta'] = data['eta'] / 100.0

        self._logger.info(
            f"[QEta] 提取数据: device_id={device_id}, 数据点={len(data)}"
        )

        return data

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理Q-η数据

        清洗数据,过滤无效值。
        效率范围: 0 ≤ η ≤ 1 (小数形式)

        Args:
            data: 原始数据

        Returns:
            DataFrame: 清洗后的数据
        """
        if data.empty:
            return data

        # 删除缺失值
        clean = data.dropna(subset=["Q", "eta"])

        # 过滤无效值(效率范围 0–1,流量≥0)
        clean = clean[(clean["Q"] >= 0) & (
            clean["eta"] >= 0) & (clean["eta"] <= 1.0)]

        self._logger.info(
            f"[QEta] 预处理: 原始={len(data)}, 清洗后={len(clean)}, "
            f"过滤={len(data) - len(clean)}"
        )

        return clean

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-η曲线约束

        从数据中找到 BEP(最佳效率点),结合额定参数计算物理约束。

        Args:
            data: 预处理后的数据
            device_params: 设备参数,需包含 rated_flow, rated_efficiency

        Returns:
            Dict: 约束参数字典
        """
        constraints = self.get_default_constraints()

        # 检查必要参数并记录警告
        if 'rated_flow' not in device_params or device_params.get('rated_flow') is None:
            self._logger.warning(
                "[QEta约束] 缺少rated_flow参数，使用默认值300.0m³/h（建议配置正确的设备参数）"
            )
        if 'rated_efficiency' not in device_params or device_params.get('rated_efficiency') is None:
            self._logger.warning(
                "[QEta约束] 缺少rated_efficiency参数，使用默认值0.8（建议配置正确的设备参数）"
            )

        # 从设备参数中获取额定值
        rated_flow = device_params.get('rated_flow') or 300.0  # m³/h
        rated_efficiency = device_params.get('rated_efficiency') or 0.8  # 小数

        # 从数据中找到最佳效率点(BEP)
        if not data.empty and 'eta' in data.columns:
            idx_max = data['eta'].idxmax()
            Q_BEP = float(data.loc[idx_max, 'Q'])
            eta_max = float(data.loc[idx_max, 'eta'])
        else:
            # 数据为空时使用默认值
            Q_BEP = rated_flow
            eta_max = rated_efficiency

        constraints.update({
            "monotonicity_type": "unimodal",
            "min_eta": 0.0,
            "max_eta": 1.0,  # 小数形式
            "min_Q": 0.0,
            "max_Q": rated_flow * 1.5,
            "rated_flow": rated_flow,
            "rated_efficiency": rated_efficiency,
            "Q_BEP": Q_BEP,
            "eta_max": eta_max,
            "efficiency_range": (0.0, 1.0),
            # BEP合理区间: 0.6 * rated_flow < Q_BEP < 1.2 * rated_flow
            "bep_valid_range": (rated_flow * 0.6, rated_flow * 1.2),
        })

        self._logger.info(
            f"[QEta] 约束计算: Q_BEP={Q_BEP:.1f}, eta_max={eta_max:.3f}, "
            f"rated_flow={rated_flow:.1f}"
        )

        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行Q-η曲线拟合

        使用多项式拟合单峰曲线。
        η 范围限制在 [0, 1]。

        Args:
            x_values: 流量数据(Q)
            y_values: 效率数据(η,小数形式 0–1)
            method_id: 方法标识
            **kwargs: 额外参数
                - degree: 多项式次数(默认3)
                - device_id: 设备ID
                - time_range: 数据时间范围

        Returns:
            FitResult: 拟合结果
        """
        try:
            # 使用三次多项式拟合单峰曲线
            degree = kwargs.get("degree", 3)
            coeffs = np.polyfit(x_values, y_values, degree)

            y_fitted = np.polyval(coeffs, x_values)

            # 限制拟合值在[0, 1]范围
            y_fitted = np.clip(y_fitted, 0.0, 1.0)

            # 计算R²
            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))
            mae = np.mean(np.abs(y_values - y_fitted))
            mape = np.mean(
                np.abs((y_values - y_fitted) / (y_values + 1e-10))) * 100

            # 检查单峰约束：应有且仅有一个极大值点
            dydx = np.diff(y_fitted)
            sign_changes = np.sum(np.diff(np.sign(dydx)) != 0)
            constraints_satisfied = sign_changes == 1  # 应有一个极值点

            # 找到最佳效率点
            bep_idx = np.argmax(y_fitted)
            q_bep = float(x_values[bep_idx])
            eta_max = float(y_fitted[bep_idx])

            # 生成公式字符串
            formula = self._generate_formula(coeffs)

            # 评估质量等级
            if r_squared >= 0.98:
                quality_grade = "excellent"
            elif r_squared >= 0.95:
                quality_grade = "good"
            elif r_squared >= 0.90:
                quality_grade = "acceptable"
            else:
                quality_grade = "poor"

            # 转换系数为字典格式
            coeffs_dict = {f"c{i}": float(c) for i, c in enumerate(coeffs)}

            return FitResult(
                success=True,
                device_id=kwargs.get('device_id'),
                curve_type=self.curve_type.value,
                method_id=method_id,
                method_name=f"多项式拟合(degree={degree})",
                version=kwargs.get('version', ''),
                # 系数改为字典
                coefficients=coeffs_dict,
                formula=formula,
                r_squared=r_squared,
                rmse=rmse,
                mae=mae,
                mape=mape,
                data_points=len(x_values),
                time_range=kwargs.get('time_range'),
                quality_grade=quality_grade,
                constraints_satisfied=constraints_satisfied,
                metadata={
                    "Q_bep": q_bep,
                    "eta_max": eta_max,
                    "degree": degree,
                },
            )

        except Exception as e:
            self._logger.error(f"Q-η曲线拟合失败: {e}", exc_info=True)
            return FitResult(
                success=False,
                device_id=kwargs.get('device_id'),
                curve_type=self.curve_type.value,
                method_id=method_id,
                method_name="拟合失败",
                metadata={"error": str(e)},
            )

    def _generate_formula(self, coeffs: np.ndarray) -> str:
        """生成公式字符串

        Args:
            coeffs: 多项式系数数组

        Returns:
            str: 公式字符串,如 "η = 0.0001*Q^3 - 0.005*Q^2 + 0.1*Q + 0.2"
        """
        degree = len(coeffs) - 1
        terms = []
        for i, c in enumerate(coeffs):
            power = degree - i
            if abs(c) < 1e-10:  # 系数接近0则跳过
                continue
            if power == 0:
                terms.append(f"{c:.4f}")
            elif power == 1:
                terms.append(f"{c:.4f}*Q")
            else:
                terms.append(f"{c:.6f}*Q^{power}")

        formula_str = " + ".join(terms).replace("+ -", "- ")
        return f"η = {formula_str} (η为小数,0–1)"
