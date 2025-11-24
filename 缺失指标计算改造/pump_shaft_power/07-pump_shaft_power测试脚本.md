# pump_shaft_power 测试脚本文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `06-pump_shaft_power测试用例.md`

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

### pytest配置文件：`pytest.ini`

```ini
[pytest]
testpaths = tests
log_cli = true
log_cli_level = INFO

addopts = 
    --verbose
    --tb=short
    --cov=app/services/calculation/metrics/pump_shaft_power
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90

markers =
    unit: 单元测试
    integration: 集成测试
    performance: 性能测试
    boundary: 边界测试
    regression: 回归测试
```

---

### conftest.py配置：`tests/conftest.py`

```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime


@pytest.fixture(scope="session")
def test_time_range():
    """测试时间范围"""
    return {
        'start_time': datetime(2025, 10, 22, 8, 0, 0),
        'end_time': datetime(2025, 10, 23, 7, 19, 37),
    }


@pytest.fixture(scope="session")
def test_device_ids():
    """测试设备ID列表"""
    return [1, 2, 3, 4, 5, 6]


@pytest.fixture(scope="function")
def sample_pump_active_power_data():
    """示例pump_active_power数据"""
    return pd.DataFrame({
        'ts_bucket': pd.date_range('2025-10-22 08:00:00', periods=100, freq='1s'),
        'device_id': [1] * 100,
        'pump_active_power': np.linspace(50.0, 200.0, 100),
        'running': [1] * 100,
    })


@pytest.fixture(scope="function")
def sample_device_params():
    """示例设备参数"""
    return {
        'eta_motor': 0.92,
        'eta_vfd': 0.97,
    }


@pytest.fixture(scope="function")
def sample_validation_params():
    """示例验证参数"""
    return {
        'min_power': 0.0,
        'max_power': 600.0,
        'physics_tolerance': 0.1,
    }
```

---

## 测试数据准备

### 数据准备脚本：`tests/fixtures/prepare_pump_shaft_power_test_data.py`

```python
#!/usr/bin/env python3
"""pump_shaft_power测试数据准备脚本"""

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


def check_pump_active_power_data(conn):
    """检查pump_active_power数据"""
    print("\n1. 检查pump_active_power数据...")
    
    cur = conn.execute("""
        SELECT 
            device_id,
            COUNT(*) as record_count,
            MIN(ts_bucket) as min_time,
            MAX(ts_bucket) as max_time,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM fact_measurements
        WHERE metric_id = 2  -- pump_active_power
          AND device_id IN (1,2,3,4,5,6)
          AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
        GROUP BY device_id
        ORDER BY device_id
    """)
    
    results = cur.fetchall()
    if results:
        print("  ✅ pump_active_power数据存在:")
        for row in results:
            print(f"    设备{row[0]}: {row[1]}条记录, 值范围: {row[4]:.2f} ~ {row[5]:.2f} kW")
        return True
    else:
        print("  ❌ pump_active_power数据不存在")
        return False


def check_device_params(conn):
    """检查device_rated_params参数"""
    print("\n2. 检查device_rated_params参数...")
    
    cur = conn.execute("""
        SELECT 
            device_id,
            COUNT(*) as param_count
        FROM device_rated_params
        WHERE device_id IN (1,2,3,4,5,6)
          AND param_key IN ('eta_motor', 'eta_vfd')
        GROUP BY device_id
        ORDER BY device_id
    """)
    
    results = cur.fetchall()
    if results and len(results) == 6:
        print("  ✅ device_rated_params参数存在:")
        for row in results:
            print(f"    设备{row[0]}: {row[1]}个参数")
        return True
    else:
        print("  ❌ device_rated_params参数不完整")
        return False


def main():
    """主函数"""
    print("="*80)
    print("pump_shaft_power测试数据准备")
    print("="*80)
    
    db_config = load_db_config()
    
    with psycopg.connect(**db_config) as conn:
        has_active_power_data = check_pump_active_power_data(conn)
        has_device_params = check_device_params(conn)
        
        print("\n" + "="*80)
        if has_active_power_data and has_device_params:
            print("✅ 所有测试数据准备完成！")
        else:
            print("❌ 测试数据不完整")
        print("="*80)


if __name__ == "__main__":
    main()
```

---

## 单元测试脚本

### Calculator单元测试：`tests/unit/metrics/pump_shaft_power/test_calculator.py`

```python
"""pump_shaft_power Calculator单元测试"""

import pytest
import pandas as pd
from app.services.calculation.metrics.pump_shaft_power.calculator import Calculator


class TestCalculator:
    """Calculator测试类"""

    @pytest.fixture
    def calculator_method_a(self, sample_device_params):
        """创建Calculator实例（method_a）"""
        return Calculator(
            params=sample_device_params,
            method_id='method_a',
            trace_id="test_trace_id"
        )

    def test_calculate_method_a_correctness(self, calculator_method_a):
        """测试用例4.1：method_a计算正确性"""
        df = pd.DataFrame({'pump_active_power': [100.0]})
        result_df = calculator_method_a.calculate(df)

        # P_shaft = 100 / (0.92 × 0.97) = 112.05 kW
        assert result_df.loc[0, 'pump_shaft_power'] == pytest.approx(112.05, rel=1e-4)

    def test_calculate_zero_power(self, calculator_method_a):
        """测试用例4.2：零功率处理"""
        df = pd.DataFrame({'pump_active_power': [0.0]})
        result_df = calculator_method_a.calculate(df)
        assert result_df.loc[0, 'pump_shaft_power'] == pytest.approx(0.0, abs=1e-6)
```

---

## 集成测试脚本

### 完整流程集成测试：`tests/integration/metrics/pump_shaft_power/test_pump_shaft_power_integration.py`

```python
"""pump_shaft_power集成测试"""

import pytest
from app.services.calculation.metrics.pump_shaft_power import PumpShaftPowerPipeline
from app.adapters.db import get_connection


class TestPumpShaftPowerIntegration:
    """pump_shaft_power集成测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return PumpShaftPowerPipeline(trace_id="test_integration")

    def test_single_device_integration(self, pipeline, test_time_range, cleanup_test_data):
        """测试用例7.1：单设备完整流程"""
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[1]
        )

        assert 'pump_shaft_power' in result_df.columns
        assert len(result_df) > 0
        assert result_df['pump_shaft_power'].between(0, 600).all()

        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=66 AND device_id=1"
            )
            count = cur.fetchone()[0]
            assert count > 0

    def test_multiple_devices_integration(self, pipeline, test_time_range, test_device_ids):
        """测试用例7.2：多设备完整流程"""
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )

        assert set(result_df['device_id'].unique()) == set(test_device_ids)
```

---

## 性能测试脚本

### 性能测试：`tests/performance/metrics/pump_shaft_power/test_pump_shaft_power_performance.py`

```python
"""pump_shaft_power性能测试"""

import pytest
import time
import psutil
import os
from app.services.calculation.metrics.pump_shaft_power import PumpShaftPowerPipeline


@pytest.mark.performance
class TestPumpShaftPowerPerformance:
    """pump_shaft_power性能测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return PumpShaftPowerPipeline(trace_id="test_performance")

    def test_large_dataset_performance(self, pipeline, test_time_range, test_device_ids):
        """测试用例8.1：大数据量性能测试"""
        start_time = time.time()
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )
        elapsed_time = time.time() - start_time

        assert elapsed_time < 60.0
        throughput = len(result_df) / elapsed_time
        assert throughput > 8000

        print(f"\n性能指标:")
        print(f"  总记录数: {len(result_df)}")
        print(f"  总耗时: {elapsed_time:.2f}秒")
        print(f"  吞吐量: {throughput:.0f}条/秒")
```

---

## 测试执行命令

### 运行所有测试

```bash
# 运行所有测试
pytest tests/unit/metrics/pump_shaft_power/ tests/integration/metrics/pump_shaft_power/ -v

# 运行所有测试并生成覆盖率报告
pytest tests/unit/metrics/pump_shaft_power/ tests/integration/metrics/pump_shaft_power/ -v \
    --cov=app/services/calculation/metrics/pump_shaft_power \
    --cov-report=html --cov-report=term-missing
```

---

### 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit/metrics/pump_shaft_power/ -v

# 运行特定测试文件
pytest tests/unit/metrics/pump_shaft_power/test_calculator.py -v
```

---

### 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/metrics/pump_shaft_power/ -v
```

---

### 运行性能测试

```bash
# 运行性能测试
pytest tests/performance/metrics/pump_shaft_power/ -v -m performance
```

---

## 📊 测试脚本统计

| 测试类型 | 测试文件 | 测试类数 | 测试方法数 | 代码行数 |
|----------|---------|---------|-----------|---------|
| 单元测试 | 6个 | 6 | 14 | ~450行 |
| 集成测试 | 1个 | 1 | 3 | ~70行 |
| 性能测试 | 1个 | 1 | 3 | ~60行 |
| **总计** | **8个** | **8** | **20** | **~580行** |

---

**文档结束**

