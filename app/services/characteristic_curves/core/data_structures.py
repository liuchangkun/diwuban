"""
特性曲线核心数据结构 (app.services.characteristic_curves.core.data_structures)

本模块定义了特性曲线拟合系统的核心数据类。
此文件是从 models.py 迁移而来，保持所有类定义和功能不变。

⚠️ 迁移说明：
- 原始文件：app/services/characteristic_curves/models.py
- 新文件：app/services/characteristic_curves/core/data_structures.py
- 迁移日期：2025-12-10
- 推荐导入：from app.services.characteristic_curves.core import FitResult

核心数据类：
- FitResult: 拟合结果
- ValidationResult: 验证结果
- EvaluationReport: 评估报告
- MethodResult: 单个方法的拟合结果
- DeviceInfo: 设备信息
- ScenarioDetectionResult: 场景识别结果
- GroupFitResult: 泵组拟合结果（P2阶段）
- SynthesisResult: 并联合成结果（P2阶段）
- CorrectionModelConfig: 修正模型配置（P2阶段）

术语统一：
- 使用 coefficients 表示拟合系数（而非 fit_params/params）
- 使用 CurveType 类型别名确保曲线类型安全

版本: v2.5 (与06_数据结构.md保持一致)
更新日期: 2025-12-08
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TypedDict

import numpy as np

# ==================== 类型定义 ====================

# 曲线类型（使用Literal确保类型安全）
CurveType = Literal["qh", "qp", "qeta", "heta", "peta", "qnpsh"]

# 状态类型
FitStatus = Literal["active", "archived", "deprecated"]

# 验证结果类型
ValidationStatus = Literal["passed", "failed", "warning"]

# 泵类型
PumpType = Literal["variable_frequency", "soft_start", "unknown"]


# ==================== TypedDict 配置参数类型 ====================


class ValidationConfig(TypedDict, total=False):
    """验证配置参数

    用于定义拟合结果验证的阈值和容差。
    total=False 表示所有字段都是可选的。
    """

    min_r_squared: float  # 最小R²阈值
    max_rmse: float  # 最大RMSE阈值
    max_mape: float  # 最大MAPE阈值
    monotonicity_tolerance: float  # 单调性容差
    boundary_tolerance: float  # 边界条件容差


class PerformanceConfig(TypedDict, total=False):
    """性能配置参数

    用于定义拟合过程的性能相关参数。
    total=False 表示所有字段都是可选的。
    """

    fitting_timeout: int  # 拟合超时时间（秒）
    batch_size: int  # 批处理大小
    max_retries: int  # 最大重试次数
    retry_delay_seconds: float  # 重试延迟（秒）


class MethodConfigDict(TypedDict):
    """方法配置字典

    用于定义单个拟合方法的完整配置。
    """

    method_id: str  # 方法唯一标识
    method_name: str  # 方法显示名称
    priority: int  # 优先级
    validation: ValidationConfig  # 验证配置
    performance: PerformanceConfig  # 性能配置


class FitResultDict(TypedDict):
    """拟合结果字典

    与 FitResult 数据类对应的 TypedDict 版本。
    用于 API 响应和数据序列化场景。
    """

    device_id: int  # 设备ID
    curve_type: CurveType  # 曲线类型
    version: str  # 版本号
    method_id: str  # 方法ID
    coefficients: Dict[str, Any]  # 拟合系数
    r_squared: float  # R²
    rmse: float  # RMSE
    mae: float  # MAE
    mape: float  # MAPE
    status: FitStatus  # 状态


# ==================== MethodResult ====================


@dataclass
class MethodResult:
    """单个拟合方法的结果

    术语统一：使用 coefficients 而非 fit_params/params

    与 FitResult 的关系：
    - MethodResult：单个拟合方法的直接输出（由 BaseMethod.fit() 返回）
    - FitResult：完整拟合流程的最终输出（包含版本、时间范围等附加信息）
    """

    # 基本信息（必需）
    method_id: str = ""

    # 拟合系数
    coefficients: Dict[str, float] = field(default_factory=dict)

    # 评估指标
    r_squared: float = 0.0  # R²
    rmse: float = 0.0  # 均方根误差
    mae: float = 0.0  # 平均绝对误差
    mape: float = 0.0  # 平均绝对百分比误差

    # 预测函数（核心）
    predict_func: Optional[Callable[[np.ndarray], np.ndarray]] = None

    # 公式表达式
    formula: str = ""

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不含 predict_func）"""
        return {
            "method_id": self.method_id,
            "coefficients": self.coefficients,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "mae": self.mae,
            "mape": self.mape,
            "formula": self.formula,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodResult":
        """从字典创建（不含 predict_func）"""
        return cls(
            method_id=data.get("method_id", ""),
            coefficients=data.get("coefficients", {}),
            r_squared=data.get("r_squared", 0.0),
            rmse=data.get("rmse", 0.0),
            mae=data.get("mae", 0.0),
            mape=data.get("mape", 0.0),
            formula=data.get("formula", ""),
            metadata=data.get("metadata", {}),
            predict_func=None,  # 需要重建
        )


# ==================== FitResult ====================


@dataclass
class FitResult:
    """拟合结果数据类

    术语统一：使用 coefficients 而非 fit_params/params

    v2.4更新（P43修复）：添加device_id、curve_type、fitted_at、valid_q_range、valid_h_range字段
    与07_泵组处理层.md中_get_pump_fit_result()返回值对齐

    v2.6更新：合并base_curve.py中的字段，保持向后兼容
    """

    # 基本信息
    device_id: Optional[int] = None  # 设备ID
    curve_type: Optional[str] = None  # 曲线类型
    method_id: str = ""  # 方法ID
    method_name: str = ""  # 方法名称
    version: str = ""  # 版本号（YYYYMMDD_HHMMSS）

    # 拟合系数
    coefficients: Dict[str, Any] = field(default_factory=dict)

    # 评估指标
    r_squared: float = 0.0  # R²
    rmse: float = 0.0  # 均方根误差
    mae: float = 0.0  # 平均绝对误差
    mape: float = 0.0  # 平均绝对百分比误差

    # 数据信息
    data_points: int = 0  # 数据点数
    time_range: Dict[str, str] = field(default_factory=dict)  # 时间范围

    # 有效范围
    valid_q_range: Tuple[float, float] = (0.0, 5000.0)  # 有效流量范围 (m³/h)
    valid_h_range: Tuple[float, float] = (0.0, 100.0)  # 有效扬程范围 (m)

    # 归一化参数
    normalization_params: Dict[str, Dict[str, float]
                               ] = field(default_factory=dict)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    fitted_at: Optional[datetime] = None  # 拟合完成时间
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 可选：原始数据和拟合值（用于可视化，不持久化）
    x_values: Optional[np.ndarray] = None  # X轴值
    y_actual: Optional[np.ndarray] = None  # 实际Y值
    y_fitted: Optional[np.ndarray] = None  # 拟合Y值

    # 兼容字段（来自base_curve.py）
    success: bool = True  # 是否成功（向后兼容）
    formula: str = ""  # 拟合公式（向后兼容）
    quality_grade: str = "good"  # 质量等级（向后兼容）
    constraints_satisfied: bool = True  # 约束是否满足（向后兼容）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含numpy数组）"""
        return {
            "method_id": self.method_id,
            "method_name": self.method_name,
            "version": self.version,
            "coefficients": self.coefficients,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "mae": self.mae,
            "mape": self.mape,
            "data_points": self.data_points,
            "time_range": self.time_range,
            "normalization_params": self.normalization_params,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_exportable_json(self, rated_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成可还原曲线的完整JSON结构

        用于导出给其他系统使用，包含完整的曲线还原信息。

        Args:
            rated_params: 设备额定参数（可选），用于生成关键工况点

        Returns:
            Dict: 完整的可还原JSON结构
        """
        # 推断模型类型和阶数
        model_type = "polynomial"
        degree = len(self.coefficients) - 1 if self.coefficients else 2
        if self.method_id:
            if "poly_2" in self.method_id or "poly2" in self.method_id:
                degree = 2
            elif "poly_3" in self.method_id or "poly3" in self.method_id:
                degree = 3
            elif "power" in self.method_id:
                model_type = "power"
            elif "exp" in self.method_id:
                model_type = "exponential"

        # 系数转换为列表格式
        coeff_list = list(self.coefficients.values()) if isinstance(
            self.coefficients, dict) else self.coefficients
        coeff_names = list(self.coefficients.keys()) if isinstance(
            self.coefficients, dict) else [f"a{i}" for i in range(len(coeff_list))]

        # 生成还原代码
        restore_code = self._generate_restore_code(
            model_type, coeff_list, coeff_names)

        # 生成采样点
        sample_curve = self._generate_sample_curve(coeff_list, model_type)

        # 变量名映射
        y_name = "H" if self.curve_type == "qh" else (
            "P" if self.curve_type == "qp" else "eta")
        y_label = "扬程" if self.curve_type == "qh" else (
            "功率" if self.curve_type == "qp" else "效率")
        y_unit = "m" if self.curve_type == "qh" else (
            "kW" if self.curve_type == "qp" else "%")

        result = {
            "_schema": {
                "version": "1.0",
                "type": "pump_characteristic_curve"
            },
            "identity": {
                "device_id": self.device_id,
                "curve_type": self.curve_type,
                "version": self.version,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            },
            "model": {
                "method_id": self.method_id,
                "method_name": self.method_name,
                "type": model_type,
                "degree": degree if model_type == "polynomial" else None,
                "coefficients": coeff_list,
                "coefficient_names": coeff_names,
                "formula": self.formula or self._build_formula(model_type, coeff_list, coeff_names, y_name),
                "restore_code": restore_code,
            },
            "normalization": {
                "enabled": bool(self.normalization_params),
                "method": "min_max" if self.normalization_params else None,
                "x_params": self.normalization_params.get("Q") or self.normalization_params.get("x"),
                "y_params": self.normalization_params.get(y_name) or self.normalization_params.get("y"),
            },
            "valid_range": {
                "x": {
                    "name": "Q",
                    "label": "流量",
                    "unit": "m³/h",
                    "min": self.valid_q_range[0] if self.valid_q_range else 0.0,
                    "max": self.valid_q_range[1] if self.valid_q_range else 500.0,
                },
                "y": {
                    "name": y_name,
                    "label": y_label,
                    "unit": y_unit,
                    "min": self.valid_h_range[0] if self.valid_h_range else 0.0,
                    "max": self.valid_h_range[1] if self.valid_h_range else 100.0,
                },
            },
            "metrics": {
                "r_squared": self.r_squared,
                "rmse": self.rmse,
                "mae": self.mae,
                "mape": self.mape,
                "data_points": self.data_points,
            },
            "sample_curve": sample_curve,
            "key_points": self._generate_key_points(coeff_list, model_type, rated_params),
            "metadata": self.metadata,
        }

        # 添加额定参数（如果提供）
        if rated_params:
            result["rated_params"] = rated_params

        return result

    def _generate_restore_code(self, model_type: str, coefficients: List, coeff_names: List[str]) -> Dict[str, str]:
        """生成各语言的还原代码"""
        if model_type == "polynomial":
            terms = " + ".join([f"({c})*Q**{i}" for i,
                               c in enumerate(coefficients)])
            py_code = f"def predict(Q):\n    return {terms}"
            js_terms = " + ".join([f"({c})*Math.pow(Q,{i})" for i,
                                  c in enumerate(coefficients)])
            js_code = f"function predict(Q) {{ return {js_terms}; }}"
            sql_terms = " + ".join([f"({c})*POWER(Q,{i})" for i,
                                   c in enumerate(coefficients)])
        elif model_type == "power" and len(coefficients) >= 3:
            H0, K, n = coefficients[0], coefficients[1], coefficients[2]
            py_code = f"def predict(Q):\n    return {H0} - {K}*(Q**{n})"
            js_code = f"function predict(Q) {{ return {H0} - {K}*Math.pow(Q,{n}); }}"
            sql_terms = f"{H0} - {K}*POWER(Q,{n})"
        else:
            py_code = "# 未知模型类型"
            js_code = "// 未知模型类型"
            sql_terms = "NULL"

        return {"python": py_code, "javascript": js_code, "sql": sql_terms}

    def _generate_sample_curve(self, coefficients: List, model_type: str, n_points: int = 21) -> Dict[str, Any]:
        """生成采样曲线点"""
        q_min = self.valid_q_range[0] if self.valid_q_range else 0.0
        q_max = self.valid_q_range[1] if self.valid_q_range else 500.0
        x_vals = np.linspace(q_min, q_max, n_points)

        if model_type == "polynomial":
            y_vals = [sum(c * (q ** i)
                          for i, c in enumerate(coefficients)) for q in x_vals]
        elif model_type == "power" and len(coefficients) >= 3:
            H0, K, n = coefficients[0], coefficients[1], coefficients[2]
            y_vals = [H0 - K * (q ** n) for q in x_vals]
        else:
            y_vals = [0.0] * n_points

        return {
            "count": n_points,
            "x": [round(float(x), 2) for x in x_vals],
            "y": [round(float(y), 2) for y in y_vals],
        }

    def _generate_key_points(self, coefficients: List, model_type: str, rated_params: Optional[Dict] = None) -> Dict[str, Any]:
        """生成关键工况点"""
        key_points = {}
        if not coefficients:
            return key_points

        # 零流量点
        if model_type == "polynomial":
            y_at_zero = coefficients[0] if coefficients else 0
        elif model_type == "power" and len(coefficients) >= 1:
            y_at_zero = coefficients[0]
        else:
            y_at_zero = 0

        key_points["shutoff"] = {"Q": 0.0, "y": round(
            float(y_at_zero), 2), "description": "零流量点"}

        # 额定点（如果有额定参数）
        if rated_params:
            q_rated = rated_params.get(
                "rated_flow") or rated_params.get("Q_rated")
            if q_rated:
                if model_type == "polynomial":
                    y_rated = sum(c * (q_rated ** i)
                                  for i, c in enumerate(coefficients))
                elif model_type == "power" and len(coefficients) >= 3:
                    H0, K, n = coefficients[0], coefficients[1], coefficients[2]
                    y_rated = H0 - K * (q_rated ** n)
                else:
                    y_rated = 0
                key_points["rated"] = {
                    "Q": float(q_rated),
                    "y": round(float(y_rated), 2),
                    "description": "额定工况点"
                }

        return key_points

    def _build_formula(self, model_type: str, coefficients: List, coeff_names: List[str], y_name: str) -> str:
        """构建公式字符串"""
        if model_type == "polynomial":
            terms = []
            for i, (c, name) in enumerate(zip(coefficients, coeff_names)):
                if i == 0:
                    terms.append(f"{c:.4f}")
                elif i == 1:
                    terms.append(f"{c:+.6f}×Q")
                else:
                    terms.append(f"{c:+.6f}×Q^{i}")
            return f"{y_name} = " + " ".join(terms)
        elif model_type == "power" and len(coefficients) >= 3:
            return f"{y_name} = {coefficients[0]:.2f} - {coefficients[1]:.6f}×Q^{coefficients[2]:.2f}"
        return f"{y_name} = f(Q)"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FitResult":
        """从字典创建"""
        data = data.copy()
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        # 移除numpy数组字段（如果存在）
        data.pop("x_values", None)
        data.pop("y_actual", None)
        data.pop("y_fitted", None)
        return cls(**data)


# ==================== ValidationResult ====================


@dataclass
class ValidationResult:
    """验证结果数据类"""

    # 总体结果
    is_valid: bool = False  # 是否通过验证
    overall_passed: bool = False  # 总体是否通过

    # 各项验证结果
    monotonicity_passed: bool = False  # 单调性验证
    boundary_passed: bool = False  # 边界条件验证
    physics_passed: bool = False  # 物理约束验证

    # 得分
    physics_score: float = 0.0  # 物理得分（0-100）

    # 详细信息
    checks: List[Dict[str, Any]] = field(default_factory=list)  # 检查项列表
    passed_checks: List[str] = field(default_factory=list)  # 通过的检查项
    failed_checks: List[str] = field(default_factory=list)  # 失败的检查项
    errors: List[str] = field(default_factory=list)  # 错误信息
    warnings: List[str] = field(default_factory=list)  # 警告信息

    # 详细结果
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "overall_passed": self.overall_passed,
            "monotonicity_passed": self.monotonicity_passed,
            "boundary_passed": self.boundary_passed,
            "physics_passed": self.physics_passed,
            "physics_score": self.physics_score,
            "checks": self.checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


# ==================== EvaluationReport ====================


@dataclass
class EvaluationReport:
    """评估报告数据类"""

    # 基本信息
    device_id: int = 0
    curve_type: str = ""
    version: str = ""

    # 数据质量
    data_quality: Dict[str, Any] = field(default_factory=dict)

    # 拟合质量
    fit_quality: Dict[str, Any] = field(default_factory=dict)

    # 物理验证
    physics_validation: Dict[str, Any] = field(default_factory=dict)

    # 稳定性分析
    stability_analysis: Dict[str, Any] = field(default_factory=dict)

    # 建议
    recommendations: List[str] = field(default_factory=list)

    # 元数据
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "curve_type": self.curve_type,
            "version": self.version,
            "data_quality": self.data_quality,
            "fit_quality": self.fit_quality,
            "physics_validation": self.physics_validation,
            "stability_analysis": self.stability_analysis,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


# ==================== DeviceInfo ====================


@dataclass
class DeviceInfo:
    """设备信息"""

    device_id: int
    device_name: str
    pump_type: str  # 泵类型: 'variable_frequency' | 'soft_start' | 'unknown'
    rated_frequency: float  # 额定频率 (Hz)
    rated_flow: float  # 额定流量 (m³/h)
    rated_head: float  # 额定扬程 (m)
    rated_power: Optional[float] = None  # 额定功率 (kW)
    rated_efficiency: Optional[float] = None  # 额定效率


# ==================== 场景识别相关 ====================


class GroupProcessingStrategy(Enum):
    """泵组处理策略

    定义5种泵组场景的处理策略，与07_泵组处理层.md中的定义保持一致。
    """

    HOMOGENEOUS_GROUP = "homogeneous"  # 同构泵组（同型号、频率一致）
    HETEROGENEOUS_GROUP = "heterogeneous"  # 异构泵组（功率差异≥10%）
    VFD_HETEROGENEOUS_FREQ = "vfd_hetero_freq"  # VFD频率异构（全VFD、频率差异≥2%）
    MIXED_GROUP = "mixed"  # 混合泵组（VFD+SS、功率差异<10%）
    MIXED_HETEROGENEOUS = "mixed_heterogeneous"  # 混合异构泵组（VFD+SS、功率差异≥10%）


class FittingScenario(Enum):
    """拟合场景枚举

    ⚠️ 注意：此枚举用于场景检测阶段，枚举值带 _group 后缀。
    与 GroupProcessingStrategy（用于处理阶段，枚举值不带后缀）不同。
    """

    # P0阶段支持的场景（单泵）
    SOFT_START_SINGLE = "soft_start_single"
    VFD_SINGLE = "vfd_single"
    QUASI_FIXED_FREQ_SINGLE = "quasi_fixed_freq_single"

    # P2阶段支持的场景（泵组）
    HOMOGENEOUS_GROUP = "homogeneous_group"  # 同构泵组
    HETEROGENEOUS_GROUP = "heterogeneous_group"  # 异构泵组
    VFD_HETEROGENEOUS_FREQ = "vfd_hetero_freq_group"  # VFD频率异构
    MIXED_GROUP = "mixed_group"  # 混合泵组
    MIXED_HETEROGENEOUS = "mixed_heterogeneous_group"  # 混合异构泵组

    # 特殊场景
    UNKNOWN = "unknown"
    NOT_SUPPORTED = "not_supported"

    @staticmethod
    def to_processing_strategy(
        scenario: "FittingScenario",
    ) -> Optional[GroupProcessingStrategy]:
        """将场景枚举转换为处理策略枚举"""
        mapping = {
            FittingScenario.HOMOGENEOUS_GROUP: GroupProcessingStrategy.HOMOGENEOUS_GROUP,
            FittingScenario.HETEROGENEOUS_GROUP: GroupProcessingStrategy.HETEROGENEOUS_GROUP,
            FittingScenario.VFD_HETEROGENEOUS_FREQ: GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ,
            FittingScenario.MIXED_GROUP: GroupProcessingStrategy.MIXED_GROUP,
            FittingScenario.MIXED_HETEROGENEOUS: GroupProcessingStrategy.MIXED_HETEROGENEOUS,
        }
        return mapping.get(scenario)


# ==================== P0 新增数据结构(设计文档3.3节) ====================


@dataclass
class GroupFitResult:
    """泵组拟合结果（P2阶段）

    与07_泵组处理层.md定义保持一致

    v3.3更新（P12修复）：增加fit_method字段标识曲线来源
    """

    # 基本信息
    station_id: int
    pump_combination: List[int]
    group_type: GroupProcessingStrategy
    curve_type: str
    pump_count: int = 0

    # 曲线生成方式（v3.3新增 P12修复）
    fit_method: str = "synthesis"  # "synthesis" | "direct_fit"

    # 合成曲线系数
    synthesis_coefficients: Dict[str, float] = field(default_factory=dict)

    # 修正模型
    correction_model: Dict[str, Any] = field(default_factory=dict)

    # 混合泵组分类信息
    vfd_pump_ids: List[int] = field(default_factory=list)  # 变频泵ID列表
    ss_pump_ids: List[int] = field(default_factory=list)  # 软启泵ID列表

    # 评估指标
    r_squared: float = 0.0
    rmse: float = 0.0

    # 元数据
    base_pump_id: Optional[int] = None  # 同构泵组的基准泵
    valid_n_range: Tuple[int, int] = (1, 1)  # 有效台数范围
    fitted_at: Optional[datetime] = None  # 拟合时间

    def __post_init__(self):
        if self.fitted_at is None:
            self.fitted_at = datetime.now()

    def to_exportable_json(self, rated_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成可还原曲线的完整JSON结构（泵组合成结果）

        用于导出给其他系统使用，包含完整的曲线还原信息。

        Args:
            rated_params: 泵组额定参数（可选）

        Returns:
            Dict: 完整的可还原JSON结构
        """
        # 变量名映射
        y_name = "H" if self.curve_type == "qh" else (
            "P" if self.curve_type == "qp" else "eta")
        y_label = "扬程" if self.curve_type == "qh" else (
            "功率" if self.curve_type == "qp" else "效率")
        y_unit = "m" if self.curve_type == "qh" else (
            "kW" if self.curve_type == "qp" else "%")

        # 系数转换为列表
        coefficients = list(self.synthesis_coefficients.values()) if isinstance(
            self.synthesis_coefficients, dict) else self.synthesis_coefficients
        coeff_names = list(self.synthesis_coefficients.keys()) if isinstance(
            self.synthesis_coefficients, dict) else [f"a{i}" for i in range(len(coefficients))]

        # 生成还原代码
        terms_py = " + ".join([f"({c})*Q**{i}" for i,
                              c in enumerate(coefficients)])
        terms_js = " + ".join([f"({c})*Math.pow(Q,{i})" for i,
                              c in enumerate(coefficients)])
        terms_sql = " + ".join([f"({c})*POWER(Q,{i})" for i,
                               c in enumerate(coefficients)])
        restore_code = {
            "python": f"def predict(Q):\n    return {terms_py}",
            "javascript": f"function predict(Q) {{ return {terms_js}; }}",
            "sql": terms_sql
        }

        # 预测函数
        def predict(Q: float) -> float:
            return sum(c * Q**i for i, c in enumerate(coefficients))

        # 生成采样点
        q_min, q_max = 0.0, 1000.0  # 默认范围
        x_vals = np.linspace(q_min, q_max, 21)
        y_vals = [predict(q) for q in x_vals]
        sample_curve = {
            "count": 21,
            "x": [round(float(x), 2) for x in x_vals],
            "y": [round(float(y), 2) for y in y_vals],
        }

        # 构建公式
        terms = []
        for i, c in enumerate(coefficients):
            if i == 0:
                terms.append(f"{c:.4f}")
            elif i == 1:
                terms.append(f"{c:+.6f}×Q")
            else:
                terms.append(f"{c:+.6f}×Q^{i}")
        formula = f"{y_name} = " + \
            " ".join(terms) if terms else f"{y_name} = f(Q)"

        # 关键点
        key_points = {"shutoff": {"Q": 0.0, "y": round(
            float(coefficients[0]) if coefficients else 0, 2), "description": "零流量点"}}
        if rated_params:
            q_rated = rated_params.get(
                "rated_flow") or rated_params.get("Q_rated")
            if q_rated:
                key_points["rated"] = {"Q": float(q_rated), "y": round(
                    float(predict(q_rated)), 2), "description": "额定工况点"}

        result = {
            "_schema": {"version": "1.0", "type": "pump_group_characteristic_curve"},
            "identity": {
                "station_id": self.station_id,
                "pump_combination": self.pump_combination,
                "pump_count": self.pump_count,
                "curve_type": self.curve_type,
                "version": self.fitted_at.strftime("%Y%m%d_%H%M%S") if self.fitted_at else None,
                "created_at": self.fitted_at.isoformat() if self.fitted_at else None,
            },
            "model": {
                "method_id": "synthesis",
                "method_name": "并联合成",
                "type": "polynomial",
                "degree": len(coefficients) - 1 if coefficients else 2,
                "coefficients": coefficients,
                "coefficient_names": coeff_names,
                "formula": formula,
                "restore_code": restore_code,
                "fit_method": self.fit_method,
            },
            "group_info": {
                "group_type": self.group_type.value if hasattr(self.group_type, 'value') else str(self.group_type),
                "pump_count": self.pump_count,
                "pump_ids": self.pump_combination,
                "base_pump_id": self.base_pump_id,
                "vfd_pump_ids": self.vfd_pump_ids,
                "ss_pump_ids": self.ss_pump_ids,
                "valid_n_range": list(self.valid_n_range),
            },
            "correction_model": self.correction_model if self.correction_model else None,
            "valid_range": {
                "x": {"name": "Q_total", "label": "总流量", "unit": "m³/h", "min": q_min, "max": q_max},
                "y": {"name": y_name, "label": y_label, "unit": y_unit, "min": 0.0, "max": 100.0},
            },
            "metrics": {"r_squared": self.r_squared, "rmse": self.rmse},
            "sample_curve": sample_curve,
            "key_points": key_points,
        }

        if rated_params:
            result["rated_params"] = rated_params

        return result


@dataclass
class SynthesisResult:
    """并联合成结果（P2阶段）

    存储在给定系统扬程下，各泵的流量分配和总流量计算结果。
    eta_total单位为小数(0-1)而非百分比。
    """

    # 合成结果
    Q_total: float  # 总流量 (m³/h)
    H_system: float  # 系统扬程 (m)

    # 各泵分配
    pump_flows: Dict[int, float]  # 各泵流量 {pump_id: Q_i}
    pump_heads: Dict[int, float]  # 各泵扬程 {pump_id: H_i}（并联时应相同）

    # 可选：功率和效率
    pump_powers: Optional[Dict[int, float]] = None  # 各泵功率 {pump_id: P_i}
    P_total: float = 0.0  # 总功率 (kW)
    eta_total: float = 0.0  # 总效率 (0-1)

    # 额定功率字典，用于负荷分配计算
    _rated_powers: Optional[Dict[int, float]] = None

    def get_flow_distribution(self) -> Dict[int, float]:
        """获取流量分配比例"""
        if self.Q_total <= 0:
            return {pid: 0.0 for pid in self.pump_flows}
        return {pid: Q / self.Q_total for pid, Q in self.pump_flows.items()}

    def get_load_distribution(
        self, rated_powers: Optional[Dict[int, float]] = None
    ) -> Dict[int, float]:
        """获取负荷分配比例

        Args:
            rated_powers: 额定功率字典 {pump_id: rated_power_kW}

        Returns:
            负荷分配比例 {pump_id: load_ratio}
        """
        powers = rated_powers or self._rated_powers

        if not powers or self.pump_powers is None:
            return {}

        return {
            pump_id: (self.pump_powers.get(
                pump_id, 0) / powers.get(pump_id, 1))
            for pump_id in self.pump_powers.keys()
            if powers.get(pump_id, 0) > 0
        }

    def get_power_distribution(self) -> Dict[int, float]:
        """获取功率分配比例"""
        if self.P_total <= 0 or self.pump_powers is None:
            return {pid: 0.0 for pid in (self.pump_powers or {})}
        return {pid: P / self.P_total for pid, P in self.pump_powers.items()}


@dataclass
class CorrectionModelConfig:
    """系统修正系数模型配置（P2阶段）

    用于配置 SystemCorrectionModel 的训练和预测参数。
    修正公式：H_actual = H_theoretical × α(N, Q_total)
    """

    # 模型类型
    model_type: Literal["linear", "polynomial", "xgboost"] = "polynomial"

    # 多项式模型参数
    polynomial_degree: int = 2  # 多项式阶数
    regularization_alpha: float = 1.0  # 正则化系数

    # 训练参数
    min_training_points: int = 100  # 最小训练数据点数
    validation_ratio: float = 0.2  # 验证集比例

    # XGBoost参数
    xgb_n_estimators: int = 100  # 树数量
    xgb_max_depth: int = 6  # 最大深度
    xgb_learning_rate: float = 0.1  # 学习率

    # 有效范围约束
    valid_n_range: Tuple[int, int] = (1, 10)  # 有效台数范围
    valid_q_range: Tuple[float, float] = (0.0, 10000.0)  # 有效流量范围 (m³/h)

    # 输出配置
    save_model: bool = True  # 是否保存模型
    model_save_path: str = "./models/correction"  # 模型保存路径


# ==================== P0 新增数据结构(设计文档3.3节) ====================


class Scenario(Enum):
    """场景枚举

    定义9种设备运行场景。
    P0阶段支持前3种单泵场景。
    """
    # P0场景
    SOFT_START_SINGLE = "soft_start_single"  # 软启动单泵
    VFD_SINGLE = "vfd_single"  # 变频单泵
    QUASI_FIXED_FREQ_SINGLE = "quasi_fixed_freq_single"  # 准恒频单泵

    # P2场景
    HOMOGENEOUS_GROUP = "homogeneous_group"  # 同型号泵组
    HETEROGENEOUS_GROUP = "heterogeneous_group"  # 异型号泵组
    VFD_HETEROGENEOUS_FREQ = "vfd_heterogeneous_freq"  # 变频异频泵组
    MIXED_GROUP = "mixed_group"  # 混合运行泵组
    MIXED_HETEROGENEOUS = "mixed_heterogeneous"  # 混合异型泵组
    GROUP_COMPOSITE = "group_composite"  # 复合泵组


@dataclass
class DataQualityReport:
    """数据质量报告

    用于评估原始数据质量,决定是否继续拟合流程。
    """
    total_points: int  # 总数据点数
    time_span_days: float  # 时间跨度(天)
    missing_ratio: float  # 缺失值比例(0-1)
    quality_score: float  # 质量评分(0-100)
    meets_minimum: bool  # 是否达到最低要求
    issues: List[str] = field(default_factory=list)  # 质量问题列表


@dataclass
class DeviceParams:
    """设备参数

    存储设备的额定参数,用于约束计算和结果验证。
    """
    device_id: int  # 设备ID
    device_type: str  # 设备类型(单泵/泵组)
    rated_flow: float  # 额定流量(m³/h)
    rated_head: float  # 额定扬程(m)
    rated_power: float  # 额定功率(kW)
    rated_efficiency: Optional[float] = None  # 额定效率
    min_frequency: Optional[float] = None  # 最小频率(Hz)
    max_frequency: Optional[float] = None  # 最大频率(Hz)


@dataclass
class ScenarioDetectionResult:
    """场景识别结果"""
    scenario: Scenario  # 场景枚举
    supported: bool  # 是否支持
    need_normalization: bool  # 是否需要归一化
    confidence: float  # 置信度(0-1)


@dataclass
class DataCleaningResult:
    """数据清洗结果

    记录数据清洗过程的详细信息。
    """
    original_count: int  # 原始数据点数
    cleaned_count: int  # 清洗后数据点数
    removed_count: int  # 移除的点数
    outlier_indices: List[int] = field(default_factory=list)  # 异常值索引列表
    missing_indices: List[int] = field(default_factory=list)  # 缺失值索引列表
    cleaning_report: Dict[str, Any] = field(default_factory=dict)  # 清洗报告详情


@dataclass
class ConstraintResult:
    """约束计算结果

    存储约束参数计算结果。
    """
    curve_type: str  # 曲线类型
    bounds: Dict[str, Tuple[float, float]] = field(
        default_factory=dict)  # 参数边界范围
    monotonicity_type: str = ""  # 单调性类型
    boundary_values: Dict[str, float] = field(
        default_factory=dict)  # 边界值(H0, P0等)
    additional_constraints: List[Dict] = field(default_factory=list)  # 额外约束条件


@dataclass
class NormalizationParams:
    """归一化参数

    存储数据归一化的参数,用于反归一化。
    """
    q_mean: float  # 流量均值
    q_std: float  # 流量标准差
    y_mean: float  # Y值均值
    y_std: float  # Y值标准差
    normalization_method: str  # 归一化方法('zscore'或'minmax')


@dataclass
class SteadyStateResult:
    """稳态识别结果

    记录稳态数据片段识别结果。
    """
    steady_segments: List[Tuple[int, int]] = field(
        default_factory=list)  # 稳态片段索引范围
    segment_count: int = 0  # 稳态片段数量
    total_steady_points: int = 0  # 总稳态点数
    steady_ratio: float = 0.0  # 稳态比例(0-1)


@dataclass
class PipelineContext:
    """管道上下文

    在管道各阶段间传递数据和状态。
    包含24个字段,覆盖所有阶段需求。
    """
    # 基本信息(必需)
    device_id: int
    curve_type: str
    config: Dict = field(default_factory=dict)

    # 时间窗口
    fit_window: Optional[Tuple[datetime, datetime]] = None
    test_window: Optional[Tuple[datetime, datetime]] = None

    # 场景和设备
    scenario: Optional[Scenario] = None
    device_params: Optional[DeviceParams] = None

    # 数据
    raw_data: Optional[Any] = None  # pd.DataFrame
    test_data: Optional[Any] = None  # pd.DataFrame
    data_quality_report: Optional[DataQualityReport] = None
    cleaned_data: Optional[Any] = None  # pd.DataFrame
    cleaning_result: Optional[DataCleaningResult] = None
    steady_data: Optional[Any] = None  # pd.DataFrame
    steady_result: Optional[SteadyStateResult] = None
    normalized_data: Optional[Any] = None  # pd.DataFrame
    norm_params: Optional[NormalizationParams] = None

    # 约束和方法
    constraints: Optional[ConstraintResult] = None
    selected_methods: Optional[List[str]] = None

    # 结果
    fit_results: Optional[List[MethodResult]] = None
    best_result: Optional['FitResult'] = None
    visualization_paths: Optional[List[str]] = None
    validation_result: Optional['ValidationResult'] = None
    evaluation_report: Optional['EvaluationReport'] = None

    # 错误记录
    errors: List[str] = field(default_factory=list)


# ==================== P2泵组直接拟合数据结构 ====================


@dataclass
class GroupOperatingPoint:
    """泵组运行工况点

    表示某一时刻泵组的运行状态，是直接拟合的基础数据单元。

    分组依据：running_pump_ids（排序后转为pump_combination_key）
    拟合输入：Q_total（X轴）、H_system（Y轴）

    v3.2版本：从 group_method_adapter.py 移至此处统一定义
    """
    # ===== 基本信息 =====
    ts_bucket: datetime           # 时间戳
    station_id: int               # 泵站ID

    # ===== 核心工况数据 =====
    Q_total: float                # 总流量 (m³/h) - 拟合X轴
    H_system: float               # 系统扬程 (m) - 拟合Y轴
    P_total: Optional[float] = None  # 总功率 (kW) - 用于Q-P曲线拟合
    eta_total: Optional[float] = None  # 总效率 (0-1) - 用于Q-η曲线拟合

    # ===== 运行状态 =====
    n_running: int = 0            # 运行台数
    running_pump_ids: Tuple[int, ...] = field(
        default_factory=tuple)  # 运行泵ID元组（已排序）

    # ===== 变频信息（VFD场景必需）=====
    pump_frequencies: Optional[Dict[int, float]
                               ] = None  # 各泵频率 {pump_id: freq_Hz}
    avg_frequency: Optional[float] = None  # 平均频率（用于频率归一化）

    # ===== 数据质量 =====
    is_steady_state: bool = True  # 是否稳态（非稳态数据应过滤）
    data_quality_score: float = 1.0  # 数据质量评分 (0-1)

    @property
    def pump_combination_key(self) -> str:
        """泵组合标识（用于分组）"""
        return ",".join(map(str, sorted(self.running_pump_ids)))

    def to_normalized(self, target_freq: float = 50.0) -> 'GroupOperatingPoint':
        """归一化到目标频率（用于VFD_HETEROGENEOUS_FREQ场景）

        相似定律（Pump Affinity Laws）：
        - Q ∝ f     流量与频率成正比
        - H ∝ f²    扬程与频率平方成正比
        - P ∝ f³    功率与频率立方成正比
        - η 在相似工况下近似不变，但低频时需要惩罚修正

        效率低频惩罚（分段修正，更符合物理实际）：
        - f < 25Hz：极低频区，机械损失占比显著增大，惩罚系数 k=0.20
        - 25Hz ≤ f < 35Hz：低频区，轻度惩罚，惩罚系数 k=0.10
        - f ≥ 35Hz：正常运行区，效率近似不变
        - f > 50Hz：超频运行，不惩罚（物理上效率可能略升）

        物理解释：
        - 低频时泵转速下降，水力效率维持但机械损失（轴承摩擦、密封损耗）
          占总功率比例增加
        - 典型离心泵在25Hz时效率可下降5-10%
        - 35Hz以上机械损失占比较小，效率接近额定值
        """
        if not self.avg_frequency or self.avg_frequency == target_freq:
            return self

        ratio = target_freq / self.avg_frequency

        # 效率惩罚计算（分段修正，更符合物理实际）
        eta_corrected = self.eta_total
        if self.eta_total is not None:
            f = self.avg_frequency
            if f < 25.0:
                # 极低频惩罚：机械损失占比显著增大
                penalty_factor = 1 - 0.20 * (1 - f / 50.0) ** 2
            elif f < 35.0:
                # 低频轻度惩罚
                penalty_factor = 1 - 0.10 * (1 - f / 50.0) ** 2
            else:
                # 35Hz以上不惩罚（包括超频运行）
                penalty_factor = 1.0
            eta_corrected = self.eta_total * penalty_factor

        return GroupOperatingPoint(
            ts_bucket=self.ts_bucket,
            station_id=self.station_id,
            Q_total=self.Q_total * ratio,           # Q ∝ f
            H_system=self.H_system * (ratio ** 2),  # H ∝ f²
            P_total=self.P_total *
            (ratio ** 3) if self.P_total else None,  # P ∝ f³
            eta_total=eta_corrected,  # 效率含低频惩罚修正
            n_running=self.n_running,
            running_pump_ids=self.running_pump_ids,
            pump_frequencies=self.pump_frequencies,
            avg_frequency=target_freq,  # 归一化后的频率
            is_steady_state=self.is_steady_state,
            data_quality_score=self.data_quality_score
        )


@dataclass
class DirectFitResult:
    """泵组直接拟合结果

    存储单个泵组合的直接拟合结果。

    v3.2版本：从 group_method_adapter.py 移至此处统一定义
    """
    station_id: int
    n_pumps: int                                # 运行台数（无上限）
    pump_combination_key: str                   # 泵组合标识
    curve_type: str                             # 曲线类型
    fit_method: str = "direct_fit"              # 拟合方式

    # 拟合结果
    coefficients: List[float] = field(default_factory=list)  # 拟合系数
    polynomial_degree: Optional[int] = None     # 多项式阶数
    r_squared: float = 0.0                      # R²
    rmse: float = 0.0                           # RMSE
    mae: float = 0.0                            # MAE
    mape: float = 0.0                           # MAPE

    # 数据信息
    data_points_used: int = 0
    valid_q_range: Optional[Tuple[float, float]] = None  # 有效流量范围
    valid_h_range: Optional[Tuple[float, float]] = None  # 有效扬程范围

    # 元数据
    fitted_at: Optional[datetime] = None
    method_id: Optional[str] = None             # 拟合方法ID
    method_name: Optional[str] = None           # 拟合方法名称
    group_type: Optional[str] = None            # 泵组类型
    frequency_normalized: bool = False          # 是否已频率归一化

    # 预测函数（不序列化）
    _predict_func: Optional[Callable[[np.ndarray], np.ndarray]] = None

    def __post_init__(self):
        if self.fitted_at is None:
            self.fitted_at = datetime.now()

    def predict(self, Q: float) -> float:
        """预测扬程"""
        if self._predict_func is not None:
            return float(self._predict_func(np.array([Q]))[0])
        # 回退到多项式预测
        return sum(c * Q**i for i, c in enumerate(self.coefficients))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不含预测函数）"""
        return {
            "station_id": self.station_id,
            "n_pumps": self.n_pumps,
            "pump_combination_key": self.pump_combination_key,
            "curve_type": self.curve_type,
            "fit_method": self.fit_method,
            "coefficients": self.coefficients,
            "polynomial_degree": self.polynomial_degree,
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "mae": self.mae,
            "mape": self.mape,
            "data_points_used": self.data_points_used,
            "valid_q_range": self.valid_q_range,
            "valid_h_range": self.valid_h_range,
            "fitted_at": self.fitted_at.isoformat() if self.fitted_at else None,
            "method_id": self.method_id,
            "method_name": self.method_name,
            "group_type": self.group_type,
            "frequency_normalized": self.frequency_normalized,
        }

    def to_exportable_json(self, rated_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成可还原曲线的完整JSON结构（泵组直接拟合）"""
        y_name = "H" if self.curve_type == "qh" else (
            "P" if self.curve_type == "qp" else "eta")
        y_label = "扬程" if self.curve_type == "qh" else (
            "功率" if self.curve_type == "qp" else "效率")
        y_unit = "m" if self.curve_type == "qh" else (
            "kW" if self.curve_type == "qp" else "%")
        coeff_names = [f"a{i}" for i in range(len(self.coefficients))]
        pump_ids = [int(x) for x in self.pump_combination_key.split(
            ",")] if self.pump_combination_key else []

        # 生成还原代码
        terms_py = " + ".join([f"({c})*Q**{i}" for i,
                              c in enumerate(self.coefficients)])
        terms_js = " + ".join([f"({c})*Math.pow(Q,{i})" for i,
                              c in enumerate(self.coefficients)])
        terms_sql = " + ".join([f"({c})*POWER(Q,{i})" for i,
                               c in enumerate(self.coefficients)])
        restore_code = {
            "python": f"def predict(Q):\n    return {terms_py}",
            "javascript": f"function predict(Q) {{ return {terms_js}; }}",
            "sql": terms_sql
        }

        # 生成采样点
        q_min = self.valid_q_range[0] if self.valid_q_range else 0.0
        q_max = self.valid_q_range[1] if self.valid_q_range else 1000.0
        x_vals = np.linspace(q_min, q_max, 21)
        y_vals = [self.predict(q) for q in x_vals]
        sample_curve = {
            "count": 21,
            "x": [round(float(x), 2) for x in x_vals],
            "y": [round(float(y), 2) for y in y_vals],
        }

        # 构建公式
        terms = []
        for i, c in enumerate(self.coefficients):
            if i == 0:
                terms.append(f"{c:.4f}")
            elif i == 1:
                terms.append(f"{c:+.6f}×Q")
            else:
                terms.append(f"{c:+.6f}×Q^{i}")
        formula = f"{y_name} = " + \
            " ".join(terms) if terms else f"{y_name} = f(Q)"

        # 关键点
        key_points = {"shutoff": {"Q": 0.0, "y": round(float(
            self.coefficients[0]) if self.coefficients else 0, 2), "description": "零流量点"}}
        if rated_params:
            q_rated = rated_params.get(
                "rated_flow") or rated_params.get("Q_rated")
            if q_rated:
                key_points["rated"] = {"Q": float(q_rated), "y": round(
                    float(self.predict(q_rated)), 2), "description": "额定工况点"}

        result = {
            "_schema": {"version": "1.0", "type": "pump_group_characteristic_curve"},
            "identity": {
                "station_id": self.station_id, "pump_combination": pump_ids,
                "pump_combination_key": self.pump_combination_key, "n_pumps": self.n_pumps,
                "curve_type": self.curve_type,
                "version": self.fitted_at.strftime("%Y%m%d_%H%M%S") if self.fitted_at else None,
                "created_at": self.fitted_at.isoformat() if self.fitted_at else None,
            },
            "model": {
                "method_id": self.method_id or "polynomial", "method_name": self.method_name or "多项式拟合",
                "type": "polynomial", "degree": self.polynomial_degree or (len(self.coefficients) - 1),
                "coefficients": self.coefficients, "coefficient_names": coeff_names,
                "formula": formula, "restore_code": restore_code,
                "fit_method": self.fit_method, "frequency_normalized": self.frequency_normalized,
            },
            "group_info": {"group_type": self.group_type, "pump_count": self.n_pumps, "pump_ids": pump_ids},
            "valid_range": {
                "x": {"name": "Q_total", "label": "总流量", "unit": "m³/h",
                      "min": self.valid_q_range[0] if self.valid_q_range else 0.0,
                      "max": self.valid_q_range[1] if self.valid_q_range else 1000.0},
                "y": {"name": y_name, "label": y_label, "unit": y_unit,
                      "min": self.valid_h_range[0] if self.valid_h_range else 0.0,
                      "max": self.valid_h_range[1] if self.valid_h_range else 100.0},
            },
            "metrics": {"r_squared": self.r_squared, "rmse": self.rmse, "mae": self.mae, "mape": self.mape, "data_points": self.data_points_used},
            "sample_curve": sample_curve,
            "key_points": key_points,
        }
        if rated_params:
            result["rated_params"] = rated_params
        return result


class CurveFitMethod(str, Enum):
    """曲线生成方式枚举

    用于标识泵组曲线是通过何种方法生成的：
    - DIRECT_FIT: 从泵组历史运行数据直接拟合
    - SYNTHESIS: 从单泵曲线合成（可能经过修正）
    """
    DIRECT_FIT = "direct_fit"      # 直接拟合
    SYNTHESIS = "synthesis"         # 合成曲线


@dataclass
class DualFitResult:
    """双方法拟合结果（v3.3新增 P13修复）

    存储合成+修正和直接拟合两种方法的结果，以及对比分析。
    用于DualMethodExecutor的返回值。

    参考文档：08_泵组直接拟合.md 第5.3节
    """
    # 基本信息
    station_id: int
    pump_combination: List[int]
    n_pumps: int
    group_type: GroupProcessingStrategy
    curve_type: str

    # 两种方法的结果
    direct_fit_result: Optional['DirectFitResult'] = None
    synthesis_result: Optional[GroupFitResult] = None

    # 对比分析结果
    comparison: Optional[Dict[str, Any]] = None

    # 状态
    direct_fit_success: bool = False
    synthesis_success: bool = False

    # 推荐使用的方法
    recommended_method: CurveFitMethod = CurveFitMethod.SYNTHESIS
    recommendation_reason: str = ""
    recommendation_confidence: float = 0.0

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)

    def get_recommended_result(self) -> Optional[Any]:
        """获取推荐的拟合结果"""
        if self.recommended_method == CurveFitMethod.DIRECT_FIT:
            return self.direct_fit_result
        return self.synthesis_result

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "station_id": self.station_id,
            "pump_combination": self.pump_combination,
            "n_pumps": self.n_pumps,
            "group_type": self.group_type.value if self.group_type else None,
            "curve_type": self.curve_type,
            "direct_fit_result": self.direct_fit_result.to_dict() if self.direct_fit_result else None,
            "synthesis_result": None,  # GroupFitResult需要单独处理
            "comparison": self.comparison,
            "direct_fit_success": self.direct_fit_success,
            "synthesis_success": self.synthesis_success,
            "recommended_method": self.recommended_method.value,
            "recommendation_reason": self.recommendation_reason,
            "recommendation_confidence": self.recommendation_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
