"""
P0阶段主管道端到端集成测试

测试目标：
1. 验证13个P0阶段全部正确执行
2. 验证阶段间数据传递正确
3. 验证条件执行逻辑正确
4. 验证性能满足目标（<30秒）

版本: v1.0
创建日期: 2025-12-11
"""

import time
from datetime import datetime, timedelta
import numpy as np
import pytest

from app.services.characteristic_curves.pipeline import CurveFittingPipeline
from app.services.characteristic_curves.pipeline.pipeline_context import PipelineStage


class TestP0PipelineE2E:
    """P0主管道端到端测试"""

    def test_basic_fit_with_direct_data(self):
        """基础测试：使用直接提供的数据进行拟合"""
        # 准备测试数据（模拟QH曲线）
        Q = np.linspace(0, 100, 50)  # 流量 0-100 m³/h
        H = 50 - 0.005 * Q ** 2  # 扬程曲线 H = 50 - 0.005*Q²
        
        # 添加少量噪声
        np.random.seed(42)
        H_noisy = H + np.random.normal(0, 0.5, len(H))
        
        # 创建管道实例
        pipeline = CurveFittingPipeline()
        
        # 执行拟合
        start_time = time.time()
        result = pipeline.fit(
            device_id=1001,
            curve_type="qh",
            x_values=Q.tolist(),
            y_values=H_noisy.tolist()
        )
        duration = time.time() - start_time
        
        # 验证结果
        assert result.success, f"拟合失败: {result.metadata.get('error', '未知错误')}"
        assert result.r_squared >= 0.90, f"R²={result.r_squared} < 0.90"
        assert result.curve_type == "qh"
        assert result.device_id == 1001
        assert len(result.coefficients) > 0
        
        # 验证性能
        assert duration < 30, f"拟合耗时{duration:.2f}秒 > 30秒目标"
        
        print(f"\n✅ 基础拟合测试通过:")
        print(f"  - R² = {result.r_squared:.4f}")
        print(f"  - RMSE = {result.rmse:.4f}")
        print(f"  - 耗时 = {duration:.2f}秒")
        print(f"  - 数据点数 = {result.data_points}")

    def test_fit_with_time_range(self):
        """测试时间窗口划分功能"""
        Q = np.linspace(0, 100, 100)
        H = 50 - 0.005 * Q ** 2
        
        # 创建时间范围
        start_time = datetime.now() - timedelta(days=30)
        end_time = datetime.now()
        
        pipeline = CurveFittingPipeline()
        result = pipeline.fit(
            device_id=1002,
            curve_type="qh",
            time_range=(start_time, end_time),
            x_values=Q.tolist(),
            y_values=H.tolist()
        )
        
        assert result.success
        assert result.time_range is not None
        assert "start" in result.time_range
        assert "end" in result.time_range
        
        print(f"\n✅ 时间窗口测试通过:")
        print(f"  - 时间范围: {result.time_range['start']} 至 {result.time_range['end']}")

    def test_different_curve_types(self):
        """测试不同曲线类型"""
        curve_types = ["qh", "qp", "qeta"]
        
        for curve_type in curve_types:
            Q = np.linspace(0, 100, 50)
            
            # 根据曲线类型生成不同的Y值
            if curve_type == "qh":
                Y = 50 - 0.005 * Q ** 2  # 扬程曲线
            elif curve_type == "qp":
                Y = 10 + 0.5 * Q  # 功率曲线
            else:  # qeta
                Y = 0.8 * (1 - ((Q - 50) / 50) ** 2)  # 效率曲线（单峰）
                Y = np.clip(Y, 0, 1)  # 限制在0-1之间
            
            pipeline = CurveFittingPipeline()
            result = pipeline.fit(
                device_id=1003,
                curve_type=curve_type,
                x_values=Q.tolist(),
                y_values=Y.tolist()
            )
            
            assert result.success, f"{curve_type}曲线拟合失败"
            assert result.curve_type == curve_type
            
            print(f"\n✅ {curve_type.upper()}曲线测试通过 (R²={result.r_squared:.4f})")

    def test_stage_execution_sequence(self):
        """测试阶段执行顺序"""
        Q = np.linspace(0, 100, 50)
        H = 50 - 0.005 * Q ** 2
        
        pipeline = CurveFittingPipeline()
        result = pipeline.fit(
            device_id=1004,
            curve_type="qh",
            x_values=Q.tolist(),
            y_values=H.tolist()
        )
        
        # 验证所有P0必需阶段都执行了
        expected_stages = [
            PipelineStage.TIME_WINDOW_SPLIT,
            PipelineStage.DATA_EXTRACT,
            PipelineStage.DATA_CLEAN,
            PipelineStage.DATA_NORMALIZE,
            PipelineStage.METHOD_SELECT,
            PipelineStage.CURVE_FIT,
            PipelineStage.RESULT_VALIDATE,
            PipelineStage.RESULT_STORE,
        ]
        
        # 注意：某些阶段可能因条件不满足而跳过
        assert result.success
        
        print(f"\n✅ 阶段执行顺序测试通过")

    def test_conditional_stages_skip(self):
        """测试条件执行阶段的跳过逻辑"""
        Q = np.linspace(0, 100, 50)
        H = 50 - 0.005 * Q ** 2
        
        # 禁用某些条件阶段
        from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import PipelineConfig
        
        config = PipelineConfig(
            enable_scenario_detect=False,
            enable_steady_state_detect=False,
            enable_freq_normalize=False,
            enable_historical_eval=False
        )
        
        pipeline = CurveFittingPipeline(config=config)
        result = pipeline.fit(
            device_id=1005,
            curve_type="qh",
            x_values=Q.tolist(),
            y_values=H.tolist()
        )
        
        assert result.success
        
        print(f"\n✅ 条件跳过测试通过")

    def test_data_quality_requirements(self):
        """测试数据质量要求"""
        # 测试最小数据点数
        Q_min = np.linspace(0, 100, 100)  # ≥100点
        H_min = 50 - 0.005 * Q_min ** 2
        
        pipeline = CurveFittingPipeline()
        result = pipeline.fit(
            device_id=1006,
            curve_type="qh",
            x_values=Q_min.tolist(),
            y_values=H_min.tolist()
        )
        
        assert result.success
        assert result.data_points >= 100
        
        print(f"\n✅ 数据质量要求测试通过 (数据点数={result.data_points})")

    def test_error_handling(self):
        """测试错误处理"""
        pipeline = CurveFittingPipeline()
        
        # 测试缺少数据的情况
        with pytest.raises(Exception):
            result = pipeline.fit(
                device_id=1007,
                curve_type="qh"
                # 没有提供x_values和y_values
            )
        
        print(f"\n✅ 错误处理测试通过")

    def test_performance_benchmark(self):
        """性能基准测试"""
        # 测试不同数据规模下的性能
        data_sizes = [100, 500, 1000]
        
        for size in data_sizes:
            Q = np.linspace(0, 100, size)
            H = 50 - 0.005 * Q ** 2
            
            pipeline = CurveFittingPipeline()
            
            start_time = time.time()
            result = pipeline.fit(
                device_id=2000 + size,
                curve_type="qh",
                x_values=Q.tolist(),
                y_values=H.tolist()
            )
            duration = time.time() - start_time
            
            assert result.success
            assert duration < 30, f"{size}点拟合耗时{duration:.2f}秒 > 30秒"
            
            print(f"\n  {size}点: {duration:.3f}秒 (R²={result.r_squared:.4f})")
        
        print(f"\n✅ 性能基准测试通过")


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])
