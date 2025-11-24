"""
集成验证测试 - 验证图片生成、报告生成、结果存储功能

测试目标：
1. CurveFittingPipeline可以接受新参数
2. 图片生成功能正常工作
3. 报告生成功能正常工作
4. 结果存储功能正常工作
"""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import (
    CurveFittingPipeline,
    PipelineConfig,
)


class TestIntegrationValidation:
    """集成验证测试"""

    def test_pipeline_accepts_new_parameters(self):
        """测试1: CurveFittingPipeline可以接受新参数"""
        # 创建mock组件
        mock_storage = MagicMock()
        mock_output = MagicMock()
        mock_output._output_dir = Path("./test_reports")
        plot_config = {"resolution": {"width": 1920, "height": 1080}}
        
        # 创建pipeline（不应该抛出异常）
        pipeline = CurveFittingPipeline(
            result_storage=mock_storage,
            result_output=mock_output,
            plot_config=plot_config,
            output_dir="./test_plots"
        )
        
        # 验证组件已正确设置
        assert pipeline._result_storage is mock_storage
        assert pipeline._result_output is mock_output
        assert pipeline._plot_config == plot_config
        assert pipeline._output_dir == "./test_plots"

    def test_pipeline_backward_compatible(self):
        """测试2: 向后兼容性 - 不提供新参数也能工作"""
        # 创建pipeline（旧方式）
        pipeline = CurveFittingPipeline()
        
        # 验证可选组件为None
        assert pipeline._result_storage is None
        assert pipeline._result_output is None
        assert pipeline._plot_config is None
        assert pipeline._output_dir == "."

    def test_fit_with_storage_integration(self):
        """测试3: 结果存储集成"""
        # 创建mock storage
        mock_storage = MagicMock()
        mock_storage.save.return_value = "v20251209_120000"
        
        # 创建pipeline
        pipeline = CurveFittingPipeline(result_storage=mock_storage)
        
        # 执行拟合
        x_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_values = np.array([5.0, 4.5, 3.8, 3.0, 2.0])
        
        result = pipeline.fit(
            device_id=1,
            curve_type="qh",
            x_values=x_values,
            y_values=y_values
        )
        
        # 验证storage.save()被调用
        assert mock_storage.save.called
        assert result.metadata.get('version') == "v20251209_120000"

    def test_fit_without_storage_still_works(self):
        """测试4: 不提供storage也能正常工作"""
        # 创建pipeline（不提供storage）
        pipeline = CurveFittingPipeline()
        
        # 执行拟合
        x_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_values = np.array([5.0, 4.5, 3.8, 3.0, 2.0])
        
        result = pipeline.fit(
            device_id=1,
            curve_type="qh",
            x_values=x_values,
            y_values=y_values
        )
        
        # 验证拟合成功
        assert result.success is True
        assert result.r_squared > 0.8

    def test_plot_generation_skipped_without_config(self):
        """测试5: 没有plot_config时跳过图片生成"""
        # 创建pipeline（不提供plot_config）
        pipeline = CurveFittingPipeline()
        
        # 执行拟合
        x_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_values = np.array([5.0, 4.5, 3.8, 3.0, 2.0])
        
        result = pipeline.fit(
            device_id=1,
            curve_type="qh",
            x_values=x_values,
            y_values=y_values
        )
        
        # 验证没有生成图片
        assert 'images' not in result.metadata or not result.metadata.get('images')

    def test_report_generation_skipped_without_output(self):
        """测试6: 没有result_output时跳过报告生成"""
        # 创建pipeline（不提供result_output）
        pipeline = CurveFittingPipeline()
        
        # 执行拟合
        x_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_values = np.array([5.0, 4.5, 3.8, 3.0, 2.0])
        
        result = pipeline.fit(
            device_id=1,
            curve_type="qh",
            x_values=x_values,
            y_values=y_values
        )
        
        # 验证没有生成报告
        assert 'reports' not in result.metadata or not result.metadata.get('reports')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

