# pump_torque 测试用例文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_torque详细设计.md`

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

验证pump_torque（泵扭矩）计算的正确性、性能和稳定性。

### 测试范围

- **设备范围**：device_id=1-6（水泵）
- **时间范围**：2025-10-22 08:00:00 ~ 2025-10-23 07:19:37
- **依赖指标**：
  - pump_active_power（metric_id=2, device_id=1-6）
  - pump_speed（metric_id=19, device_id=1-6，新实现）
  - pump_flow_rate（metric_id=18, device_id=1-6，method_b使用）
  - pump_head（metric_id=17, device_id=1-6，method_b使用）
- **计算方法**：method_a（功率-转速法），method_b（水力功率法）

### 测试环境

- **数据库**：PostgreSQL + TimescaleDB
- **测试框架**：pytest 7.4+
- **覆盖率目标**：单元测试95%，集成测试90%

---

## 单元测试用例

### 测试文件：`tests/unit/metrics/pump_torque/test_data_loader.py`

#### 测试用例1.1：正常数据加载

**测试ID**：`test_load_data_success`  
**测试目的**：验证DataLoader能正确加载pump_active_power和pump_speed数据  
**前置条件**：
- pump_active_power数据存在（metric_id=2, device_id=1-6）
- pump_speed数据存在（metric_id=19, device_id=1-6）
- 时间范围内有数据

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data方法加载数据
3. 验证返回的DataFrame

**预期结果**：
- 返回DataFrame包含必需列：ts_bucket, device_id, pump_active_power, pump_speed
- 数据量 > 0
- pump_active_power值在合理范围（0-600 kW）
- pump_speed值在合理范围（0-3000 rpm）

**断言代码**：
```python
assert isinstance(df, pd.DataFrame)
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_active_power', 'pump_speed'}
assert len(df) > 0
assert df['pump_active_power'].between(0, 600).all()
assert df['pump_speed'].between(0, 3000).all()
assert df['pump_active_power'].notna().all()
assert df['pump_speed'].notna().all()
```

---

#### 测试用例1.2：空数据处理

**测试ID**：`test_load_data_empty`  
**测试目的**：验证DataLoader能正确处理空数据  
**前置条件**：查询不存在的设备

**测试步骤**：
1. 创建DataLoader实例
2. 查询不存在的设备（device_id=999）
3. 验证返回空DataFrame

**预期结果**：
- 返回空DataFrame
- 列结构正确

**断言代码**：
```python
assert isinstance(df, pd.DataFrame)
assert len(df) == 0
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_active_power', 'pump_speed'}
```

---

#### 测试用例1.3：依赖数据JOIN验证

**测试ID**：`test_load_data_join_validation`  
**测试目的**：验证DataLoader能正确JOIN两个依赖指标  
**前置条件**：pump_active_power和pump_speed数据存在

**测试步骤**：
1. 创建DataLoader实例
2. 加载数据
3. 验证JOIN结果

**预期结果**：
- 所有记录都有pump_active_power和pump_speed值
- 时间戳对齐

**断言代码**：
```python
assert df['pump_active_power'].notna().all()
assert df['pump_speed'].notna().all()
assert df.groupby(['ts_bucket', 'device_id']).size().max() == 1
```

---

### 测试文件：`tests/unit/metrics/pump_torque/test_calculator.py`

#### 测试用例4.1：method_a计算正确性

**测试ID**：`test_calculate_method_a_correctness`  
**测试目的**：验证method_a计算公式正确  
**前置条件**：pump_active_power和pump_speed数据可用

**测试步骤**：
1. 创建包含pump_active_power和pump_speed的测试数据（P=100 kW, n=1500 rpm）
2. 创建Calculator实例（method_a）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- T = 9549.3 × 100 / 1500 = 636.62 N·m

**断言代码**：
```python
assert result_df.loc[0, 'pump_torque'] == pytest.approx(636.62, rel=1e-4)
```

---

#### 测试用例4.2：method_b计算正确性

**测试ID**：`test_calculate_method_b_correctness`  
**测试目的**：验证method_b计算公式正确  
**前置条件**：pump_flow_rate, pump_head, pump_speed数据可用

**测试步骤**：
1. 创建包含pump_flow_rate, pump_head, pump_speed的测试数据（Q=60 m³/h, H=100 m, n=1500 rpm）
2. 创建Calculator实例（method_b）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- T = 1000 × 9.81 × (60/3600) × 100 / (2π × 1500 / 60) ≈ 104.0 N·m

**断言代码**：
```python
assert result_df.loc[0, 'pump_torque'] == pytest.approx(104.0, rel=1e-2)
```

---

#### 测试用例4.3：零转速处理

**测试ID**：`test_calculate_zero_speed`  
**测试目的**：验证零转速时的处理  
**前置条件**：pump_speed=0

**测试步骤**：
1. 创建pump_speed=0的测试数据
2. 创建Calculator实例（method_a）
3. 调用calculate方法
4. 验证处理结果

**预期结果**：
- 返回NaN或标记为无效（避免除零错误）

**断言代码**：
```python
assert pd.isna(result_df.loc[0, 'pump_torque']) or result_df.loc[0, 'quality'] == 'invalid'
```

---

### 测试文件：`tests/unit/metrics/pump_torque/test_method_selector.py`

#### 测试用例3.1：method_a优先级验证

**测试ID**：`test_method_selection_priority_a`
**测试目的**：验证当pump_active_power和pump_speed都可用时，选择method_a
**前置条件**：pump_active_power和pump_speed数据都存在

**测试步骤**：
1. 创建包含pump_active_power和pump_speed的测试数据
2. 创建MethodSelector实例
3. 调用select_method方法
4. 验证选择的方法

**预期结果**：
- 选择method_a（优先级100）

**断言代码**：
```python
assert result_df.loc[0, 'selected_method'] == 'method_a'
```

---

#### 测试用例3.2：method_b降级验证

**测试ID**：`test_method_selection_fallback_b`
**测试目的**：验证当pump_active_power不可用时，降级到method_b
**前置条件**：pump_flow_rate, pump_head, pump_speed数据存在，pump_active_power缺失

**测试步骤**：
1. 创建包含pump_flow_rate, pump_head, pump_speed的测试数据（无pump_active_power）
2. 创建MethodSelector实例
3. 调用select_method方法
4. 验证选择的方法

**预期结果**：
- 选择method_b（优先级90）

**断言代码**：
```python
assert result_df.loc[0, 'selected_method'] == 'method_b'
```

---

#### 测试用例3.3：无可用方法处理

**测试ID**：`test_method_selection_no_method`
**测试目的**：验证当所有依赖数据都不可用时的处理
**前置条件**：所有依赖数据都缺失

**测试步骤**：
1. 创建空的测试数据（无任何依赖指标）
2. 创建MethodSelector实例
3. 调用select_method方法
4. 验证处理结果

**预期结果**：
- selected_method为None或'none'

**断言代码**：
```python
assert result_df.loc[0, 'selected_method'] in [None, 'none']
```

---

### 测试文件：`tests/unit/metrics/pump_torque/test_validator.py`

#### 测试用例5.1：范围验证

**测试ID**：`test_validate_range`
**测试目的**：验证pump_torque值在合理范围内（0-10000 N·m）
**前置条件**：pump_torque计算结果可用

**测试步骤**：
1. 创建包含不同pump_torque值的测试数据（-100, 0, 5000, 10000, 15000 N·m）
2. 创建Validator实例
3. 调用validate方法
4. 验证范围验证结果

**预期结果**：
- -100 N·m：invalid
- 0 N·m：valid
- 5000 N·m：valid
- 10000 N·m：valid
- 15000 N·m：invalid

**断言代码**：
```python
assert result_df.loc[0, 'valid_range'] == False  # -100
assert result_df.loc[1, 'valid_range'] == True   # 0
assert result_df.loc[2, 'valid_range'] == True   # 5000
assert result_df.loc[3, 'valid_range'] == True   # 10000
assert result_df.loc[4, 'valid_range'] == False  # 15000
```

---

#### 测试用例5.2：物理关系验证

**测试ID**：`test_validate_physics`
**测试目的**：验证扭矩与功率、转速的物理关系（T = 9549.3 × P / n）
**前置条件**：pump_torque, pump_active_power, pump_speed数据可用

**测试步骤**：
1. 创建包含pump_torque, pump_active_power, pump_speed的测试数据
2. 创建Validator实例
3. 调用validate方法
4. 验证物理关系

**预期结果**：
- 计算值与实际值的误差 < 1%

**断言代码**：
```python
assert result_df.loc[0, 'valid_physics'] == True
assert result_df.loc[0, 'physics_error'] < 0.01
```

---

### 测试文件：`tests/unit/metrics/pump_torque/test_pipeline.py`

#### 测试用例6.1：完整流程测试

**测试ID**：`test_pipeline_complete_flow`
**测试目的**：验证Pipeline完整流程（加载→过滤→选择→计算→验证→写入）
**前置条件**：所有依赖数据和参数可用

**测试步骤**：
1. 创建Pipeline实例
2. 调用run方法
3. 验证返回结果

**预期结果**：
- 返回DataFrame包含pump_torque列
- 所有值在合理范围内
- 数据已写入数据库

**断言代码**：
```python
assert 'pump_torque' in result_df.columns
assert result_df['pump_torque'].between(0, 10000).all()
assert len(result_df) > 0
```

---

## 集成测试用例

### 测试文件：`tests/integration/metrics/pump_torque/test_pump_torque_integration.py`

#### 测试用例7.1：单设备完整流程

**测试ID**：`test_single_device_integration`
**测试目的**：验证单个设备的完整计算流程
**前置条件**：设备1的所有依赖数据可用

**测试步骤**：
1. 创建Pipeline实例
2. 运行设备1的计算
3. 验证结果和数据库写入

**预期结果**：
- 计算成功
- 数据写入fact_measurements表（metric_id=20, device_id=1）
- 数据量 > 0

**断言代码**：
```python
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
```

---

#### 测试用例7.2：多设备完整流程

**测试ID**：`test_multiple_devices_integration`
**测试目的**：验证多个设备的完整计算流程
**前置条件**：设备1-6的所有依赖数据可用

**测试步骤**：
1. 创建Pipeline实例
2. 运行设备1-6的计算
3. 验证结果

**预期结果**：
- 所有设备都有数据
- 每个设备的数据量 > 0

**断言代码**：
```python
assert set(result_df['device_id'].unique()) == set([1, 2, 3, 4, 5, 6])
for device_id in [1, 2, 3, 4, 5, 6]:
    device_data = result_df[result_df['device_id'] == device_id]
    assert len(device_data) > 0
```

---

#### 测试用例7.3：依赖数据验证

**测试ID**：`test_dependency_data_validation`
**测试目的**：验证依赖数据的完整性和准确性
**前置条件**：pump_active_power和pump_speed数据存在

**测试步骤**：
1. 创建Pipeline实例
2. 加载依赖数据
3. 验证数据完整性

**预期结果**：
- pump_active_power和pump_speed数据都存在
- 时间戳对齐

**断言代码**：
```python
df = pipeline.data_loader.load_data(device_ids=[1])
assert 'pump_active_power' in df.columns
assert 'pump_speed' in df.columns
assert df['pump_active_power'].notna().all()
assert df['pump_speed'].notna().all()
```

---

#### 测试用例7.4：pump_speed依赖验证

**测试ID**：`test_pump_speed_dependency`
**测试目的**：验证pump_speed（新实现指标）的依赖关系
**前置条件**：pump_speed已实施并有数据

**测试步骤**：
1. 查询pump_speed数据（metric_id=19）
2. 验证pump_speed数据可用
3. 验证pump_torque可以正确使用pump_speed

**预期结果**：
- pump_speed数据存在
- pump_torque计算成功

**断言代码**：
```python
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

## 性能测试用例

### 测试文件：`tests/performance/metrics/pump_torque/test_pump_torque_performance.py`

#### 测试用例8.1：大数据量性能测试

**测试ID**：`test_large_dataset_performance`
**测试目的**：验证大数据量下的计算性能
**前置条件**：设备1-6的完整时间范围数据

**测试步骤**：
1. 创建Pipeline实例
2. 运行设备1-6的完整计算
3. 记录耗时和吞吐量

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**断言代码**：
```python
start_time = time.time()
result_df = pipeline.run(device_ids=[1, 2, 3, 4, 5, 6])
elapsed_time = time.time() - start_time

assert elapsed_time < 60.0
throughput = len(result_df) / elapsed_time
assert throughput > 8000
```

---

#### 测试用例8.2：批量写入性能测试

**测试ID**：`test_batch_write_performance`
**测试目的**：验证批量写入数据库的性能
**前置条件**：计算结果可用

**测试步骤**：
1. 准备大量计算结果
2. 批量写入数据库
3. 记录写入速度

**预期结果**：
- 写入速度 > 1000条/秒

**断言代码**：
```python
start_time = time.time()
pipeline.writer.write(result_df)
elapsed_time = time.time() - start_time

write_speed = len(result_df) / elapsed_time
assert write_speed > 1000
```

---

#### 测试用例8.3：内存使用测试

**测试ID**：`test_memory_usage`
**测试目的**：验证内存使用在合理范围内
**前置条件**：设备1-6的完整时间范围数据

**测试步骤**：
1. 记录初始内存使用
2. 运行完整计算
3. 记录峰值内存使用

**预期结果**：
- 内存增量 < 2GB

**断言代码**：
```python
process = psutil.Process()
initial_memory = process.memory_info().rss

result_df = pipeline.run(device_ids=[1, 2, 3, 4, 5, 6])

peak_memory = process.memory_info().rss
memory_increase = peak_memory - initial_memory

assert memory_increase < 2 * 1024 * 1024 * 1024  # 2GB
```

---

## 边界测试用例

### 测试文件：`tests/boundary/metrics/pump_torque/test_pump_torque_boundary.py`

#### 测试用例9.1：零值处理

**测试ID**：`test_zero_values`
**测试目的**：验证零值的正确处理
**前置条件**：测试数据包含零值

**测试步骤**：
1. 创建包含零值的测试数据（P=0, n=0）
2. 运行计算
3. 验证处理结果

**预期结果**：
- P=0时，T=0
- n=0时，T=NaN或标记为无效

**断言代码**：
```python
# P=0, n=1500
df1 = pd.DataFrame({'pump_active_power': [0.0], 'pump_speed': [1500.0]})
result1 = calculator.calculate(df1)
assert result1.loc[0, 'pump_torque'] == pytest.approx(0.0, abs=1e-6)

# P=100, n=0
df2 = pd.DataFrame({'pump_active_power': [100.0], 'pump_speed': [0.0]})
result2 = calculator.calculate(df2)
assert pd.isna(result2.loc[0, 'pump_torque']) or result2.loc[0, 'quality'] == 'invalid'
```

---

#### 测试用例9.2：极值处理

**测试ID**：`test_extreme_values`
**测试目的**：验证极值的正确处理
**前置条件**：测试数据包含极值

**测试步骤**：
1. 创建包含极值的测试数据（P=600 kW, n=3000 rpm）
2. 运行计算
3. 验证处理结果

**预期结果**：
- 计算结果在合理范围内（0-10000 N·m）

**断言代码**：
```python
df = pd.DataFrame({'pump_active_power': [600.0], 'pump_speed': [3000.0]})
result_df = calculator.calculate(df)
assert result_df.loc[0, 'pump_torque'] >= 0
assert result_df.loc[0, 'pump_torque'] <= 10000
```

---

#### 测试用例9.3：缺失数据处理

**测试ID**：`test_missing_data`
**测试目的**：验证缺失数据的正确处理
**前置条件**：测试数据包含NaN值

**测试步骤**：
1. 创建包含NaN值的测试数据
2. 运行计算
3. 验证处理结果

**预期结果**：
- 缺失数据被正确标记或跳过

**断言代码**：
```python
df = pd.DataFrame({
    'pump_active_power': [100.0, np.nan, 200.0],
    'pump_speed': [1500.0, 1500.0, np.nan]
})
result_df = calculator.calculate(df)
assert pd.isna(result_df.loc[1, 'pump_torque'])
assert pd.isna(result_df.loc[2, 'pump_torque'])
```

---

## 回归测试用例

### 测试文件：`tests/regression/metrics/pump_torque/test_pump_torque_regression.py`

#### 测试用例10.1：与现有系统对比

**测试ID**：`test_regression_comparison`
**测试目的**：验证新实现与现有系统的一致性
**前置条件**：现有系统有pump_torque数据（如果有）

**测试步骤**：
1. 从现有系统获取pump_torque数据
2. 运行新实现的计算
3. 对比结果

**预期结果**：
- 差异 < 5%（如果现有系统有数据）
- 或验证新实现的合理性（如果现有系统无数据）

**断言代码**：
```python
# 如果现有系统有数据
if existing_data is not None:
    diff = abs(new_data - existing_data) / existing_data
    assert diff.mean() < 0.05

# 如果现有系统无数据，验证新实现的合理性
else:
    assert new_data.between(0, 10000).all()
    assert new_data.notna().sum() / len(new_data) > 0.95
```

---

## 📊 测试用例统计

| 测试类型 | 测试文件 | 测试用例数 | 覆盖组件 |
|----------|---------|-----------|---------|
| 单元测试 | 6个 | 18个 | DataLoader, DataFilter, MethodSelector, Calculator, Validator, Pipeline |
| 集成测试 | 1个 | 4个 | 完整流程 + pump_speed依赖 |
| 性能测试 | 1个 | 3个 | 大数据量 + 批量写入 + 内存 |
| 边界测试 | 1个 | 3个 | 零值 + 极值 + 缺失数据 |
| 回归测试 | 1个 | 1个 | 与现有系统对比 |
| **总计** | **10个** | **29个** | **全覆盖** |

---

## ✅ 测试用例验收标准

**覆盖率**：
- [ ] 单元测试覆盖所有6个组件
- [ ] 集成测试覆盖完整流程和pump_speed依赖
- [ ] 性能测试覆盖性能指标
- [ ] 边界测试覆盖边界条件
- [ ] 回归测试覆盖系统对比

**质量**：
- [ ] 所有测试用例有完整描述
- [ ] 所有测试用例有清晰的断言
- [ ] 所有测试用例可独立运行

**特殊验证**：
- [ ] pump_speed依赖验证（新实现指标）
- [ ] 两种计算方法验证（method_a, method_b）
- [ ] 物理关系验证（T = 9549.3 × P / n）

---

**文档结束**

