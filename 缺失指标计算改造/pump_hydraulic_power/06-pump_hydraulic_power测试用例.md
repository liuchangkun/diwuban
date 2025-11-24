# pump_hydraulic_power 测试用例文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-pump_hydraulic_power详细设计.md`

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

验证pump_hydraulic_power（泵水力功率）计算的正确性、性能和稳定性。

### 测试范围

- **设备范围**：device_id=1-6（水泵）
- **时间范围**：2025-10-22 08:00:00 ~ 2025-10-23 07:19:37
- **依赖指标**：
  - pump_flow_rate（metric_id=18, device_id=1-6）
  - pump_head（metric_id=17, device_id=1-6）
- **计算方法**：method_a（流量-扬程法）

### 测试环境

- **数据库**：PostgreSQL + TimescaleDB
- **测试框架**：pytest 7.4+
- **覆盖率目标**：单元测试95%，集成测试90%

---

## 单元测试用例

### 测试文件：`tests/unit/metrics/pump_hydraulic_power/test_data_loader.py`

#### 测试用例1.1：正常数据加载

**测试ID**：`test_load_data_success`  
**测试目的**：验证DataLoader能正确加载pump_flow_rate和pump_head数据  
**前置条件**：
- pump_flow_rate数据存在（metric_id=18, device_id=1-6）
- pump_head数据存在（metric_id=17, device_id=1-6）
- 时间范围内有数据

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data方法加载数据
3. 验证返回的DataFrame

**预期结果**：
- 返回DataFrame包含必需列：ts_bucket, device_id, pump_flow_rate, pump_head
- 数据量 > 0
- pump_flow_rate值在合理范围（0-3000 m³/h）
- pump_head值在合理范围（0-150 m）

**断言代码**：
```python
assert isinstance(df, pd.DataFrame)
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_flow_rate', 'pump_head'}
assert len(df) > 0
assert df['pump_flow_rate'].between(0, 3000).all()
assert df['pump_head'].between(0, 150).all()
assert df['pump_flow_rate'].notna().all()
assert df['pump_head'].notna().all()
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
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pump_flow_rate', 'pump_head'}
```

---

#### 测试用例1.3：依赖数据JOIN验证

**测试ID**：`test_load_data_join_validation`  
**测试目的**：验证DataLoader能正确JOIN两个依赖指标  
**前置条件**：pump_flow_rate和pump_head数据存在

**测试步骤**：
1. 创建DataLoader实例
2. 加载数据
3. 验证JOIN结果

**预期结果**：
- 所有记录都有pump_flow_rate和pump_head值
- 时间戳对齐

**断言代码**：
```python
assert df['pump_flow_rate'].notna().all()
assert df['pump_head'].notna().all()
assert df.groupby(['ts_bucket', 'device_id']).size().max() == 1
```

---

### 测试文件：`tests/unit/metrics/pump_hydraulic_power/test_calculator.py`

#### 测试用例4.1：method_a计算正确性

**测试ID**：`test_calculate_method_a_correctness`  
**测试目的**：验证method_a计算公式正确  
**前置条件**：
- method_a参数已配置（rho=1000, g=9.81）

**测试步骤**：
1. 创建包含pump_flow_rate和pump_head的测试数据（Q=60 m³/h, H=100 m）
2. 创建Calculator实例（method_a）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_h = 1000 × 9.81 × (60/3600) × 100 / 1000 = 16.35 kW

**断言代码**：
```python
assert result_df.loc[0, 'pump_hydraulic_power'] == pytest.approx(16.35, rel=1e-4)
```

---

#### 测试用例4.2：零流量处理

**测试ID**：`test_calculate_zero_flow`  
**测试目的**：验证零流量时的计算  
**前置条件**：pump_flow_rate=0

**测试步骤**：
1. 创建pump_flow_rate=0的测试数据
2. 创建Calculator实例（method_a）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_h = 0 kW

**断言代码**：
```python
assert result_df.loc[0, 'pump_hydraulic_power'] == pytest.approx(0.0, abs=1e-6)
```

---

#### 测试用例4.3：零扬程处理

**测试ID**：`test_calculate_zero_head`  
**测试目的**：验证零扬程时的计算  
**前置条件**：pump_head=0

**测试步骤**：
1. 创建pump_head=0的测试数据
2. 创建Calculator实例（method_a）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_h = 0 kW

**断言代码**：
```python
assert result_df.loc[0, 'pump_hydraulic_power'] == pytest.approx(0.0, abs=1e-6)
```

---

### 测试文件：`tests/unit/metrics/pump_hydraulic_power/test_validator.py`

#### 测试用例5.1：范围验证

**测试ID**：`test_validate_range`
**测试目的**：验证Validator能正确验证功率范围
**前置条件**：验证参数已配置（min_power=0.0, max_power=500.0 kW）

**测试步骤**：
1. 创建包含不同功率值的测试数据（-10, 0, 250, 500, 600 kW）
2. 创建Validator实例
3. 调用validate方法
4. 验证范围标记

**预期结果**：
- -10 kW: valid_range=False
- 0 kW: valid_range=True
- 250 kW: valid_range=True
- 500 kW: valid_range=True
- 600 kW: valid_range=False

**断言代码**：
```python
assert result_df.loc[0, 'valid_range'] == False
assert result_df.loc[1, 'valid_range'] == True
assert result_df.loc[2, 'valid_range'] == True
assert result_df.loc[3, 'valid_range'] == True
assert result_df.loc[4, 'valid_range'] == False
```

---

#### 测试用例5.2：物理约束验证

**测试ID**：`test_validate_physics`
**测试目的**：验证Validator能正确验证物理约束（P_h ≤ P_shaft）
**前置条件**：pump_shaft_power数据可用

**测试步骤**：
1. 创建包含pump_hydraulic_power和pump_shaft_power的测试数据
2. 创建Validator实例
3. 调用validate方法
4. 验证物理约束标记

**预期结果**：
- P_h ≤ P_shaft: valid_physics=True
- P_h > P_shaft: valid_physics=False

**断言代码**：
```python
assert result_df.loc[0, 'valid_physics'] == True
assert result_df.loc[1, 'valid_physics'] == False
```

---

### 测试文件：`tests/unit/metrics/pump_hydraulic_power/test_pipeline.py`

#### 测试用例6.1：完整流程

**测试ID**：`test_pipeline_complete_flow`
**测试目的**：验证Pipeline能正确执行完整流程
**前置条件**：所有组件已实现，测试数据已准备

**测试步骤**：
1. 创建Pipeline实例
2. 调用run方法
3. 验证返回结果

**预期结果**：
- 返回DataFrame包含pump_hydraulic_power列
- 数据量 > 0
- 所有值在合理范围

**断言代码**：
```python
assert 'pump_hydraulic_power' in result_df.columns
assert len(result_df) > 0
assert result_df['pump_hydraulic_power'].between(0, 500).all()
```

---

## 集成测试用例

### 测试文件：`tests/integration/metrics/pump_hydraulic_power/test_pump_hydraulic_power_integration.py`

#### 测试用例7.1：单设备完整流程

**测试ID**：`test_single_device_integration`
**测试目的**：验证单设备完整计算流程
**前置条件**：pump_flow_rate和pump_head数据存在，数据库连接正常

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程（device_id=1）
3. 验证结果
4. 验证数据库写入

**预期结果**：
- 计算结果正确
- 数据已写入fact_measurements表（metric_id=67, device_id=1）

**断言代码**：
```python
assert 'pump_hydraulic_power' in result_df.columns
assert len(result_df) > 0
assert result_df['pump_hydraulic_power'].between(0, 500).all()

with get_connection() as conn:
    cur = conn.execute(
        "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=67 AND device_id=1"
    )
    count = cur.fetchone()[0]
    assert count > 0
```

---

#### 测试用例7.2：多设备完整流程

**测试ID**：`test_multiple_devices_integration`
**测试目的**：验证多设备完整计算流程
**前置条件**：pump_flow_rate和pump_head数据存在（device_id=1-6）

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程（device_id=1-6）
3. 验证结果
4. 验证数据库写入

**预期结果**：
- 所有设备都有计算结果
- 数据已写入数据库

**断言代码**：
```python
assert set(result_df['device_id'].unique()) == set([1,2,3,4,5,6])
for device_id in [1,2,3,4,5,6]:
    device_data = result_df[result_df['device_id'] == device_id]
    assert len(device_data) > 0
```

---

#### 测试用例7.3：依赖数据验证

**测试ID**：`test_dependency_data_validation`
**测试目的**：验证依赖数据的完整性
**前置条件**：pump_flow_rate和pump_head数据存在

**测试步骤**：
1. 创建Pipeline实例
2. 验证依赖数据加载
3. 验证数据对齐

**预期结果**：
- pump_flow_rate和pump_head数据完整
- 时间戳对齐

**断言代码**：
```python
assert 'pump_flow_rate' in df.columns
assert 'pump_head' in df.columns
assert df['pump_flow_rate'].notna().all()
assert df['pump_head'].notna().all()
```

---

## 性能测试用例

### 测试文件：`tests/performance/metrics/pump_hydraulic_power/test_pump_hydraulic_power_performance.py`

#### 测试用例8.1：大数据量性能测试

**测试ID**：`test_large_dataset_performance`
**测试目的**：验证大数据量下的计算性能
**前置条件**：完整时间范围的数据（约500,000条）

**测试步骤**：
1. 创建Pipeline实例
2. 记录开始时间
3. 运行完整流程（device_id=1-6）
4. 记录结束时间
5. 计算耗时和吞吐量

**预期结果**：
- 总耗时 < 60秒
- 吞吐量 > 8000条/秒

**断言代码**：
```python
assert elapsed_time < 60.0
throughput = len(result_df) / elapsed_time
assert throughput > 8000
```

---

#### 测试用例8.2：批量写入性能测试

**测试ID**：`test_batch_write_performance`
**测试目的**：验证批量写入性能
**前置条件**：有计算结果

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程
3. 记录写入耗时
4. 计算写入速度

**预期结果**：
- 写入速度 > 1000条/秒

**断言代码**：
```python
write_speed = len(result_df) / write_time
assert write_speed > 1000
```

---

#### 测试用例8.3：内存使用测试

**测试ID**：`test_memory_usage`
**测试目的**：验证内存使用合理
**前置条件**：完整时间范围的数据

**测试步骤**：
1. 记录初始内存
2. 创建Pipeline实例
3. 运行完整流程
4. 记录峰值内存
5. 计算内存增量

**预期结果**：
- 内存增量 < 2GB

**断言代码**：
```python
assert memory_increase < 2 * 1024 * 1024 * 1024  # 2GB
```

---

## 边界测试用例

### 测试文件：`tests/boundary/metrics/pump_hydraulic_power/test_pump_hydraulic_power_boundary.py`

#### 测试用例9.1：零流量零扬程处理

**测试ID**：`test_zero_flow_zero_head`
**测试目的**：验证零流量零扬程时的处理
**前置条件**：pump_flow_rate=0, pump_head=0

**测试步骤**：
1. 创建pump_flow_rate=0, pump_head=0的测试数据
2. 运行完整流程
3. 验证结果

**预期结果**：
- P_h = 0 kW
- 不抛出异常

**断言代码**：
```python
assert result_df['pump_hydraulic_power'].iloc[0] == pytest.approx(0.0, abs=1e-6)
```

---

#### 测试用例9.2：极大流量处理

**测试ID**：`test_extreme_flow`
**测试目的**：验证极大流量时的处理
**前置条件**：pump_flow_rate=3000 m³/h（接近最大值）

**测试步骤**：
1. 创建pump_flow_rate=3000的测试数据
2. 运行完整流程
3. 验证结果

**预期结果**：
- P_h计算正确
- 不抛出异常

**断言代码**：
```python
assert result_df['pump_hydraulic_power'].iloc[0] > 0
assert result_df['pump_hydraulic_power'].iloc[0] < 500
```

---

#### 测试用例9.3：缺失依赖数据处理

**测试ID**：`test_missing_dependency_data`
**测试目的**：验证缺失依赖数据时的处理
**前置条件**：pump_flow_rate或pump_head数据缺失

**测试步骤**：
1. 模拟pump_flow_rate或pump_head数据缺失
2. 运行完整流程
3. 验证处理结果

**预期结果**：
- 返回空DataFrame或标记为无效
- 不抛出异常

**断言代码**：
```python
assert len(result_df) == 0 or result_df['quality'].eq('invalid').all()
```

---

## 回归测试用例

### 测试文件：`tests/regression/metrics/pump_hydraulic_power/test_pump_hydraulic_power_regression.py`

#### 测试用例10.1：与现有系统对比

**测试ID**：`test_regression_comparison`
**测试目的**：验证新实现与现有系统的一致性
**前置条件**：现有系统有pump_hydraulic_power数据，新实现已完成

**测试步骤**：
1. 从现有系统获取pump_hydraulic_power数据
2. 运行新实现
3. 对比结果

**预期结果**：
- 差异 < 1%
- 覆盖率 > 95%

**断言代码**：
```python
diff_ratio = abs(new_value - old_value) / old_value
assert diff_ratio < 0.01
coverage = len(matched) / len(old_data)
assert coverage > 0.95
```

---

## 📊 测试用例统计

| 测试类型 | 测试文件 | 测试用例数 | 覆盖组件 |
|----------|---------|-----------|---------|
| 单元测试 | 6个 | 13 | DataLoader, DataFilter, MethodSelector, Calculator, Validator, Pipeline |
| 集成测试 | 1个 | 3 | 完整流程, 依赖数据, 数据写入 |
| 性能测试 | 1个 | 3 | 计算性能, 写入性能, 内存使用 |
| 边界测试 | 1个 | 3 | 零值, 极值, 缺失数据 |
| 回归测试 | 1个 | 1 | 与现有系统对比 |
| **总计** | **10个** | **23** | **全覆盖** |

---

## ✅ 测试用例验收标准

**覆盖率**：
- [ ] 单元测试覆盖率 > 95%
- [ ] 集成测试覆盖关键流程
- [ ] 性能测试覆盖性能指标
- [ ] 边界测试覆盖边界条件

**质量**：
- [ ] 所有测试用例有明确的测试ID
- [ ] 所有测试用例有清晰的测试目的
- [ ] 所有测试用例有完整的断言代码
- [ ] 所有测试用例可独立运行

---

**文档结束**
