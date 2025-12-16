"""
P0性能基准测试 (test_p0_performance.py)

测试目标：
- 单设备拟合耗时 < 30秒
- 批量处理性能
- 内存占用 < 500MB
- 数据库查询 < 3秒

版本: v1.0
创建日期: 2025-12-11
"""

import time
import psutil
import numpy as np
import pytest
from datetime import datetime, timedelta

from app.services.characteristic_curves.pipeline import CurveFittingPipeline
from app.services.characteristic_curves.core.enums import CurveType


class TestP0Performance:
    """P0性能基准测试"""

    @pytest.fixture
    def pipeline(self):
        """创建pipeline实例"""
        return CurveFittingPipeline()

    @pytest.fixture
    def large_dataset(self):
        """生成大规模测试数据"""
        np.random.seed(42)
        Q = np.linspace(0, 100, 500)  # 500个点
        H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, 500)
        return Q.tolist(), H.tolist()

    def test_single_device_fit_performance(self, pipeline, large_dataset):
        """PERF-001: 单设备拟合性能 (目标<30秒)"""
        Q, H = large_dataset
        
        start_time = time.time()
        
        result = pipeline.fit(
            device_id=1001,
            curve_type="qh",
            x_values=Q,
            y_values=H,
        )
        
        duration = time.time() - start_time
        
        # 验证结果成功
        assert result.success is True
        
        # 性能要求：<30秒
        assert duration < 30.0, f"拟合耗时 {duration:.2f}秒，超过30秒限制"
        
        print(f"\n单设备拟合耗时: {duration:.2f}秒")

    def test_memory_usage(self, pipeline, large_dataset):
        """PERF-002: 内存占用测试 (目标<500MB)"""
        Q, H = large_dataset
        
        # 获取初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行拟合
        result = pipeline.fit(
            device_id=1001,
            curve_type="qh",
            x_values=Q,
            y_values=H,
        )
        
        # 获取峰值内存
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # 验证内存增长<500MB
        assert memory_increase < 500.0, f"内存增长 {memory_increase:.2f}MB，超过500MB限制"
        
        print(f"\n内存增长: {memory_increase:.2f}MB")

    def test_batch_processing_performance(self, pipeline):
        """PERF-003: 批量处理性能"""
        np.random.seed(42)
        
        # 准备10个设备的数据
        devices_data = []
        for device_id in range(1001, 1011):
            Q = np.linspace(0, 100, 100)
            H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, 100)
            devices_data.append((device_id, Q.tolist(), H.tolist()))
        
        start_time = time.time()
        results = []
        
        for device_id, Q, H in devices_data:
            result = pipeline.fit(
                device_id=device_id,
                curve_type="qh",
                x_values=Q,
                y_values=H,
            )
            results.append(result)
        
        duration = time.time() - start_time
        avg_time = duration / len(devices_data)
        
        # 验证所有结果成功
        assert all(r.success for r in results)
        
        # 平均每台<30秒
        assert avg_time < 30.0, f"平均拟合耗时 {avg_time:.2f}秒"
        
        print(f"\n批量处理10台设备:")
        print(f"  总耗时: {duration:.2f}秒")
        print(f"  平均耗时: {avg_time:.2f}秒")

    def test_different_data_sizes(self, pipeline):
        """PERF-004: 不同数据规模性能测试"""
        np.random.seed(42)
        
        data_sizes = [50, 100, 200, 500, 1000]
        results = []
        
        for size in data_sizes:
            Q = np.linspace(0, 100, size)
            H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, size)
            
            start_time = time.time()
            result = pipeline.fit(
                device_id=1001,
                curve_type="qh",
                x_values=Q.tolist(),
                y_values=H.tolist(),
            )
            duration = time.time() - start_time
            
            results.append({
                "size": size,
                "duration": duration,
                "success": result.success,
            })
        
        # 验证所有测试成功
        assert all(r["success"] for r in results)
        
        # 验证最大数据量<30秒
        max_duration = max(r["duration"] for r in results)
        assert max_duration < 30.0
        
        print("\n不同数据规模性能:")
        for r in results:
            print(f"  {r['size']}点: {r['duration']:.2f}秒")

    def test_curve_type_performance_comparison(self, pipeline):
        """PERF-005: 不同曲线类型性能对比"""
        np.random.seed(42)
        
        # 准备数据
        Q = np.linspace(0, 100, 200)
        
        curve_data = {
            "qh": 50 - 0.005 * Q ** 2,
            "qp": 10 + 0.1 * Q + 0.001 * Q ** 2,
            "qeta": 0.8 * np.exp(-((Q - 50) ** 2) / (2 * 15 ** 2)),
        }
        
        results = {}
        
        for curve_type, y_true in curve_data.items():
            y = y_true + np.random.normal(0, 0.5, len(y_true))
            
            start_time = time.time()
            result = pipeline.fit(
                device_id=1001,
                curve_type=curve_type,
                x_values=Q.tolist(),
                y_values=y.tolist(),
            )
            duration = time.time() - start_time
            
            results[curve_type] = {
                "duration": duration,
                "r_squared": result.r_squared,
                "success": result.success,
            }
        
        # 验证所有类型<30秒
        for curve_type, data in results.items():
            assert data["success"], f"{curve_type}拟合失败"
            assert data["duration"] < 30.0, f"{curve_type}耗时超过30秒"
        
        print("\n不同曲线类型性能:")
        for curve_type, data in results.items():
            print(f"  {curve_type}: {data['duration']:.2f}秒, R²={data['r_squared']:.4f}")

    def test_concurrent_fitting_simulation(self, pipeline):
        """PERF-006: 并发拟合模拟（顺序执行）"""
        np.random.seed(42)
        
        # 模拟5个并发请求（实际顺序执行）
        concurrent_requests = 5
        
        Q = np.linspace(0, 100, 200)
        H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, 200)
        
        start_time = time.time()
        results = []
        
        for i in range(concurrent_requests):
            result = pipeline.fit(
                device_id=1001 + i,
                curve_type="qh",
                x_values=Q.tolist(),
                y_values=H.tolist(),
            )
            results.append(result)
        
        duration = time.time() - start_time
        avg_time = duration / concurrent_requests
        
        # 验证所有请求成功
        assert all(r.success for r in results)
        
        # 平均响应时间<30秒
        assert avg_time < 30.0
        
        print(f"\n并发模拟({concurrent_requests}个请求):")
        print(f"  总耗时: {duration:.2f}秒")
        print(f"  平均耗时: {avg_time:.2f}秒")
        print(f"  吞吐量: {concurrent_requests/duration:.2f}请求/秒")


class TestPerformanceBaseline:
    """性能基线记录"""
    
    @pytest.fixture
    def pipeline(self):
        """创建pipeline实例"""
        return CurveFittingPipeline()

    def test_record_baseline(self, pipeline):
        """BASELINE-001: 记录标准性能基线"""
        np.random.seed(42)
        
        # 标准测试数据：200点
        Q = np.linspace(0, 100, 200)
        H = 50 - 0.005 * Q ** 2 + np.random.normal(0, 0.5, 200)
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        result = pipeline.fit(
            device_id=1001,
            curve_type="qh",
            x_values=Q.tolist(),
            y_values=H.tolist(),
        )
        duration = time.time() - start_time
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        # 打印基线数据
        print("\n" + "="*60)
        print("性能基线数据 (200点标准数据集)")
        print("="*60)
        print(f"拟合耗时: {duration:.3f}秒")
        print(f"内存增长: {memory_increase:.2f}MB")
        print(f"R²得分: {result.r_squared:.4f}")
        print(f"成功状态: {result.success}")
        print("="*60)
        
        # 基线要求
        assert duration < 30.0
        assert memory_increase < 500.0
        assert result.success is True
        assert result.r_squared >= 0.90


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
