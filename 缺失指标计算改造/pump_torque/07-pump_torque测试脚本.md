# pump_torque 测试脚本文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_torque详细设计.md`, `06-pump_torque测试用例.md`

---

## 📋 目录

1. [测试环境配置](#测试环境配置)
2. [测试数据准备](#测试数据准备)
3. [单元测试脚本](#单元测试脚本)
4. [集成测试脚本](#集成测试脚本)
5. [性能测试脚本](#性能测试脚本)
6. [测试执行命令](#测试执行命令)

---

## 测试环境配置

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    -p no:cacheprovider
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    boundary: Boundary tests
    regression: Regression tests
    slow: Slow running tests
```

---

### conftest.py

```python
"""pytest配置和fixtures"""
import pytest
import pandas as pd
from datetime import datetime
from src.database.connection import get_connection

@pytest.fixture(scope="session")
def db_connection():
    """数据库连接fixture"""
    conn = get_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def sample_data():
    """测试数据fixture"""
    return pd.DataFrame({
        'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)] * 3,
        'device_id': [1, 2, 3],
        'pump_active_power': [100.0, 200.0, 300.0],  # kW
        'pump_speed': [1500.0, 1800.0, 2000.0],  # rpm
    })

@pytest.fixture(scope="function")
def sample_data_method_b():
    """method_b测试数据fixture"""
    return pd.DataFrame({
        'ts_bucket': [datetime(2025, 10, 22, 8, 0, 0)] * 3,
        'device_id': [1, 2, 3],
        'pump_flow_rate': [60.0, 120.0, 180.0],  # m³/h
        'pump_head': [100.0, 80.0, 60.0],  # m
        'pump_speed': [1500.0, 1800.0, 2000.0],  # rpm
    })

@pytest.fixture(scope="function")
def sample_calculation_params():
    """计算参数fixture"""
    return {
        'rho': 1000.0,  # kg/m³
        'g': 9.81,  # m/s²
    }

@pytest.fixture(scope="function")
def sample_validation_params():
    """验证参数fixture"""
    return {
        'min_torque': 0.0,  # N·m
        'max_torque': 10000.0,  # N·m
    }
```

---

## 测试数据准备

### 测试数据准备脚本

```python
"""测试数据准备脚本"""
import pandas as pd
from datetime import datetime, timedelta
from src.database.connection import get_connection

def prepare_test_data():
    """准备测试数据"""
    # 时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0)
    end_time = datetime(2025, 10, 23, 7, 19, 37)
    
    # 生成时间序列（1秒间隔）
    time_range = pd.date_range(start=start_time, end=end_time, freq='1S')
    
    # 为每个设备生成测试数据
    test_data = []
    for device_id in [1, 2, 3, 4, 5, 6]:
        for ts in time_range:
            test_data.append({
                'ts_bucket': ts,
                'device_id': device_id,
                'pump_active_power': 100.0 + device_id * 50.0,  # kW
                'pump_speed': 1500.0 + device_id * 100.0,  # rpm
            })
    
    return pd.DataFrame(test_data)

if __name__ == '__main__':
    df = prepare_test_data()
    print(f"生成测试数据: {len(df)}条")
    print(df.head())
```

---

## 单元测试脚本

### 1. DataLoader单元测试

**文件**: `tests/unit/metrics/pump_torque/test_data_loader.py`

```python
"""DataLoader单元测试"""
import pytest
import pandas as pd
from src.metrics.pump_torque.data_loader import DataLoader

class TestDataLoader:
    """DataLoader测试类"""
    
    @pytest.fixture(scope="function")
    def data_loader(self, db_connection):
        """DataLoader fixture"""
        return DataLoader(db_connection)
    
    def test_load_data_success(self, data_loader):
        """测试正常数据加载"""
        df = data_loader.load_data(device_ids=[1, 2, 3])
        
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_active_power', 'pump_speed'}
        assert len(df) > 0
        assert df['pump_active_power'].between(0, 600).all()
        assert df['pump_speed'].between(0, 3000).all()
        assert df['pump_active_power'].notna().all()
        assert df['pump_speed'].notna().all()
    
    def test_load_data_empty(self, data_loader):
        """测试空数据处理"""
        df = data_loader.load_data(device_ids=[999])
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_active_power', 'pump_speed'}
    
    def test_load_data_join_validation(self, data_loader):
        """测试依赖数据JOIN验证"""
        df = data_loader.load_data(device_ids=[1])
        
        assert df['pump_active_power'].notna().all()
        assert df['pump_speed'].notna().all()
        assert df.groupby(['ts_bucket', 'device_id']).size().max() == 1
```

---

### 2. Calculator单元测试

**文件**: `tests/unit/metrics/pump_torque/test_calculator.py`

```python
"""Calculator单元测试"""
import pytest
import pandas as pd
from src.metrics.pump_torque.calculator import CalculatorMethodA, CalculatorMethodB

class TestCalculatorMethodA:
    """CalculatorMethodA测试类"""

    @pytest.fixture(scope="function")
    def calculator_method_a(self):
        """Calculator fixture"""
        return CalculatorMethodA()

    def test_calculate_method_a_correctness(self, calculator_method_a):
        """测试method_a计算正确性"""
        df = pd.DataFrame({
            'pump_active_power': [100.0],  # kW
            'pump_speed': [1500.0],  # rpm
        })
        result_df = calculator_method_a.calculate(df)

        # T = 9549.3 × 100 / 1500 = 636.62 N·m
        assert result_df.loc[0, 'pump_torque'] == pytest.approx(636.62, rel=1e-4)

    def test_calculate_zero_power(self, calculator_method_a):
        """测试零功率处理"""
        df = pd.DataFrame({
            'pump_active_power': [0.0],
            'pump_speed': [1500.0],
        })
        result_df = calculator_method_a.calculate(df)

        assert result_df.loc[0, 'pump_torque'] == pytest.approx(0.0, abs=1e-6)

    def test_calculate_zero_speed(self, calculator_method_a):
        """测试零转速处理"""
        df = pd.DataFrame({
            'pump_active_power': [100.0],
            'pump_speed': [0.0],
        })
        result_df = calculator_method_a.calculate(df)

        assert pd.isna(result_df.loc[0, 'pump_torque']) or result_df.loc[0, 'quality'] == 'invalid'


class TestCalculatorMethodB:
    """CalculatorMethodB测试类"""

    @pytest.fixture(scope="function")
    def calculator_method_b(self, sample_calculation_params):
        """Calculator fixture"""
        return CalculatorMethodB(sample_calculation_params)

    def test_calculate_method_b_correctness(self, calculator_method_b):
        """测试method_b计算正确性"""
        df = pd.DataFrame({
            'pump_flow_rate': [60.0],  # m³/h
            'pump_head': [100.0],  # m
            'pump_speed': [1500.0],  # rpm
        })
        result_df = calculator_method_b.calculate(df)

        # T = 1000 × 9.81 × (60/3600) × 100 / (2π × 1500 / 60) ≈ 104.0 N·m
        assert result_df.loc[0, 'pump_torque'] == pytest.approx(104.0, rel=1e-2)
```

---

### 3. MethodSelector单元测试

**文件**: `tests/unit/metrics/pump_torque/test_method_selector.py`

```python
"""MethodSelector单元测试"""
import pytest
import pandas as pd
from src.metrics.pump_torque.method_selector import MethodSelector

class TestMethodSelector:
    """MethodSelector测试类"""

    @pytest.fixture(scope="function")
    def method_selector(self):
        """MethodSelector fixture"""
        return MethodSelector()

    def test_method_selection_priority_a(self, method_selector):
        """测试method_a优先级"""
        df = pd.DataFrame({
            'pump_active_power': [100.0],
            'pump_speed': [1500.0],
        })
        result_df = method_selector.select_method(df)

        assert result_df.loc[0, 'selected_method'] == 'method_a'

    def test_method_selection_fallback_b(self, method_selector):
        """测试method_b降级"""
        df = pd.DataFrame({
            'pump_flow_rate': [60.0],
            'pump_head': [100.0],
            'pump_speed': [1500.0],
        })
        result_df = method_selector.select_method(df)

        assert result_df.loc[0, 'selected_method'] == 'method_b'

    def test_method_selection_no_method(self, method_selector):
        """测试无可用方法"""
        df = pd.DataFrame({
            'ts_bucket': [pd.Timestamp('2025-10-22 08:00:00')],
            'device_id': [1],
        })
        result_df = method_selector.select_method(df)

        assert result_df.loc[0, 'selected_method'] in [None, 'none']
```

---

### 4. Validator单元测试

**文件**: `tests/unit/metrics/pump_torque/test_validator.py`

```python
"""Validator单元测试"""
import pytest
import pandas as pd
from src.metrics.pump_torque.validator import Validator

class TestValidator:
    """Validator测试类"""

    @pytest.fixture(scope="function")
    def validator(self, sample_validation_params):
        """Validator fixture"""
        return Validator(sample_validation_params)

    def test_validate_range(self, validator):
        """测试范围验证"""
        df = pd.DataFrame({
            'pump_torque': [-100.0, 0.0, 5000.0, 10000.0, 15000.0]
        })
        result_df = validator.validate(df)

        assert result_df.loc[0, 'valid_range'] == False
        assert result_df.loc[1, 'valid_range'] == True
        assert result_df.loc[2, 'valid_range'] == True
        assert result_df.loc[3, 'valid_range'] == True
        assert result_df.loc[4, 'valid_range'] == False
```

---

## 集成测试脚本

### 5. 完整流程集成测试

**文件**: `tests/integration/metrics/pump_torque/test_pump_torque_integration.py`

```python
"""pump_torque集成测试"""
import pytest
import pandas as pd
from src.metrics.pump_torque.pipeline import Pipeline
from src.database.connection import get_connection

class TestPumpTorqueIntegration:
    """pump_torque集成测试类"""

    @pytest.fixture(scope="function")
    def pipeline(self, db_connection):
        """Pipeline fixture"""
        return Pipeline(db_connection)

    def test_single_device_integration(self, pipeline):
        """测试单设备完整流程"""
        result_df = pipeline.run(device_ids=[1])

        assert 'pump_torque' in result_df.columns
        assert len(result_df) > 0
        assert result_df['pump_torque'].between(0, 10000).all()

        # 验证数据库写入
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=20 AND device_id=1"
            )
            count = cur.fetchone()[0]
            assert count > 0

    def test_multiple_devices_integration(self, pipeline):
        """测试多设备完整流程"""
        result_df = pipeline.run(device_ids=[1, 2, 3, 4, 5, 6])

        assert set(result_df['device_id'].unique()) == set([1, 2, 3, 4, 5, 6])
        for device_id in [1, 2, 3, 4, 5, 6]:
            device_data = result_df[result_df['device_id'] == device_id]
            assert len(device_data) > 0

    def test_dependency_data_validation(self, pipeline):
        """测试依赖数据验证"""
        df = pipeline.data_loader.load_data(device_ids=[1])

        assert 'pump_active_power' in df.columns
        assert 'pump_speed' in df.columns
        assert df['pump_active_power'].notna().all()
        assert df['pump_speed'].notna().all()

    def test_pump_speed_dependency(self, pipeline):
        """测试pump_speed依赖验证"""
        # 验证pump_speed数据存在
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=19 AND device_id=1"
            )
            count = cur.fetchone()[0]
            assert count > 0

        # 验证pump_torque计算成功
        result_df = pipeline.run(device_ids=[1])
        assert len(result_df) > 0
```

---

## 性能测试脚本

### 6. 性能测试

**文件**: `tests/performance/metrics/pump_torque/test_pump_torque_performance.py`

```python
"""pump_torque性能测试"""
import pytest
import time
import psutil
from src.metrics.pump_torque.pipeline import Pipeline

class TestPumpTorquePerformance:
    """pump_torque性能测试类"""

    @pytest.fixture(scope="function")
    def pipeline(self, db_connection):
        """Pipeline fixture"""
        return Pipeline(db_connection)

    @pytest.mark.slow
    def test_large_dataset_performance(self, pipeline):
        """测试大数据量性能"""
        start_time = time.time()
        result_df = pipeline.run(device_ids=[1, 2, 3, 4, 5, 6])
        elapsed_time = time.time() - start_time

        assert elapsed_time < 60.0
        throughput = len(result_df) / elapsed_time
        assert throughput > 8000

        print(f"\n性能指标:")
        print(f"  总耗时: {elapsed_time:.2f}秒")
        print(f"  数据量: {len(result_df)}条")
        print(f"  吞吐量: {throughput:.0f}条/秒")

    @pytest.mark.slow
    def test_batch_write_performance(self, pipeline):
        """测试批量写入性能"""
        result_df = pipeline.run(device_ids=[1])

        start_time = time.time()
        pipeline.writer.write(result_df)
        elapsed_time = time.time() - start_time

        write_speed = len(result_df) / elapsed_time
        assert write_speed > 1000

        print(f"\n写入性能:")
        print(f"  写入耗时: {elapsed_time:.2f}秒")
        print(f"  写入速度: {write_speed:.0f}条/秒")

    @pytest.mark.slow
    def test_memory_usage(self, pipeline):
        """测试内存使用"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        result_df = pipeline.run(device_ids=[1, 2, 3, 4, 5, 6])

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        assert memory_increase < 2 * 1024 * 1024 * 1024  # 2GB

        print(f"\n内存使用:")
        print(f"  初始内存: {initial_memory / 1024 / 1024:.2f}MB")
        print(f"  峰值内存: {peak_memory / 1024 / 1024:.2f}MB")
        print(f"  内存增量: {memory_increase / 1024 / 1024:.2f}MB")
```

---

## 测试执行命令

### 运行所有测试

```bash
# 运行所有测试
pytest tests/unit/metrics/pump_torque/ -v

# 运行集成测试
pytest tests/integration/metrics/pump_torque/ -v

# 运行性能测试
pytest tests/performance/metrics/pump_torque/ -v -m slow

# 运行所有测试并生成覆盖率报告
pytest tests/unit/metrics/pump_torque/ --cov=src/metrics/pump_torque --cov-report=html
```

### 运行特定测试

```bash
# 运行DataLoader测试
pytest tests/unit/metrics/pump_torque/test_data_loader.py -v

# 运行Calculator测试
pytest tests/unit/metrics/pump_torque/test_calculator.py -v

# 运行MethodSelector测试
pytest tests/unit/metrics/pump_torque/test_method_selector.py -v

# 运行Validator测试
pytest tests/unit/metrics/pump_torque/test_validator.py -v

# 运行集成测试
pytest tests/integration/metrics/pump_torque/test_pump_torque_integration.py -v

# 运行性能测试
pytest tests/performance/metrics/pump_torque/test_pump_torque_performance.py -v -m slow
```

### 生成测试报告

```bash
# 生成HTML测试报告
pytest tests/unit/metrics/pump_torque/ --html=reports/pump_torque_test_report.html --self-contained-html

# 生成JUnit XML报告
pytest tests/unit/metrics/pump_torque/ --junitxml=reports/pump_torque_junit.xml

# 生成覆盖率报告
pytest tests/unit/metrics/pump_torque/ --cov=src/metrics/pump_torque --cov-report=html:reports/pump_torque_coverage
```

---

## 📊 测试脚本统计

| 测试类型 | 测试文件 | 测试类 | 测试方法数 | 代码行数 |
|----------|---------|--------|-----------|---------|
| 单元测试 | 4个 | 5个 | 11个 | ~200行 |
| 集成测试 | 1个 | 1个 | 4个 | ~80行 |
| 性能测试 | 1个 | 1个 | 3个 | ~60行 |
| **总计** | **6个** | **7个** | **18个** | **~340行** |

---

## ✅ 测试脚本验收标准

**代码质量**：
- [ ] 所有测试脚本符合pytest规范
- [ ] 所有测试方法有清晰的文档字符串
- [ ] 所有测试使用适当的fixtures
- [ ] 所有测试可独立运行

**覆盖率**：
- [ ] 单元测试覆盖所有组件
- [ ] 集成测试覆盖关键流程和pump_speed依赖
- [ ] 性能测试覆盖性能指标

**可执行性**：
- [ ] 所有测试脚本可直接运行
- [ ] 所有测试命令可直接执行
- [ ] 所有测试报告可正常生成

**特殊验证**：
- [ ] pump_speed依赖测试（新实现指标）
- [ ] 两种计算方法测试（method_a, method_b）

---

**文档结束**

