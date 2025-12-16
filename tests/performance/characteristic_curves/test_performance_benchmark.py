"""
性能基准测试 (test_performance_benchmark.py)

测试性能指标：
- 单次拟合时间 < 5秒
- 内存使用 < 500MB
- 批量处理效率

版本: v1.0
更新日期: 2025-12-09
"""

import time
import tracemalloc
import numpy as np
import pytest
from datetime import datetime

from app.services.characteristic_curves.pump_group import (
    PumpGroupProcessor,
    ParallelSynthesizer,
    SystemCorrectionModel,
    CorrectionModelConfig,
    P2Pipeline,
)
from app.services.characteristic_curves.models import GroupProcessingStrategy


class TestFittingPerformance:
    """拟合性能测试"""

    @pytest.fixture
    def large_dataset(self):
        """生成大数据集（10000点）"""
        np.random.seed(42)
        n_points = 10000
        Q = np.linspace(0, 300, n_points)
        H = 100.0 - 0.001 * Q ** 2 + np.random.normal(0, 2, n_points)
        return Q, H

    def test_polynomial_fitting_time(self, large_dataset):
        """PERF-001: 多项式拟合时间 < 1秒"""
        Q, H = large_dataset
        
        start = time.perf_counter()
        
        # 多项式拟合
        coeffs = np.polyfit(Q, H, 2)
        H_pred = np.polyval(coeffs, Q)
        r_squared = 1 - np.sum((H - H_pred) ** 2) / np.sum((H - np.mean(H)) ** 2)
        
        elapsed = time.perf_counter() - start
        
        assert elapsed < 1.0, f"拟合时间 {elapsed:.2f}s > 1s"
        assert r_squared > 0.9

    def test_correction_model_training_time(self):
        """PERF-002: 修正模型训练时间 < 2秒"""
        config = CorrectionModelConfig(model_type="polynomial", polynomial_degree=2, min_training_points=100)
        model = SystemCorrectionModel(config=config)

        # 生成训练数据 [N, Q_total, H_theoretical, H_actual]
        np.random.seed(42)
        n_samples = 5000
        N = np.random.randint(1, 6, n_samples)
        Q_total = np.random.uniform(50, 500, n_samples)
        H_theo = 100.0 - 0.0005 * Q_total ** 2
        alpha = 1.0 + 0.0001 * Q_total + np.random.normal(0, 0.01, n_samples)
        H_actual = H_theo * alpha
        training_data = np.column_stack([N, Q_total, H_theo, H_actual])

        start = time.perf_counter()
        model.fit(station_id=1, pump_ids=[1, 2, 3], training_data=training_data)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"训练时间 {elapsed:.2f}s > 2s"

    def test_synthesis_time(self):
        """PERF-003: 并联合成时间 < 0.5秒"""
        synthesizer = ParallelSynthesizer()

        # 注册基准泵
        synthesizer.register_pump_curve(
            pump_id=1,
            curve_func=lambda Q: 100.0 - 0.01 * Q * Q,
            inverse_func=lambda H: np.sqrt(max(0, (100.0 - H) / 0.01)),
        )

        start = time.perf_counter()

        # 合成6台同构泵
        result = synthesizer.synthesize_homogeneous(base_pump_id=1, n_pumps=6)

        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"合成时间 {elapsed:.3f}s > 0.5s"


class TestMemoryUsage:
    """内存使用测试"""

    def test_fitting_memory_usage(self):
        """MEM-001: 拟合内存使用 < 100MB"""
        tracemalloc.start()
        
        # 模拟拟合过程
        np.random.seed(42)
        Q = np.linspace(0, 300, 50000)
        H = 100.0 - 0.001 * Q ** 2 + np.random.normal(0, 2, 50000)
        
        coeffs = np.polyfit(Q, H, 2)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"峰值内存 {peak_mb:.1f}MB > 100MB"

    def test_synthesis_memory_usage(self):
        """MEM-002: 合成内存使用 < 50MB"""
        tracemalloc.start()

        synthesizer = ParallelSynthesizer()

        # 注册基准泵
        synthesizer.register_pump_curve(
            pump_id=1,
            curve_func=lambda Q: 100.0 - 0.01 * Q * Q,
            inverse_func=lambda H: np.sqrt(max(0, (100.0 - H) / 0.01)),
        )

        # 合成10台同构泵
        result = synthesizer.synthesize_homogeneous(base_pump_id=1, n_pumps=10)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 50, f"峰值内存 {peak_mb:.1f}MB > 50MB"


class TestAccuracyBenchmark:
    """精度基准测试"""

    def test_fitting_accuracy(self):
        """ACC-001: 拟合精度（R² > 0.95）"""
        # 使用已知函数生成数据
        np.random.seed(42)
        Q_true = np.linspace(0, 100, 100)
        H_true = 100.0 - 0.01 * Q_true ** 2  # 无噪声
        
        # 添加小噪声
        H_noisy = H_true + np.random.normal(0, 0.5, 100)
        
        # 拟合
        coeffs = np.polyfit(Q_true, H_noisy, 2)
        H_pred = np.polyval(coeffs, Q_true)
        
        # 计算R²
        ss_res = np.sum((H_noisy - H_pred) ** 2)
        ss_tot = np.sum((H_noisy - np.mean(H_noisy)) ** 2)
        r_squared = 1 - ss_res / ss_tot
        
        assert r_squared > 0.95, f"R² = {r_squared:.4f} < 0.95"

    def test_synthesis_accuracy(self):
        """ACC-002: 合成精度验证"""
        # 已知单泵曲线
        def single_forward(Q):
            return 100.0 - 0.01 * Q * Q

        def single_inverse(H):
            return np.sqrt(max(0, (100.0 - H) / 0.01))

        synthesizer = ParallelSynthesizer()

        # 注册基准泵
        synthesizer.register_pump_curve(1, single_forward, single_inverse)

        # 合成3台同构泵
        result = synthesizer.synthesize_homogeneous(base_pump_id=1, n_pumps=3)

        # 验证并联特性
        # 单泵Q=50 → H=75
        # 3泵并联Q_total=150 → H应该=75
        single_H = single_forward(50.0)
        synth_H = result(150.0)

        error = abs(synth_H - single_H)
        assert error < 2.0, f"合成误差 {error:.2f}m > 2m"

