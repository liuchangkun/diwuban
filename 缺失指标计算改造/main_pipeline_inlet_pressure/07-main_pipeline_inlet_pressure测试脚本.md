# main_pipeline_inlet_pressure 测试脚本文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `06-main_pipeline_inlet_pressure测试用例.md`

---

## 📋 目录

1. [测试环境配置](#测试环境配置)
2. [测试数据准备](#测试数据准备)
3. [单元测试脚本](#单元测试脚本)
4. [集成测试脚本](#集成测试脚本)
5. [性能测试脚本](#性能测试脚本)
6. [测试执行命令](#测试执行命令)
7. [测试报告生成](#测试报告生成)

---

## 测试环境配置

### pytest配置文件：`pytest.ini`

```ini
[pytest]
testpaths = tests

log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=app/services/calculation/metrics/main_pipeline_inlet_pressure
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90

markers =
    unit: 单元测试
    integration: 集成测试
    performance: 性能测试
    boundary: 边界测试
    regression: 回归测试
    slow: 慢速测试
```

---

### conftest.py配置：`tests/conftest.py`

```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock
import psycopg
import yaml


@pytest.fixture(scope="session")
def test_time_range():
    """测试时间范围"""
    return {
        'start_time': datetime(2025, 10, 22, 8, 0, 0),
        'end_time': datetime(2025, 10, 23, 7, 19, 37),
    }


@pytest.fixture(scope="session")
def test_device_id():
    """测试设备ID（总管）"""
    return 7


@pytest.fixture(scope="session")
def pool_device_id():
    """水池设备ID"""
    return 8


@pytest.fixture(scope="function")
def sample_pool_liquid_level_data():
    """示例pool_liquid_level数据"""
    return pd.DataFrame({
        'ts_bucket': pd.date_range('2025-10-22 08:00:00', periods=100, freq='1s'),
        'device_id': [8] * 100,
        'pool_liquid_level': np.linspace(4.0, 6.0, 100),
        'running': [1] * 100,
    })


@pytest.fixture(scope="function")
def sample_calculation_params_method_b():
    """示例method_b计算参数"""
    return {
        'P_atm': 0.101325,
        'rho': 1000.0,
        'g': 9.81,
    }


@pytest.fixture(scope="function")
def sample_calculation_params_pin_coef_v1():
    """示例PIN_COEF_V1计算参数"""
    return {
        'b0': 0.101325,
        'b1': 0.00981,
        'b2': 0.0,
        'b3': 0.0,
    }


@pytest.fixture(scope="function")
def sample_validation_params():
    """示例验证参数"""
    return {
        'min_pressure': 0.0,
        'max_pressure': 1.0,
        'physics_tolerance': 0.1,
        'max_pressure_change_rate': 0.1,
    }


@pytest.fixture(scope="function")
def cleanup_test_data(db_config):
    """清理测试数据"""
    yield
    # 测试后清理
    with psycopg.connect(**db_config) as conn:
        conn.execute(
            "DELETE FROM fact_measurements WHERE metric_id=61 AND ts_bucket >= %s",
            (datetime(2025, 10, 22, 8, 0, 0),)
        )
        conn.commit()
```

---

## 测试数据准备

### 数据准备脚本：`tests/fixtures/prepare_main_pipeline_inlet_pressure_test_data.py`

```python
#!/usr/bin/env python3
"""
main_pipeline_inlet_pressure测试数据准备脚本
"""

import sys
from pathlib import Path
from datetime import datetime
import psycopg
import yaml

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))


def load_db_config():
    """加载数据库配置"""
    config_path = project_root / "configs" / "database.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_pool_liquid_level_data(conn):
    """检查pool_liquid_level数据"""
    print("\n1. 检查pool_liquid_level数据...")
    
    cur = conn.execute("""
        SELECT 
            device_id,
            COUNT(*) as record_count,
            MIN(ts_bucket) as min_time,
            MAX(ts_bucket) as max_time,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM fact_measurements
        WHERE metric_id = 5  -- pool_liquid_level
          AND device_id = 8
          AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
        GROUP BY device_id
    """)
    
    results = cur.fetchall()
    if results:
        print("  ✅ pool_liquid_level数据存在:")
        for row in results:
            print(f"    设备{row[0]}: {row[1]}条记录, {row[2]} ~ {row[3]}, 值范围: {row[4]:.2f} ~ {row[5]:.2f} m")
        return True
    else:
        print("  ❌ pool_liquid_level数据不存在")
        return False


def check_calculation_params(conn):
    """检查calculation_parameters参数"""
    print("\n2. 检查calculation_parameters参数...")
    
    cur = conn.execute("""
        SELECT 
            method_id,
            COUNT(*) as param_count
        FROM calculation_parameters
        WHERE metric_key = 'main_pipeline_inlet_pressure'
        GROUP BY method_id
        ORDER BY method_id
    """)
    
    results = cur.fetchall()
    if results:
        print("  ✅ calculation_parameters参数存在:")
        for row in results:
            print(f"    {row[0]}: {row[1]}个参数")
        return True
    else:
        print("  ❌ calculation_parameters参数不存在")
        return False


def main():
    """主函数"""
    print("="*80)
    print("main_pipeline_inlet_pressure测试数据准备")
    print("="*80)
    
    db_config = load_db_config()
    
    with psycopg.connect(**db_config) as conn:
        has_pool_data = check_pool_liquid_level_data(conn)
        has_calc_params = check_calculation_params(conn)
        
        print("\n" + "="*80)
        if has_pool_data and has_calc_params:
            print("✅ 所有测试数据准备完成！")
        else:
            print("❌ 测试数据不完整，请执行SQL文件:")
            if not has_calc_params:
                print("  - 缺失指标计算改造/database_backups/calculation_parameters_backup_20251122.sql")
            if not has_pool_data:
                print("  - pool_liquid_level数据需要从原始数据导入")
        print("="*80)


if __name__ == "__main__":
    main()
```

---

## 单元测试脚本

### DataLoader单元测试：`tests/unit/metrics/main_pipeline_inlet_pressure/test_data_loader.py`

```python
"""main_pipeline_inlet_pressure DataLoader单元测试"""

import pytest
import pandas as pd
from datetime import datetime

from app.services.calculation.metrics.main_pipeline_inlet_pressure.data_loader import DataLoader


class TestDataLoader:
    """DataLoader测试类"""

    @pytest.fixture
    def data_loader(self):
        """创建DataLoader实例"""
        return DataLoader(trace_id="test_trace_id")

    def test_load_data_success(self, data_loader, test_time_range, pool_device_id):
        """测试用例1.1：正常数据加载"""
        df = data_loader.load_data(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[pool_device_id]
        )

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pool_liquid_level'}
        assert len(df) > 0
        assert df['pool_liquid_level'].between(0, 10).all()
        assert df['pool_liquid_level'].notna().all()

    def test_load_data_empty(self, data_loader):
        """测试用例1.2：空数据处理"""
        df = data_loader.load_data(
            start_time=datetime(2025, 10, 22, 8, 0, 0),
            end_time=datetime(2025, 10, 22, 9, 0, 0),
            device_ids=[999]
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pool_liquid_level'}

    def test_load_data_device_filter(self, data_loader, test_time_range):
        """测试用例1.3：设备类型过滤"""
        df = data_loader.load_data(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        assert df['device_id'].unique() == [8]
```

---

### Calculator单元测试：`tests/unit/metrics/main_pipeline_inlet_pressure/test_calculator.py`

```python
"""main_pipeline_inlet_pressure Calculator单元测试"""

import pytest
import pandas as pd

from app.services.calculation.metrics.main_pipeline_inlet_pressure.calculator import Calculator


class TestCalculator:
    """Calculator测试类"""

    @pytest.fixture
    def calculator_method_b(self, sample_calculation_params_method_b):
        """创建Calculator实例（method_b）"""
        return Calculator(
            params=sample_calculation_params_method_b,
            method_id='method_b',
            trace_id="test_trace_id"
        )

    @pytest.fixture
    def calculator_pin_coef_v1(self, sample_calculation_params_pin_coef_v1):
        """创建Calculator实例（PIN_COEF_V1）"""
        return Calculator(
            params=sample_calculation_params_pin_coef_v1,
            method_id='PIN_COEF_V1',
            trace_id="test_trace_id"
        )

    def test_calculate_method_b_correctness(self, calculator_method_b):
        """测试用例4.1：method_b计算正确性"""
        df = pd.DataFrame({
            'pool_liquid_level': [5.0]
        })

        result_df = calculator_method_b.calculate(df)

        # P_in = 0.101325 + 1000 × 9.81 × 5.0 / 1e6 = 0.150375 MPa
        assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(0.150375, rel=1e-6)

    def test_calculate_pin_coef_v1_correctness(self, calculator_pin_coef_v1):
        """测试用例4.2：PIN_COEF_V1计算正确性"""
        df = pd.DataFrame({
            'pool_liquid_level': [5.0]
        })

        result_df = calculator_pin_coef_v1.calculate(df)

        # P_in = 0.101325 + 0.00981×5.0 = 0.150375 MPa
        expected = 0.101325 + 0.00981 * 5.0
        assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(expected, rel=1e-6)

    def test_calculate_zero_level(self, calculator_method_b):
        """测试用例4.3：零液位处理"""
        df = pd.DataFrame({
            'pool_liquid_level': [0.0]
        })

        result_df = calculator_method_b.calculate(df)

        # P_in = P_atm = 0.101325 MPa
        assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(0.101325, rel=1e-6)
```

---

### Validator单元测试：`tests/unit/metrics/main_pipeline_inlet_pressure/test_validator.py`

```python
"""main_pipeline_inlet_pressure Validator单元测试"""

import pytest
import pandas as pd

from app.services.calculation.metrics.main_pipeline_inlet_pressure.validator import Validator


class TestValidator:
    """Validator测试类"""

    @pytest.fixture
    def validator(self, sample_validation_params):
        """创建Validator实例"""
        return Validator(params=sample_validation_params, trace_id="test_trace_id")

    def test_validate_range(self, validator):
        """测试用例5.1：范围验证"""
        df = pd.DataFrame({
            'main_pipeline_inlet_pressure': [-0.1, 0.0, 0.5, 1.0, 1.5]
        })

        result_df = validator.validate(df)

        assert result_df.loc[0, 'valid_range'] == False
        assert result_df.loc[1, 'valid_range'] == True
        assert result_df.loc[2, 'valid_range'] == True
        assert result_df.loc[3, 'valid_range'] == True
        assert result_df.loc[4, 'valid_range'] == False

    def test_validate_physics(self, validator):
        """测试用例5.2：物理约束验证"""
        df = pd.DataFrame({
            'pool_liquid_level': [5.0, 5.0],
            'main_pipeline_inlet_pressure': [0.150375, 0.200000]
        })

        result_df = validator.validate(df)

        assert result_df.loc[0, 'valid_physics'] == True
        assert result_df.loc[1, 'valid_physics'] == False
```

---

## 集成测试脚本

### 完整流程集成测试：`tests/integration/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_integration.py`

```python
"""main_pipeline_inlet_pressure集成测试"""

import pytest
import pandas as pd
from datetime import datetime
import psycopg

from app.services.calculation.metrics.main_pipeline_inlet_pressure import MainPipelineInletPressurePipeline
from app.adapters.db import get_connection


class TestMainPipelineInletPressureIntegration:
    """main_pipeline_inlet_pressure集成测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return MainPipelineInletPressurePipeline(trace_id="test_integration")

    def test_single_device_integration(self, pipeline, test_time_range, test_device_id, cleanup_test_data):
        """测试用例7.1：单设备完整流程"""
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[test_device_id]
        )

        assert 'main_pipeline_inlet_pressure' in result_df.columns
        assert len(result_df) > 0
        assert result_df['main_pipeline_inlet_pressure'].between(0, 1).all()

        # 验证数据库写入
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=61 AND device_id=7"
            )
            count = cur.fetchone()[0]
            assert count > 0

    def test_cross_device_dependency(self, pipeline, test_time_range, test_device_id):
        """测试用例7.4：跨设备数据依赖"""
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[test_device_id]
        )

        assert len(result_df) > 0
```

---

## 性能测试脚本

### 性能测试：`tests/performance/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_performance.py`

```python
"""main_pipeline_inlet_pressure性能测试"""

import pytest
import time
import psutil
import os

from app.services.calculation.metrics.main_pipeline_inlet_pressure import MainPipelineInletPressurePipeline


@pytest.mark.performance
class TestMainPipelineInletPressurePerformance:
    """main_pipeline_inlet_pressure性能测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return MainPipelineInletPressurePipeline(trace_id="test_performance")

    def test_large_dataset_performance(self, pipeline, test_time_range, test_device_id):
        """测试用例8.1：大数据量性能测试"""
        start_time = time.time()
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[test_device_id]
        )
        elapsed_time = time.time() - start_time

        assert elapsed_time < 30.0
        throughput = len(result_df) / elapsed_time
        assert throughput > 2000

        print(f"\n性能指标:")
        print(f"  总记录数: {len(result_df)}")
        print(f"  总耗时: {elapsed_time:.2f}秒")
        print(f"  吞吐量: {throughput:.0f}条/秒")

    def test_memory_usage(self, pipeline, test_time_range, test_device_id):
        """测试用例8.3：内存使用测试"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[test_device_id]
        )

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        assert memory_increase < 1 * 1024 * 1024 * 1024  # 1GB

        print(f"\n内存使用:")
        print(f"  初始内存: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"  峰值内存: {peak_memory / 1024 / 1024:.2f} MB")
        print(f"  内存增量: {memory_increase / 1024 / 1024:.2f} MB")
```

---

## 测试执行命令

### 运行所有测试

```bash
# 运行所有测试
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ tests/integration/metrics/main_pipeline_inlet_pressure/ tests/performance/metrics/main_pipeline_inlet_pressure/ -v

# 运行所有测试并生成覆盖率报告
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ tests/integration/metrics/main_pipeline_inlet_pressure/ -v --cov=app/services/calculation/metrics/main_pipeline_inlet_pressure --cov-report=html --cov-report=term-missing
```

---

### 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ -v

# 运行特定测试文件
pytest tests/unit/metrics/main_pipeline_inlet_pressure/test_data_loader.py -v

# 运行特定测试用例
pytest tests/unit/metrics/main_pipeline_inlet_pressure/test_data_loader.py::TestDataLoader::test_load_data_success -v
```

---

### 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/metrics/main_pipeline_inlet_pressure/ -v

# 运行集成测试并生成详细日志
pytest tests/integration/metrics/main_pipeline_inlet_pressure/ -v --log-cli-level=DEBUG
```

---

### 运行性能测试

```bash
# 运行性能测试
pytest tests/performance/metrics/main_pipeline_inlet_pressure/ -v -m performance
```

---

## 测试报告生成

### 生成HTML覆盖率报告

```bash
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ tests/integration/metrics/main_pipeline_inlet_pressure/ \
    --cov=app/services/calculation/metrics/main_pipeline_inlet_pressure \
    --cov-report=html \
    --cov-report=term-missing
```

---

### 生成JUnit XML报告

```bash
pytest tests/unit/metrics/main_pipeline_inlet_pressure/ tests/integration/metrics/main_pipeline_inlet_pressure/ \
    --junitxml=test-results/main_pipeline_inlet_pressure_junit.xml \
    -v
```

---

## 📊 测试脚本统计

| 测试类型 | 测试文件 | 测试类数 | 测试方法数 | 代码行数 |
|----------|---------|---------|-----------|---------|
| 单元测试 | 6个 | 6 | 16 | ~500行 |
| 集成测试 | 1个 | 1 | 4 | ~80行 |
| 性能测试 | 1个 | 1 | 3 | ~70行 |
| 边界测试 | 1个 | 1 | 3 | ~50行 |
| 回归测试 | 1个 | 1 | 1 | ~30行 |
| **总计** | **10个** | **10** | **27** | **~730行** |

---

**文档结束**

