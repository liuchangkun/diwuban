"""
特性曲线拟合服务（app.services.curve_fitting）

本模块负责水泵特性曲线的拟合计算，提供：

核心功能：
- 数据预处理：清洗、过滤、异常值检测
- 曲线拟合：多种数学模型的拟合算法
- 质量评估：拟合优度、误差分析、置信区间
- 结果管理：曲线存储、版本控制、有效期管理

支持的曲线类型：
- H-Q：扬程-流量特性曲线
- η-Q：效率-流量特性曲线
- N-Q：功率-流量特性曲线

拟合方法：
- 多项式拟合：适用于大多数离心泵曲线
- 指数拟合：适用于特殊工况下的曲线
- 幂函数拟合：适用于相似工况分析
- 自定义模型：支持用户定义的数学模型
"""

from __future__ import annotations

import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

try:
    import numpy as np
    from scipy import optimize, stats
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import PolynomialFeatures
except ImportError:
    # 如果没有安装科学计算库，提供备用实现
    np = None
    optimize = None
    stats = None

from app.adapters.db.gateway import get_conn
from app.core.config.loader import Settings
from app.core.exceptions import (
    CurveFittingError,
    DataValidationError,
    error_handler,
)
from app.models import (
    Curve,
    CurveCreate,
    CurveFittingRequest,
    CurveFittingResult,
    CurveType,
    FittingMethod,
    PumpOperationPoint,
)


import logging

_act = logging.getLogger(__name__)


class CurveFittingService:
    """
    特性曲线拟合服务

    提供完整的水泵特性曲线拟合功能，包括数据预处理、
    曲线拟合、质量评估和结果管理。
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        # 拟合参数配置
        self.min_data_points = 50  # 最小数据点数
        self.outlier_threshold = 3.0  # 异常值阈值（标准差倍数）
        self.min_r_squared = 0.8  # 最小拟合优度要求

        # 检查科学计算库可用性
        if np is None:
            pass

    @error_handler(context_fields=["device_id", "curve_type"])
    async def fit_curve(self, request: CurveFittingRequest) -> CurveFittingResult:
        """
        执行曲线拟合

        Args:
            request: 拟合请求参数

        Returns:
            拟合结果
        """
        start_time = time.time()

        _act.info(
            "[流程-开始] [曲线拟合]",
            extra={
                "extra_data": {
                    "device_id": request.device_id,
                    "curve_type": request.curve_type.value,
                    "method": request.method.value,
                    "start_time": request.start_time.isoformat() if request.start_time else None,
                    "end_time": request.end_time.isoformat() if request.end_time else None,
                }
            },
        )

        try:
            # 1. 数据获取和预处理
            _act.info("[流程-阶段] [运行数据获取]")
            raw_data = await self._fetch_operation_data(request)
            _act.info(
                "[流程-阶段] [运行数据已获取]",
                extra={"extra_data": {"total_points": len(raw_data)}},
            )

            if len(raw_data) < self.min_data_points:
                _act.warning(
                    "[流程-跳过] [数据点不足]",
                    extra={
                        "extra_data": {
                            "total_points": len(raw_data),
                            "min_required": self.min_data_points,
                        }
                    },
                )
                return CurveFittingResult(
                    success=False,
                    total_points=len(raw_data),
                    used_points=0,
                    outliers_removed=0,
                    error_message=f"数据点数不足，需要至少 {self.min_data_points} 个点",
                    fitting_duration_ms=(time.time() - start_time) * 1000,
                )

            # 2. 数据清洗和过滤
            _act.info("[流程-阶段] [数据清洗开始]")
            cleaned_data, outliers_count = self._preprocess_data(raw_data, request)
            _act.info(
                "[流程-阶段] [数据清洗完成]",
                extra={
                    "extra_data": {
                        "cleaned_points": len(cleaned_data),
                        "outliers_removed": outliers_count,
                    }
                },
            )

            if len(cleaned_data) < request.min_data_points:
                _act.warning(
                    "[流程-跳过] [清洗后数据不足]",
                    extra={
                        "extra_data": {
                            "cleaned_points": len(cleaned_data),
                            "min_required": request.min_data_points,
                        }
                    },
                )
                return CurveFittingResult(
                    success=False,
                    total_points=len(raw_data),
                    used_points=len(cleaned_data),
                    outliers_removed=outliers_count,
                    error_message="清洗后数据点数不足",
                    fitting_duration_ms=(time.time() - start_time) * 1000,
                )

            # 3. 执行拟合
            _act.info(
                "[流程-阶段] [曲线拟合计算开始]",
                extra={
                    "extra_data": {
                        "method": request.method.value,
                        "curve_type": request.curve_type.value,
                        "data_points": len(cleaned_data),
                    }
                },
            )
            if np is not None:
                # 使用完整的科学计算库
                equation, r_squared, quality_metrics = await self._fit_with_scipy(
                    cleaned_data, request
                )
            else:
                # 使用简化算法
                equation, r_squared, quality_metrics = await self._fit_simplified(
                    cleaned_data, request
                )
            _act.info(
                "[流程-阶段] [曲线拟合计算完成]",
                extra={
                    "extra_data": {
                        "r_squared": float(r_squared),
                        "rmse": float(quality_metrics.get("rmse", 0)),
                        "mae": float(quality_metrics.get("mae", 0)),
                    }
                },
            )

            # 4. 质量检查
            _act.info("[流程-阶段] [拟合质量检查]")
            if r_squared < request.min_r_squared:
                _act.warning(
                    "[流程-跳过] [拟合质量不达标]",
                    extra={
                        "extra_data": {
                            "r_squared": float(r_squared),
                            "min_required": request.min_r_squared,
                        }
                    },
                )
                return CurveFittingResult(
                    success=False,
                    r_squared=Decimal(str(r_squared)),
                    total_points=len(raw_data),
                    used_points=len(cleaned_data),
                    outliers_removed=outliers_count,
                    error_message=f"拟合质量不达标，R² = {r_squared:.4f} < {request.min_r_squared}",
                    fitting_duration_ms=(time.time() - start_time) * 1000,
                )

            # 5. 创建曲线对象
            _act.info("[流程-阶段] [曲线记录创建]")
            curve = await self._create_curve_record(
                request, equation, r_squared, len(cleaned_data)
            )
            _act.info(
                "[流程-阶段] [曲线记录已创建]",
                extra={"extra_data": {"curve_id": curve.curve_id}},
            )

            # 6. 生成结果
            result = CurveFittingResult(
                success=True,
                curve=curve,
                r_squared=Decimal(str(r_squared)),
                rmse=Decimal(str(quality_metrics.get("rmse", 0))),
                mae=Decimal(str(quality_metrics.get("mae", 0))),
                total_points=len(raw_data),
                used_points=len(cleaned_data),
                outliers_removed=outliers_count,
                fitting_duration_ms=(time.time() - start_time) * 1000,
                algorithm_version="1.0.0",
            )

            _act.info(
                "[流程-完成] [曲线拟合]",
                extra={
                    "extra_data": {
                        "device_id": request.device_id,
                        "r_squared": float(r_squared),
                        "total_points": len(raw_data),
                        "used_points": len(cleaned_data),
                        "outliers_removed": outliers_count,
                        "duration_ms": result.fitting_duration_ms,
                    }
                },
            )

            return result

        except Exception as e:
            _act.error(
                "[流程-错误] [曲线拟合失败]",
                extra={"extra_data": {"device_id": request.device_id, "error": str(e)}},
                exc_info=True,
            )
            raise CurveFittingError(f"曲线拟合失败: {e}") from e

    async def _fetch_operation_data(
        self, request: CurveFittingRequest
    ) -> List[PumpOperationPoint]:
        """
        获取运行数据

        从数据库中获取指定时间范围内的泵运行数据。
        """
        _act.info(
            "[数据库-查询] [运行数据查询开始]",
            extra={
                "extra_data": {
                    "device_id": request.device_id,
                    "start_time": request.start_time.isoformat() if request.start_time else None,
                    "end_time": request.end_time.isoformat() if request.end_time else None,
                }
            },
        )

        # 构建查询SQL
        sql = """
        SELECT
            timestamp,
            flow_rate,
            pressure,
            power,
            frequency
        FROM operation_data
        WHERE device_id = %s
            AND timestamp >= %s AND timestamp < %s
            AND flow_rate IS NOT NULL
            AND power IS NOT NULL
            AND status = 1  -- 正常运行状态
        ORDER BY timestamp
        """

        data_points = []

        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql, (request.device_id, request.start_time, request.end_time)
                )

                for row in cur.fetchall():
                    timestamp, flow_rate, pressure, power, frequency = row

                    # 计算扬程（如果有压力数据）
                    head = None
                    if pressure is not None:
                        # 压力转扬程的简化计算（实际应考虑液体密度和重力加速度）
                        head = float(pressure) * 102.0  # 1 MPa ≈ 102 m H2O

                    # 创建运行工况点
                    point = PumpOperationPoint(
                        timestamp=timestamp,
                        device_id=request.device_id,
                        flow_rate=Decimal(str(flow_rate)),
                        head=Decimal(str(head)) if head is not None else None,
                        power=Decimal(str(power)),
                        frequency=(
                            Decimal(str(frequency)) if frequency is not None else None
                        ),
                    )

                    data_points.append(point)

        _act.info(
            "[数据库-查询] [运行数据查询完成]",
            extra={"extra_data": {"total_points": len(data_points)}},
        )
        return data_points

    def _preprocess_data(
        self, raw_data: List[PumpOperationPoint], request: CurveFittingRequest
    ) -> Tuple[List[PumpOperationPoint], int]:
        """
        数据预处理

        包括异常值检测、数据过滤和质量检查。
        """
        _act.info(
            "[流程-阶段] [数据预处理开始]",
            extra={"extra_data": {"raw_points": len(raw_data)}},
        )

        cleaned_data = []
        outliers_removed = 0

        if request.remove_outliers and np is not None:
            _act.info("[流程-阶段] [异常值检测-Z-score方法]")
            # 使用科学计算库进行异常值检测
            flow_rates = [float(point.flow_rate) for point in raw_data]
            powers = [float(point.power) for point in raw_data]

            # 使用 Z-score 方法检测异常值
            flow_z_scores = np.abs(stats.zscore(flow_rates))
            power_z_scores = np.abs(stats.zscore(powers))

            for i, point in enumerate(raw_data):
                # 检查是否为异常值
                is_outlier = (
                    flow_z_scores[i] > request.outlier_threshold
                    or power_z_scores[i] > request.outlier_threshold
                )

                if is_outlier:
                    outliers_removed += 1
                    continue

                # 其他过滤条件
                if self._is_valid_operating_point(point, request):
                    cleaned_data.append(point)
        else:
            # 简化的数据过滤
            _act.info("[流程-阶段] [数据过滤-简化方法]")
            for point in raw_data:
                if self._is_valid_operating_point(point, request):
                    cleaned_data.append(point)

        _act.info(
            "[流程-阶段] [数据预处理完成]",
            extra={
                "extra_data": {
                    "cleaned_points": len(cleaned_data),
                    "outliers_removed": outliers_removed,
                    "filter_rate": f"{(1 - len(cleaned_data) / len(raw_data)) * 100:.2f}%"
                    if raw_data
                    else "0%",
                }
            },
        )
        return cleaned_data, outliers_removed

    def _is_valid_operating_point(
        self, point: PumpOperationPoint, request: CurveFittingRequest
    ) -> bool:
        """
        检查运行工况点是否有效
        """
        # 基本有效性检查
        if point.flow_rate <= 0 or point.power <= 0:
            return False

        if request.operating_range_only:
            # 仅保留正常运行工况（可根据实际需要调整）
            if point.frequency is not None and (
                point.frequency < 30 or point.frequency > 50
            ):
                return False

        return True

    async def _fit_with_scipy(
        self, data: List[PumpOperationPoint], request: CurveFittingRequest
    ) -> Tuple[Dict[str, Any], float, Dict[str, float]]:
        """
        使用 SciPy 进行高精度拟合
        """
        _act.info(
            "[流程-阶段] [SciPy拟合-变量提取]",
            extra={"extra_data": {"curve_type": request.curve_type.value}},
        )
        # 提取拟合变量
        x_data, y_data = self._extract_fitting_variables(data, request.curve_type)

        if request.fitting_method == FittingMethod.POLYNOMIAL:
            _act.info("[流程-阶段] [多项式拟合方法]")
            return self._fit_polynomial_scipy(x_data, y_data, request)
        else:
            # 默认使用多项式拟合
            _act.info("[流程-阶段] [默认多项式拟合]")
            return self._fit_polynomial_scipy(x_data, y_data, request)

    def _fit_polynomial_scipy(
        self, x_data, y_data, request: CurveFittingRequest
    ) -> Tuple[Dict[str, Any], float, Dict[str, float]]:
        """
        使用 SciPy 进行多项式拟合
        """
        degree = request.polynomial_degree or 2
        _act.info(
            "[流程-阶段] [多项式拟合-sklearn]",
            extra={"extra_data": {"degree": degree, "data_points": len(x_data)}},
        )

        # 使用 sklearn 进行多项式拟合
        poly_features = PolynomialFeatures(degree=degree)
        linear_reg = LinearRegression()

        pipeline = Pipeline([("poly", poly_features), ("linear", linear_reg)])

        # 拟合
        pipeline.fit(x_data.reshape(-1, 1), y_data)

        # 预测
        y_pred = pipeline.predict(x_data.reshape(-1, 1))

        # 计算质量指标
        r_squared = r2_score(y_data, y_pred)
        rmse = np.sqrt(mean_squared_error(y_data, y_pred))
        mae = mean_absolute_error(y_data, y_pred)

        # 提取系数
        coefficients = linear_reg.coef_.tolist()
        intercept = float(linear_reg.intercept_)

        # 构建方程信息
        equation = {
            "type": "polynomial",
            "degree": degree,
            "coefficients": coefficients,
            "intercept": intercept,
            "formula": self._generate_polynomial_formula(coefficients, intercept),
        }

        quality_metrics = {"rmse": rmse, "mae": mae}

        _act.info(
            "[流程-阶段] [多项式拟合完成]",
            extra={
                "extra_data": {
                    "degree": degree,
                    "r_squared": float(r_squared),
                    "rmse": float(rmse),
                    "mae": float(mae),
                }
            },
        )
        return equation, r_squared, quality_metrics

    async def _fit_simplified(
        self, data: List[PumpOperationPoint], request: CurveFittingRequest
    ) -> Tuple[Dict[str, Any], float, Dict[str, float]]:
        """
        简化的拟合算法（不依赖科学计算库）
        """
        _act.info(
            "[流程-阶段] [简化拟合算法]",
            extra={"extra_data": {"curve_type": request.curve_type.value}},
        )

        # 提取数据
        x_values = []
        y_values = []

        for point in data:
            if request.curve_type == CurveType.N_Q:
                x_values.append(float(point.flow_rate))
                y_values.append(float(point.power))
            elif request.curve_type == CurveType.H_Q and point.head is not None:
                x_values.append(float(point.flow_rate))
                y_values.append(float(point.head))
            # 可以添加更多曲线类型的处理

        if len(x_values) < 3:
            raise CurveFittingError("数据不足，无法进行拟合")

        # 简单的线性拟合（y = ax + b）
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        # 计算线性回归系数
        a = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        b = (sum_y - a * sum_x) / n

        # 计算 R²
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(x_values, y_values))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 构建方程信息
        equation = {
            "type": "linear",
            "parameters": {"slope": a, "intercept": b},
            "formula": f"y = {a:.4f} * x + {b:.4f}",
        }

        # 简化的质量指标
        rmse = (ss_res / n) ** 0.5 if n > 0 else 0
        mae = sum(abs(y - (a * x + b)) for x, y in zip(x_values, y_values)) / n

        quality_metrics = {"rmse": rmse, "mae": mae}

        _act.info(
            "[流程-阶段] [简化拟合完成]",
            extra={
                "extra_data": {
                    "r_squared": float(r_squared),
                    "rmse": float(rmse),
                    "mae": float(mae),
                }
            },
        )
        return equation, r_squared, quality_metrics

    def _extract_fitting_variables(
        self, data: List[PumpOperationPoint], curve_type: str
    ):
        """
        提取拟合变量

        根据曲线类型提取 x 和 y 变量。
        """
        if np is not None:
            if curve_type == CurveType.N_Q:
                # 功率-流量曲线：x=流量，y=功率
                x_data = np.array([float(point.flow_rate) for point in data])
                y_data = np.array([float(point.power) for point in data])
            elif curve_type == CurveType.H_Q:
                # 扬程-流量曲线：x=流量，y=扬程
                x_data = np.array([float(point.flow_rate) for point in data])
                y_data = np.array(
                    [float(point.head) for point in data if point.head is not None]
                )
                if len(y_data) != len(x_data):
                    raise DataValidationError("扬程数据缺失，无法拟合 H-Q 曲线")
            else:
                raise CurveFittingError(f"不支持的曲线类型: {curve_type}")

            return x_data, y_data
        else:
            # 简化版本，返回原始数据
            return data, None

    def _generate_polynomial_formula(
        self, coefficients: List[float], intercept: float
    ) -> str:
        """
        生成多项式公式字符串
        """
        terms = []

        # 常数项
        if abs(intercept) > 1e-6:
            terms.append(f"{intercept:.4f}")

        # 各次项
        for i, coef in enumerate(coefficients[1:], 1):  # 跳过第一个系数（常数项）
            if abs(coef) > 1e-6:
                if i == 1:
                    terms.append(f"{coef:.4f} * x")
                else:
                    terms.append(f"{coef:.4f} * x^{i}")

        if not terms:
            return "y = 0"

        return "y = " + " + ".join(terms)

    async def _create_curve_record(
        self,
        request: CurveFittingRequest,
        equation: Dict[str, Any],
        r_squared: float,
        data_point_count: int,
    ) -> Curve:
        """
        创建曲线记录

        将拟合结果保存到数据库。
        """
        # 获取设备的泵站ID
        station_id = await self._get_device_station_id(request.device_id)

        # 生成数据时间范围描述
        source_data_range = (
            f"{request.start_time.strftime('%Y-%m-%d')} to "
            f"{request.end_time.strftime('%Y-%m-%d')}"
        )

        # 创建曲线对象
        curve_data = CurveCreate(
            station_id=station_id,
            device_id=request.device_id,
            curve_type=request.curve_type,
            equation=equation,
            r_squared=Decimal(str(r_squared)),
            valid_from=datetime.now(),
            created_by="curve_fitting_service_v1.0",
            source_data_range=source_data_range,
            fitting_method=request.fitting_method,
            data_point_count=data_point_count,
        )

        # 保存到数据库（这里简化为直接返回Curve对象）
        # 实际应该调用数据库网关保存
        curve = Curve(**curve_data.model_dump())
        curve.curve_id = 1  # 模拟数据库自增ID

        return curve

    async def _get_device_station_id(self, device_id: str) -> str:
        """
        获取设备所属的泵站ID
        """
        _act.info(
            "[数据库-查询] [设备泵站ID查询]",
            extra={"extra_data": {"device_id": device_id}},
        )

        sql = "SELECT station_id FROM device WHERE device_id = %s"

        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (device_id,))
                result = cur.fetchone()

                if result:
                    _act.info(
                        "[数据库-查询] [设备泵站ID已找到]",
                        extra={"extra_data": {"station_id": result[0]}},
                    )
                    return result[0]
                else:
                    # 如果没有找到设备，返回默认值或抛出异常
                    fallback_id = device_id.split("_")[0]  # 假设设备ID格式为 STATION_DEVICE
                    _act.warning(
                        "[数据库-查询] [设备未找到-使用回退值]",
                        extra={"extra_data": {"device_id": device_id, "fallback_id": fallback_id}},
                    )
                    return fallback_id
