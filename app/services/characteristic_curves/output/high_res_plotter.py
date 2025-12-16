"""
8K高分辨率绘图器 (app.services.characteristic_curves.output.high_res_plotter)

本模块提供8K高清拟合曲线绘图功能：
- 8K UHD分辨率（7680×4320）
- 全中文标签支持
- 多种图表类型（主曲线图、对比图等）
- 曲线关键信息标注（BEP、高效区间、最大流量/扬程等）
- 所有配置从YAML读取，禁止硬编码

使用方式：
    from app.services.characteristic_curves.output import HighResPlotter
    from app.services.characteristic_curves.output.high_res_plotter import CurveAnnotations
    
    plotter = HighResPlotter(config)
    
    # 基础绘图
    curve_path = plotter.plot_curve(x_data, y_data, curve_type, predict_func, output_path)
    
    # 带标注绘图
    annotations = CurveAnnotations(
        device_info=DeviceInfo(device_id=1, name="1号泵", model="XXX-200"),
        rated_point=RatedPoint(Q=200, H=35, eta=0.82, P=55),
        bep=BEPPoint(Q=180, H=38, eta=0.85),
        operating_range=OperatingRange(Q_min=100, Q_max=280),
        efficiency_zones=[EfficiencyZone(eta_threshold=0.75, Q_min=140, Q_max=220)]
    )
    curve_path = plotter.plot_curve_with_annotations(..., annotations=annotations)

版本: v2.0
创建日期: 2025-12-09
更新日期: 2025-12-14
参考文档: 特性曲线开发/开发文档/07_辅助模块/03_可视化.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy import stats


# ============================================================================
# 标注数据结构定义
# ============================================================================

@dataclass
class DeviceInfo:
    """设备基础信息"""
    device_id: int
    name: Optional[str] = None
    model: Optional[str] = None
    rated_speed: Optional[float] = None  # 额定转速 rpm
    impeller_diameter: Optional[float] = None  # 叶轮直径 mm


@dataclass
class RatedPoint:
    """额定工况点"""
    Q: float  # 额定流量 m³/h
    H: Optional[float] = None  # 额定扬程 m
    eta: Optional[float] = None  # 额定效率 (0-1)
    P: Optional[float] = None  # 额定功率 kW


@dataclass
class BEPPoint:
    """最佳效率点 (Best Efficiency Point)"""
    Q: float  # BEP流量 m³/h
    H: Optional[float] = None  # BEP扬程 m
    eta: float = 0.0  # 最高效率 (0-1)
    P: Optional[float] = None  # BEP功率 kW


@dataclass
class OperatingRange:
    """运行范围"""
    Q_min: float  # 最小流量 m³/h
    Q_max: float  # 最大流量 m³/h
    H_min: Optional[float] = None  # 最小扬程 m
    H_max: Optional[float] = None  # 最大扬程 m (关死点)


@dataclass
class EfficiencyZone:
    """效率区间"""
    eta_threshold: float  # 效率阈值 (0-1), 如0.75表示75%
    Q_min: float  # 区间最小流量
    Q_max: float  # 区间最大流量
    H_min: Optional[float] = None  # 区间最小扬程
    H_max: Optional[float] = None  # 区间最大扬程
    label: Optional[str] = None  # 自定义标签，如"高效区"


@dataclass
class WarningZone:
    """警告区域（不推荐运行区）"""
    Q_min: float
    Q_max: float
    reason: str  # 警告原因，如"汽蚀风险"、"效率过低"
    severity: str = "warning"  # "warning" 或 "danger"


@dataclass
class DesignPoint:
    """设计工况点"""
    Q: float
    H: float
    description: Optional[str] = None


@dataclass
class FitEquation:
    """拟合公式信息"""
    formula: str  # 公式字符串，如 "H = 45.2 - 0.0012Q²"
    coefficients: Optional[Dict[str, float]] = None  # 系数字典
    method_name: Optional[str] = None  # 拟合方法名


@dataclass
class DataInfo:
    """数据信息"""
    data_points: int  # 数据点数
    time_range_start: Optional[datetime] = None  # 数据起始时间
    time_range_end: Optional[datetime] = None  # 数据结束时间
    data_source: Optional[str] = None  # 数据来源


@dataclass
class FitMetrics:
    """拟合精度指标"""
    r_squared: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None


@dataclass
class MotorInfo:
    """电机信息（用于Q-P曲线）"""
    rated_power: float  # 电机额定功率 kW
    overload_limit: Optional[float] = None  # 过载限制 kW


@dataclass
class PumpGroupInfo:
    """泵组信息"""
    station_id: int
    station_name: Optional[str] = None
    pump_ids: List[int] = field(default_factory=list)
    pump_combination: Optional[str] = None  # 如 "1,2,3"
    n_pumps: int = 0
    # "parallel_synthesis" 或 "direct_fit"
    synthesis_method: Optional[str] = None
    parallel_loss_coefficient: Optional[float] = None  # 并联损失系数


@dataclass
class SwitchPoint:
    """台数切换点（泵组用）"""
    Q_threshold: float  # 切换流量阈值
    action: str  # "start" 或 "stop"
    from_n: int  # 从几台
    to_n: int  # 到几台
    description: Optional[str] = None


@dataclass
class SpecificEnergy:
    """比能耗信息"""
    sec_value: float  # 比能耗 kWh/m³
    sec_min: Optional[float] = None  # 最低比能耗
    sec_min_Q: Optional[float] = None  # 最低比能耗对应流量


@dataclass
class CurveAnnotations:
    """曲线标注信息（单泵）

    包含绘制特性曲线时需要标注的所有信息。
    所有字段均为可选，根据实际情况填充。
    """
    # 设备信息
    device_info: Optional[DeviceInfo] = None

    # 关键工况点
    rated_point: Optional[RatedPoint] = None
    bep: Optional[BEPPoint] = None
    design_point: Optional[DesignPoint] = None

    # 运行范围
    operating_range: Optional[OperatingRange] = None

    # 效率区间（可多个，如75%区、80%区）
    efficiency_zones: List[EfficiencyZone] = field(default_factory=list)

    # 警告区域
    warning_zones: List[WarningZone] = field(default_factory=list)

    # 拟合信息
    fit_equation: Optional[FitEquation] = None
    fit_metrics: Optional[FitMetrics] = None

    # 数据信息
    data_info: Optional[DataInfo] = None

    # 电机信息（Q-P曲线用）
    motor_info: Optional[MotorInfo] = None

    # 曲线特征点
    H0: Optional[float] = None  # 关死点扬程 (Q=0时)
    Q_max_at_H0: Optional[float] = None  # 最大流量 (H=0时)
    P_no_load: Optional[float] = None  # 空载功率


@dataclass
class PumpGroupAnnotations:
    """泵组曲线标注信息

    包含绘制泵组特性曲线时需要标注的所有信息。
    """
    # 泵组基础信息
    group_info: Optional[PumpGroupInfo] = None

    # 关键工况点
    group_bep: Optional[BEPPoint] = None

    # 运行范围
    operating_range: Optional[OperatingRange] = None

    # 高效运行区域
    efficiency_zones: List[EfficiencyZone] = field(default_factory=list)

    # 台数切换点
    switch_points: List[SwitchPoint] = field(default_factory=list)

    # 各台数运行信息
    n_pump_curves: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    # 格式: {1: {'Q_max': 300, 'label': '1台运行'}, 2: {...}, ...}

    # 比能耗信息
    specific_energy: Optional[SpecificEnergy] = None

    # 拟合信息
    fit_equation: Optional[FitEquation] = None
    fit_metrics: Optional[FitMetrics] = None

    # 数据信息
    data_info: Optional[DataInfo] = None

    # 曲线特征
    Q_total_max: Optional[float] = None  # 泵组最大总流量
    H_group_max: Optional[float] = None  # 泵组最大扬程

    # 推荐运行区域
    recommended_zone: Optional[EfficiencyZone] = None

    # 避免运行区域
    avoid_zones: List[WarningZone] = field(default_factory=list)


# ============================================================================
# HighResPlotter 类定义
# ============================================================================

class HighResPlotter:
    """8K高分辨率绘图器

    所有配置从config字典读取，禁止硬编码。
    缺失必需配置时抛出异常。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化绘图器

        Args:
            config: 配置字典（从visualization.yaml读取）

        Raises:
            KeyError: 缺失必需配置项
            ValueError: 配置值无效
        """
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

        # 验证并加载配置
        self._validate_config(config)
        self._config = config

        # 设置matplotlib后端
        backend = config['performance']['backend']
        matplotlib.use(backend)

        # 设置中文字体
        self._setup_chinese_font()

        self._logger.info(
            "[HighResPlotter] 初始化完成",
            extra={"extra_data": {
                "分辨率": f"{config['resolution']['width']}×{config['resolution']['height']}",
                "DPI": config['resolution']['dpi'],
                "字体": config['fonts']['primary']
            }}
        )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置完整性

        Raises:
            KeyError: 缺失必需配置项
        """
        required_keys = [
            'resolution', 'fonts', 'colors', 'output', 'style',
            'stats_box', 'curve_labels', 'performance'
        ]

        for key in required_keys:
            if key not in config:
                raise KeyError(f"配置缺失必需项: {key}")

        # 验证resolution子项
        resolution_keys = ['width', 'height',
                           'dpi', 'figure_width', 'figure_height']
        for key in resolution_keys:
            if key not in config['resolution']:
                raise KeyError(f"配置缺失必需项: resolution.{key}")

    def _setup_chinese_font(self) -> None:
        """设置中文字体"""
        font_primary = self._config['fonts']['primary']
        font_fallback = self._config['fonts']['fallback']

        plt.rcParams['font.sans-serif'] = [font_primary, font_fallback]
        plt.rcParams['axes.unicode_minus'] = False

    def plot_curve(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        predict_func: Callable[[np.ndarray], np.ndarray],
        output_path: Path,
        title: Optional[str] = None,
        r_squared: Optional[float] = None,
        rmse: Optional[float] = None,
        data_points: Optional[int] = None,
        method_name: Optional[str] = None
    ) -> Path:
        """绘制主拟合曲线图（8K分辨率）【P0必须实现】

        Args:
            x_data: X轴数据（如流量Q）
            y_data: Y轴数据（如扬程H）
            curve_type: 曲线类型（'qh', 'qp', 'qeta'）
            predict_func: 预测函数 y = f(x)
            output_path: 输出文件路径
            title: 自定义标题（可选）
            r_squared: R²值（用于统计信息框）
            rmse: RMSE值（用于统计信息框）
            data_points: 数据点数（用于统计信息框）
            method_name: 方法名称（用于统计信息框）

        Returns:
            Path: 保存的文件路径

        Raises:
            KeyError: 曲线类型不在配置中
        """
        # 验证曲线类型
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        # 获取配置
        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        # 创建8K画布
        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制原始数据散点
        ax.scatter(
            x_data, y_data,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='运行数据',
            zorder=2
        )

        # 绘制拟合曲线
        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)
        y_smooth = predict_func(x_smooth)
        ax.plot(
            x_smooth, y_smooth,
            c=colors['curve'],
            linewidth=style['curve']['line_width'],
            linestyle=style['curve']['line_style'],
            label='拟合曲线',
            zorder=3
        )

        # 计算并绘制95%置信区间
        y_fitted = predict_func(x_data)
        residuals = y_data - y_fitted
        std_residuals = np.std(residuals)
        confidence_95 = 1.96 * std_residuals

        ax.fill_between(
            x_smooth,
            predict_func(x_smooth) - confidence_95,
            predict_func(x_smooth) + confidence_95,
            color=colors['confidence_95'],
            alpha=style['confidence']['alpha'],
            label='95%置信区间',
            zorder=1
        )

        # 设置标题和标签
        plot_title = title or labels['title']
        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        # 设置网格
        ax.grid(
            True,
            alpha=style['grid']['alpha'],
            linewidth=style['grid']['line_width'],
            linestyle=style['grid']['line_style'],
            color=colors['grid']
        )

        # 设置刻度字体大小
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 添加图例
        ax.legend(
            fontsize=self._config['fonts']['legend_size'],
            framealpha=style['legend']['frame_alpha'],
            shadow=style['legend']['shadow'],
            edgecolor=colors['grid']
        )

        # 添加统计信息框
        if r_squared is not None or rmse is not None:
            self._add_stats_box(ax, r_squared, rmse, data_points, method_name)

        # 紧凑布局
        if self._config['output']['tight_layout']:
            plt.tight_layout()

        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            output_path,
            format=self._config['output']['format'],
            dpi=resolution['dpi'],
            bbox_inches='tight',
            transparent=self._config['output']['transparent'],
            facecolor=self._config['output']['background_color'],
            pil_kwargs={
                'compress_level': self._config['output']['compression']}
        )

        # 关闭图形释放内存
        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 主曲线图已生成",
            extra={"extra_data": {
                "输出路径": str(output_path),
                "曲线类型": curve_type,
                "数据点数": len(x_data)
            }}
        )

        return output_path

    def _add_stats_box(
        self,
        ax: plt.Axes,
        r_squared: Optional[float],
        rmse: Optional[float],
        data_points: Optional[int],
        method_name: Optional[str]
    ) -> None:
        """添加统计信息框

        Args:
            ax: matplotlib轴对象
            r_squared: R²值
            rmse: RMSE值
            data_points: 数据点数
            method_name: 方法名称
        """
        stats_config = self._config['stats_box']

        # 构建统计信息文本
        stats_lines = []
        if method_name:
            stats_lines.append(f"方法: {method_name}")
        if r_squared is not None:
            stats_lines.append(f"R² = {r_squared:.4f}")
        if rmse is not None:
            stats_lines.append(f"RMSE = {rmse:.4f}")
        if data_points is not None:
            stats_lines.append(f"数据点数: {data_points}")

        if not stats_lines:
            return

        stats_text = '\n'.join(stats_lines)

        # 添加文本框
        props = dict(
            boxstyle=f'round,pad=0.5,rounding_size={stats_config["border_radius"]}',
            facecolor=stats_config['background_color'],
            edgecolor=stats_config['border_color'],
            alpha=stats_config['alpha']
        )

        ax.text(
            0.98, 0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=stats_config['font_size'],
            verticalalignment='top',
            horizontalalignment='right',
            bbox=props
        )

    def plot_comparison(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        curves: List[Dict[str, Any]],
        output_path: Path,
        title: Optional[str] = None,
        recommended_index: Optional[int] = None
    ) -> Path:
        """绘制对比图（多条曲线对比）【P0必须实现】

        Args:
            x_data: X轴数据（原始数据）
            y_data: Y轴数据（原始数据）
            curve_type: 曲线类型（'qh', 'qp', 'qeta'）
            curves: 曲线列表，每个元素为字典：
                {
                    'name': str,  # 曲线名称（如"并联合成"、"直接拟合"）
                    'predict_func': Callable,  # 预测函数
                    'color': str,  # 颜色（可选，不提供则使用默认）
                    'r_squared': float,  # R²值（可选）
                    'rmse': float  # RMSE值（可选）
                }
            output_path: 输出文件路径
            title: 自定义标题（可选）
            recommended_index: 推荐曲线的索引（可选，用于高亮显示）

        Returns:
            Path: 保存的文件路径

        Raises:
            KeyError: 曲线类型不在配置中
            ValueError: curves列表为空
        """
        if not curves:
            raise ValueError("curves列表不能为空")

        # 验证曲线类型
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        # 获取配置
        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        # 创建8K画布
        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制原始数据散点
        ax.scatter(
            x_data, y_data,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='运行数据',
            zorder=2
        )

        # 绘制多条曲线
        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)
        default_colors = colors.get(
            'history', ['#e74c3c', '#2ecc71', '#9b59b6', '#f39c12'])

        for i, curve_info in enumerate(curves):
            curve_name = curve_info['name']
            predict_func = curve_info['predict_func']
            curve_color = curve_info.get(
                'color', default_colors[i % len(default_colors)])

            # 判断是否为推荐曲线
            is_recommended = (
                recommended_index is not None and i == recommended_index)

            # 绘制曲线
            line_width = style['curve']['line_width']
            if is_recommended:
                line_width = line_width * 1.5  # 推荐曲线加粗

            label_text = curve_name
            if is_recommended:
                label_text = f"★ {curve_name} (推荐)"

            # 添加R²和RMSE到标签
            if 'r_squared' in curve_info and 'rmse' in curve_info:
                label_text += f" (R²={curve_info['r_squared']:.4f}, RMSE={curve_info['rmse']:.4f})"

            y_smooth = predict_func(x_smooth)
            ax.plot(
                x_smooth, y_smooth,
                c=curve_color,
                linewidth=line_width,
                linestyle=style['curve']['line_style'],
                label=label_text,
                zorder=3 if not is_recommended else 4
            )

        # 设置标题和标签
        plot_title = title or f"{labels['title']} - 方法对比"
        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        # 设置网格
        ax.grid(
            True,
            alpha=style['grid']['alpha'],
            linewidth=style['grid']['line_width'],
            linestyle=style['grid']['line_style'],
            color=colors['grid']
        )

        # 设置刻度字体大小
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 添加图例
        ax.legend(
            fontsize=self._config['fonts']['legend_size'],
            framealpha=style['legend']['frame_alpha'],
            shadow=style['legend']['shadow'],
            edgecolor=colors['grid'],
            loc='best'
        )

        # 紧凑布局
        if self._config['output']['tight_layout']:
            plt.tight_layout()

        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            output_path,
            format=self._config['output']['format'],
            dpi=resolution['dpi'],
            bbox_inches='tight',
            transparent=self._config['output']['transparent'],
            facecolor=self._config['output']['background_color'],
            pil_kwargs={
                'compress_level': self._config['output']['compression']}
        )

        # 关闭图形释放内存
        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 对比图已生成",
            extra={"extra_data": {
                "输出路径": str(output_path),
                "曲线类型": curve_type,
                "曲线数量": len(curves)
            }}
        )

        return output_path

    def plot_residuals(
        self,
        x_values: np.ndarray,
        residuals: np.ndarray,
        y_predicted: np.ndarray,
        curve_type: str,
        output_path: Path,
        title: Optional[str] = None
    ) -> Path:
        """绘制残差分析图（8K分辨率，2×2子图布局）【P0必须实现】

        包含四个子图：
        1. 残差vs预测值散点图
        2. 残差vs流量散点图
        3. 残差分布直方图
        4. 残差Q-Q图

        Args:
            x_values: X轴数据（流量Q）
            residuals: 残差数组 (y_actual - y_predicted)
            y_predicted: 预测值
            curve_type: 曲线类型
            output_path: 输出文件路径
            title: 自定义标题（可选）

        Returns:
            Path: 保存的文件路径
        """
        # 验证曲线类型
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        # 获取配置
        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        # 创建8K画布，2×2子图布局
        fig, axes = plt.subplots(
            2, 2,
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )
        ax1, ax2, ax3, ax4 = axes.flatten()

        # 残差统计
        mu = np.mean(residuals)
        sigma = np.std(residuals)

        # =====================================================
        # 子图1: 残差 vs 预测值
        # =====================================================
        ax1.scatter(
            y_predicted, residuals,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width']
        )

        # 添加零线和±2σ线
        ax1.axhline(y=0, color=colors['curve'], linestyle='--',
                    linewidth=style['curve']['line_width'], label='零线')
        ax1.axhline(y=2*sigma, color='#e74c3c', linestyle=':',
                    linewidth=1.5, label='+2σ')
        ax1.axhline(y=-2*sigma, color='#e74c3c', linestyle=':',
                    linewidth=1.5, label='-2σ')

        ax1.set_xlabel('预测值', fontsize=self._config['fonts']['label_size'])
        ax1.set_ylabel('残差', fontsize=self._config['fonts']['label_size'])
        ax1.set_title(
            '残差 vs 预测值', fontsize=self._config['fonts']['title_size'])
        ax1.grid(True, alpha=style['grid']['alpha'],
                 linewidth=style['grid']['line_width'],
                 linestyle=style['grid']['line_style'], color=colors['grid'])
        ax1.legend(fontsize=self._config['fonts']['legend_size'] * 0.8)
        ax1.tick_params(labelsize=self._config['fonts']['tick_size'])

        # =====================================================
        # 子图2: 残差 vs 流量
        # =====================================================
        ax2.scatter(
            x_values, residuals,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width']
        )

        ax2.axhline(y=0, color=colors['curve'], linestyle='--',
                    linewidth=style['curve']['line_width'], label='零线')
        ax2.axhline(y=2*sigma, color='#e74c3c', linestyle=':',
                    linewidth=1.5, label='+2σ')
        ax2.axhline(y=-2*sigma, color='#e74c3c', linestyle=':',
                    linewidth=1.5, label='-2σ')

        ax2.set_xlabel(labels['xlabel'],
                       fontsize=self._config['fonts']['label_size'])
        ax2.set_ylabel('残差', fontsize=self._config['fonts']['label_size'])
        ax2.set_title('残差 vs 流量', fontsize=self._config['fonts']['title_size'])
        ax2.grid(True, alpha=style['grid']['alpha'],
                 linewidth=style['grid']['line_width'],
                 linestyle=style['grid']['line_style'], color=colors['grid'])
        ax2.legend(fontsize=self._config['fonts']['legend_size'] * 0.8)
        ax2.tick_params(labelsize=self._config['fonts']['tick_size'])

        # =====================================================
        # 子图3: 残差分布直方图
        # =====================================================
        n_bins = min(30, max(10, len(residuals) // 50))
        ax3.hist(
            residuals, bins=n_bins,
            color=colors['scatter'], alpha=0.7, edgecolor='black',
            density=True, label='残差分布'
        )

        # 添加正态分布拟合曲线
        x_hist = np.linspace(residuals.min(), residuals.max(), 100)
        y_hist = stats.norm.pdf(x_hist, mu, sigma)
        ax3.plot(
            x_hist, y_hist,
            color=colors['curve'],
            linewidth=style['curve']['line_width'],
            label=f'正态分布\nμ={mu:.4f}\nσ={sigma:.4f}'
        )

        ax3.set_xlabel('残差', fontsize=self._config['fonts']['label_size'])
        ax3.set_ylabel('概率密度', fontsize=self._config['fonts']['label_size'])
        ax3.set_title('残差分布直方图', fontsize=self._config['fonts']['title_size'])
        ax3.grid(True, alpha=style['grid']['alpha'],
                 linewidth=style['grid']['line_width'],
                 linestyle=style['grid']['line_style'], color=colors['grid'])
        ax3.legend(fontsize=self._config['fonts']['legend_size'] * 0.8)
        ax3.tick_params(labelsize=self._config['fonts']['tick_size'])

        # =====================================================
        # 子图4: Q-Q图（正态性检验）
        # =====================================================
        # 标准化残差
        standardized = (residuals - mu) / sigma if sigma > 0 else residuals

        # 计算理论分位数和样本分位数
        sorted_residuals = np.sort(standardized)
        n = len(sorted_residuals)
        theoretical_quantiles = stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)

        ax4.scatter(
            theoretical_quantiles, sorted_residuals,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='残差分位数'
        )

        # 添加45度参考线
        lims = [min(theoretical_quantiles.min(), sorted_residuals.min()),
                max(theoretical_quantiles.max(), sorted_residuals.max())]
        ax4.plot(lims, lims, color=colors['curve'], linestyle='--',
                 linewidth=style['curve']['line_width'], label='理论正态线')

        # Shapiro-Wilk检验
        if len(residuals) >= 20 and len(residuals) <= 5000:
            _, p_value = stats.shapiro(residuals[:5000])
            normality_text = f"Shapiro-Wilk p={p_value:.4f}\n"
            normality_text += "正态性: " + ("✓ 通过" if p_value > 0.05 else "✗ 未通过")
        else:
            normality_text = "样本量不适用Shapiro-Wilk检验"

        ax4.text(
            0.05, 0.95, normality_text,
            transform=ax4.transAxes,
            fontsize=self._config['fonts']['annotation_size'],
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8)
        )

        ax4.set_xlabel('理论分位数', fontsize=self._config['fonts']['label_size'])
        ax4.set_ylabel('样本分位数', fontsize=self._config['fonts']['label_size'])
        ax4.set_title(
            'Q-Q图（正态性检验）', fontsize=self._config['fonts']['title_size'])
        ax4.grid(True, alpha=style['grid']['alpha'],
                 linewidth=style['grid']['line_width'],
                 linestyle=style['grid']['line_style'], color=colors['grid'])
        ax4.legend(fontsize=self._config['fonts']['legend_size'] * 0.8)
        ax4.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 总标题
        plot_title = title or f"{labels['title']} - 残差分析（4项诊断）"
        fig.suptitle(
            plot_title, fontsize=self._config['fonts']['title_size'] + 8, y=0.99)

        # 紧凑布局
        if self._config['output']['tight_layout']:
            plt.tight_layout(rect=[0, 0, 1, 0.97])

        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            output_path,
            format=self._config['output']['format'],
            dpi=resolution['dpi'],
            bbox_inches='tight',
            transparent=self._config['output']['transparent'],
            facecolor=self._config['output']['background_color'],
            pil_kwargs={
                'compress_level': self._config['output']['compression']}
        )

        # 关闭图形释放内存
        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 残差分析图已生成（4子图）",
            extra={"extra_data": {
                "输出路径": str(output_path),
                "曲线类型": curve_type,
                "残差统计": {"均值": float(mu), "标准差": float(sigma)}
            }}
        )

        return output_path

    def plot_confidence_band(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        predict_func: Callable[[np.ndarray], np.ndarray],
        output_path: Path,
        title: Optional[str] = None
    ) -> Path:
        """绘制置信区间图（95%/99%双区间）

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            curve_type: 曲线类型
            predict_func: 预测函数
            output_path: 输出路径
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制散点
        ax.scatter(
            x_data, y_data,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='运行数据',
            zorder=2
        )

        # 计算拟合值和残差
        y_fitted = predict_func(x_data)
        residuals = y_data - y_fitted
        std_residuals = np.std(residuals)

        # 置信区间
        confidence_95 = 1.96 * std_residuals
        confidence_99 = 2.576 * std_residuals

        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)
        y_smooth = predict_func(x_smooth)

        # 绘制99%置信区间（底层）
        ax.fill_between(
            x_smooth,
            y_smooth - confidence_99,
            y_smooth + confidence_99,
            color=colors.get('confidence_99', '#f5b7b1'),
            alpha=style['confidence']['alpha'] * 0.7,
            label=f'99%置信区间 (±{confidence_99:.2f})',
            zorder=0
        )

        # 绘制95%置信区间
        ax.fill_between(
            x_smooth,
            y_smooth - confidence_95,
            y_smooth + confidence_95,
            color=colors.get('confidence_95', '#fadbd8'),
            alpha=style['confidence']['alpha'],
            label=f'95%置信区间 (±{confidence_95:.2f})',
            zorder=1
        )

        # 绘制拟合曲线
        ax.plot(
            x_smooth, y_smooth,
            c=colors['curve'],
            linewidth=style['curve']['line_width'],
            linestyle=style['curve']['line_style'],
            label='拟合曲线',
            zorder=3
        )

        # 添加置信区间边界线
        ax.plot(x_smooth, y_smooth + confidence_95, '--',
                c=colors['curve'], alpha=0.5, linewidth=1)
        ax.plot(x_smooth, y_smooth - confidence_95, '--',
                c=colors['curve'], alpha=0.5, linewidth=1)
        ax.plot(x_smooth, y_smooth + confidence_99, ':',
                c='#e74c3c', alpha=0.5, linewidth=1)
        ax.plot(x_smooth, y_smooth - confidence_99, ':',
                c='#e74c3c', alpha=0.5, linewidth=1)

        # 设置标题和标签
        plot_title = title or f"{labels['title']} - 置信区间分析"
        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        ax.grid(True, alpha=style['grid']['alpha'],
                linewidth=style['grid']['line_width'],
                linestyle=style['grid']['line_style'], color=colors['grid'])
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 添加统计信息框
        stats_text = f"残差标准差: {std_residuals:.4f}\n95%置信宽度: ±{confidence_95:.4f}\n99%置信宽度: ±{confidence_99:.4f}"
        props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9)
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=self._config['fonts']['annotation_size'],
                verticalalignment='top', bbox=props)

        ax.legend(fontsize=self._config['fonts']['legend_size'],
                  framealpha=style['legend']['frame_alpha'],
                  shadow=style['legend']['shadow'], loc='best')

        if self._config['output']['tight_layout']:
            plt.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, format=self._config['output']['format'],
                    dpi=resolution['dpi'], bbox_inches='tight',
                    transparent=self._config['output']['transparent'],
                    facecolor=self._config['output']['background_color'],
                    pil_kwargs={'compress_level': self._config['output']['compression']})

        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 置信区间图已生成",
            extra={"extra_data": {"输出路径": str(
                output_path), "曲线类型": curve_type}}
        )
        return output_path

    def plot_sensitivity(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        coefficients: Dict[str, float],
        output_path: Path,
        sensitivity_range: float = 0.1,
        title: Optional[str] = None
    ) -> Path:
        """绘制参数敏感性分析图

        展示各参数±10%变化时对曲线的影响

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            curve_type: 曲线类型
            coefficients: 拟合系数字典
            output_path: 输出路径
            sensitivity_range: 敏感性范围（默认0.1即±10%）
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        # 子图数量 = 参数数量
        n_params = len(coefficients)
        n_cols = min(3, n_params)
        n_rows = (n_params + n_cols - 1) // n_cols

        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )
        if n_params == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        # 基准预测函数
        coef_list = list(coefficients.values())
        coef_names = list(coefficients.keys())

        def predict_with_coeffs(x, coeffs):
            result = np.zeros_like(x, dtype=float)
            for i, c in enumerate(coeffs):
                result += c * (x ** i)
            return result

        x_smooth = np.linspace(x_data.min(), x_data.max(), 200)
        y_baseline = predict_with_coeffs(x_smooth, coef_list)

        sensitivity_colors = ['#e74c3c', '#3498db']  # +变化红色，-变化蓝色

        for idx, (param_name, param_value) in enumerate(coefficients.items()):
            if idx >= len(axes):
                break
            ax = axes[idx]

            # 绘制散点
            ax.scatter(x_data, y_data, c=colors['scatter'],
                       alpha=0.3, s=style['scatter']['size']*0.5, label='数据')

            # 绘制基准曲线
            ax.plot(x_smooth, y_baseline, c='black', linewidth=2, label='基准')

            # +10%变化
            coeffs_up = coef_list.copy()
            coeffs_up[idx] = param_value * (1 + sensitivity_range)
            y_up = predict_with_coeffs(x_smooth, coeffs_up)
            ax.plot(x_smooth, y_up, c=sensitivity_colors[0], linewidth=1.5,
                    linestyle='--', label=f'+{sensitivity_range:.0%}')

            # -10%变化
            coeffs_down = coef_list.copy()
            coeffs_down[idx] = param_value * (1 - sensitivity_range)
            y_down = predict_with_coeffs(x_smooth, coeffs_down)
            ax.plot(x_smooth, y_down, c=sensitivity_colors[1], linewidth=1.5,
                    linestyle='--', label=f'-{sensitivity_range:.0%}')

            # 计算敏感性指标（最大偏差）
            max_deviation = max(np.max(np.abs(y_up - y_baseline)),
                                np.max(np.abs(y_down - y_baseline)))

            ax.set_title(f'{param_name}\n(±{sensitivity_range:.0%}偏差: {max_deviation:.2f})',
                         fontsize=self._config['fonts']['title_size'] * 0.7)
            ax.set_xlabel(
                labels['xlabel'], fontsize=self._config['fonts']['label_size'] * 0.7)
            ax.set_ylabel(
                labels['ylabel'], fontsize=self._config['fonts']['label_size'] * 0.7)
            ax.grid(True, alpha=style['grid']['alpha'])
            ax.legend(fontsize=self._config['fonts']['legend_size'] * 0.6)
            ax.tick_params(labelsize=self._config['fonts']['tick_size'] * 0.7)

        # 隐藏多余子图
        for idx in range(n_params, len(axes)):
            axes[idx].set_visible(False)

        plot_title = title or f"{labels['title']} - 参数敏感性分析"
        fig.suptitle(
            plot_title, fontsize=self._config['fonts']['title_size'] + 8, y=0.99)

        if self._config['output']['tight_layout']:
            plt.tight_layout(rect=[0, 0, 1, 0.97])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, format=self._config['output']['format'],
                    dpi=resolution['dpi'], bbox_inches='tight',
                    transparent=self._config['output']['transparent'],
                    facecolor=self._config['output']['background_color'],
                    pil_kwargs={'compress_level': self._config['output']['compression']})

        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 敏感性分析图已生成",
            extra={"extra_data": {"输出路径": str(output_path), "参数数": n_params}}
        )
        return output_path

    def plot_version_comparison(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        current_predict_func: Callable[[np.ndarray], np.ndarray],
        history_curves: List[Dict[str, Any]],
        output_path: Path,
        title: Optional[str] = None
    ) -> Path:
        """绘制版本对比图（当前vs历史版本）

        Args:
            x_data: 当前数据X
            y_data: 当前数据Y
            curve_type: 曲线类型
            current_predict_func: 当前版本预测函数
            history_curves: 历史版本曲线列表
                [{version, predict_func, r_squared, created_at}, ...]
            output_path: 输出路径
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制散点
        ax.scatter(
            x_data, y_data,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            label='当前运行数据',
            zorder=2
        )

        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)

        # 绘制当前版本曲线（加粗突出）
        y_current = current_predict_func(x_smooth)
        ax.plot(
            x_smooth, y_current,
            c=colors['curve'],
            linewidth=style['curve']['line_width'] * 1.5,
            linestyle='-',
            label='★ 当前版本',
            zorder=4
        )

        # 绘制历史版本曲线
        history_colors = colors.get(
            'history', ['#95a5a6', '#7f8c8d', '#bdc3c7', '#ecf0f1'])
        for i, hist in enumerate(history_curves[-5:]):  # 最近5个历史版本
            color = history_colors[i % len(history_colors)]
            version = hist.get('version', f'v{i+1}')
            predict_func = hist.get('predict_func')
            r_squared = hist.get('r_squared', 0)

            if predict_func is not None:
                y_hist = predict_func(x_smooth)
                label = f"{version} (R²={r_squared:.4f})"
                ax.plot(
                    x_smooth, y_hist,
                    c=color,
                    linewidth=style['curve']['line_width'] * 0.8,
                    linestyle='--',
                    alpha=0.7,
                    label=label,
                    zorder=3
                )

        # 设置标题和标签
        plot_title = title or f"{labels['title']} - 版本对比"
        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        ax.grid(True, alpha=style['grid']['alpha'],
                linewidth=style['grid']['line_width'],
                linestyle=style['grid']['line_style'], color=colors['grid'])
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])
        ax.legend(fontsize=self._config['fonts']['legend_size'],
                  framealpha=style['legend']['frame_alpha'],
                  shadow=style['legend']['shadow'], loc='best')

        if self._config['output']['tight_layout']:
            plt.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, format=self._config['output']['format'],
                    dpi=resolution['dpi'], bbox_inches='tight',
                    transparent=self._config['output']['transparent'],
                    facecolor=self._config['output']['background_color'],
                    pil_kwargs={'compress_level': self._config['output']['compression']})

        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 版本对比图已生成",
            extra={"extra_data": {"输出路径": str(
                output_path), "历史版本数": len(history_curves)}}
        )
        return output_path

    def plot_density(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        predict_func: Callable[[np.ndarray], np.ndarray],
        output_path: Path,
        title: Optional[str] = None
    ) -> Path:
        """绘制运行工况密度图（热力图）

        展示运行点的分布密度，帮助识别常用工况

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            curve_type: 曲线类型
            predict_func: 预测函数
            output_path: 输出路径
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制2D直方图热力图
        h = ax.hist2d(
            x_data, y_data,
            bins=[50, 50],
            cmap='YlOrRd',
            alpha=0.8,
            cmin=1  # 最小计数为1才显示颜色
        )
        plt.colorbar(h[3], ax=ax, label='运行点密度')

        # 绘制拟合曲线
        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)
        y_smooth = predict_func(x_smooth)
        ax.plot(
            x_smooth, y_smooth,
            c='#3498db',
            linewidth=style['curve']['line_width'],
            linestyle='-',
            label='拟合曲线',
            zorder=5
        )

        # 标注高密度区域（常用工况）
        hist, xedges, yedges = np.histogram2d(x_data, y_data, bins=[20, 20])
        max_idx = np.unravel_index(np.argmax(hist), hist.shape)
        peak_x = (xedges[max_idx[0]] + xedges[max_idx[0]+1]) / 2
        peak_y = (yedges[max_idx[1]] + yedges[max_idx[1]+1]) / 2

        ax.scatter([peak_x], [peak_y], marker='*', s=500, c='gold',
                   edgecolors='black', linewidths=2, label='高频工况点', zorder=10)
        ax.annotate(
            f'高频工况\n({peak_x:.0f}, {peak_y:.1f})',
            xy=(peak_x, peak_y),
            xytext=(peak_x + (x_data.max()-x_data.min())*0.1,
                    peak_y + (y_data.max()-y_data.min())*0.1),
            fontsize=self._config['fonts']['annotation_size'],
            fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#d35400', lw=2),
            color='#d35400'
        )

        # 设置标题和标签
        plot_title = title or f"{labels['title']} - 运行工况密度分布"
        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        ax.grid(True, alpha=style['grid']['alpha'] * 0.5,
                linewidth=style['grid']['line_width'],
                linestyle=style['grid']['line_style'], color=colors['grid'])
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])
        ax.legend(fontsize=self._config['fonts']['legend_size'],
                  framealpha=style['legend']['frame_alpha'], loc='best')

        # 添加统计信息框
        stats_text = (f"数据点数: {len(x_data):,}\n"
                      f"流量范围: {x_data.min():.0f}~{x_data.max():.0f} m³/h\n"
                      f"高频工况: Q={peak_x:.0f}, Y={peak_y:.1f}")
        props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9)
        ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
                fontsize=self._config['fonts']['annotation_size'],
                verticalalignment='bottom', horizontalalignment='right', bbox=props)

        if self._config['output']['tight_layout']:
            plt.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, format=self._config['output']['format'],
                    dpi=resolution['dpi'], bbox_inches='tight',
                    transparent=self._config['output']['transparent'],
                    facecolor=self._config['output']['background_color'],
                    pil_kwargs={'compress_level': self._config['output']['compression']})

        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 运行工况密度图已生成",
            extra={"extra_data": {"输出路径": str(output_path), "数据点数": len(
                x_data), "高频工况": f"({peak_x:.0f}, {peak_y:.1f})"}}
        )
        return output_path

    # ========================================================================
    # 标注绘制方法
    # ========================================================================

    def _add_bep_marker(
        self,
        ax: plt.Axes,
        bep: BEPPoint,
        curve_type: str
    ) -> None:
        """添加BEP点标注

        Args:
            ax: matplotlib轴对象
            bep: BEP点信息
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 根据曲线类型确定Y值
        if curve_type == 'qh' and bep.H is not None:
            y_val = bep.H
            label = f'BEP (Q={bep.Q:.0f}, H={bep.H:.1f}, η={bep.eta:.1%})'
        elif curve_type == 'qp' and bep.P is not None:
            y_val = bep.P
            label = f'BEP (Q={bep.Q:.0f}, P={bep.P:.1f}, η={bep.eta:.1%})'
        elif curve_type == 'qeta':
            y_val = bep.eta * 100  # 转换为百分比
            label = f'BEP (Q={bep.Q:.0f}, η={bep.eta:.1%})'
        else:
            return

        # 绘制金色五角星
        ax.scatter(
            bep.Q, y_val,
            marker='*', s=400, c='gold',
            edgecolors='black', linewidths=1.5,
            label=label,
            zorder=10
        )

        # 添加文字标注
        ax.annotate(
            'BEP',
            xy=(bep.Q, y_val),
            xytext=(bep.Q + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.05,
                    y_val + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05),
            fontsize=annotation_size,
            fontweight='bold',
            color='#d35400',
            arrowprops=dict(arrowstyle='->', color='#d35400', lw=1.5)
        )

    def _add_rated_point(
        self,
        ax: plt.Axes,
        rated: RatedPoint,
        curve_type: str
    ) -> None:
        """添加额定工况点标注

        Args:
            ax: matplotlib轴对象
            rated: 额定工况点信息
            curve_type: 曲线类型
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 根据曲线类型确定Y值
        if curve_type == 'qh' and rated.H is not None:
            y_val = rated.H
            label = f'额定点 (Q={rated.Q:.0f}, H={rated.H:.1f})'
        elif curve_type == 'qp' and rated.P is not None:
            y_val = rated.P
            label = f'额定点 (Q={rated.Q:.0f}, P={rated.P:.1f})'
        elif curve_type == 'qeta' and rated.eta is not None:
            y_val = rated.eta * 100
            label = f'额定点 (Q={rated.Q:.0f}, η={rated.eta:.1%})'
        else:
            return

        # 绘制红色菱形
        ax.scatter(
            rated.Q, y_val,
            marker='D', s=200, c='#e74c3c',
            edgecolors='white', linewidths=1.5,
            label=label,
            zorder=9
        )

        # 添加文字标注
        ax.annotate(
            '额定点',
            xy=(rated.Q, y_val),
            xytext=(rated.Q - (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.08,
                    y_val + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05),
            fontsize=annotation_size,
            color='#c0392b',
            arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.5)
        )

    def _add_efficiency_zone(
        self,
        ax: plt.Axes,
        zone: EfficiencyZone,
        curve_type: str,
        predict_func: Optional[Callable] = None
    ) -> None:
        """添加效率区间标注

        Args:
            ax: matplotlib轴对象
            zone: 效率区间信息
            curve_type: 曲线类型
            predict_func: 预测函数（用于确定阴影边界）
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 根据效率阈值选择颜色
        if zone.eta_threshold >= 0.80:
            color = '#27ae60'  # 深绿色 - 高效区
            alpha = 0.25
        elif zone.eta_threshold >= 0.75:
            color = '#2ecc71'  # 绿色 - 良好区
            alpha = 0.20
        else:
            color = '#f1c40f'  # 黄色 - 一般区
            alpha = 0.15

        # 获取Y轴范围
        y_min, y_max = ax.get_ylim()

        # 如果有预测函数，使用曲线作为上边界
        if predict_func is not None and curve_type in ['qh', 'qp']:
            x_zone = np.linspace(zone.Q_min, zone.Q_max, 100)
            y_zone = predict_func(x_zone)
            ax.fill_between(
                x_zone, y_min, y_zone,
                color=color, alpha=alpha,
                zorder=0
            )
        else:
            # 简单矩形区域
            ax.axvspan(
                zone.Q_min, zone.Q_max,
                color=color, alpha=alpha,
                zorder=0
            )

        # 添加边界线
        ax.axvline(x=zone.Q_min, color=color,
                   linestyle='--', linewidth=1.5, alpha=0.7)
        ax.axvline(x=zone.Q_max, color=color,
                   linestyle='--', linewidth=1.5, alpha=0.7)

        # 添加标签
        label = zone.label or f'η≥{zone.eta_threshold:.0%}区'
        mid_x = (zone.Q_min + zone.Q_max) / 2
        ax.text(
            mid_x, y_max * 0.95,
            label,
            fontsize=annotation_size,
            ha='center', va='top',
            color=color,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8)
        )

    def _add_warning_zone(
        self,
        ax: plt.Axes,
        zone: WarningZone
    ) -> None:
        """添加警告区域标注

        Args:
            ax: matplotlib轴对象
            zone: 警告区域信息
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 根据严重程度选择颜色
        if zone.severity == 'danger':
            color = '#e74c3c'  # 红色
            alpha = 0.2
        else:
            color = '#f39c12'  # 橙色
            alpha = 0.15

        # 绘制警告区域
        ax.axvspan(
            zone.Q_min, zone.Q_max,
            color=color, alpha=alpha,
            zorder=0
        )

        # 添加警告文字
        y_min, y_max = ax.get_ylim()
        mid_x = (zone.Q_min + zone.Q_max) / 2
        ax.text(
            mid_x, y_min + (y_max - y_min) * 0.1,
            f'⚠ {zone.reason}',
            fontsize=annotation_size * 0.8,
            ha='center', va='bottom',
            color=color,
            fontweight='bold',
            rotation=90 if (zone.Q_max - zone.Q_min) < (ax.get_xlim()
                                                        [1] - ax.get_xlim()[0]) * 0.1 else 0
        )

    def _add_operating_range(
        self,
        ax: plt.Axes,
        op_range: OperatingRange,
        predict_func: Optional[Callable] = None
    ) -> None:
        """添加运行范围标注

        Args:
            ax: matplotlib轴对象
            op_range: 运行范围信息
            predict_func: 预测函数
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 绘制最小/最大流量线
        ax.axvline(
            x=op_range.Q_min, color='#9b59b6', linestyle='-.',
            linewidth=2, alpha=0.8, label=f'Q_min={op_range.Q_min:.0f}'
        )
        ax.axvline(
            x=op_range.Q_max, color='#9b59b6', linestyle='-.',
            linewidth=2, alpha=0.8, label=f'Q_max={op_range.Q_max:.0f}'
        )

        # 在线上添加文字
        y_min, y_max = ax.get_ylim()
        ax.text(
            op_range.Q_min, y_max * 0.85,
            f'Q_min\n{op_range.Q_min:.0f}',
            fontsize=annotation_size * 0.8,
            ha='right', va='top',
            color='#9b59b6'
        )
        ax.text(
            op_range.Q_max, y_max * 0.85,
            f'Q_max\n{op_range.Q_max:.0f}',
            fontsize=annotation_size * 0.8,
            ha='left', va='top',
            color='#9b59b6'
        )

    def _add_curve_limits(
        self,
        ax: plt.Axes,
        annotations: CurveAnnotations,
        curve_type: str,
        predict_func: Optional[Callable] = None
    ) -> None:
        """添加曲线极限点标注（H0、Q_max等）

        Args:
            ax: matplotlib轴对象
            annotations: 标注信息
            curve_type: 曲线类型
            predict_func: 预测函数
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        if curve_type == 'qh':
            # 标注关死点扬程 H0 (Q=0时)
            if annotations.H0 is not None:
                ax.scatter(
                    0, annotations.H0,
                    marker='o', s=150, c='#3498db',
                    edgecolors='white', linewidths=1.5,
                    zorder=8
                )
                ax.annotate(
                    f'H₀={annotations.H0:.1f}m',
                    xy=(0, annotations.H0),
                    xytext=(ax.get_xlim()[1] * 0.05, annotations.H0),
                    fontsize=annotation_size,
                    color='#3498db',
                    arrowprops=dict(arrowstyle='->', color='#3498db', lw=1)
                )

            # 标注最大流量 (H=0时)
            if annotations.Q_max_at_H0 is not None:
                ax.scatter(
                    annotations.Q_max_at_H0, 0,
                    marker='o', s=150, c='#3498db',
                    edgecolors='white', linewidths=1.5,
                    zorder=8
                )
                ax.annotate(
                    f'Q_max={annotations.Q_max_at_H0:.0f}',
                    xy=(annotations.Q_max_at_H0, 0),
                    xytext=(annotations.Q_max_at_H0, ax.get_ylim()[1] * 0.1),
                    fontsize=annotation_size,
                    color='#3498db',
                    arrowprops=dict(arrowstyle='->', color='#3498db', lw=1)
                )

        elif curve_type == 'qp':
            # 标注空载功率
            if annotations.P_no_load is not None:
                ax.axhline(
                    y=annotations.P_no_load, color='#95a5a6',
                    linestyle=':', linewidth=1.5
                )
                ax.text(
                    ax.get_xlim()[1] * 0.02, annotations.P_no_load,
                    f'空载 P₀={annotations.P_no_load:.1f}kW',
                    fontsize=annotation_size * 0.8,
                    color='#7f8c8d', va='bottom'
                )

            # 标注电机额定功率线
            if annotations.motor_info is not None:
                ax.axhline(
                    y=annotations.motor_info.rated_power, color='#e74c3c',
                    linestyle='--', linewidth=2, label=f'电机额定功率 {annotations.motor_info.rated_power}kW'
                )
                # 过载警告区
                if annotations.motor_info.overload_limit:
                    ax.axhspan(
                        annotations.motor_info.rated_power,
                        annotations.motor_info.overload_limit,
                        color='#e74c3c', alpha=0.1
                    )

    def _add_info_box(
        self,
        ax: plt.Axes,
        annotations: Union[CurveAnnotations, PumpGroupAnnotations],
        curve_type: str,
        position: str = 'upper left'
    ) -> None:
        """添加综合信息框

        Args:
            ax: matplotlib轴对象
            annotations: 标注信息
            curve_type: 曲线类型
            position: 信息框位置
        """
        stats_config = self._config['stats_box']
        info_lines = []

        # 设备/泵组信息
        if isinstance(annotations, CurveAnnotations) and annotations.device_info:
            dev = annotations.device_info
            if dev.name:
                info_lines.append(f"设备: {dev.name}")
            if dev.model:
                info_lines.append(f"型号: {dev.model}")
            if dev.rated_speed:
                info_lines.append(f"转速: {dev.rated_speed:.0f} rpm")
        elif isinstance(annotations, PumpGroupAnnotations) and annotations.group_info:
            grp = annotations.group_info
            if grp.station_name:
                info_lines.append(f"泵站: {grp.station_name}")
            if grp.pump_combination:
                info_lines.append(f"泵组合: {grp.pump_combination}")
            info_lines.append(f"运行台数: {grp.n_pumps}台")

        # 拟合公式
        fit_eq = getattr(annotations, 'fit_equation', None)
        if fit_eq and fit_eq.formula:
            info_lines.append(f"公式: {fit_eq.formula}")

        # 精度指标
        fit_metrics = getattr(annotations, 'fit_metrics', None)
        if fit_metrics:
            if fit_metrics.r_squared is not None:
                info_lines.append(f"R² = {fit_metrics.r_squared:.4f}")
            if fit_metrics.rmse is not None:
                info_lines.append(f"RMSE = {fit_metrics.rmse:.4f}")
            if fit_metrics.mape is not None:
                info_lines.append(f"MAPE = {fit_metrics.mape:.2f}%")

        # 数据信息
        data_info = getattr(annotations, 'data_info', None)
        if data_info:
            info_lines.append(f"数据点数: {data_info.data_points}")
            if data_info.time_range_start and data_info.time_range_end:
                start_str = data_info.time_range_start.strftime('%Y-%m-%d')
                end_str = data_info.time_range_end.strftime('%Y-%m-%d')
                info_lines.append(f"时间范围: {start_str} ~ {end_str}")

        # 关键参数
        if isinstance(annotations, CurveAnnotations):
            if curve_type == 'qh':
                if annotations.H0:
                    info_lines.append(f"H₀ = {annotations.H0:.1f} m")
                if annotations.Q_max_at_H0:
                    info_lines.append(
                        f"Q_max = {annotations.Q_max_at_H0:.0f} m³/h")
            if annotations.bep:
                info_lines.append(
                    f"BEP: Q={annotations.bep.Q:.0f}, η={annotations.bep.eta:.1%}")
        elif isinstance(annotations, PumpGroupAnnotations):
            if annotations.Q_total_max:
                info_lines.append(
                    f"Q_total_max = {annotations.Q_total_max:.0f} m³/h")
            if annotations.H_group_max:
                info_lines.append(f"H_max = {annotations.H_group_max:.1f} m")
            if annotations.group_bep:
                info_lines.append(f"泵组BEP: η={annotations.group_bep.eta:.1%}")

        if not info_lines:
            return

        info_text = '\n'.join(info_lines)

        # 确定位置
        if position == 'upper left':
            x, y, ha, va = 0.02, 0.98, 'left', 'top'
        elif position == 'upper right':
            x, y, ha, va = 0.98, 0.98, 'right', 'top'
        elif position == 'lower left':
            x, y, ha, va = 0.02, 0.02, 'left', 'bottom'
        else:  # lower right
            x, y, ha, va = 0.98, 0.02, 'right', 'bottom'

        props = dict(
            boxstyle=f'round,pad=0.5,rounding_size={stats_config["border_radius"]}',
            facecolor=stats_config['background_color'],
            edgecolor=stats_config['border_color'],
            alpha=stats_config['alpha']
        )

        ax.text(
            x, y, info_text,
            transform=ax.transAxes,
            fontsize=stats_config['font_size'],
            verticalalignment=va,
            horizontalalignment=ha,
            bbox=props,
            family='monospace'
        )

    def _add_all_annotations(
        self,
        ax: plt.Axes,
        annotations: CurveAnnotations,
        curve_type: str,
        predict_func: Optional[Callable] = None
    ) -> None:
        """添加所有标注（单泵）

        Args:
            ax: matplotlib轴对象
            annotations: 标注信息
            curve_type: 曲线类型
            predict_func: 预测函数
        """
        # 1. 绘制警告区域（底层）
        for zone in annotations.warning_zones:
            self._add_warning_zone(ax, zone)

        # 2. 绘制效率区间
        for zone in annotations.efficiency_zones:
            self._add_efficiency_zone(ax, zone, curve_type, predict_func)

        # 3. 绘制运行范围
        if annotations.operating_range:
            self._add_operating_range(
                ax, annotations.operating_range, predict_func)

        # 4. 绘制曲线极限点
        self._add_curve_limits(ax, annotations, curve_type, predict_func)

        # 5. 绘制额定点
        if annotations.rated_point:
            self._add_rated_point(ax, annotations.rated_point, curve_type)

        # 6. 绘制BEP点（最上层）
        if annotations.bep:
            self._add_bep_marker(ax, annotations.bep, curve_type)

        # 7. 添加信息框
        self._add_info_box(ax, annotations, curve_type, position='upper left')

    def plot_curve_with_annotations(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        predict_func: Callable[[np.ndarray], np.ndarray],
        output_path: Path,
        annotations: CurveAnnotations,
        title: Optional[str] = None
    ) -> Path:
        """绘制带标注的特性曲线图（单泵）

        Args:
            x_data: X轴数据（流量Q）
            y_data: Y轴数据（扬程H/功率P/效率η）
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            predict_func: 预测函数
            output_path: 输出文件路径
            annotations: 标注信息
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        # 验证曲线类型
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        # 获取配置
        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]

        # 创建8K画布
        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制原始数据散点
        ax.scatter(
            x_data, y_data,
            c=colors['scatter'],
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='运行数据',
            zorder=2
        )

        # 绘制拟合曲线
        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)
        y_smooth = predict_func(x_smooth)
        ax.plot(
            x_smooth, y_smooth,
            c=colors['curve'],
            linewidth=style['curve']['line_width'],
            linestyle=style['curve']['line_style'],
            label='拟合曲线',
            zorder=3
        )

        # 绘制95%置信区间
        y_fitted = predict_func(x_data)
        residuals = y_data - y_fitted
        std_residuals = np.std(residuals)
        confidence_95 = 1.96 * std_residuals

        ax.fill_between(
            x_smooth,
            predict_func(x_smooth) - confidence_95,
            predict_func(x_smooth) + confidence_95,
            color=colors['confidence_95'],
            alpha=style['confidence']['alpha'],
            label='95%置信区间',
            zorder=1
        )

        # 设置标题和标签
        plot_title = title or labels['title']
        # 添加设备信息到标题
        if annotations.device_info:
            dev = annotations.device_info
            title_parts = [plot_title]
            if dev.name:
                title_parts.append(f"| {dev.name}")
            if dev.model:
                title_parts.append(f"| {dev.model}")
            plot_title = ' '.join(title_parts)

        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        # 设置网格
        ax.grid(
            True,
            alpha=style['grid']['alpha'],
            linewidth=style['grid']['line_width'],
            linestyle=style['grid']['line_style'],
            color=colors['grid']
        )

        # 设置刻度字体大小
        ax.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 添加所有标注
        self._add_all_annotations(ax, annotations, curve_type, predict_func)

        # 添加图例
        ax.legend(
            fontsize=self._config['fonts']['legend_size'],
            framealpha=style['legend']['frame_alpha'],
            shadow=style['legend']['shadow'],
            edgecolor=colors['grid'],
            loc='best'
        )

        # 紧凑布局
        if self._config['output']['tight_layout']:
            plt.tight_layout()

        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            output_path,
            format=self._config['output']['format'],
            dpi=resolution['dpi'],
            bbox_inches='tight',
            transparent=self._config['output']['transparent'],
            facecolor=self._config['output']['background_color'],
            pil_kwargs={
                'compress_level': self._config['output']['compression']}
        )

        # 关闭图形释放内存
        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 带标注曲线图已生成",
            extra={"extra_data": {
                "输出路径": str(output_path),
                "曲线类型": curve_type,
                "数据点数": len(x_data),
                "包含BEP": annotations.bep is not None,
                "高效区数量": len(annotations.efficiency_zones)
            }}
        )

        return output_path

    # ========================================================================
    # 泵组曲线绘制方法
    # ========================================================================

    def _add_pump_group_annotations(
        self,
        ax: plt.Axes,
        annotations: PumpGroupAnnotations,
        curve_type: str,
        predict_func: Optional[Callable] = None
    ) -> None:
        """添加泵组曲线标注

        Args:
            ax: matplotlib轴对象
            annotations: 泵组标注信息
            curve_type: 曲线类型
            predict_func: 预测函数
        """
        annotation_size = self._config['fonts'].get('annotation_size', 24)

        # 1. 绘制避免运行区域
        for zone in annotations.avoid_zones:
            self._add_warning_zone(ax, zone)

        # 2. 绘制效率区间
        for zone in annotations.efficiency_zones:
            self._add_efficiency_zone(ax, zone, curve_type, predict_func)

        # 3. 绘制推荐运行区域
        if annotations.recommended_zone:
            zone = annotations.recommended_zone
            ax.axvspan(
                zone.Q_min, zone.Q_max,
                color='#27ae60', alpha=0.15,
                label='推荐运行区',
                zorder=0
            )

        # 4. 绘制运行范围
        if annotations.operating_range:
            self._add_operating_range(
                ax, annotations.operating_range, predict_func)

        # 5. 绘制台数切换点
        for sp in annotations.switch_points:
            color = '#27ae60' if sp.action == 'start' else '#e74c3c'
            ax.axvline(
                x=sp.Q_threshold, color=color, linestyle=':',
                linewidth=2, alpha=0.8
            )
            y_pos = ax.get_ylim()[1] * 0.5
            label = sp.description or f"{sp.from_n}→{sp.to_n}台"
            ax.text(
                sp.Q_threshold, y_pos,
                label,
                fontsize=annotation_size * 0.7,
                ha='center', va='bottom',
                color=color,
                rotation=90
            )

        # 6. 标注泵组最大流量/扬程
        if annotations.Q_total_max is not None and curve_type == 'qh':
            ax.axvline(
                x=annotations.Q_total_max, color='#3498db', linestyle='--',
                linewidth=2, alpha=0.8
            )
            ax.text(
                annotations.Q_total_max, ax.get_ylim()[1] * 0.9,
                f'Q_total_max\n{annotations.Q_total_max:.0f}',
                fontsize=annotation_size * 0.8,
                ha='left', va='top',
                color='#3498db'
            )

        if annotations.H_group_max is not None and curve_type == 'qh':
            ax.axhline(
                y=annotations.H_group_max, color='#3498db', linestyle='--',
                linewidth=2, alpha=0.8
            )
            ax.text(
                ax.get_xlim()[0] * 1.02, annotations.H_group_max,
                f'H_max={annotations.H_group_max:.1f}m',
                fontsize=annotation_size * 0.8,
                ha='left', va='bottom',
                color='#3498db'
            )

        # 7. 绘制泵组BEP点
        if annotations.group_bep:
            bep = annotations.group_bep
            if curve_type == 'qh' and bep.H is not None:
                ax.scatter(
                    bep.Q, bep.H,
                    marker='*', s=500, c='gold',
                    edgecolors='black', linewidths=2,
                    label=f'泵组BEP (Q={bep.Q:.0f}, H={bep.H:.1f}, η={bep.eta:.1%})',
                    zorder=10
                )
                ax.annotate(
                    '泵组BEP',
                    xy=(bep.Q, bep.H),
                    xytext=(bep.Q + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.05,
                            bep.H + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05),
                    fontsize=annotation_size,
                    fontweight='bold',
                    color='#d35400',
                    arrowprops=dict(arrowstyle='->', color='#d35400', lw=2)
                )

        # 8. 添加信息框
        self._add_info_box(ax, annotations, curve_type, position='upper left')

    def plot_pump_group_curve(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        curve_type: str,
        predict_func: Callable[[np.ndarray], np.ndarray],
        output_path: Path,
        annotations: PumpGroupAnnotations,
        n_pump_curves: Optional[Dict[int, Callable]] = None,
        title: Optional[str] = None
    ) -> Path:
        """绘制泵组特性曲线图

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            curve_type: 曲线类型
            predict_func: 主预测函数（当前台数曲线）
            output_path: 输出路径
            annotations: 泵组标注信息
            n_pump_curves: 各台数曲线字典 {n: predict_func}
            title: 自定义标题

        Returns:
            Path: 保存的文件路径
        """
        # 验证曲线类型
        if curve_type not in self._config['curve_labels']:
            raise KeyError(f"未知的曲线类型: {curve_type}")

        # 获取配置
        resolution = self._config['resolution']
        colors = self._config['colors']
        style = self._config['style']
        labels = self._config['curve_labels'][curve_type]
        pump_group_colors = colors.get('pump_group', {})

        # 创建8K画布
        fig, ax = plt.subplots(
            figsize=(resolution['figure_width'], resolution['figure_height']),
            dpi=resolution['dpi']
        )

        # 绘制原始数据散点
        scatter_color = pump_group_colors.get('data', colors['scatter'])
        ax.scatter(
            x_data, y_data,
            c=scatter_color,
            alpha=style['scatter']['alpha'],
            s=style['scatter']['size'],
            linewidths=style['scatter']['edge_width'],
            label='运行数据',
            zorder=2
        )

        # 绘制各台数曲线
        curve_colors = colors.get(
            'history', ['#e74c3c', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c'])
        x_smooth = np.linspace(x_data.min(), x_data.max(), 1000)

        if n_pump_curves:
            for i, (n, func) in enumerate(sorted(n_pump_curves.items())):
                curve_color = curve_colors[i % len(curve_colors)]
                y_smooth = func(x_smooth)
                curve_info = annotations.n_pump_curves.get(n, {})
                label = curve_info.get('label', f'{n}台运行')
                ax.plot(
                    x_smooth, y_smooth,
                    c=curve_color,
                    linewidth=style['curve']['line_width'],
                    linestyle=style['curve']['line_style'],
                    label=label,
                    zorder=3
                )
        else:
            # 只绘制主曲线
            y_smooth = predict_func(x_smooth)
            ax.plot(
                x_smooth, y_smooth,
                c=pump_group_colors.get('synthesis', colors['curve']),
                linewidth=style['curve']['line_width'],
                linestyle=style['curve']['line_style'],
                label='泵组曲线',
                zorder=3
            )

        # 设置标题
        plot_title = title or labels['title']
        if annotations.group_info:
            grp = annotations.group_info
            title_parts = [plot_title]
            if grp.station_name:
                title_parts.append(f"| {grp.station_name}")
            if grp.pump_combination:
                title_parts.append(f"| 泵{grp.pump_combination}并联")
            plot_title = ' '.join(title_parts)

        ax.set_title(
            plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'],
                      fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'],
                      fontsize=self._config['fonts']['label_size'])

        # 设置网格
        ax.grid(
            True,
            alpha=style['grid']['alpha'],
            linewidth=style['grid']['line_width'],
            linestyle=style['grid']['line_style'],
            color=colors['grid']
        )

        ax.tick_params(labelsize=self._config['fonts']['tick_size'])

        # 添加泵组标注
        self._add_pump_group_annotations(
            ax, annotations, curve_type, predict_func)

        # 添加图例
        ax.legend(
            fontsize=self._config['fonts']['legend_size'],
            framealpha=style['legend']['frame_alpha'],
            shadow=style['legend']['shadow'],
            edgecolor=colors['grid'],
            loc='best'
        )

        # 紧凑布局
        if self._config['output']['tight_layout']:
            plt.tight_layout()

        # 保存图片
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            output_path,
            format=self._config['output']['format'],
            dpi=resolution['dpi'],
            bbox_inches='tight',
            transparent=self._config['output']['transparent'],
            facecolor=self._config['output']['background_color'],
            pil_kwargs={
                'compress_level': self._config['output']['compression']}
        )

        # 关闭图形
        if self._config['performance']['close_figures']:
            plt.close(fig)

        self._logger.info(
            "[HighResPlotter] 泵组曲线图已生成",
            extra={"extra_data": {
                "输出路径": str(output_path),
                "曲线类型": curve_type,
                "泵站ID": annotations.group_info.station_id if annotations.group_info else None,
                "台数曲线数": len(n_pump_curves) if n_pump_curves else 1
            }}
        )

        return output_path
