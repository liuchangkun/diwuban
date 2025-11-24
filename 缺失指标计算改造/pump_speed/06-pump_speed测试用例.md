# pump_speed 测试用例文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_speed详细设计.md`

---

## 📋 目录

1. [测试概述](#测试概述)
2. [单元测试用例](#单元测试用例)
3. [集成测试用例](#集成测试用例)
4. [性能测试用例](#性能测试用例)
5. [边界测试用例](#边界测试用例)
6. [回归测试用例](#回归测试用例)

---

## 测试概述

### 测试目标

验证pump_speed指标计算的正确性、稳定性和性能。

### 测试范围

- **单元测试**：各组件独立功能测试（DataLoader, DataFilter, MethodSelector, Calculator, Validator, Pipeline）
- **集成测试**：完整流程测试（数据加载→计算→验证→写入）
- **性能测试**：大数据量下的性能测试
- **边界测试**：边界条件和异常情况测试
- **回归测试**：与现有系统对比测试

### 测试环境

- **Python版本**：3.11+
- **测试框架**：pytest 7.4+
- **数据库**：PostgreSQL 15 + TimescaleDB 2.11
- **测试数据**：设备1-6，时间范围2025-10-22 08:00:00 到 2025-10-23 07:19:37

### 测试数据准备

**依赖数据**：
- `pump_frequency`（metric_id=1）：设备1-6的频率数据
- `mv_device_running_1s`：设备运行状态数据

**参数数据**：
- `device_rated_params`：设备1-6的额定参数（pole_pairs, slip等）
- `calculation_parameters`：pump_speed的计算参数（method_a, method_b, method_c, validation）

---

## 单元测试用例

### 测试文件：`tests/unit/metrics/pump_speed/test_data_loader.py`

#### 测试用例1.1：正常数据加载

**测试ID**：`test_load_data_success`  
**测试目的**：验证DataLoader能正确加载pump_frequency数据  
**前置条件**：
- 数据库中存在pump_frequency数据（metric_id=1）
- 设备1-6有数据

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data(start_time, end_time, device_ids=[1,2,3,4,5,6])
3. 验证返回DataFrame

**预期结果**：
- 返回DataFrame包含列：ts_bucket, device_id, pump_frequency
- 数据行数 > 0
- pump_frequency值在合理范围（0-60 Hz）
- 无空值

**断言**：
```python
assert isinstance(df, pd.DataFrame)
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_frequency'}
assert len(df) > 0
assert df['pump_frequency'].between(0, 60).all()
assert df['pump_frequency'].notna().all()
```

---

#### 测试用例1.2：空数据处理

**测试ID**：`test_load_data_empty`  
**测试目的**：验证DataLoader能正确处理无数据情况  
**前置条件**：
- 查询时间范围内无数据

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data(start_time, end_time, device_ids=[999])（不存在的设备）
3. 验证返回空DataFrame

**预期结果**：
- 返回空DataFrame
- 列结构正确

**断言**：
```python
assert isinstance(df, pd.DataFrame)
assert len(df) == 0
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_frequency'}
```

---

#### 测试用例1.3：设备类型过滤

**测试ID**：`test_load_data_device_type_filter`  
**测试目的**：验证DataLoader只加载type='pump'的设备  
**前置条件**：
- 数据库中有pump和non-pump设备

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data()（不指定device_ids）
3. 验证返回的device_id都是pump类型

**预期结果**：
- 返回的device_id只包含1-6（pump设备）
- 不包含设备7-8（非pump设备）

**断言**：
```python
assert df['device_id'].isin([1,2,3,4,5,6]).all()
assert not df['device_id'].isin([7,8]).any()
```

---

### 测试文件：`tests/unit/metrics/pump_speed/test_data_filter.py`

#### 测试用例2.1：运行状态过滤

**测试ID**：`test_filter_by_running_state`  
**测试目的**：验证DataFilter能正确过滤running=1的数据  
**前置条件**：
- 测试数据包含running=0和running=1的记录

**测试步骤**：
1. 创建测试DataFrame（包含running=0和running=1）
2. 创建DataFilter实例
3. 调用filter_data(df)
4. 验证返回DataFrame

**预期结果**：
- 返回DataFrame只包含running=1的记录
- 数据行数 < 原始数据行数

**断言**：
```python
assert (filtered_df['running'] == 1).all()
assert len(filtered_df) < len(original_df)
```

---

#### 测试用例2.2：空数据过滤

**测试ID**：`test_filter_empty_data`  
**测试目的**：验证DataFilter能正确处理空DataFrame  
**前置条件**：无

**测试步骤**：
1. 创建空DataFrame
2. 创建DataFilter实例
3. 调用filter_data(df)
4. 验证返回空DataFrame

**预期结果**：
- 返回空DataFrame
- 不抛出异常

**断言**：
```python
assert isinstance(filtered_df, pd.DataFrame)
assert len(filtered_df) == 0
```

---

### 测试文件：`tests/unit/metrics/pump_speed/test_method_selector.py`

#### 测试用例3.1：method_a选择

**测试ID**：`test_select_method_a`  
**测试目的**：验证MethodSelector能正确选择method_a  
**前置条件**：
- 有pump_frequency数据
- 无设备特定参数

**测试步骤**：
1. 创建测试DataFrame（包含pump_frequency）
2. 创建MethodSelector实例（无device_params）
3. 调用select_method(df, device_id=1)
4. 验证返回method_id

**预期结果**：
- 返回method_id='method_a'
- 日志输出选择原因

**断言**：
```python
assert method_id == 'method_a'
assert 'method_a' in caplog.text
```

---

#### 测试用例3.2：method_b选择

**测试ID**：`test_select_method_b`
**测试目的**：验证MethodSelector能正确选择method_b
**前置条件**：
- 有pump_frequency数据
- 有设备参数（pole_pairs, slip）

**测试步骤**：
1. 创建测试DataFrame（包含pump_frequency）
2. 创建MethodSelector实例（包含device_params={'pole_pairs': 2, 'slip': 0.02}）
3. 调用select_method(df, device_id=1)
4. 验证返回method_id

**预期结果**：
- 返回method_id='method_b'
- 优先级高于method_a

**断言**：
```python
assert method_id == 'method_b'
assert 'method_b' in caplog.text
assert 'pole_pairs' in caplog.text
```

---

#### 测试用例3.3：method_c选择

**测试ID**：`test_select_method_c`
**测试目的**：验证MethodSelector能正确选择method_c
**前置条件**：
- 有pump_frequency数据
- 有校准参数（calibration_a, calibration_b）

**测试步骤**：
1. 创建测试DataFrame（包含pump_frequency）
2. 创建MethodSelector实例（包含device_params={'calibration_a': 30.0, 'calibration_b': 0.0}）
3. 调用select_method(df, device_id=1)
4. 验证返回method_id

**预期结果**：
- 返回method_id='method_c'
- 优先级高于method_a和method_b

**断言**：
```python
assert method_id == 'method_c'
assert 'method_c' in caplog.text
assert 'calibration' in caplog.text
```

---

### 测试文件：`tests/unit/metrics/pump_speed/test_calculator.py`

#### 测试用例4.1：method_a计算正确性

**测试ID**：`test_calculate_method_a_correctness`
**测试目的**：验证method_a计算公式正确
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[25.0, 50.0, 60.0]）
2. 创建Calculator实例（params={'f_ref': 50.0, 'n_ref': 1500.0}）
3. 调用_method_a(df)
4. 验证计算结果

**预期结果**：
- pump_frequency=25.0 → pump_speed=750.0 rpm
- pump_frequency=50.0 → pump_speed=1500.0 rpm
- pump_frequency=60.0 → pump_speed=1800.0 rpm

**断言**：
```python
assert df.loc[0, 'pump_speed'] == pytest.approx(750.0, rel=1e-6)
assert df.loc[1, 'pump_speed'] == pytest.approx(1500.0, rel=1e-6)
assert df.loc[2, 'pump_speed'] == pytest.approx(1800.0, rel=1e-6)
```

---

#### 测试用例4.2：method_b计算正确性

**测试ID**：`test_calculate_method_b_correctness`
**测试目的**：验证method_b计算公式正确
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[50.0]）
2. 创建Calculator实例（params={'pole_pairs': 2, 'slip': 0.02}）
3. 调用_method_b(df)
4. 验证计算结果

**预期结果**：
- pump_frequency=50.0, pole_pairs=2, slip=0.02 → pump_speed=1470.0 rpm

**断言**：
```python
# n_sync = 60 * 50 / 2 = 1500 rpm
# n = 1500 * (1 - 0.02) = 1470 rpm
assert df.loc[0, 'pump_speed'] == pytest.approx(1470.0, rel=1e-6)
```

---

#### 测试用例4.3：method_c计算正确性

**测试ID**：`test_calculate_method_c_correctness`
**测试目的**：验证method_c计算公式正确
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[50.0]）
2. 创建Calculator实例（params={'calibration_a': 30.0, 'calibration_b': 0.0}）
3. 调用_method_c(df)
4. 验证计算结果

**预期结果**：
- pump_frequency=50.0, a=30.0, b=0.0 → pump_speed=1500.0 rpm

**断言**：
```python
# n = 30.0 * 50.0 + 0.0 = 1500.0 rpm
assert df.loc[0, 'pump_speed'] == pytest.approx(1500.0, rel=1e-6)
```

---

### 测试文件：`tests/unit/metrics/pump_speed/test_validator.py`

#### 测试用例5.1：范围验证

**测试ID**：`test_validate_range`
**测试目的**：验证Validator能正确检查转速范围
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_speed=[-100, 0, 1500, 3000, 3500]）
2. 创建Validator实例（params={'min_speed': 0, 'max_speed': 3000}）
3. 调用validate(df)
4. 验证valid_range列

**预期结果**：
- pump_speed=-100 → valid_range=False
- pump_speed=0 → valid_range=True
- pump_speed=1500 → valid_range=True
- pump_speed=3000 → valid_range=True
- pump_speed=3500 → valid_range=False

**断言**：
```python
assert df.loc[0, 'valid_range'] == False
assert df.loc[1, 'valid_range'] == True
assert df.loc[2, 'valid_range'] == True
assert df.loc[3, 'valid_range'] == True
assert df.loc[4, 'valid_range'] == False
```

---

#### 测试用例5.2：物理约束验证

**测试ID**：`test_validate_physics`
**测试目的**：验证Validator能正确检查物理约束（n ≈ 30×f）
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[50.0, 50.0], pump_speed=[1500.0, 2000.0]）
2. 创建Validator实例（params={'physics_tolerance': 0.1}）
3. 调用validate(df)
4. 验证valid_physics列

**预期结果**：
- pump_frequency=50.0, pump_speed=1500.0 → valid_physics=True（30×50=1500）
- pump_frequency=50.0, pump_speed=2000.0 → valid_physics=False（偏差>10%）

**断言**：
```python
assert df.loc[0, 'valid_physics'] == True
assert df.loc[1, 'valid_physics'] == False
```

---

#### 测试用例5.3：异常值检测

**测试ID**：`test_validate_outlier`
**测试目的**：验证Validator能正确检测异常值
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_speed=[1500, 1510, 1520, 2000]，时间间隔1秒）
2. 创建Validator实例（params={'max_speed_change_rate': 100}）
3. 调用validate(df)
4. 验证valid_outlier列

**预期结果**：
- 前3个值变化率<100 rpm/s → valid_outlier=True
- 第4个值变化率=480 rpm/s → valid_outlier=False

**断言**：
```python
assert df.loc[0, 'valid_outlier'] == True
assert df.loc[1, 'valid_outlier'] == True
assert df.loc[2, 'valid_outlier'] == True
assert df.loc[3, 'valid_outlier'] == False
```

---

### 测试文件：`tests/unit/metrics/pump_speed/test_pipeline.py`

#### 测试用例6.1：完整流程测试

**测试ID**：`test_pipeline_end_to_end`
**测试目的**：验证Pipeline能正确执行完整流程
**前置条件**：
- Mock所有依赖组件

**测试步骤**：
1. 创建Pipeline实例（使用Mock组件）
2. 调用run(start_time, end_time, device_ids=[1])
3. 验证各组件调用顺序

**预期结果**：
- DataLoader.load_data()被调用1次
- DataFilter.filter_data()被调用1次
- MethodSelector.select_method()被调用1次
- Calculator.calculate()被调用1次
- Validator.validate()被调用1次
- 返回DataFrame包含pump_speed和quality列

**断言**：
```python
assert mock_loader.load_data.call_count == 1
assert mock_filter.filter_data.call_count == 1
assert mock_selector.select_method.call_count == 1
assert mock_calculator.calculate.call_count == 1
assert mock_validator.validate.call_count == 1
assert 'pump_speed' in result_df.columns
assert 'quality' in result_df.columns
```

---

## 集成测试用例

### 测试文件：`tests/integration/metrics/pump_speed/test_pump_speed_integration.py`

#### 测试用例7.1：单设备完整流程

**测试ID**：`test_single_device_integration`
**测试目的**：验证单设备完整计算流程
**前置条件**：
- 数据库中有设备1的pump_frequency数据
- 数据库中有设备1的参数配置

**测试步骤**：
1. 创建PumpSpeedPipeline实例（真实组件）
2. 调用run(start_time, end_time, device_ids=[1])
3. 验证返回结果
4. 查询数据库验证写入

**预期结果**：
- 返回DataFrame包含pump_speed列
- 数据行数 > 0
- 数据库中写入成功（metric_id=19）

**断言**：
```python
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
```

---

#### 测试用例7.2：多设备完整流程

**测试ID**：`test_multiple_devices_integration`
**测试目的**：验证多设备完整计算流程
**前置条件**：
- 数据库中有设备1-6的pump_frequency数据

**测试步骤**：
1. 创建PumpSpeedPipeline实例
2. 调用run(start_time, end_time, device_ids=[1,2,3,4,5,6])
3. 验证返回结果
4. 查询数据库验证写入

**预期结果**：
- 返回DataFrame包含6个设备的数据
- 每个设备数据行数 > 0
- 数据库中写入成功

**断言**：
```python
assert set(result_df['device_id'].unique()) == {1,2,3,4,5,6}
for device_id in [1,2,3,4,5,6]:
    device_data = result_df[result_df['device_id'] == device_id]
    assert len(device_data) > 0
```

---

#### 测试用例7.3：参数加载集成

**测试ID**：`test_parameter_loading_integration`
**测试目的**：验证参数从数据库正确加载
**前置条件**：
- calculation_parameters表中有pump_speed参数

**测试步骤**：
1. 创建ParameterManager实例
2. 调用get_parameters('pump_speed', 'method_a')
3. 验证返回参数

**预期结果**：
- 返回参数包含f_ref=50.0, n_ref=1500.0

**断言**：
```python
params = param_manager.get_parameters('pump_speed', 'method_a')
assert params['f_ref'] == 50.0
assert params['n_ref'] == 1500.0
```

---

#### 测试用例7.4：数据写入集成

**测试ID**：`test_data_writing_integration`
**测试目的**：验证计算结果正确写入数据库
**前置条件**：
- 有计算结果DataFrame

**测试步骤**：
1. 创建DataWriter实例
2. 调用write_results(result_df, metric_id=19)
3. 查询数据库验证写入

**预期结果**：
- 数据库中写入成功
- 写入数据量与result_df一致

**断言**：
```python
writer.write_results(result_df, metric_id=19)

with get_connection() as conn:
    cur = conn.execute(
        "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=19"
    )
    count = cur.fetchone()[0]
    assert count == len(result_df)
```

---

## 性能测试用例

### 测试文件：`tests/performance/metrics/pump_speed/test_pump_speed_performance.py`

#### 测试用例8.1：大数据量性能测试

**测试ID**：`test_large_dataset_performance`
**测试目的**：验证大数据量下的计算性能
**前置条件**：
- 数据库中有设备1-6的完整数据（约50万条）

**测试步骤**：
1. 创建PumpSpeedPipeline实例
2. 记录开始时间
3. 调用run(start_time, end_time, device_ids=[1,2,3,4,5,6])
4. 记录结束时间
5. 计算耗时

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**断言**：
```python
elapsed_time = end_time - start_time
assert elapsed_time < 60.0
assert len(result_df) / elapsed_time > 8000
```

---

#### 测试用例8.2：批量写入性能测试

**测试ID**：`test_batch_writing_performance`
**测试目的**：验证批量写入性能
**前置条件**：
- 有10万条计算结果

**测试步骤**：
1. 创建DataWriter实例
2. 记录开始时间
3. 调用write_results(result_df, metric_id=19)
4. 记录结束时间
5. 计算写入速度

**预期结果**：
- 写入速度 > 1000条/秒

**断言**：
```python
elapsed_time = end_time - start_time
write_speed = len(result_df) / elapsed_time
assert write_speed > 1000
```

---

#### 测试用例8.3：内存使用测试

**测试ID**：`test_memory_usage`
**测试目的**：验证内存使用合理
**前置条件**：
- 数据库中有设备1-6的完整数据

**测试步骤**：
1. 记录初始内存使用
2. 创建PumpSpeedPipeline实例
3. 调用run(start_time, end_time, device_ids=[1,2,3,4,5,6])
4. 记录峰值内存使用
5. 计算内存增量

**预期结果**：
- 内存增量 < 2GB

**断言**：
```python
memory_increase = peak_memory - initial_memory
assert memory_increase < 2 * 1024 * 1024 * 1024  # 2GB
```

---

## 边界测试用例

### 测试文件：`tests/boundary/metrics/pump_speed/test_pump_speed_boundary.py`

#### 测试用例9.1：零频率处理

**测试ID**：`test_zero_frequency`
**测试目的**：验证零频率的正确处理
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[0.0]）
2. 创建Calculator实例
3. 调用_method_a(df)
4. 验证结果

**预期结果**：
- pump_speed=0.0
- 不抛出异常

**断言**：
```python
assert df.loc[0, 'pump_speed'] == 0.0
```

---

#### 测试用例9.2：极大频率处理

**测试ID**：`test_extreme_frequency`
**测试目的**：验证极大频率的正确处理
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[100.0]）
2. 创建Calculator实例
3. 调用_method_a(df)
4. 创建Validator实例
5. 调用validate(df)

**预期结果**：
- pump_speed=3000.0
- valid_range=True（如果max_speed=3000）

**断言**：
```python
assert df.loc[0, 'pump_speed'] == 3000.0
assert df.loc[0, 'valid_range'] == True
```

---

#### 测试用例9.3：缺失数据处理

**测试ID**：`test_missing_data`
**测试目的**：验证缺失数据的正确处理
**前置条件**：无

**测试步骤**：
1. 创建测试DataFrame（pump_frequency=[NaN]）
2. 创建Calculator实例
3. 调用_method_a(df)
4. 验证结果

**预期结果**：
- pump_speed=NaN
- 不抛出异常

**断言**：
```python
assert pd.isna(df.loc[0, 'pump_speed'])
```

---

## 回归测试用例

### 测试文件：`tests/regression/metrics/pump_speed/test_pump_speed_regression.py`

#### 测试用例10.1：与现有系统对比

**测试ID**：`test_regression_comparison`
**测试目的**：验证新系统与现有系统结果一致
**前置条件**：
- 现有系统有pump_speed计算结果

**测试步骤**：
1. 从现有系统查询pump_speed结果
2. 使用新系统计算相同时间范围的pump_speed
3. 对比两个结果

**预期结果**：
- 差异 < 1%（允许小幅优化）
- 一致性 > 95%

**断言**：
```python
diff = abs(new_result - old_result) / old_result
assert (diff < 0.01).sum() / len(diff) > 0.95
```

---

## 📊 测试用例统计

| 测试类型 | 测试文件数 | 测试用例数 | 覆盖率目标 |
|----------|-----------|-----------|-----------|
| 单元测试 | 6 | 18 | 95% |
| 集成测试 | 1 | 4 | 90% |
| 性能测试 | 1 | 3 | N/A |
| 边界测试 | 1 | 3 | N/A |
| 回归测试 | 1 | 1 | N/A |
| **总计** | **10** | **29** | **90%** |

---

## ✅ 验收标准

**单元测试**：
- [ ] 所有单元测试通过率 100%
- [ ] 代码覆盖率 > 95%
- [ ] 无跳过的测试用例

**集成测试**：
- [ ] 所有集成测试通过率 100%
- [ ] 数据库写入验证通过
- [ ] 参数加载验证通过

**性能测试**：
- [ ] 大数据量耗时 < 60秒
- [ ] 批量写入速度 > 1000条/秒
- [ ] 内存使用 < 2GB

**边界测试**：
- [ ] 所有边界测试通过率 100%
- [ ] 无异常抛出

**回归测试**：
- [ ] 与现有系统一致性 > 95%

---

**文档结束**

