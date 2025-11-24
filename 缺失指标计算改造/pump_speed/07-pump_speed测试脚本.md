# pump_speed 测试脚本文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `06-pump_speed测试用例.md`

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
# 测试目录
testpaths = tests

# 日志配置
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# 覆盖率配置
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=app/services/calculation/metrics/pump_speed
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90

# 标记
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
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any
import psycopg
from psycopg.rows import dict_row
import yaml


@pytest.fixture(scope="session")
def db_config():
    """数据库配置"""
    config_path = Path(__file__).parent.parent / "configs" / "database.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


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
def sample_pump_frequency_data():
    """示例pump_frequency数据"""
    return pd.DataFrame({
        'ts_bucket': pd.date_range('2025-10-22 08:00:00', periods=100, freq='1s'),
        'device_id': [1] * 100,
        'pump_frequency': np.linspace(25.0, 50.0, 100),
        'running': [1] * 100,
    })


@pytest.fixture(scope="function")
def sample_device_params():
    """示例设备参数"""
    return {
        'pole_pairs': 2,
        'slip': 0.02,
        'calibration_a': 30.0,
        'calibration_b': 0.0,
    }


@pytest.fixture(scope="function")
def sample_calculation_params():
    """示例计算参数"""
    return {
        'f_ref': 50.0,
        'n_ref': 1500.0,
        'min_speed': 0.0,
        'max_speed': 3000.0,
        'physics_tolerance': 0.1,
        'max_speed_change_rate': 100.0,
    }


@pytest.fixture(scope="function")
def mock_db_connection(db_config):
    """Mock数据库连接"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    conn.execute.return_value = cursor
    return conn


@pytest.fixture(scope="function")
def cleanup_test_data(db_config):
    """清理测试数据"""
    yield
    # 测试后清理
    with psycopg.connect(**db_config) as conn:
        conn.execute(
            "DELETE FROM fact_measurements WHERE metric_id=19 AND ts_bucket >= %s",
            (datetime(2025, 10, 22, 8, 0, 0),)
        )
        conn.commit()
```

---

## 测试数据准备

### 数据准备脚本：`tests/fixtures/prepare_pump_speed_test_data.py`

```python
#!/usr/bin/env python3
"""
pump_speed测试数据准备脚本

功能：
1. 检查pump_frequency数据是否存在
2. 检查device_rated_params参数是否存在
3. 检查calculation_parameters参数是否存在
4. 生成测试数据（如果不存在）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import psycopg
from psycopg.rows import dict_row
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))


def load_db_config():
    """加载数据库配置"""
    config_path = project_root / "configs" / "database.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_pump_frequency_data(conn):
    """检查pump_frequency数据"""
    print("\n1. 检查pump_frequency数据...")
    
    cur = conn.execute("""
        SELECT 
            device_id,
            COUNT(*) as record_count,
            MIN(ts_bucket) as min_time,
            MAX(ts_bucket) as max_time
        FROM fact_measurements
        WHERE metric_id = 1  -- pump_frequency
          AND device_id IN (1,2,3,4,5,6)
          AND ts_bucket BETWEEN '2025-10-22 08:00:00' AND '2025-10-23 07:19:37'
        GROUP BY device_id
        ORDER BY device_id
    """)
    
    results = cur.fetchall()
    if results:
        print("  ✅ pump_frequency数据存在:")
        for row in results:
            print(f"    设备{row[0]}: {row[1]}条记录, {row[2]} ~ {row[3]}")
        return True
    else:
        print("  ❌ pump_frequency数据不存在")
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


def check_calculation_params(conn):
    """检查calculation_parameters参数"""
    print("\n3. 检查calculation_parameters参数...")
    
    cur = conn.execute("""
        SELECT 
            method_id,
            COUNT(*) as param_count
        FROM calculation_parameters
        WHERE metric_key = 'pump_speed'
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
    print("pump_speed测试数据准备")
    print("="*80)
    
    # 加载配置
    db_config = load_db_config()
    
    with psycopg.connect(**db_config) as conn:
        # 检查数据
        has_frequency_data = check_pump_frequency_data(conn)
        has_device_params = check_device_params(conn)
        has_calc_params = check_calculation_params(conn)
        
        # 总结
        print("\n" + "="*80)
        if has_frequency_data and has_device_params and has_calc_params:
            print("✅ 所有测试数据准备完成！")
        else:
            print("❌ 测试数据不完整，请执行以下SQL文件:")
            if not has_device_params:
                print("  - 缺失指标计算改造/database_backups/device_rated_params_backup_20251122.sql")
            if not has_calc_params:
                print("  - 缺失指标计算改造/database_backups/calculation_parameters_backup_20251122.sql")
            if not has_frequency_data:
                print("  - pump_frequency数据需要从原始数据导入")
        print("="*80)


if __name__ == "__main__":
    main()
```

---

## 单元测试脚本

### DataLoader单元测试：`tests/unit/metrics/pump_speed/test_data_loader.py`

```python
"""
pump_speed DataLoader单元测试
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.services.calculation.metrics.pump_speed.data_loader import DataLoader


class TestDataLoader:
    """DataLoader测试类"""

    @pytest.fixture
    def data_loader(self):
        """创建DataLoader实例"""
        return DataLoader(trace_id="test_trace_id")

    def test_load_data_success(self, data_loader, test_time_range, test_device_ids):
        """测试用例1.1：正常数据加载"""
        # 执行
        df = data_loader.load_data(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )

        # 验证
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_frequency'}
        assert len(df) > 0
        assert df['pump_frequency'].between(0, 60).all()
        assert df['pump_frequency'].notna().all()

    def test_load_data_empty(self, data_loader):
        """测试用例1.2：空数据处理"""
        # 执行（不存在的设备）
        df = data_loader.load_data(
            start_time=datetime(2025, 10, 22, 8, 0, 0),
            end_time=datetime(2025, 10, 22, 9, 0, 0),
            device_ids=[999]
        )

        # 验证
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_frequency'}

    def test_load_data_device_type_filter(self, data_loader, test_time_range):
        """测试用例1.3：设备类型过滤"""
        # 执行（不指定device_ids，应该只加载pump设备）
        df = data_loader.load_data(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time']
        )

        # 验证
        assert df['device_id'].isin([1,2,3,4,5,6]).all()
        assert not df['device_id'].isin([7,8]).any()
```

---

### Calculator单元测试：`tests/unit/metrics/pump_speed/test_calculator.py`

```python
"""
pump_speed Calculator单元测试
"""

import pytest
import pandas as pd
import numpy as np

from app.services.calculation.metrics.pump_speed.calculator import Calculator


class TestCalculator:
    """Calculator测试类"""

    @pytest.fixture
    def calculator_method_a(self, sample_calculation_params):
        """创建Calculator实例（method_a）"""
        params = {
            'f_ref': sample_calculation_params['f_ref'],
            'n_ref': sample_calculation_params['n_ref'],
        }
        return Calculator(params=params, method_id='method_a', trace_id="test_trace_id")

    @pytest.fixture
    def calculator_method_b(self, sample_device_params):
        """创建Calculator实例（method_b）"""
        params = {
            'pole_pairs': sample_device_params['pole_pairs'],
            'slip': sample_device_params['slip'],
        }
        return Calculator(params=params, method_id='method_b', trace_id="test_trace_id")

    def test_calculate_method_a_correctness(self, calculator_method_a):
        """测试用例4.1：method_a计算正确性"""
        # 准备数据
        df = pd.DataFrame({
            'pump_frequency': [25.0, 50.0, 60.0]
        })

        # 执行
        result_df = calculator_method_a.calculate(df)

        # 验证
        assert result_df.loc[0, 'pump_speed'] == pytest.approx(750.0, rel=1e-6)
        assert result_df.loc[1, 'pump_speed'] == pytest.approx(1500.0, rel=1e-6)
        assert result_df.loc[2, 'pump_speed'] == pytest.approx(1800.0, rel=1e-6)

    def test_calculate_method_b_correctness(self, calculator_method_b):
        """测试用例4.2：method_b计算正确性"""
        # 准备数据
        df = pd.DataFrame({
            'pump_frequency': [50.0]
        })

        # 执行
        result_df = calculator_method_b.calculate(df)

        # 验证
        # n_sync = 60 * 50 / 2 = 1500 rpm
        # n = 1500 * (1 - 0.02) = 1470 rpm
        assert result_df.loc[0, 'pump_speed'] == pytest.approx(1470.0, rel=1e-6)
```

---

### Validator单元测试：`tests/unit/metrics/pump_speed/test_validator.py`

```python
"""
pump_speed Validator单元测试
"""

import pytest
import pandas as pd
import numpy as np

from app.services.calculation.metrics.pump_speed.validator import Validator


class TestValidator:
    """Validator测试类"""

    @pytest.fixture
    def validator(self, sample_calculation_params):
        """创建Validator实例"""
        params = {
            'min_speed': sample_calculation_params['min_speed'],
            'max_speed': sample_calculation_params['max_speed'],
            'physics_tolerance': sample_calculation_params['physics_tolerance'],
            'max_speed_change_rate': sample_calculation_params['max_speed_change_rate'],
        }
        return Validator(params=params, trace_id="test_trace_id")

    def test_validate_range(self, validator):
        """测试用例5.1：范围验证"""
        # 准备数据
        df = pd.DataFrame({
            'pump_speed': [-100, 0, 1500, 3000, 3500]
        })

        # 执行
        result_df = validator.validate(df)

        # 验证
        assert result_df.loc[0, 'valid_range'] == False
        assert result_df.loc[1, 'valid_range'] == True
        assert result_df.loc[2, 'valid_range'] == True
        assert result_df.loc[3, 'valid_range'] == True
        assert result_df.loc[4, 'valid_range'] == False

    def test_validate_physics(self, validator):
        """测试用例5.2：物理约束验证"""
        # 准备数据
        df = pd.DataFrame({
            'pump_frequency': [50.0, 50.0],
            'pump_speed': [1500.0, 2000.0]
        })

        # 执行
        result_df = validator.validate(df)

        # 验证
        assert result_df.loc[0, 'valid_physics'] == True  # 30×50=1500
        assert result_df.loc[1, 'valid_physics'] == False  # 偏差>10%
```

---

## 集成测试脚本

### 完整流程集成测试：`tests/integration/metrics/pump_speed/test_pump_speed_integration.py`

```python
"""
pump_speed集成测试
"""

import pytest
import pandas as pd
from datetime import datetime
import psycopg

from app.services.calculation.metrics.pump_speed import PumpSpeedPipeline
from app.adapters.db import get_connection


class TestPumpSpeedIntegration:
    """pump_speed集成测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return PumpSpeedPipeline(trace_id="test_integration")

    def test_single_device_integration(self, pipeline, test_time_range, cleanup_test_data):
        """测试用例7.1：单设备完整流程"""
        # 执行
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=[1]
        )

        # 验证结果
        assert 'pump_speed' in result_df.columns
        assert len(result_df) > 0
        assert result_df['pump_speed'].between(0, 3000).all()

        # 验证数据库写入
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=19 AND device_id=1"
            )
            count = cur.fetchone()[0]
            assert count > 0

    def test_multiple_devices_integration(self, pipeline, test_time_range, test_device_ids, cleanup_test_data):
        """测试用例7.2：多设备完整流程"""
        # 执行
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )

        # 验证结果
        assert set(result_df['device_id'].unique()) == set(test_device_ids)
        for device_id in test_device_ids:
            device_data = result_df[result_df['device_id'] == device_id]
            assert len(device_data) > 0
```

---

## 性能测试脚本

### 性能测试：`tests/performance/metrics/pump_speed/test_pump_speed_performance.py`

```python
"""
pump_speed性能测试
"""

import pytest
import time
import psutil
import os

from app.services.calculation.metrics.pump_speed import PumpSpeedPipeline


@pytest.mark.performance
class TestPumpSpeedPerformance:
    """pump_speed性能测试类"""

    @pytest.fixture
    def pipeline(self):
        """创建Pipeline实例"""
        return PumpSpeedPipeline(trace_id="test_performance")

    def test_large_dataset_performance(self, pipeline, test_time_range, test_device_ids):
        """测试用例8.1：大数据量性能测试"""
        # 执行
        start_time = time.time()
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )
        elapsed_time = time.time() - start_time

        # 验证
        assert elapsed_time < 60.0
        throughput = len(result_df) / elapsed_time
        assert throughput > 8000

        print(f"\n性能指标:")
        print(f"  总记录数: {len(result_df)}")
        print(f"  总耗时: {elapsed_time:.2f}秒")
        print(f"  吞吐量: {throughput:.0f}条/秒")

    def test_memory_usage(self, pipeline, test_time_range, test_device_ids):
        """测试用例8.3：内存使用测试"""
        # 记录初始内存
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行
        result_df = pipeline.run(
            start_time=test_time_range['start_time'],
            end_time=test_time_range['end_time'],
            device_ids=test_device_ids
        )

        # 记录峰值内存
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        # 验证
        assert memory_increase < 2 * 1024 * 1024 * 1024  # 2GB

        print(f"\n内存使用:")
        print(f"  初始内存: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"  峰值内存: {peak_memory / 1024 / 1024:.2f} MB")
        print(f"  内存增量: {memory_increase / 1024 / 1024:.2f} MB")
```

---

## 测试执行命令

### 运行所有测试

```bash
# 运行所有测试（单元+集成+性能）
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ tests/performance/metrics/pump_speed/ -v

# 运行所有测试并生成覆盖率报告
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ -v --cov=app/services/calculation/metrics/pump_speed --cov-report=html --cov-report=term-missing
```

---

### 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit/metrics/pump_speed/ -v

# 运行特定测试文件
pytest tests/unit/metrics/pump_speed/test_data_loader.py -v

# 运行特定测试用例
pytest tests/unit/metrics/pump_speed/test_data_loader.py::TestDataLoader::test_load_data_success -v

# 运行单元测试并生成覆盖率报告
pytest tests/unit/metrics/pump_speed/ -v --cov=app/services/calculation/metrics/pump_speed --cov-report=html
```

---

### 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/metrics/pump_speed/ -v

# 运行集成测试（跳过慢速测试）
pytest tests/integration/metrics/pump_speed/ -v -m "not slow"

# 运行集成测试并生成详细日志
pytest tests/integration/metrics/pump_speed/ -v --log-cli-level=DEBUG
```

---

### 运行性能测试

```bash
# 运行性能测试
pytest tests/performance/metrics/pump_speed/ -v -m performance

# 运行性能测试并生成基准报告
pytest tests/performance/metrics/pump_speed/ -v -m performance --benchmark-only

# 运行性能测试并保存结果
pytest tests/performance/metrics/pump_speed/ -v -m performance --benchmark-save=pump_speed_baseline
```

---

### 运行边界测试

```bash
# 运行边界测试
pytest tests/boundary/metrics/pump_speed/ -v

# 运行边界测试并显示详细错误
pytest tests/boundary/metrics/pump_speed/ -v --tb=long
```

---

### 运行回归测试

```bash
# 运行回归测试
pytest tests/regression/metrics/pump_speed/ -v

# 运行回归测试并生成对比报告
pytest tests/regression/metrics/pump_speed/ -v --html=regression_report.html --self-contained-html
```

---

## 测试报告生成

### 生成HTML覆盖率报告

```bash
# 生成HTML覆盖率报告
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ \
    --cov=app/services/calculation/metrics/pump_speed \
    --cov-report=html \
    --cov-report=term-missing

# 打开报告
# Windows: start htmlcov/index.html
# Linux/Mac: open htmlcov/index.html
```

---

### 生成JUnit XML报告（用于CI/CD）

```bash
# 生成JUnit XML报告
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ \
    --junitxml=test-results/pump_speed_junit.xml \
    -v
```

---

### 生成详细测试报告

```bash
# 生成HTML测试报告
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ \
    -v \
    --html=test-results/pump_speed_report.html \
    --self-contained-html

# 生成JSON测试报告
pytest tests/unit/metrics/pump_speed/ tests/integration/metrics/pump_speed/ \
    -v \
    --json-report \
    --json-report-file=test-results/pump_speed_report.json
```

---

### 生成性能基准报告

```bash
# 生成性能基准报告
pytest tests/performance/metrics/pump_speed/ \
    -v \
    -m performance \
    --benchmark-only \
    --benchmark-save=pump_speed_baseline \
    --benchmark-autosave

# 对比性能基准
pytest tests/performance/metrics/pump_speed/ \
    -v \
    -m performance \
    --benchmark-only \
    --benchmark-compare=pump_speed_baseline
```

---

## 📊 测试脚本统计

| 测试类型 | 测试文件 | 测试类数 | 测试方法数 | 代码行数 |
|----------|---------|---------|-----------|---------|
| 单元测试 | 6个 | 6 | 18 | ~600行 |
| 集成测试 | 1个 | 1 | 4 | ~100行 |
| 性能测试 | 1个 | 1 | 3 | ~80行 |
| 边界测试 | 1个 | 1 | 3 | ~60行 |
| 回归测试 | 1个 | 1 | 1 | ~40行 |
| **总计** | **10个** | **10** | **29** | **~880行** |

---

## ✅ 测试脚本验收标准

**代码质量**：
- [ ] 所有测试脚本符合PEP 8规范
- [ ] 所有测试脚本有完整的文档字符串
- [ ] 所有测试脚本有清晰的断言消息

**测试覆盖**：
- [ ] 单元测试覆盖率 > 95%
- [ ] 集成测试覆盖关键流程
- [ ] 性能测试覆盖性能指标
- [ ] 边界测试覆盖边界条件

**测试执行**：
- [ ] 所有测试可以独立运行
- [ ] 所有测试可以并行运行
- [ ] 所有测试有清理机制
- [ ] 所有测试有超时控制

**测试报告**：
- [ ] 可以生成HTML覆盖率报告
- [ ] 可以生成JUnit XML报告
- [ ] 可以生成性能基准报告
- [ ] 可以生成详细测试报告

---

**文档结束**

