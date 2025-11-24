"""
特性曲线核心数据结构 (app.services.characteristic_curves.models)

本模块定义了特性曲线拟合系统的核心数据类：
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


class DeviceParams(TypedDict):
    """设备额定参数

    用于定义泵设备的额定工作参数。
    """

    rated_flow: float  # 额定流量 (m³/h)
    rated_head: float  # 额定扬程 (m)
    rated_power: float  # 额定功率 (kW)
    rated_efficiency: float  # 额定效率 (0-1)


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
    normalization_params: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    fitted_at: Optional[datetime] = None  # 拟合完成时间
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 可选：原始数据和拟合值（用于可视化，不持久化）
    x_values: Optional[np.ndarray] = None  # X轴值
    y_actual: Optional[np.ndarray] = None  # 实际Y值
    y_fitted: Optional[np.ndarray] = None  # 拟合Y值

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


@dataclass
class ScenarioDetectionResult:
    """场景识别结果"""

    # 识别结果
    scenario: FittingScenario  # 场景类型
    supported: bool  # 当前版本是否支持

    # 设备信息
    device_id: Optional[int] = None  # 单泵时的设备ID
    station_id: Optional[int] = None  # 泵组时的泵站ID
    device_ids: Optional[List[int]] = None  # 泵组时的设备ID列表

    # 泵类型信息
    pump_type: Optional[str] = None  # 泵类型
    pump_types: Optional[Dict[str, int]] = None  # 泵组时各类型数量

    # 频率统计
    freq_std: Optional[float] = None  # 频率标准差
    freq_range: Optional[Tuple[float, float]] = None  # 频率范围 (min, max)

    # 额定参数差异（泵组）
    power_variation: Optional[float] = None  # 功率变异系数

    # 处理建议
    need_normalization: bool = False  # 是否需要频率归一化
    normalization_strategy: Optional[str] = None  # 归一化策略

    # 不支持时的原因
    not_supported_reason: Optional[str] = None


# ==================== 泵组相关（P2阶段） ====================


@dataclass
class GroupFitResult:
    """泵组拟合结果（P2阶段）

    与07_泵组处理层.md定义保持一致
    """

    # 基本信息
    station_id: int
    pump_combination: List[int]
    group_type: GroupProcessingStrategy
    curve_type: str
    pump_count: int = 0

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
            pump_id: (self.pump_powers.get(pump_id, 0) / powers.get(pump_id, 1))
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
