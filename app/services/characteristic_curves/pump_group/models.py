"""
泵组直接拟合数据模型

本模块定义泵组直接拟合功能所需的数据结构：
- GroupFitData: 泵组拟合数据
- GroupOperatingPoint: 泵组运行工况点
- DirectFitResult: 直接拟合结果
- ComparisonResult: 对比分析结果
- CurveFitMethod: 曲线拟合方法枚举

版本: v1.0
创建日期: 2025-12-09
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np


class CurveFitMethod(str, Enum):
    """曲线拟合方法"""

    SYNTHESIS = "synthesis"  # 并联合成
    DIRECT_FIT = "direct_fit"  # 直接拟合


@dataclass
class GroupFitData:
    """泵组拟合数据"""

    station_id: int
    pump_ids: List[int]  # 泵ID列表
    curve_type: str  # 曲线类型 ('qh', 'qp', 'qeta')

    # 运行工况点
    operating_points: List["GroupOperatingPoint"] = field(default_factory=list)

    # 数据统计
    total_points: int = 0  # 总数据点数
    valid_points: int = 0  # 有效数据点数
    outlier_points: int = 0  # 异常点数

    # 数据范围
    q_range: Optional[Tuple[float, float]] = None  # 流量范围 (min, max)
    h_range: Optional[Tuple[float, float]] = None  # 扬程范围 (min, max)

    # 元数据
    extracted_at: Optional[datetime] = None  # 提取时间
    time_range: Optional[Tuple[datetime, datetime]] = None  # 数据时间范围

    def to_numpy(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        转换为numpy数组

        Returns:
            Tuple[np.ndarray, np.ndarray]: (Q数组, H数组)
        """
        Q = np.array([p.Q_total for p in self.operating_points])
        H = np.array([p.H_system for p in self.operating_points])
        return Q, H


@dataclass
class GroupOperatingPoint:
    """泵组运行工况点"""

    ts_bucket: datetime  # 时间戳
    Q_total: float  # 总流量 (m³/h)
    H_system: float  # 系统扬程 (m)
    running_pumps: Tuple[int, ...]  # 运行泵ID元组（排序后）
    pump_frequencies: Optional[Dict[int, float]] = None  # 泵频率映射 {pump_id: freq_hz}

    def __post_init__(self):
        """确保running_pumps是排序后的元组"""
        if isinstance(self.running_pumps, list):
            self.running_pumps = tuple(sorted(self.running_pumps))


@dataclass
class DirectFitResult:
    """直接拟合结果"""

    station_id: int
    pump_combination: List[int]  # 泵组合
    curve_type: str  # 曲线类型 ('qh', 'qp', 'qeta')

    # 拟合结果
    coefficients: List[float]  # 多项式系数 [a0, a1, a2, ...]
    polynomial_degree: int  # 多项式阶数

    # 评估指标
    r_squared: float  # R²
    rmse: float  # RMSE
    mae: float  # MAE
    mape: float  # MAPE

    # 交叉验证结果
    cv_mean_r2: Optional[float] = None  # 交叉验证平均R²
    cv_std_r2: Optional[float] = None  # 交叉验证R²标准差
    cv_fold_scores: Optional[List[float]] = None  # 各折R²分数

    # 数据信息
    data_points_used: int = 0  # 使用的数据点数
    valid_q_range: Optional[Tuple[float, float]] = None  # 有效流量范围
    valid_h_range: Optional[Tuple[float, float]] = None  # 有效扬程范围

    # 元数据
    fitted_at: Optional[datetime] = None  # 拟合时间
    group_type: Optional[str] = None  # 泵组类型
    frequency_normalized: bool = False  # 是否进行了频率归一化

    # 显示名称
    method_display_name: str = "直接拟合"  # 用于图片标题和图例

    # 原始数据（用于绘图）
    Q_data: Optional[Any] = None  # 流量数据（np.ndarray）
    H_data: Optional[Any] = None  # 扬程数据（np.ndarray）

    # 预测函数（用于绘图）
    forward_func: Optional[Callable] = None  # 正向预测函数 H = f(Q)


@dataclass
class ComparisonResult:
    """对比分析结果"""

    # 指标差异（百分比）
    r_squared_diff_pct: float  # R²差异百分比
    rmse_diff_pct: float  # RMSE差异百分比
    mae_diff_pct: float  # MAE差异百分比
    mape_diff_pct: float  # MAPE差异百分比

    # 推荐结果
    recommended_method: CurveFitMethod  # 推荐方法
    recommendation_reason: str  # 推荐理由（中文）

    # 详细对比
    direct_fit_metrics: Dict[str, float]  # 直接拟合指标
    synthesis_metrics: Dict[str, float]  # 合成曲线指标

    # 元数据
    compared_at: Optional[datetime] = None  # 对比时间

