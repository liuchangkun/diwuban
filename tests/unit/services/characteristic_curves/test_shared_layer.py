"""
共用层测试 (test_shared_layer.py)

测试 shared 模块中的所有类：
- CacheManager: 缓存管理器
- BatchProcessor: 批处理器
- ParameterOptimizer: 参数优化器
- ResultOutput: 结果输出器
- ResultStorage: 结果存储（数据库测试）
- TimeWindowSplitter: 时间窗口划分器（数据库测试）
- HistoricalDataEvaluator: 历史数据评估器

测试用例遵循约束：
- 禁止使用默认值，所有参数显式指定
- 禁止回退机制
"""

from app.services.characteristic_curves.shared.historical_data_evaluator import (
    TimeWindow,
)
from app.services.characteristic_curves.shared import (
    BatchProcessor,
    CacheManager,
    HistoricalDataEvaluator,
    ParameterOptimizer,
    ResultOutput,
    ResultStorage,
    TimeWindowSplitter,
)
from app.services.characteristic_curves.models import FitResult
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time
import pytest

# P2模块已删除，等待P0完成后重写
pytestmark = pytest.mark.skip(reason="P2模块已删除，等待P0完成后重写")


class TestCacheManager:
    """CacheManager 缓存管理器测试"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """每个测试前重置缓存单例"""
        cache = CacheManager(max_size=100, ttl_seconds=3600)
        cache.clear()
        cache.reset_stats()
        yield cache
        cache.clear()

    def test_set_and_get(self, reset_cache):
        """CM-001: 缓存设置和获取"""
        cache = reset_cache

        # 设置缓存
        cache.set("test_key_1", {"value": 123}, ttl_seconds=60)

        # 获取缓存
        result = cache.get("test_key_1")

        assert result is not None
        assert result["value"] == 123

    def test_cache_expiration(self, reset_cache):
        """CM-002: 缓存过期测试"""
        cache = reset_cache

        # 设置极短过期时间
        cache.set("expire_key", "expire_value", ttl_seconds=1)

        # 立即获取应该存在
        assert cache.get("expire_key") == "expire_value"

        # 等待过期
        time.sleep(1.1)

        # 过期后应该返回 None
        assert cache.get("expire_key") is None

    def test_lru_eviction(self, reset_cache):
        """CM-003: LRU淘汰测试"""
        # 创建一个小容量缓存
        small_cache = CacheManager.__new__(CacheManager)
        small_cache._initialized = False
        small_cache.__init__(max_size=3, ttl_seconds=3600)
        small_cache.clear()
        small_cache.reset_stats()

        # 填满缓存
        small_cache.set("key1", "value1", ttl_seconds=3600)
        small_cache.set("key2", "value2", ttl_seconds=3600)
        small_cache.set("key3", "value3", ttl_seconds=3600)

        # 访问 key1 使其变为最近使用
        small_cache.get("key1")

        # 添加新条目，应该淘汰 key2（最久未使用）
        small_cache.set("key4", "value4", ttl_seconds=3600)

        # key2 应该被淘汰
        assert small_cache.get("key2") is None
        # key1, key3, key4 应该存在
        assert small_cache.get("key1") == "value1"
        assert small_cache.get("key3") == "value3"
        assert small_cache.get("key4") == "value4"

    def test_clear(self, reset_cache):
        """CM-004: 清空缓存测试"""
        cache = reset_cache

        # 添加多个条目
        cache.set("clear_key1", "value1", ttl_seconds=60)
        cache.set("clear_key2", "value2", ttl_seconds=60)
        cache.set("clear_key3", "value3", ttl_seconds=60)

        # 清空所有
        count = cache.clear()

        assert count == 3
        assert cache.get("clear_key1") is None
        assert cache.get("clear_key2") is None

    def test_get_stats(self, reset_cache):
        """CM-005: 获取统计信息测试"""
        cache = reset_cache

        # 添加并访问
        cache.set("stats_key", "stats_value", ttl_seconds=60)
        cache.get("stats_key")  # hit
        cache.get("nonexistent")  # miss

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert 0 <= stats["hit_rate"] <= 1

    def test_build_key(self, reset_cache):
        """CM-006: 构建缓存键测试"""
        cache = reset_cache

        key = cache.build_key(
            device_id=105,
            curve_type="qh",
            method_id="math_poly_2",
            version="20251208"
        )

        assert "105" in key
        assert "qh" in key
        assert "math_poly_2" in key
        assert "version=20251208" in key

    def test_invalidate_on_save(self, reset_cache):
        """CM-007: 保存后缓存失效测试"""
        cache = reset_cache

        # 添加匹配的缓存条目
        cache.set("105:qh:math_poly_2:v1", "data1", ttl_seconds=60)
        cache.set("105:qh:math_poly_2:v2", "data2", ttl_seconds=60)
        cache.set("105:qp:math_poly_2:v1", "data3", ttl_seconds=60)

        # 失效 device_id=105, curve_type=qh 的缓存
        count = cache.invalidate_on_save(device_id=105, curve_type="qh")

        # 应该清除 2 个条目
        assert count == 2
        assert cache.get("105:qh:math_poly_2:v1") is None
        assert cache.get("105:qh:math_poly_2:v2") is None
        # qp 类型的应该还在
        assert cache.get("105:qp:math_poly_2:v1") == "data3"

    def test_reset_stats(self, reset_cache):
        """CM-008: 重置统计信息测试"""
        cache = reset_cache

        # 产生一些统计
        cache.set("reset_key", "value", ttl_seconds=60)
        cache.get("reset_key")
        cache.get("nonexistent")

        # 重置
        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestBatchProcessor:
    """BatchProcessor 批处理器测试"""

    def test_iterate_batches(self):
        """BP-001: 分批迭代测试"""
        processor = BatchProcessor(batch_size=3)

        # 创建测试数据
        data = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7, 8],
            "y": [10, 20, 30, 40, 50, 60, 70, 80]
        })

        batches = list(processor.iterate_batches(data, batch_size=3))

        # 应该分为 3 批：3+3+2
        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 2

    def test_process_sequential(self):
        """BP-002: 顺序处理任务测试"""
        processor = BatchProcessor(batch_size=5000)

        tasks = [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
            {"id": 3, "value": 30}
        ]

        def process_func(task):
            return task["value"] * 2

        results = processor.process_sequential(tasks, process_func)

        assert results == [20, 40, 60]

    def test_process_batches(self):
        """BP-003: 分批处理数据测试"""
        processor = BatchProcessor(batch_size=5)

        data = pd.DataFrame({
            "value": list(range(12))
        })

        def sum_func(batch):
            return batch["value"].sum()

        results = processor.process_batches(data, sum_func, batch_size=5)

        # 12 条数据分为 3 批：0-4, 5-9, 10-11
        assert len(results) == 3
        assert results[0] == sum(range(5))      # 0+1+2+3+4 = 10
        assert results[1] == sum(range(5, 10))  # 5+6+7+8+9 = 35
        assert results[2] == sum(range(10, 12))  # 10+11 = 21

    def test_process_batches_empty_data(self):
        """BP-004: 空数据处理测试"""
        processor = BatchProcessor(batch_size=5)

        data = pd.DataFrame()

        def dummy_func(batch):
            return len(batch)

        results = processor.process_batches(data, dummy_func, batch_size=5)

        assert results == []


class TestParameterOptimizer:
    """ParameterOptimizer 参数优化器测试"""

    def test_cross_validate(self):
        """PO-001: 交叉验证测试"""
        optimizer = ParameterOptimizer(n_folds=3, random_state=42)

        # 生成简单线性数据
        np.random.seed(42)
        X = np.linspace(0, 100, 50)
        y = 2 * X + 10 + np.random.normal(0, 1, 50)

        def fit_func(X_train, y_train, params):
            # 简单线性拟合
            degree = params.get("degree", 1)
            coeffs = np.polyfit(X_train, y_train, degree)
            return lambda x: np.polyval(coeffs, x)

        result = optimizer.cross_validate(
            X=X,
            y=y,
            fit_func=fit_func,
            params={"degree": 1},
            n_folds=3
        )

        assert "mean_r2" in result
        assert "std_r2" in result
        assert "fold_scores" in result
        assert len(result["fold_scores"]) == 3
        assert result["mean_r2"] > 0.9  # 线性数据应该有很高的 R²

    def test_grid_search(self):
        """PO-002: 网格搜索测试"""
        optimizer = ParameterOptimizer(n_folds=3, random_state=42)

        # 生成二次数据
        np.random.seed(42)
        X = np.linspace(0, 10, 30)
        y = 0.5 * X**2 - 2 * X + 5 + np.random.normal(0, 0.5, 30)

        def fit_func(X_train, y_train, params):
            degree = params["degree"]
            coeffs = np.polyfit(X_train, y_train, degree)
            return lambda x: np.polyval(coeffs, x)

        result = optimizer.grid_search(
            X=X,
            y=y,
            fit_func=fit_func,
            param_grid={"degree": [1, 2, 3]}
        )

        assert "best_params" in result
        assert "best_score" in result
        assert "all_results" in result
        # 二次数据应该选择 degree=2 为最优
        assert result["best_params"]["degree"] == 2


class TestResultOutput:
    """ResultOutput 结果输出器测试"""

    @pytest.fixture
    def sample_fit_result(self):
        """创建测试用 FitResult"""
        return FitResult(
            device_id=105,
            curve_type="qh",
            method_id="math_poly_2",
            method_name="二次多项式",
            version="20251208_150000",
            coefficients={"a": -0.001, "b": 0.0, "c": 120.0},
            r_squared=0.9856,
            rmse=1.234,
            mae=0.987,
            mape=2.5,
            data_points=200,
            time_range={"start": "2025-01-01", "end": "2025-01-31"},
            normalization_params={},
            created_at=datetime(2025, 12, 8, 15, 0, 0),
            fitted_at=datetime(2025, 12, 8, 15, 0, 1),
            metadata={"source": "test"},
        )

    def test_to_json(self, sample_fit_result):
        """RO-001: JSON 输出测试"""
        output = ResultOutput(output_dir=Path("."))

        json_str = output.to_json(
            fit_result=sample_fit_result,
            indent=2,
            include_metadata=True
        )

        assert isinstance(json_str, str)
        assert "105" in json_str
        assert "qh" in json_str
        assert "0.9856" in json_str

    def test_to_dict(self, sample_fit_result):
        """RO-002: 字典输出测试"""
        output = ResultOutput(output_dir=Path("."))

        result_dict = output.to_dict(
            fit_result=sample_fit_result,
            include_metadata=True
        )

        assert isinstance(result_dict, dict)
        assert result_dict["device_id"] == 105
        assert result_dict["curve_type"] == "qh"
        assert result_dict["r_squared"] == 0.9856
        assert "metadata" in result_dict

    def test_generate_report(self, sample_fit_result, tmp_path):
        """RO-003: Markdown 报告生成测试"""
        output = ResultOutput(output_dir=tmp_path)

        # 构造output_paths
        output_paths = {
            'main_curve': str(tmp_path / 'curve.png'),
            'residuals': str(tmp_path / 'residuals.png')
        }

        report_path = output.generate_report(
            fit_result=sample_fit_result,
            device_id=105,
            curve_type='qh',
            output_paths=output_paths,
            format='markdown'
        )

        assert report_path is not None
        from pathlib import Path
        report_file = Path(report_path)
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "拟合报告" in content
        assert "105" in content
        assert "0.9856" in content


class TestResultStorage:
    """ResultStorage 结果存储测试（需要数据库）

    注意：由于 ResultStorage 使用自己的数据库连接（get_connection()），
    测试数据会被持久化到数据库。因此使用唯一版本号避免冲突。
    """

    @pytest.fixture
    def unique_suffix(self):
        """生成唯一后缀，避免版本冲突"""
        import uuid
        return uuid.uuid4().hex[:8]

    @pytest.fixture
    def sample_fit_result(self, real_device_ids, unique_suffix):
        """创建测试用 FitResult - 使用真实设备ID和唯一版本号"""
        if not real_device_ids:
            pytest.skip("没有可用的真实设备ID")

        return FitResult(
            device_id=real_device_ids[0],  # 使用真实设备ID
            curve_type="qh",
            method_id="test_method",
            method_name="测试方法",
            version=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_suffix}",
            coefficients={"a": -0.001, "b": 0.0, "c": 120.0},
            r_squared=0.9856,
            rmse=1.234,
            mae=0.987,
            mape=2.5,
            data_points=200,
            time_range={"start": "2025-01-01T00:00:00",
                        "end": "2025-01-31T23:59:59"},
            normalization_params={"Q": {"min": 0.0, "max": 300.0}},
            created_at=datetime.now(),
            fitted_at=datetime.now(),
            metadata={"method_params": {"degree": 2}},
        )

    def test_save_atomic_write(self, db_transaction, sample_fit_result):
        """RS-001: 三表原子写入测试"""
        storage = ResultStorage()

        version = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result
        )

        assert version is not None
        assert len(version) > 0

    def test_load_latest_version(self, db_transaction, sample_fit_result, unique_suffix):
        """RS-002: 加载最新版本测试"""
        storage = ResultStorage()

        # 先保存（使用唯一版本号避免冲突）
        version_name = f"load_latest_{unique_suffix}"
        saved_version = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=version_name
        )

        # 再加载
        loaded = storage.load(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type
        )

        assert loaded is not None
        assert loaded.version == saved_version
        assert loaded.r_squared == sample_fit_result.r_squared

    def test_load_specific_version(self, db_transaction, sample_fit_result, unique_suffix):
        """RS-003: 加载指定版本测试"""
        storage = ResultStorage()

        # 保存两个版本（使用唯一后缀避免冲突）
        version1 = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=f"v1_test_{unique_suffix}"
        )

        sample_fit_result.r_squared = 0.9999
        version2 = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=f"v2_test_{unique_suffix}"
        )

        # 加载指定版本
        loaded = storage.load(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            version=version1
        )

        assert loaded is not None
        assert loaded.version == version1

    def test_list_versions(self, db_transaction, sample_fit_result, unique_suffix):
        """RS-004: 列出版本测试"""
        storage = ResultStorage()

        # 保存两个版本（使用唯一后缀避免冲突）
        v1_name = f"list_v1_{unique_suffix}"
        v2_name = f"list_v2_{unique_suffix}"

        storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=v1_name
        )
        storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=v2_name
        )

        versions = storage.list_versions(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            limit=10,
            include_deprecated=False
        )

        assert len(versions) >= 2
        assert any(v["version"] == v1_name for v in versions)
        assert any(v["version"] == v2_name for v in versions)

    def test_delete_version_soft(self, db_transaction, sample_fit_result, unique_suffix):
        """RS-005: 软删除版本测试"""
        storage = ResultStorage()

        # 保存（使用唯一后缀避免冲突）
        version = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=f"delete_test_{unique_suffix}"
        )

        # 软删除
        result = storage.delete_version(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            version=version,
            soft_delete=True
        )

        assert result is True

        # 加载应该返回 None（因为状态已变为 deprecated）
        loaded = storage.load(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            version=version
        )
        assert loaded is None

    def test_get_latest_version(self, db_transaction, sample_fit_result, unique_suffix):
        """RS-006: 获取最新版本号测试"""
        storage = ResultStorage()

        # 保存（使用唯一后缀避免冲突）
        saved_version = storage.save(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type,
            fit_result=sample_fit_result,
            version=f"latest_test_{unique_suffix}"
        )

        latest = storage.get_latest_version(
            device_id=sample_fit_result.device_id,
            curve_type=sample_fit_result.curve_type
        )

        assert latest == saved_version


class TestTimeWindowSplitter:
    """TimeWindowSplitter 时间窗口划分器测试"""

    def test_split_with_custom_range_default_ratio(self):
        """TW-001: 自定义时间范围划分（默认75%/25%比例）"""
        splitter = TimeWindowSplitter(
            fit_ratio=0.75,
            min_fit_days=30,
            min_test_days=7,
            min_test_points=100
        )

        start_time = datetime(2025, 1, 1)
        end_time = datetime(2025, 4, 1)  # 90天

        result = splitter.split_with_custom_range(
            start_time=start_time,
            end_time=end_time,
            total_points=1000
        )

        # 验证比例
        assert result.fit_days == 67  # 90 * 0.75 ≈ 67
        assert result.test_days == 23  # 90 - 67 = 23
        assert result.total_days == 90
        assert result.fit_window.start == start_time
        assert result.test_window.end == end_time

    def test_split_min_days_check(self):
        """TW-002: 最小天数检查测试"""
        splitter = TimeWindowSplitter(
            fit_ratio=0.75,
            min_fit_days=30,
            min_test_days=7,
            min_test_points=100
        )

        # 数据天数不足
        start_time = datetime(2025, 1, 1)
        end_time = datetime(2025, 1, 20)  # 只有19天

        result = splitter.split_with_custom_range(
            start_time=start_time,
            end_time=end_time,
            total_points=100
        )

        # 应该有警告
        assert len(result.warnings) > 0
        assert any("数据天数不足" in w for w in result.warnings)

    def test_split_from_database(self, db_connection, real_device_ids):
        """TW-003: 从数据库划分时间窗口测试"""
        if not real_device_ids:
            pytest.skip("没有可用的真实设备ID")

        splitter = TimeWindowSplitter(
            fit_ratio=0.75,
            min_fit_days=30,
            min_test_days=7,
            min_test_points=100
        )

        device_id = real_device_ids[0]

        result = splitter.split(
            device_id=device_id,
            curve_type="qh"
        )

        # 验证结果结构
        assert hasattr(result, "fit_window")
        assert hasattr(result, "test_window")
        assert hasattr(result, "total_days")
        assert hasattr(result, "can_evaluate")


class TestHistoricalDataEvaluator:
    """HistoricalDataEvaluator 历史数据评估器测试"""

    def test_evaluate_data_quality(self):
        """HDE-001: 数据质量评估测试"""
        evaluator = HistoricalDataEvaluator(data_extractor=None)

        # 创建测试数据
        data = pd.DataFrame({
            "pump_flow_rate": [100.0, 150.0, 200.0, None, 250.0],
            "pump_head": [110.0, 100.0, 85.0, 70.0, None],
            "pump_efficiency": [0.75, 0.80, 0.82, 0.78, 0.70]
        })

        result = evaluator.evaluate_data_quality(
            data=data,
            required_columns=["pump_flow_rate", "pump_head", "pump_efficiency"]
        )

        assert result["row_count"] == 5
        assert "completeness" in result
        assert result["completeness"]["pump_flow_rate"] == 0.8  # 4/5
        assert result["completeness"]["pump_head"] == 0.8      # 4/5
        assert result["completeness"]["pump_efficiency"] == 1.0  # 5/5
        assert result["overall_quality_score"] > 0

    def test_evaluate_data_quality_missing_columns(self):
        """HDE-002: 数据质量评估 - 缺失列"""
        evaluator = HistoricalDataEvaluator(data_extractor=None)

        data = pd.DataFrame({
            "pump_flow_rate": [100.0, 150.0, 200.0],
        })

        result = evaluator.evaluate_data_quality(
            data=data,
            required_columns=["pump_flow_rate", "pump_head"]
        )

        assert "pump_head" in result["missing_columns"]

    def test_evaluate_prediction_accuracy_with_data(self):
        """HDE-003: 预测准确性评估测试（使用提供的测试数据）"""
        evaluator = HistoricalDataEvaluator(data_extractor=None)

        # 创建测试数据
        test_data = pd.DataFrame({
            "pump_flow_rate": [100.0, 150.0, 200.0, 250.0, 300.0],
            "pump_head": [115.0, 105.0, 90.0, 70.0, 45.0]  # 真实值
        })

        # 创建预测函数（H = 120 - 0.001*Q²）
        def predict_func(q):
            return 120.0 - 0.001 * q * q

        test_window = TimeWindow(
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31),
            point_count=5
        )

        result = evaluator.evaluate_prediction_accuracy(
            device_id=105,
            curve_type="qh",
            predict_func=predict_func,
            test_window=test_window,
            test_data=test_data
        )

        assert "test_point_count" in result
        assert result["test_point_count"] == 5
        assert "deviation_stats" in result
        assert "pass_rate" in result
        assert "overall_passed" in result

    def test_evaluate_stability(self):
        """HDE-004: 稳定性评估测试"""
        evaluator = HistoricalDataEvaluator(data_extractor=None)

        result = evaluator.evaluate_stability(
            device_id=105,
            curve_type="qh",
            versions=["v1", "v2", "v3"]
        )

        assert "stability_score" in result
        assert "evaluated_versions" in result
        assert result["evaluated_versions"] == 3

    def test_compare_versions(self):
        """HDE-005: 版本对比测试"""
        evaluator = HistoricalDataEvaluator(data_extractor=None)

        result = evaluator.compare_versions(
            device_id=105,
            curve_type="qh",
            version1="v1_20251208",
            version2="v2_20251208"
        )

        assert result["device_id"] == 105
        assert result["curve_type"] == "qh"
        assert result["version1"] == "v1_20251208"
        assert result["version2"] == "v2_20251208"
