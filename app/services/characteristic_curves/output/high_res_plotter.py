"""
8K高分辨率绘图器 (app.services.characteristic_curves.output.high_res_plotter)

本模块提供8K高清拟合曲线绘图功能：
- 8K UHD分辨率（7680×4320）
- 全中文标签支持
- 多种图表类型（主曲线图、对比图等）
- 所有配置从YAML读取，禁止硬编码

使用方式：
    from app.services.characteristic_curves.output import HighResPlotter
    
    plotter = HighResPlotter(config)
    curve_path = plotter.plot_curve(x_data, y_data, fit_result, predict_func, output_path)

版本: v1.0
创建日期: 2025-12-09
参考文档: 特性曲线开发/开发文档/07_辅助模块/03_可视化.md
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


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
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
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
        resolution_keys = ['width', 'height', 'dpi', 'figure_width', 'figure_height']
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
        ax.set_title(plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'], fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'], fontsize=self._config['fonts']['label_size'])

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
            pil_kwargs={'compress_level': self._config['output']['compression']}
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
        default_colors = colors.get('history', ['#e74c3c', '#2ecc71', '#9b59b6', '#f39c12'])

        for i, curve_info in enumerate(curves):
            curve_name = curve_info['name']
            predict_func = curve_info['predict_func']
            curve_color = curve_info.get('color', default_colors[i % len(default_colors)])

            # 判断是否为推荐曲线
            is_recommended = (recommended_index is not None and i == recommended_index)

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
        ax.set_title(plot_title, fontsize=self._config['fonts']['title_size'], pad=20)
        ax.set_xlabel(labels['xlabel'], fontsize=self._config['fonts']['label_size'])
        ax.set_ylabel(labels['ylabel'], fontsize=self._config['fonts']['label_size'])

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
            pil_kwargs={'compress_level': self._config['output']['compression']}
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

