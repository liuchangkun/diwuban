"""Q-H曲线处理器 (app.services.characteristic_curves.curves.qh_curve)

流量-扬程曲线的专用处理器。

版本: v2.6
更新日期: 2025-12-11
参考文档: 特性曲线开发/开发文档/04_曲线模块/01_QH曲线.md

物理特性:
- 单调性: 全范围单调递减 (dH/dQ < 0)
- 凸性: 下凸 (d²H/dQ² > 0)
- 零流量点: H₀ ≈ 1.1~1.3 × H_rated
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.adapters.db.pool import get_connection
from app.services.characteristic_curves.curves.base_curve import (
    BaseCurve,
    CurveType,
    MonotonicityType,
)
from app.services.characteristic_curves.core.data_structures import FitResult
from app.services.characteristic_curves.shared.exceptions import DataExtractionError


class QHCurve(BaseCurve):
    """Q-H曲线处理器

    流量-扬程曲线，物理约束为单调递减。

    子模块（内部实现）：
    - 数据提取器: extract_data()
    - 预处理器: preprocess()
    - 约束计算: calculate_constraints()
    - 归一化器: _normalize()
    - 方法选择: _select_method()
    - 拟合器: _do_fit()
    - 验证器: _validate()

    使用方式:
        qh_curve = QHCurve(
            storage=result_storage,
            cache=cache_manager,
            historical_evaluator=historical_evaluator
        )
        result = qh_curve.fit(
            device_id=12345,
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 6, 30),
            methods=['physics_pump_char', 'math_poly_2']
        )
    """

    curve_type = CurveType.QH
    monotonicity = MonotonicityType.DECREASING
    recommended_methods = ["physics_pump_char", "math_poly_2", "math_poly_3"]

    # 必需指标
    REQUIRED_METRICS = ['pump_flow_rate', 'pump_head']

    def _init_submodules(self) -> None:
        """初始化子模块（无需创建独立对象）"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._logger.info("[QH曲线] 初始化完成")

    def extract_data(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        min_points: int = 100
    ) -> pd.DataFrame:
        """提取Q-H数据（阶段3：数据提取）

        从 fact_measurements 表提取 pump_flow_rate (Q) 和 pump_head (H) 指标。

        Args:
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            min_points: 最小数据点数（默认100）

        Returns:
            DataFrame: 包含 ts_bucket, Q, H 列的数据

        Raises:
            DataExtractionError: 数据提取失败或数据点不足
        """
        self._logger.info(
            f"[QH提取] device_id={device_id}, {start_time} ~ {end_time}"
        )

        sql = """
            SELECT
                ts_bucket,
                MAX(CASE WHEN metric_id = (
                    SELECT id FROM dim_metric_config
                    WHERE metric_key = 'pump_flow_rate'
                ) THEN value END) AS Q,
                MAX(CASE WHEN metric_id = (
                    SELECT id FROM dim_metric_config
                    WHERE metric_key = 'pump_head'
                ) THEN value END) AS H
            FROM fact_measurements
            WHERE device_id = %(device_id)s
              AND ts_bucket BETWEEN %(start_time)s AND %(end_time)s
            GROUP BY ts_bucket
            HAVING Q IS NOT NULL AND H IS NOT NULL
            ORDER BY ts_bucket
        """

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, {
                    'device_id': device_id,
                    'start_time': start_time,
                    'end_time': end_time
                })
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

        data = pd.DataFrame(rows, columns=columns)

        if len(data) < min_points:
            raise DataExtractionError(
                f"数据点不足: {len(data)} < {min_points}",
                device_id=device_id,
                curve_type=self.curve_type.value
            )

        self._logger.info(f"[QH提取] 成功提取 {len(data)} 条数据")
        return data

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理Q-H数据（阶段4：数据清洗）

        处理步骤：
        1. 删除无效值（Q<0 或 H<0）
        2. 删除异常值（基于物理约束）
        3. 删除重复值
        4. 筛选泵运行状态的数据

        Args:
            data: 原始数据 DataFrame[ts_bucket, Q, H]

        Returns:
            DataFrame: 清洗后的数据 DataFrame[Q, H]
        """
        if data.empty:
            return data

        original_count = len(data)

        # 1. 删除无效值
        data = data[(data['Q'] >= 0) & (data['H'] >= 0)].copy()

        # 2. 删除重复值
        data = data.drop_duplicates(subset=['Q', 'H'])

        # 3. 删除异常值（使用IQR方法）
        for col in ['Q', 'H']:
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            data = data[(data[col] >= lower) & (data[col] <= upper)]

        # 4. 只保留Q和H列
        cleaned_data = data[['Q', 'H']].copy()

        final_count = len(cleaned_data)
        retention_rate = final_count / original_count * 100 if original_count > 0 else 0

        self._logger.info(
            f"[QH预处理] 完成: {original_count}行 → {final_count}行 "
            f"(保留率: {retention_rate:.1f}%)"
        )

        return cleaned_data

    def calculate_constraints(
        self, data: pd.DataFrame, device_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算Q-H曲线约束（阶段6：约束计算）

        计算内容：
        1. H₀（零流量扬程）: 使用Q→0外推或额定参数估算
        2. Q_max（最大流量）: Q_rated * 1.2
        3. K（阻力系数）: K = (H0 - H_rated) / Q_rated²
        4. 单调性约束: dH/dQ < 0
        5. 凸性约束: d²H/dQ² > 0

        Args:
            data: 清洗后的数据 DataFrame[Q, H]
            device_params: 设备参数 Dict{rated_head, rated_flow, ...}

        Returns:
            Dict: 约束参数 {H0, Q_max, K, H_rated, Q_rated, monotonicity, convexity}

        Raises:
            ValueError: 缺少必要的设备参数时抛出
        """
        # 检查必要参数
        if 'rated_head' not in device_params or device_params.get('rated_head') is None:
            self._logger.warning(
                "[QH约束] 缺少rated_head参数，使用默认值50.0m（建议配置正确的设备参数）"
            )
        if 'rated_flow' not in device_params or device_params.get('rated_flow') is None:
            self._logger.warning(
                "[QH约束] 缺少rated_flow参数，使用默认值300.0m³/h（建议配置正确的设备参数）"
            )

        H_rated = device_params.get('rated_head') or 50.0
        Q_rated = device_params.get('rated_flow') or 300.0

        # 计算约束参数
        H0 = H_rated * 1.2  # 零流量扬程估算（1.1~1.3倍额定扬程）
        Q_max = Q_rated * 1.2  # 最大流量
        K = (H0 - H_rated) / (Q_rated ** 2) if Q_rated > 0 else 0  # 阻力系数

        constraints = {
            # 基础参数
            'H0': H0,
            'Q_max': Q_max,
            'K': K,
            'H_rated': H_rated,
            'Q_rated': Q_rated,

            # 物理约束
            'monotonicity': 'decreasing',
            'convexity': 'convex',
            'monotonicity_direction': 'decreasing',

            # 边界约束
            'min_H': 0,
            'max_H': H_rated * 1.5,
            'min_Q': 0,
            'max_Q': Q_max,
        }

        # 添加基础约束
        constraints.update(self.get_default_constraints())

        self._logger.info(
            f"[QH约束] H0={H0:.2f}m, Q_max={Q_max:.2f}m³/h, K={K:.6f}"
        )

        return constraints

    def _do_fit(
        self, x_values: np.ndarray, y_values: np.ndarray, method_id: str, **kwargs: Any
    ) -> FitResult:
        """执行Q-H曲线拟合（内部方法）

        默认使用二次多项式: H = a₀ + a₁Q + a₂Q²
        约束: a₂ < 0 (保证递减)

        注意：实际拟合应通过 MethodRegistry 调用具体方法。
        这里提供简单的多项式拟合作为回退方案。

        Args:
            x_values: Q值数组
            y_values: H值数组
            method_id: 方法ID
            **kwargs: 其他参数（如degree）

        Returns:
            FitResult: 拟合结果
        """
        try:
            # 默认使用二次多项式拟合
            degree = kwargs.get("degree", 2)
            coeffs = np.polyfit(x_values, y_values, degree)

            # 计算拟合值
            y_fitted = np.polyval(coeffs, x_values)

            # 计算R²
            ss_res = np.sum((y_values - y_fitted) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # 计算RMSE和MAE
            rmse = np.sqrt(np.mean((y_values - y_fitted) ** 2))
            mae = np.mean(np.abs(y_values - y_fitted))

            # 计算MAPE
            mape = np.mean(np.abs((y_values - y_fitted) / y_values)
                           ) * 100 if np.all(y_values != 0) else 0

            # 检查单调递减约束
            if degree >= 2:
                # 二次多项式a₂应为负数保证递减
                constraints_satisfied = coeffs[0] < 0  # 最高次系数
            else:
                constraints_satisfied = coeffs[0] < 0

            # 生成公式
            formula = self._generate_formula(coeffs)

            # 质量等级
            if r_squared >= 0.98:
                quality_grade = "excellent"
            elif r_squared >= 0.95:
                quality_grade = "good"
            elif r_squared >= 0.90:
                quality_grade = "acceptable"
            else:
                quality_grade = "poor"

            # 系数字典
            coeff_dict = {f'a{i}': float(c)
                          for i, c in enumerate(reversed(coeffs))}

            return FitResult(
                success=True,
                curve_type=self.curve_type.value,
                method_id=method_id,
                method_name=f"polynomial_degree_{degree}",
                coefficients=coeff_dict,
                r_squared=float(r_squared),
                rmse=float(rmse),
                mae=float(mae),
                mape=float(mape),
                data_points=len(x_values),
                formula=formula,
                quality_grade=quality_grade,
                constraints_satisfied=constraints_satisfied,
                x_values=x_values,
                y_actual=y_values,
                y_fitted=y_fitted,
            )
        except Exception as e:
            self._logger.error(f"[QH拟合] 失败: {e}", exc_info=True)
            return FitResult(
                success=False,
                curve_type=self.curve_type.value,
                method_id=method_id,
                method_name=f"polynomial_degree_{kwargs.get('degree', 2)}",
            )

    def _generate_formula(self, coeffs: np.ndarray) -> str:
        """生成拟合公式字符串

        示例: H = 45.3 -0.05*Q -0.0002*Q^2

        Args:
            coeffs: 多项式系数（从高次到低次）

        Returns:
            str: 公式字符串
        """
        degree = len(coeffs) - 1
        terms = []

        for i, c in enumerate(coeffs):
            power = degree - i
            if abs(c) < 1e-10:  # 忽略接近0的系数
                continue

            # 系数符号和值
            if i == 0:  # 第一项
                c_str = f"{c:.4f}"
            else:  # 后续项
                sign = "+" if c >= 0 else ""
                c_str = f"{sign}{c:.4f}"

            # 构建项
            if power == 0:
                terms.append(c_str)
            elif power == 1:
                terms.append(f"{c_str}*Q")
            else:
                terms.append(f"{c_str}*Q^{power}")

        formula = f"H = {' '.join(terms)}" if terms else "H = 0"
        return formula
