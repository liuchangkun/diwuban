# pump_flow_rate 重构未完成工作实施计划

> **计划日期**: 2025-11-15  
> **计划模式**: RIPER-5 协议 - 计划模式  
> **基于**: 研究模式发现 + 用户明确指示  
> **版本**: v1.0

---

## 📋 计划模式初始化确认

### 已读取规则文档
- ✅ 规则/模式模块/规则-模式3-计划.md
- ✅ .memory/规则层/编码规范.md (1406行)
- ✅ .memory/规则层/数据库规范.md (825行)

### 核心规则摘要
1. **文件大小限制**: 单文件不超过600行 [强制]
2. **代码占位符**: 禁止使用TODO/FIXME (除非计划明确说明) [强制]
3. **SQL参数化**: 必须使用参数化查询 [强制]
4. **日志中文化**: 所有日志必须使用中文 [强制]
5. **测试覆盖率**: 单元测试覆盖率 ≥ 80% [强制]
6. **连接池使用**: 必须使用 get_connection() 上下文管理器 [强制]

---

## 🎯 用户明确指示

### 任务1: 修复硬编码 station_id 问题 🔴 高优先级
- **要求**: 立即修复 scheduler.py 中的硬编码 station_id 问题
- **当前问题**: `_get_station_id()` 方法硬编码返回 1
- **解决方案**: 从 dim_devices 表查询设备所属泵站

### 任务2: 删除 calculation_logs 表 🟡 中优先级
- **要求**: 当前的文件日志已经足够，删除这个表
- **影响范围**: 
  - 删除数据库表和分区
  - 删除相关的 TODO 注释
  - 删除迁移脚本

### 任务3: 测试覆盖率提升到 100% 🟡 中优先级
- **要求**: 直接进入执行模式，开始实现测试
- **当前覆盖率**: 43%
- **目标覆盖率**: 100%
- **工作量**: 
  - 实现现有5个测试文件中的25个 TODO
  - 创建缺失的6个测试文件

---

## 📊 数据库表结构验证

### dim_devices 表结构
```
id                   bigint               NOT NULL
station_id           bigint               NOT NULL  ← 需要查询的字段
name                 text                 NOT NULL
type                 text                 NOT NULL
pump_type            text                 NULL
extra                jsonb                NULL
created_at           timestamp with time zone NULL
is_active            boolean              NOT NULL
```

**验证结果**: ✅ station_id 字段存在，可以直接查询

---

## 📝 详细更改计划

### 更改1: 修复 scheduler.py 中的硬编码 station_id

**文件**: `app/services/calculation/shared/scheduler.py`

**理由**: 
- 当前硬编码返回 station_id=1，多泵站场景下会导致数据错误
- 违反项目规则：禁止硬编码值

**具体更改**:
1. 修改 `_get_station_id(device_id: int) -> int` 方法
2. 添加数据库查询逻辑，从 dim_devices 表查询 station_id
3. 添加缓存机制，避免重复查询
4. 添加错误处理，如果设备不存在则抛出异常
5. 删除 TODO 注释

**涉及的函数/类**:
- `Scheduler._get_station_id(device_id: int) -> int`

**依赖关系**:
- 依赖: dim_devices 表（已存在）
- 影响: 所有调用 `_get_station_id()` 的地方（当前只有内部使用）

**错误处理**:
- 设备不存在: 抛出 ValueError
- 数据库查询失败: 记录错误日志并抛出 DatabaseError

---

### 更改2: 删除 calculation_logs 表及相关代码

**文件**:
1. `app/services/calculation/shared/logging_helper.py` (删除 TODO 注释)
2. `缺失指标计算改造/pump_flow_rate/migrations/001_create_calculation_logs.sql` (标记为废弃)
3. `缺失指标计算改造/pump_flow_rate/migrations/001_rollback_calculation_logs.sql` (执行回滚)

**理由**:
- 用户明确表示文件日志已经足够
- calculation_logs 表已创建但从未使用
- 删除未使用的表可以简化系统

**具体更改**:
1. 执行回滚脚本删除 calculation_logs 表
2. 删除 logging_helper.py 中的 TODO 注释和 `_write_to_database()` 方法
3. 在迁移脚本中添加废弃标记

**涉及的函数/类**:
- `CalculationLogger._write_to_database()` (删除整个方法)

**依赖关系**:
- 无依赖（表从未被使用）
- 无影响（删除后不影响任何功能）

---

### 更改3: 实现所有测试文件

**文件**: 11个测试文件（5个现有 + 6个新建）

**理由**:
- 当前测试覆盖率仅 43%，远低于 80% 的目标
- 用户要求达到 100% 覆盖率
- 所有现有测试文件只有框架，没有实际测试逻辑

**具体更改**:

#### 3.1 实现现有测试文件 (5个文件, 25个 TODO)

1. **tests/services/calculation/shared/test_scheduler.py** (5个测试)
   - test_create_tasks_single_device
   - test_create_tasks_multiple_devices
   - test_create_tasks_time_chunking
   - test_execute_tasks_parallel
   - test_execute_tasks_with_errors

2. **tests/services/calculation/metrics/pump_flow_rate/test_data_loader.py** (3个测试)
   - test_load_data_success
   - test_load_data_with_running_status
   - test_load_data_empty_result

3. **tests/services/calculation/metrics/pump_flow_rate/test_methods.py** (7个测试)
   - test_method_a_power_frequency_weight
   - test_method_b_cumulative_derivative
   - test_method_c_direct_reading
   - test_method_d_power_weight
   - test_method_e_frequency_weight
   - test_method_f_regression
   - test_methods_with_zero_values

4. **tests/services/calculation/metrics/pump_flow_rate/test_pipeline.py** (4个测试)
   - test_pipeline_execute_success
   - test_pipeline_execute_with_invalid_device
   - test_pipeline_execute_with_no_data
   - test_pipeline_execute_with_all_methods

5. **tests/services/calculation/test_integration.py** (6个测试)
   - 实现所有 TODO 测试

#### 3.2 创建缺失的测试文件 (6个文件)

1. **tests/services/calculation/shared/test_data_writer.py**
   - test_write_success
   - test_write_empty_data
   - test_write_batch_size_adaptation
   - test_write_duplicate_handling

2. **tests/services/calculation/shared/test_parameter_manager.py**
   - test_get_parameters_global
   - test_get_parameters_station_override
   - test_get_parameters_device_override
   - test_get_parameters_cache
   - test_get_parameters_not_found
   - test_get_parameters_invalid_metric

3. **tests/services/calculation/metrics/pump_flow_rate/test_data_filter.py**
   - test_filter_stopped_devices
   - test_filter_nan_inf
   - test_filter_negative_values
   - test_filter_outliers
   - test_filter_empty_data

4. **tests/services/calculation/metrics/pump_flow_rate/test_method_selector.py**
   - test_select_method_a
   - test_select_method_c
   - test_select_method_d
   - test_select_method_e
   - test_select_no_suitable_method

5. **tests/services/calculation/metrics/pump_flow_rate/test_calculator.py**
   - test_calculate_success
   - test_calculate_invalid_method
   - test_calculate_missing_parameters

6. **tests/services/calculation/metrics/pump_flow_rate/test_validator.py**
   - test_validate_success
   - test_validate_nan_values
   - test_validate_negative_values
   - test_validate_outliers

---

## ✅ 实施检查清单

### 阶段1: 修复硬编码 station_id (预计30分钟)

1. ✅ 读取 `app/services/calculation/shared/scheduler.py` 文件，定位 `_get_station_id()` 方法
2. ✅ 修改 `_get_station_id()` 方法，添加数据库查询逻辑
3. ✅ 添加缓存机制（使用 `@lru_cache` 或实例变量）
4. ✅ 添加错误处理（设备不存在、数据库查询失败）
5. ✅ 删除 TODO 注释
6. ✅ 运行测试验证修改正确性

### 阶段2: 删除 calculation_logs 表 (预计20分钟)

7. ✅ 执行回滚脚本 `缺失指标计算改造/pump_flow_rate/migrations/001_rollback_calculation_logs.sql`
8. ✅ 验证表已删除
9. ✅ 修改 `app/services/calculation/shared/logging_helper.py`，删除 `_write_to_database()` 方法
10. ✅ 删除 logging_helper.py 中的 TODO 注释
11. ✅ 在迁移脚本中添加废弃标记

### 阶段3: 实现测试文件 (预计8小时)

#### 3.1 实现 test_scheduler.py (5个测试, 1小时)
12. ✅ 实现 test_create_tasks_single_device
13. ✅ 实现 test_create_tasks_multiple_devices
14. ✅ 实现 test_create_tasks_time_chunking
15. ✅ 实现 test_execute_tasks_parallel
16. ✅ 实现 test_execute_tasks_with_errors

#### 3.2 创建 test_data_writer.py (4个测试, 1小时)
17. ✅ 创建测试文件
18. ✅ 实现 test_write_success
19. ✅ 实现 test_write_empty_data
20. ✅ 实现 test_write_batch_size_adaptation
21. ✅ 实现 test_write_duplicate_handling

#### 3.3 创建 test_parameter_manager.py (6个测试, 1小时)
22. ✅ 创建测试文件
23. ✅ 实现 test_get_parameters_global
24. ✅ 实现 test_get_parameters_station_override
25. ✅ 实现 test_get_parameters_device_override
26. ✅ 实现 test_get_parameters_cache
27. ✅ 实现 test_get_parameters_not_found
28. ✅ 实现 test_get_parameters_invalid_metric

#### 3.4 实现 test_data_loader.py (3个测试, 30分钟)
29. ✅ 实现 test_load_data_success
30. ✅ 实现 test_load_data_with_running_status
31. ✅ 实现 test_load_data_empty_result

#### 3.5 创建 test_data_filter.py (5个测试, 1小时)
32. ✅ 创建测试文件
33. ✅ 实现 test_filter_stopped_devices
34. ✅ 实现 test_filter_nan_inf
35. ✅ 实现 test_filter_negative_values
36. ✅ 实现 test_filter_outliers
37. ✅ 实现 test_filter_empty_data

#### 3.6 创建 test_method_selector.py (5个测试, 1小时)
38. ✅ 创建测试文件
39. ✅ 实现 test_select_method_a
40. ✅ 实现 test_select_method_c
41. ✅ 实现 test_select_method_d
42. ✅ 实现 test_select_method_e
43. ✅ 实现 test_select_no_suitable_method

#### 3.7 创建 test_calculator.py (3个测试, 30分钟)
44. ✅ 创建测试文件
45. ✅ 实现 test_calculate_success
46. ✅ 实现 test_calculate_invalid_method
47. ✅ 实现 test_calculate_missing_parameters

#### 3.8 创建 test_validator.py (4个测试, 1小时)
48. ✅ 创建测试文件
49. ✅ 实现 test_validate_success
50. ✅ 实现 test_validate_nan_values
51. ✅ 实现 test_validate_negative_values
52. ✅ 实现 test_validate_outliers

#### 3.9 实现 test_methods.py (7个测试, 1小时)
53. ✅ 实现 test_method_a_power_frequency_weight
54. ✅ 实现 test_method_b_cumulative_derivative
55. ✅ 实现 test_method_c_direct_reading
56. ✅ 实现 test_method_d_power_weight
57. ✅ 实现 test_method_e_frequency_weight
58. ✅ 实现 test_method_f_regression
59. ✅ 实现 test_methods_with_zero_values

#### 3.10 实现 test_pipeline.py (4个测试, 30分钟)
60. ✅ 实现 test_pipeline_execute_success
61. ✅ 实现 test_pipeline_execute_with_invalid_device
62. ✅ 实现 test_pipeline_execute_with_no_data
63. ✅ 实现 test_pipeline_execute_with_all_methods

#### 3.11 实现 test_integration.py (6个测试, 30分钟)
64. ✅ 实现所有 TODO 测试

### 阶段4: 验证和测试 (预计30分钟)

65. ✅ 运行所有测试: `pytest tests/services/calculation/ -v`
66. ✅ 检查测试覆盖率: `pytest tests/services/calculation/ --cov=app/services/calculation --cov-report=term-missing`
67. ✅ 验证覆盖率达到 100%
68. ✅ 运行完整的端到端测试: `python scripts/tools/run_pump_flow_rate_new_architecture.py`
69. ✅ 检查日志输出，确认所有功能正常

---

**计划模式完成，准备进入执行模式**

