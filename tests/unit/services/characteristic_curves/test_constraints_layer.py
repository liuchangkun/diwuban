"""
约束层测试 (test_constraints_layer.py)

测试 constraints 模块中的所有类：
- ConstraintLearner: 约束学习器
- ConstraintParameterManager: 约束参数管理器

测试用例遵循约束：
- 禁止使用默认值，所有参数显式指定
- 禁止回退机制
"""

import pytest

from app.services.characteristic_curves.constraints import (
    ConstraintLearner,
    ConstraintParameterManager,
)
from app.services.characteristic_curves.shared import CacheManager, ResultStorage


class TestConstraintLearner:
    """ConstraintLearner 约束学习器测试"""

    def test_init_with_method(self):
        """CL-001: 初始化测试 - 指定学习方法"""
        storage = ResultStorage()
        learner = ConstraintLearner(storage=storage, method="3sigma")
        
        assert learner.method == "3sigma"
        assert learner._storage is storage

    def test_init_quantile_method(self):
        """CL-002: 初始化测试 - 分位数方法"""
        learner = ConstraintLearner(storage=ResultStorage(), method="quantile")
        
        assert learner.method == "quantile"

    def test_method_setter_valid(self):
        """CL-003: 设置有效学习方法"""
        learner = ConstraintLearner(storage=ResultStorage(), method="3sigma")
        
        learner.method = "quantile"
        assert learner.method == "quantile"
        
        learner.method = "rated_based"
        assert learner.method == "rated_based"

    def test_method_setter_invalid(self):
        """CL-004: 设置无效学习方法应抛出异常"""
        learner = ConstraintLearner(storage=ResultStorage(), method="3sigma")
        
        with pytest.raises(ValueError) as exc_info:
            learner.method = "invalid_method"
        
        assert "不支持的学习方法" in str(exc_info.value)

    def test_learn_3sigma_algorithm(self):
        """CL-005: 3sigma 算法测试"""
        learner = ConstraintLearner(storage=ResultStorage(), method="3sigma")
        
        # 模拟历史数据
        history = [
            {"coefficients": {"a": -0.001, "b": 0.0, "c": 120.0}},
            {"coefficients": {"a": -0.0012, "b": 0.01, "c": 118.0}},
            {"coefficients": {"a": -0.0008, "b": -0.01, "c": 122.0}},
            {"coefficients": {"a": -0.0011, "b": 0.005, "c": 119.0}},
            {"coefficients": {"a": -0.0009, "b": -0.005, "c": 121.0}},
        ]
        
        params = learner._learn_3sigma(history)
        
        # 验证每个系数都有 min/max/mean
        assert "a_min" in params
        assert "a_max" in params
        assert "a_mean" in params
        assert "c_min" in params
        assert "c_max" in params

    def test_learn_quantile_algorithm(self):
        """CL-006: 分位数算法测试"""
        learner = ConstraintLearner(storage=ResultStorage(), method="quantile")
        
        history = [
            {"coefficients": {"a": -0.001, "c": 120.0}},
            {"coefficients": {"a": -0.0012, "c": 118.0}},
            {"coefficients": {"a": -0.0008, "c": 122.0}},
            {"coefficients": {"a": -0.0011, "c": 119.0}},
            {"coefficients": {"a": -0.0009, "c": 121.0}},
        ]
        
        params = learner._learn_quantile(
            history,
            lower_quantile=0.05,
            upper_quantile=0.95
        )
        
        assert "a_min" in params
        assert "a_max" in params
        assert "a_median" in params

    def test_learn_curve_constraints_alias(self, db_transaction, real_device_ids):
        """CL-007: learn_curve_constraints 别名方法测试"""
        if not real_device_ids:
            pytest.skip("没有可用的真实设备ID")

        # 确保数据库连接池已初始化（设置 _pool_initialized 标志）
        from pathlib import Path
        from app.core.config.loader_new import load_settings
        from app.adapters.db import init_database

        settings = load_settings(Path("configs"))
        init_database(settings)

        learner = ConstraintLearner(storage=ResultStorage(), method="3sigma")

        # learn_curve_constraints 是 learn_from_history 的别名
        result = learner.learn_curve_constraints(
            device_id=real_device_ids[0],
            curve_type="qh",
            min_samples=5  # 降低阈值以便测试
        )

        assert "learned_params" in result
        assert "confidence" in result
        assert "sample_count" in result
        assert "method" in result


class TestConstraintParameterManager:
    """ConstraintParameterManager 约束参数管理器测试"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """每个测试前重置缓存"""
        cache = CacheManager(max_size=100, ttl_seconds=3600)
        cache.clear()
        cache.reset_stats()
        yield cache
        cache.clear()

    def test_init(self, reset_cache):
        """CPM-001: 初始化测试"""
        manager = ConstraintParameterManager(
            learner=ConstraintLearner(storage=ResultStorage(), method="3sigma"),
            cache=reset_cache
        )
        
        assert manager.learner is not None
        assert manager.cache is not None

    def test_update_constraints(self, reset_cache):
        """CPM-002: 更新约束参数测试"""
        manager = ConstraintParameterManager(
            learner=ConstraintLearner(storage=ResultStorage(), method="3sigma"),
            cache=reset_cache
        )
        
        constraints = {
            "q_min": 0.0,
            "q_max": 300.0,
            "h_min": 30.0,
            "h_max": 120.0
        }
        
        result = manager.update_constraints(
            device_id=105,
            curve_type="qh",
            constraints=constraints,
            source="manual"
        )
        
        assert result is True

    def test_invalidate_cache(self, reset_cache):
        """CPM-003: 缓存失效测试"""
        manager = ConstraintParameterManager(
            learner=ConstraintLearner(storage=ResultStorage(), method="3sigma"),
            cache=reset_cache
        )
        
        # 先设置一些缓存
        cache_key = reset_cache.build_key(
            device_id=105,
            curve_type="qh",
            method_id="constraints"
        )
        reset_cache.set(cache_key, {"test": "value"}, ttl_seconds=60)
        
        # 使缓存失效
        manager.invalidate_cache(device_id=105, curve_type="qh")
        
        # 验证缓存已被清除
        assert reset_cache.get(cache_key) is None

