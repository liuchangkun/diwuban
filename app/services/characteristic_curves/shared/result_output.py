"""
结果输出器 (app.services.characteristic_curves.shared.result_output)

本模块提供拟合结果的多种输出格式：
- JSON格式输出
- 日志格式输出
- Markdown报告生成

使用方式：
    from app.services.characteristic_curves.shared import ResultOutput
    
    output = ResultOutput()
    json_str = output.to_json(fit_result)
    output.to_log(fit_result)
    report_path = output.generate_report(fit_result)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from app.services.characteristic_curves.models import FitResult


class ResultOutput:
    """结果输出器
    
    支持多种格式输出拟合结果。
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """初始化结果输出器
        
        Args:
            output_dir: 输出目录（用于保存报告），默认为当前目录
        """
        self._output_dir = output_dir or Path(".")
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._logger.info(
            "[结果输出] 初始化",
            extra={"extra_data": {"组件": "ResultOutput", "输出目录": str(self._output_dir)}}
        )

    def to_json(
        self,
        fit_result: FitResult,
        indent: int = 2,
        include_metadata: bool = True
    ) -> str:
        """将拟合结果转换为JSON格式
        
        Args:
            fit_result: 拟合结果
            indent: 缩进空格数
            include_metadata: 是否包含元数据
            
        Returns:
            str: JSON格式字符串
        """
        data = self._fit_result_to_dict(fit_result, include_metadata)
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)

    def to_dict(
        self,
        fit_result: FitResult,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """将拟合结果转换为字典
        
        Args:
            fit_result: 拟合结果
            include_metadata: 是否包含元数据
            
        Returns:
            Dict: 字典格式结果
        """
        return self._fit_result_to_dict(fit_result, include_metadata)

    def to_log(
        self,
        fit_result: FitResult,
        level: int = logging.INFO
    ) -> None:
        """将拟合结果输出到日志
        
        Args:
            fit_result: 拟合结果
            level: 日志级别
        """
        quality_stars = self._get_quality_stars(fit_result.r_squared)
        
        extra_data = {
            "设备ID": fit_result.device_id,
            "曲线类型": fit_result.curve_type,
            "方法": fit_result.method_name,
            "R²": f"{fit_result.r_squared:.4f}",
            "RMSE": f"{fit_result.rmse:.4f}",
            "数据点数": fit_result.data_points,
            "质量": "⭐" * quality_stars
        }
        
        self._logger.log(
            level,
            f"[拟合结果] 设备{fit_result.device_id} {fit_result.curve_type}曲线",
            extra={"extra_data": extra_data}
        )

    def generate_report(
        self,
        fit_result: FitResult,
        x_data: Optional[np.ndarray] = None,
        y_data: Optional[np.ndarray] = None,
        y_fitted: Optional[np.ndarray] = None,
        image_paths: Optional[Dict[str, Path]] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """生成Markdown格式报告
        
        Args:
            fit_result: 拟合结果
            x_data: X轴数据
            y_data: 实际Y值
            y_fitted: 拟合Y值
            image_paths: 图片路径字典
            output_path: 输出路径，默认自动生成
            
        Returns:
            Path: 报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fit_report_{fit_result.device_id}_{fit_result.curve_type}_{timestamp}.md"
            output_path = self._output_dir / filename
        
        # 生成报告内容
        sections = [
            self._generate_summary(fit_result),
            self._generate_method_description(fit_result),
            self._generate_parameters(fit_result),
            self._generate_statistics(fit_result),
        ]
        
        if x_data is not None and y_data is not None and y_fitted is not None:
            sections.append(self._generate_residual_analysis(y_data, y_fitted))
        
        if image_paths:
            sections.append(self._generate_visualization_section(image_paths))
        
        report_content = "\n".join(sections)
        
        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_content, encoding="utf-8")
        
        self._logger.info(
            f"[结果输出] 报告已生成: {output_path}",
            extra={"extra_data": {"路径": str(output_path)}}
        )

        return output_path

    def _fit_result_to_dict(
        self,
        fit_result: FitResult,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """将FitResult转换为字典"""
        data = {
            "device_id": fit_result.device_id,
            "curve_type": fit_result.curve_type,
            "method_name": fit_result.method_name,
            "coefficients": fit_result.coefficients,
            "r_squared": fit_result.r_squared,
            "rmse": fit_result.rmse,
            "mae": fit_result.mae,
            "mape": fit_result.mape,
            "data_points": fit_result.data_points,
            "valid_q_range": fit_result.valid_q_range,
            "valid_h_range": fit_result.valid_h_range,
            "fitted_at": fit_result.fitted_at.isoformat() if fit_result.fitted_at else None,
        }

        if include_metadata:
            data["metadata"] = fit_result.metadata

        return data

    def _get_quality_stars(self, r_squared: float) -> int:
        """根据R²计算质量星级"""
        if r_squared >= 0.99:
            return 5
        elif r_squared >= 0.95:
            return 4
        elif r_squared >= 0.90:
            return 3
        elif r_squared >= 0.80:
            return 2
        else:
            return 1

    def _generate_summary(self, fit_result: FitResult) -> str:
        """模块1: 报告摘要（P0必须实现）"""
        quality_stars = self._get_quality_stars(fit_result.r_squared)
        fitted_at = fit_result.fitted_at.strftime('%Y-%m-%d %H:%M:%S') if fit_result.fitted_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""# 特性曲线拟合报告

## 1. 报告摘要

- **设备ID**: {fit_result.device_id or 'N/A'}
- **曲线类型**: {fit_result.curve_type or 'N/A'}
- **拟合方法**: {fit_result.method_name}
- **拟合质量**: {'⭐' * quality_stars}
- **R²**: {fit_result.r_squared:.4f}
- **数据点数**: {fit_result.data_points}
- **生成时间**: {fitted_at}
"""

    def _generate_method_description(self, fit_result: FitResult) -> str:
        """模块2: 拟合方法说明"""
        return f"""
## 2. 拟合方法说明

- **方法名称**: {fit_result.method_name}
- **参数数量**: {len(fit_result.coefficients)}
"""

    def _generate_parameters(self, fit_result: FitResult) -> str:
        """模块3: 参数估计结果（P0必须实现）"""
        params_table = "| 参数 | 值 |\n|------|------|\n"
        for key, value in fit_result.coefficients.items():
            if isinstance(value, (int, float)):
                params_table += f"| {key} | {value:.6f} |\n"
            else:
                params_table += f"| {key} | {value} |\n"

        return f"""
## 3. 参数估计结果

{params_table}"""

    def _generate_statistics(self, fit_result: FitResult) -> str:
        """模块4: 统计检验指标（P0必须实现）"""
        return f"""
## 4. 统计检验指标

| 指标 | 值 | 说明 |
|------|------|------|
| R² | {fit_result.r_squared:.4f} | 决定系数 |
| RMSE | {fit_result.rmse:.4f} | 均方根误差 |
| MAE | {fit_result.mae:.4f} | 平均绝对误差 |
| MAPE | {fit_result.mape:.2f}% | 平均绝对百分比误差 |
"""

    def _generate_residual_analysis(
        self,
        y_actual: np.ndarray,
        y_fitted: np.ndarray
    ) -> str:
        """模块5: 残差分析"""
        residuals = y_actual - y_fitted

        return f"""
## 5. 残差分析

| 统计量 | 值 |
|--------|------|
| 残差均值 | {np.mean(residuals):.4f} |
| 残差标准差 | {np.std(residuals):.4f} |
| 残差最大值 | {np.max(residuals):.4f} |
| 残差最小值 | {np.min(residuals):.4f} |
"""

    def _generate_visualization_section(self, image_paths: Dict[str, Path]) -> str:
        """模块6: 可视化图表（P0必须实现）"""
        section = "\n## 6. 可视化图表\n\n"
        for name, path in image_paths.items():
            section += f"### {name}\n\n![{name}]({path})\n\n"
        return section

    @property
    def output_dir(self) -> Path:
        """获取输出目录"""
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Union[str, Path]) -> None:
        """设置输出目录"""
        self._output_dir = Path(value)

