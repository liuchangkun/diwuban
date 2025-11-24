# main_pipeline_inlet_pressure 测试用例文档

> **文档版本**: v1.0  
> **创建日期**: 2025-11-22  
> **状态**: 计划阶段  
> **协议**: RIPER-5  
> **参考文档**: `01-main_pipeline_inlet_pressure详细设计.md`

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

验证main_pipeline_inlet_pressure（总管进口压力）计算的正确性、性能和稳定性。

### 测试范围

- **设备范围**：device_id=7（总管）
- **时间范围**：2025-10-22 08:00:00 ~ 2025-10-23 07:19:37
- **依赖指标**：pool_liquid_level（metric_id=5, device_id=8）
- **计算方法**：method_b（静压法）、PIN_COEF_V1（等效系数法）

### 测试环境

- **数据库**：PostgreSQL + TimescaleDB
- **测试框架**：pytest 7.4+
- **覆盖率目标**：单元测试95%，集成测试90%

---

## 单元测试用例

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_data_loader.py`

#### 测试用例1.1：正常数据加载

**测试ID**：`test_load_data_success`  
**测试目的**：验证DataLoader能正确加载pool_liquid_level数据  
**前置条件**：
- pool_liquid_level数据存在（metric_id=5, device_id=8）
- 时间范围内有数据

**测试步骤**：
1. 创建DataLoader实例
2. 调用load_data方法加载数据
3. 验证返回的DataFrame

**预期结果**：
- 返回DataFrame包含必需列：ts_bucket, device_id, pool_liquid_level
- 数据量 > 0
- pool_liquid_level值在合理范围（0-10 m）

**断言代码**：
```python
assert isinstance(df, pd.DataFrame)
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pool_liquid_level'}
assert len(df) > 0
assert df['pool_liquid_level'].between(0, 10).all()
assert df['pool_liquid_level'].notna().all()
```

---

#### 测试用例1.2：空数据处理

**测试ID**：`test_load_data_empty`  
**测试目的**：验证DataLoader能正确处理空数据  
**前置条件**：查询不存在的时间范围

**测试步骤**：
1. 创建DataLoader实例
2. 查询不存在的时间范围
3. 验证返回空DataFrame

**预期结果**：
- 返回空DataFrame
- 列结构正确

**断言代码**：
```python
assert isinstance(df, pd.DataFrame)
assert len(df) == 0
assert set(df.columns) >= {'ts_bucket', 'device_id', 'pool_liquid_level'}
```

---

#### 测试用例1.3：设备类型过滤

**测试ID**：`test_load_data_device_filter`  
**测试目的**：验证DataLoader只加载device_id=8的数据  
**前置条件**：pool_liquid_level数据存在

**测试步骤**：
1. 创建DataLoader实例
2. 加载数据（不指定device_ids）
3. 验证只有device_id=8的数据

**预期结果**：
- 所有数据的device_id=8

**断言代码**：
```python
assert df['device_id'].unique() == [8]
```

---

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_data_filter.py`

#### 测试用例2.1：运行状态过滤

**测试ID**：`test_filter_by_running_state`  
**测试目的**：验证DataFilter能正确过滤运行状态  
**前置条件**：
- 数据包含running列
- 有running=0和running=1的数据

**测试步骤**：
1. 创建包含running=0和running=1的测试数据
2. 创建DataFilter实例
3. 调用filter方法
4. 验证只保留running=1的数据

**预期结果**：
- 所有数据的running=1
- 数据量减少

**断言代码**：
```python
assert filtered_df['running'].eq(1).all()
assert len(filtered_df) < len(df)
```

---

#### 测试用例2.2：空数据过滤

**测试ID**：`test_filter_empty_data`  
**测试目的**：验证DataFilter能正确处理空数据  
**前置条件**：输入空DataFrame

**测试步骤**：
1. 创建空DataFrame
2. 创建DataFilter实例
3. 调用filter方法
4. 验证返回空DataFrame

**预期结果**：
- 返回空DataFrame
- 不抛出异常

**断言代码**：
```python
assert len(filtered_df) == 0
assert isinstance(filtered_df, pd.DataFrame)
```

---

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_method_selector.py`

#### 测试用例3.1：method_b选择

**测试ID**：`test_select_method_b`  
**测试目的**：验证MethodSelector能正确选择method_b  
**前置条件**：
- pool_liquid_level数据可用
- method_b参数已配置

**测试步骤**：
1. 创建包含pool_liquid_level的测试数据
2. 创建MethodSelector实例
3. 调用select_method方法
4. 验证选择method_b

**预期结果**：
- 返回method_b
- 优先级=100

**断言代码**：
```python
assert selected_method == 'method_b'
assert priority == 100
```

---

#### 测试用例3.2：PIN_COEF_V1选择

**测试ID**：`test_select_pin_coef_v1`  
**测试目的**：验证MethodSelector能正确选择PIN_COEF_V1  
**前置条件**：
- pool_liquid_level数据可用
- method_b不可用（参数缺失）
- PIN_COEF_V1参数已配置

**测试步骤**：
1. 创建包含pool_liquid_level的测试数据
2. 模拟method_b参数缺失
3. 创建MethodSelector实例
4. 调用select_method方法
5. 验证选择PIN_COEF_V1

**预期结果**：
- 返回PIN_COEF_V1
- 优先级=90

**断言代码**：
```python
assert selected_method == 'PIN_COEF_V1'
assert priority == 90
```

---

#### 测试用例3.3：无可用方法

**测试ID**：`test_no_available_method`  
**测试目的**：验证MethodSelector在无可用方法时的处理  
**前置条件**：
- pool_liquid_level数据缺失
- 所有方法都不可用

**测试步骤**：
1. 创建不包含pool_liquid_level的测试数据
2. 创建MethodSelector实例
3. 调用select_method方法
4. 验证返回None

**预期结果**：
- 返回None或抛出异常

**断言代码**：
```python
assert selected_method is None or raises(NoAvailableMethodError)
```

---

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_calculator.py`

#### 测试用例4.1：method_b计算正确性

**测试ID**：`test_calculate_method_b_correctness`
**测试目的**：验证method_b计算公式正确
**前置条件**：
- method_b参数已配置（P_atm=0.101325, rho=1000, g=9.81）

**测试步骤**：
1. 创建包含pool_liquid_level的测试数据（h=5.0 m）
2. 创建Calculator实例（method_b）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_in = 0.101325 + 1000 × 9.81 × 5.0 / 1e6 = 0.150375 MPa

**断言代码**：
```python
assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(0.150375, rel=1e-6)
```

---

#### 测试用例4.2：PIN_COEF_V1计算正确性

**测试ID**：`test_calculate_pin_coef_v1_correctness`
**测试目的**：验证PIN_COEF_V1计算公式正确
**前置条件**：
- PIN_COEF_V1参数已配置（b0, b1, b2, b3）

**测试步骤**：
1. 创建包含pool_liquid_level的测试数据（h=5.0 m）
2. 创建Calculator实例（PIN_COEF_V1）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_in = b0 + b1×h + b2×h² + b3×h³

**断言代码**：
```python
expected = b0 + b1*5.0 + b2*25.0 + b3*125.0
assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(expected, rel=1e-6)
```

---

#### 测试用例4.3：零液位处理

**测试ID**：`test_calculate_zero_level`
**测试目的**：验证零液位时的计算
**前置条件**：pool_liquid_level=0

**测试步骤**：
1. 创建pool_liquid_level=0的测试数据
2. 创建Calculator实例（method_b）
3. 调用calculate方法
4. 验证计算结果

**预期结果**：
- P_in = P_atm = 0.101325 MPa

**断言代码**：
```python
assert result_df.loc[0, 'main_pipeline_inlet_pressure'] == pytest.approx(0.101325, rel=1e-6)
```

---

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_validator.py`

#### 测试用例5.1：范围验证

**测试ID**：`test_validate_range`
**测试目的**：验证Validator能正确验证压力范围
**前置条件**：
- 验证参数已配置（min_pressure=0.0, max_pressure=1.0 MPa）

**测试步骤**：
1. 创建包含不同压力值的测试数据（-0.1, 0.0, 0.5, 1.0, 1.5 MPa）
2. 创建Validator实例
3. 调用validate方法
4. 验证范围标记

**预期结果**：
- -0.1 MPa: valid_range=False
- 0.0 MPa: valid_range=True
- 0.5 MPa: valid_range=True
- 1.0 MPa: valid_range=True
- 1.5 MPa: valid_range=False

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
**测试目的**：验证Validator能正确验证物理约束
**前置条件**：
- pool_liquid_level数据可用
- physics_tolerance参数已配置

**测试步骤**：
1. 创建包含pool_liquid_level和main_pipeline_inlet_pressure的测试数据
2. 创建Validator实例
3. 调用validate方法
4. 验证物理约束标记

**预期结果**：
- P_in ≈ P_atm + ρ×g×h/1e6（误差<10%）: valid_physics=True
- 偏差>10%: valid_physics=False

**断言代码**：
```python
assert result_df.loc[0, 'valid_physics'] == True
assert result_df.loc[1, 'valid_physics'] == False
```

---

#### 测试用例5.3：压力变化率验证

**测试ID**：`test_validate_change_rate`
**测试目的**：验证Validator能正确验证压力变化率
**前置条件**：
- max_pressure_change_rate参数已配置（0.1 MPa/s）

**测试步骤**：
1. 创建包含时间序列压力数据的测试数据
2. 创建Validator实例
3. 调用validate方法
4. 验证变化率标记

**预期结果**：
- 变化率<0.1 MPa/s: valid_change_rate=True
- 变化率>0.1 MPa/s: valid_change_rate=False

**断言代码**：
```python
assert result_df.loc[0, 'valid_change_rate'] == True
assert result_df.loc[1, 'valid_change_rate'] == False
```

---

### 测试文件：`tests/unit/metrics/main_pipeline_inlet_pressure/test_pipeline.py`

#### 测试用例6.1：完整流程

**测试ID**：`test_pipeline_complete_flow`
**测试目的**：验证Pipeline能正确执行完整流程
**前置条件**：
- 所有组件已实现
- 测试数据已准备

**测试步骤**：
1. 创建Pipeline实例
2. 调用run方法
3. 验证返回结果

**预期结果**：
- 返回DataFrame包含main_pipeline_inlet_pressure列
- 数据量 > 0
- 所有值在合理范围

**断言代码**：
```python
assert 'main_pipeline_inlet_pressure' in result_df.columns
assert len(result_df) > 0
assert result_df['main_pipeline_inlet_pressure'].between(0, 1).all()
```

---

## 集成测试用例

### 测试文件：`tests/integration/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_integration.py`

#### 测试用例7.1：单设备完整流程

**测试ID**：`test_single_device_integration`
**测试目的**：验证device_id=7的完整计算流程
**前置条件**：
- pool_liquid_level数据存在（device_id=8）
- 数据库连接正常

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程（device_id=7）
3. 验证结果
4. 验证数据库写入

**预期结果**：
- 计算结果正确
- 数据已写入fact_measurements表（metric_id=61, device_id=7）

**断言代码**：
```python
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
```

---

#### 测试用例7.2：参数加载集成

**测试ID**：`test_parameter_loading_integration`
**测试目的**：验证参数加载的完整流程
**前置条件**：
- calculation_parameters表有数据

**测试步骤**：
1. 创建Pipeline实例
2. 验证参数加载
3. 验证参数值正确

**预期结果**：
- 所有参数正确加载
- 参数值符合预期

**断言代码**：
```python
assert 'P_atm' in params
assert params['P_atm'] == 0.101325
assert 'rho' in params
assert params['rho'] == 1000.0
```

---

#### 测试用例7.3：数据写入集成

**测试ID**：`test_data_write_integration`
**测试目的**：验证数据写入的完整流程
**前置条件**：
- 数据库连接正常
- 有计算结果

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程
3. 验证数据写入
4. 验证数据完整性

**预期结果**：
- 数据成功写入
- 写入记录数=计算记录数
- 数据值正确

**断言代码**：
```python
with get_connection() as conn:
    cur = conn.execute(
        "SELECT COUNT(*) FROM fact_measurements WHERE metric_id=61 AND device_id=7"
    )
    count = cur.fetchone()[0]
    assert count == len(result_df)
```

---

#### 测试用例7.4：跨设备数据依赖

**测试ID**：`test_cross_device_dependency`
**测试目的**：验证跨设备数据依赖（device_id=7依赖device_id=8）
**前置条件**：
- pool_liquid_level数据存在（device_id=8）

**测试步骤**：
1. 创建Pipeline实例
2. 运行完整流程（device_id=7）
3. 验证正确加载device_id=8的数据

**预期结果**：
- 正确加载device_id=8的pool_liquid_level数据
- 计算结果正确

**断言代码**：
```python
assert 'pool_liquid_level' in loaded_data.columns
assert loaded_data['device_id'].unique() == [8]
assert len(result_df) > 0
```

---

## 性能测试用例

### 测试文件：`tests/performance/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_performance.py`

#### 测试用例8.1：大数据量性能测试

**测试ID**：`test_large_dataset_performance`
**测试目的**：验证大数据量下的计算性能
**前置条件**：
- 完整时间范围的数据（约84,000条）

**测试步骤**：
1. 创建Pipeline实例
2. 记录开始时间
3. 运行完整流程
4. 记录结束时间
5. 计算耗时和吞吐量

**预期结果**：
- 总耗时 < 30秒
- 吞吐量 > 2000条/秒

**断言代码**：
```python
assert elapsed_time < 30.0
throughput = len(result_df) / elapsed_time
assert throughput > 2000
```

---

#### 测试用例8.2：批量写入性能测试

**测试ID**：`test_batch_write_performance`
**测试目的**：验证批量写入性能
**前置条件**：
- 有计算结果

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
**前置条件**：
- 完整时间范围的数据

**测试步骤**：
1. 记录初始内存
2. 创建Pipeline实例
3. 运行完整流程
4. 记录峰值内存
5. 计算内存增量

**预期结果**：
- 内存增量 < 1GB

**断言代码**：
```python
assert memory_increase < 1 * 1024 * 1024 * 1024  # 1GB
```

---

## 边界测试用例

### 测试文件：`tests/boundary/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_boundary.py`

#### 测试用例9.1：零液位处理

**测试ID**：`test_zero_level`
**测试目的**：验证零液位时的处理
**前置条件**：pool_liquid_level=0

**测试步骤**：
1. 创建pool_liquid_level=0的测试数据
2. 运行完整流程
3. 验证结果

**预期结果**：
- P_in = P_atm = 0.101325 MPa
- 不抛出异常

**断言代码**：
```python
assert result_df['main_pipeline_inlet_pressure'].iloc[0] == pytest.approx(0.101325, rel=1e-6)
```

---

#### 测试用例9.2：极大液位处理

**测试ID**：`test_extreme_level`
**测试目的**：验证极大液位时的处理
**前置条件**：pool_liquid_level=10 m（接近最大值）

**测试步骤**：
1. 创建pool_liquid_level=10的测试数据
2. 运行完整流程
3. 验证结果

**预期结果**：
- P_in = 0.101325 + 1000×9.81×10/1e6 = 0.199425 MPa
- 不抛出异常

**断言代码**：
```python
assert result_df['main_pipeline_inlet_pressure'].iloc[0] == pytest.approx(0.199425, rel=1e-6)
```

---

#### 测试用例9.3：缺失数据处理

**测试ID**：`test_missing_data`
**测试目的**：验证缺失数据时的处理
**前置条件**：pool_liquid_level数据缺失

**测试步骤**：
1. 模拟pool_liquid_level数据缺失
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

### 测试文件：`tests/regression/metrics/main_pipeline_inlet_pressure/test_main_pipeline_inlet_pressure_regression.py`

#### 测试用例10.1：与现有系统对比

**测试ID**：`test_regression_comparison`
**测试目的**：验证新实现与现有系统的一致性
**前置条件**：
- 现有系统有main_pipeline_inlet_pressure数据
- 新实现已完成

**测试步骤**：
1. 从现有系统获取main_pipeline_inlet_pressure数据
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
| 单元测试 | 6个 | 16 | DataLoader, DataFilter, MethodSelector, Calculator, Validator, Pipeline |
| 集成测试 | 1个 | 4 | 完整流程, 参数加载, 数据写入, 跨设备依赖 |
| 性能测试 | 1个 | 3 | 计算性能, 写入性能, 内存使用 |
| 边界测试 | 1个 | 3 | 零液位, 极大液位, 缺失数据 |
| 回归测试 | 1个 | 1 | 与现有系统对比 |
| **总计** | **10个** | **27** | **全覆盖** |

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

