"""
泵组曲线绘图器 (app.services.characteristic_curves.pump_group.group_curve_plotter)

本模块提供泵组专用的曲线绘图功能：
- 复用HighResPlotter的底层绘图能力
- 添加泵组业务逻辑（泵组合标识、方法标识）
- 支持并联合成曲线、直接拟合曲线、对比图

使用方式：
    from app.services.characteristic_curves.pump_group import GroupCurvePlotter
    
    plotter = GroupCurvePlotter(config)
    comparison_path = plotter.plot_comparison_curve(...)

版本: v1.0
创建日期: 2025-12-09
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from app.services.characteristic_curves.output import HighResPlotter
from app.services.characteristic_curves.pump_group.models import (
    CurveFitMethod,
    DirectFitResult,
)


class GroupCurvePlotter:
    """泵组曲线绘图器
    
    通过组合模式复用HighResPlotter，添加泵组业务逻辑。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化泵组绘图器
        
        Args:
            config: 配置字典（从visualization.yaml读取）
            
        Raises:
            KeyError: 缺失必需配置项
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._config = config
        
        # 组合模式：持有HighResPlotter实例
        self._plotter = HighResPlotter(config)
        
        self._logger.info("[GroupCurvePlotter] 初始化完成")

    def plot_synthesis_curve(
        self,
        Q_data: np.ndarray,
        H_data: np.ndarray,
        synthesis_result: Dict[str, Any],
        station_id: int,
        pump_combination: List[int],
        curve_type: str,
        output_path: Path
    ) -> Path:
        """绘制并联合成曲线图
        
        Args:
            Q_data: 流量数据
            H_data: 扬程数据
            synthesis_result: 合成结果字典（包含forward_func, r_squared, rmse等）
            station_id: 站点ID
            pump_combination: 泵组合列表
            curve_type: 曲线类型
            output_path: 输出文件路径
            
        Returns:
            Path: 保存的文件路径
        """
        # 构建泵组标题
        pump_str = '+'.join(f"泵{pid}" for pid in pump_combination)
        title = f"站点{station_id} - {pump_str} - 并联合成曲线"
        
        # 提取预测函数和统计信息
        predict_func = synthesis_result['forward_func']
        r_squared = synthesis_result.get('r_squared')
        rmse = synthesis_result.get('rmse')
        
        # 调用HighResPlotter绘制
        return self._plotter.plot_curve(
            x_data=Q_data,
            y_data=H_data,
            curve_type=curve_type,
            predict_func=predict_func,
            output_path=output_path,
            title=title,
            r_squared=r_squared,
            rmse=rmse,
            data_points=len(Q_data),
            method_name="并联合成"
        )

    def plot_direct_fit_curve(
        self,
        Q_data: np.ndarray,
        H_data: np.ndarray,
        direct_fit_result: DirectFitResult,
        station_id: int,
        pump_combination: List[int],
        output_path: Path
    ) -> Path:
        """绘制直接拟合曲线图
        
        Args:
            Q_data: 流量数据
            H_data: 扬程数据
            direct_fit_result: 直接拟合结果
            station_id: 站点ID
            pump_combination: 泵组合列表
            output_path: 输出文件路径
            
        Returns:
            Path: 保存的文件路径
        """
        # 构建泵组标题
        pump_str = '+'.join(f"泵{pid}" for pid in pump_combination)
        title = f"站点{station_id} - {pump_str} - 直接拟合曲线"
        
        # 构建预测函数
        def predict_func(Q: np.ndarray) -> np.ndarray:
            return direct_fit_result.forward_func(Q)
        
        # 调用HighResPlotter绘制
        return self._plotter.plot_curve(
            x_data=Q_data,
            y_data=H_data,
            curve_type=direct_fit_result.curve_type,
            predict_func=predict_func,
            output_path=output_path,
            title=title,
            r_squared=direct_fit_result.r_squared,
            rmse=direct_fit_result.rmse,
            data_points=direct_fit_result.data_points,
            method_name="直接拟合"
        )

    def plot_comparison_curve(
        self,
        Q_data: np.ndarray,
        H_data: np.ndarray,
        synthesis_result: Dict[str, Any],
        direct_fit_result: DirectFitResult,
        recommended_method: CurveFitMethod,
        station_id: int,
        pump_combination: List[int],
        output_path: Path
    ) -> Path:
        """绘制对比图（并联合成 vs 直接拟合）

        Args:
            Q_data: 流量数据
            H_data: 扬程数据
            synthesis_result: 合成结果字典
            direct_fit_result: 直接拟合结果
            recommended_method: 推荐方法
            station_id: 站点ID
            pump_combination: 泵组合列表
            output_path: 输出文件路径

        Returns:
            Path: 保存的文件路径
        """
        # 构建泵组标题
        pump_str = '+'.join(f"泵{pid}" for pid in pump_combination)
        title = f"站点{station_id} - {pump_str} - 方法对比"

        # 获取泵组专用颜色配置
        pump_group_colors = self._config['colors']['pump_group']

        # 构建曲线列表
        curves = [
            {
                'name': '并联合成',
                'predict_func': synthesis_result['forward_func'],
                'color': pump_group_colors['synthesis'],
                'r_squared': synthesis_result.get('r_squared'),
                'rmse': synthesis_result.get('rmse')
            },
            {
                'name': '直接拟合',
                'predict_func': direct_fit_result.forward_func,
                'color': pump_group_colors['direct_fit'],
                'r_squared': direct_fit_result.r_squared,
                'rmse': direct_fit_result.rmse
            }
        ]

        # 确定推荐曲线的索引
        recommended_index = None
        if recommended_method == CurveFitMethod.SYNTHESIS:
            recommended_index = 0
        elif recommended_method == CurveFitMethod.DIRECT_FIT:
            recommended_index = 1

        # 调用HighResPlotter绘制对比图
        return self._plotter.plot_comparison(
            x_data=Q_data,
            y_data=H_data,
            curve_type=direct_fit_result.curve_type,
            curves=curves,
            output_path=output_path,
            title=title,
            recommended_index=recommended_index
        )

