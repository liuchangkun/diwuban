# pump_inlet_pressure 计算方法详细分析报告

**生成时间**：2025-10-31 01:30  
**分析对象**：pump_inlet_pressure 指标的所有已注册计算方法  
**目标设备**：device_id=1-6（设备类型：pump）  
**当前状态**：pump_inlet_pressure 在数据库中有 0 条计算结果  

---

## 📋 执行摘要

**关键发现**：
1. ✅ pump_inlet_pressure 已成功注册 2 个计算方法（method_a 和 method_b）
2. ❌ 两个方法都无法在 device_id=1-6 上成功计算
3. 🔄 存在循环依赖：pump_inlet_pressure ↔ main_pipeline_inlet_pressure
4. 📊 device_id=1-6 上有 11 个可用的实测指标（100% 数据完整性）

**根本原因**：
- **method_b** 依赖 `pool_liquid_level`，但该数据只在 device_id=8 上存在，device_id=1-6 上完全缺失
- **method_a** 依赖 `main_pipeline_inlet_pressure`，但该指标本身也依赖 `pump_inlet_pressure`，形成循环依赖

**推荐解决方案**：
- **方案A**（推荐）：修改数据映射，使 pool_liquid_level 对所有 pump 设备可用
- **方案B**（备选）：添加一个基于实测数据的新方法（如使用 pump_outlet_pressure 反推）
- **方案C**（兜底）：添加一个使用固定估算值的方法

---

## 📊 方法基本信息汇总

| method_id | method_name | method_code | priority | dependencies | allowed_device_types | accuracy_level | is_enabled |
|-----------|-------------|-------------|----------|--------------|---------------------|----------------|------------|
| pump_inlet_pressure_method_b | 从水池液位推算 | B | 100 | {pool_liquid_level} | {pump} | high | true |
| pump_inlet_pressure_method_a | 使用总管进口压力代替 | A | 90 | {main_pipeline_inlet_pressure} | {pump} | medium | true |

---

## 🔍 方法分析：pump_inlet_pressure_method_b

### 基本信息
- **方法ID**：pump_inlet_pressure_method_b
- **方法名称**：从水池液位推算
- **方法代码**：B
- **优先级**：100（最高）
- **允许设备类型**：{pump}
- **准确度等级**：high
- **启用状态**：true
- **计算公式**：P_in = P_atm + ρ × g × L / 1e6

### 依赖指标分析

#### 依赖指标1：pool_liquid_level

**数据来源**：实测数据（水池液位传感器）

**数据分布（device_id=1-6）**：
```
查询结果：0 行记录
```

| device_id | total_count | non_null_count | null_count | min | max | avg | 数据可用性 |
|-----------|-------------|----------------|------------|-----|-----|-----|----------|
| 1         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 2         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 3         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 4         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 5         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 6         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |

**数据样本**：
```
查询结果：0 行记录（无可用数据）
```

**补充信息**：
- pool_liquid_level 在 device_id=8 上有 7200 条记录（100% 完整性）
- 数值范围：3.559 ~ 3.593 米
- 这说明 pool_liquid_level 是泵站级别的数据，不是设备级别的数据

**数据可用性**：❌ **不可用**
- device_id=1-6 上完全没有 pool_liquid_level 数据
- 依赖检查失败，方法无法使用

### 可用性结论
- **状态**：❌ **不可用**
- **原因**：依赖指标 pool_liquid_level 在目标设备（device_id=1-6）上完全缺失
- **影响设备**：device_id=1, 2, 3, 4, 5, 6（所有 pump 类型设备）

### 失败原因
- **根本原因**：数据映射配置问题
  - pool_liquid_level 是泵站级别的数据（存储在 device_id=8）
  - 但 pump_inlet_pressure 需要在设备级别计算（device_id=1-6）
  - 当前数据映射没有将泵站级别的 pool_liquid_level 复制到各个泵设备
- **缺失数据**：pool_liquid_level（device_id=1-6）
- **建议解决方案**：
  1. **修改数据映射配置**：在 `configs/data_mapping.v2.json` 中，将 pool_liquid_level 映射到所有 pump 设备
  2. **修改 ETL 逻辑**：在数据导入阶段，将 device_id=8 的 pool_liquid_level 复制到 device_id=1-6
  3. **修改方法依赖**：改为从 device_id=8 查询 pool_liquid_level（需要修改计算逻辑）

---

## 🔍 方法分析：pump_inlet_pressure_method_a

### 基本信息
- **方法ID**：pump_inlet_pressure_method_a
- **方法名称**：使用总管进口压力代替
- **方法代码**：A
- **优先级**：90
- **允许设备类型**：{pump}
- **准确度等级**：medium
- **启用状态**：true
- **计算假设**：假设泵进口与总管进口压力相近（并联系统）

### 依赖指标分析

#### 依赖指标1：main_pipeline_inlet_pressure

**数据来源**：计算数据（依赖其他指标计算得出）

**数据分布（device_id=1-6）**：
```
查询结果：0 行记录
```

| device_id | total_count | non_null_count | null_count | min | max | avg | 数据可用性 |
|-----------|-------------|----------------|------------|-----|-----|-----|----------|
| 1         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 2         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 3         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 4         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 5         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |
| 6         | 0           | 0              | 0          | -   | -   | -   | ❌ 无数据 |

**数据样本**：
```
查询结果：0 行记录（无可用数据）
```

**补充信息**：
- main_pipeline_inlet_pressure 是计算指标，不是实测数据
- 该指标应该在 device_id=7（main_pipeline 类型设备）上计算
- device_id=1-6 是 pump 类型设备，不应该有 main_pipeline_inlet_pressure 数据

**数据可用性**：❌ **不可用**
- device_id=1-6 上完全没有 main_pipeline_inlet_pressure 数据
- 依赖检查失败，方法无法使用

### 循环依赖检测

**main_pipeline_inlet_pressure 的计算方法**：

| method_id | method_name | priority | dependencies | allowed_device_types |
|-----------|-------------|----------|--------------|---------------------|
| PIN_COEF_V1 | 综合计算（新版） | 110 | {pump_inlet_pressure, pool_liquid_level} | {main_pipeline} |
| main_pipeline_inlet_pressure_method_a | 由泵进口压力直接近似 | 100 | {pump_inlet_pressure} | {main_pipeline} |
| main_pipeline_inlet_pressure_method_b | 由水池液位推算 | 90 | {pool_liquid_level} | {main_pipeline} |

**循环依赖确认**：✅ **存在循环依赖**

**依赖链分析**：
```
pump_inlet_pressure (method_a, device_id=1-6)
  ↓ 依赖
main_pipeline_inlet_pressure (device_id=7)
  ↓ 依赖 (PIN_COEF_V1 和 method_a)
pump_inlet_pressure (device_id=1-6)
  ↓ 循环！
```

**循环依赖说明**：
1. pump_inlet_pressure 的 method_a 依赖 main_pipeline_inlet_pressure
2. main_pipeline_inlet_pressure 的 PIN_COEF_V1（优先级最高）依赖 pump_inlet_pressure
3. main_pipeline_inlet_pressure 的 method_a（优先级第二）也依赖 pump_inlet_pressure
4. 形成死锁：两个指标互相依赖，都无法计算

### 可用性结论
- **状态**：❌ **不可用**
- **原因**：
  1. 依赖指标 main_pipeline_inlet_pressure 在目标设备（device_id=1-6）上完全缺失
  2. 存在循环依赖：pump_inlet_pressure ↔ main_pipeline_inlet_pressure
- **影响设备**：device_id=1, 2, 3, 4, 5, 6（所有 pump 类型设备）

### 失败原因
- **根本原因**：循环依赖 + 设备类型不匹配
  - main_pipeline_inlet_pressure 应该在 device_id=7（main_pipeline 类型）上计算
  - 但 pump_inlet_pressure 需要在 device_id=1-6（pump 类型）上计算
  - 两个指标互相依赖，形成死锁
- **缺失数据**：main_pipeline_inlet_pressure（device_id=1-6）
- **建议解决方案**：
  1. **打破循环依赖**：修改 main_pipeline_inlet_pressure 的方法，不依赖 pump_inlet_pressure
  2. **跨设备查询**：修改计算逻辑，允许从 device_id=7 查询 main_pipeline_inlet_pressure
  3. **放弃此方法**：使用其他不依赖 main_pipeline_inlet_pressure 的方法

---

## 📊 可用实测数据汇总（device_id=1-6）

以下是 device_id=1-6 上所有可用的实测指标（非空数据量 > 1000）：

| metric_key | total_count | non_null_count | non_null_percentage | 数据质量 |
|------------|-------------|----------------|---------------------|---------|
| pump_voltage_c | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_power_factor | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_voltage_a | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_voltage_b | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_active_power | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_current_a | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_current_b | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_current_c | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_frequency | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_kwh | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_outlet_pressure | 43200 | 43200 | 100.00% | ✅ 优秀 |
| pump_cumulative_flow | 4155 | 4155 | 100.00% | ✅ 优秀（部分设备）|
| pump_flow_rate | 4155 | 4155 | 100.00% | ✅ 优秀（部分设备）|
| pump_speed | 4155 | 4155 | 100.00% | ✅ 优秀（部分设备）|
| pump_torque | 4155 | 4155 | 100.00% | ✅ 优秀（部分设备）|

**关键观察**：
- ✅ 有 11 个实测指标，数据完整性 100%
- ✅ pump_outlet_pressure（泵出口压力）数据完整，可用于反推进口压力
- ✅ pump_active_power、pump_frequency 等电气参数完整
- ⚠️ 缺少直接的压力测量数据（pump_inlet_pressure）

---

## 🎯 替代方案探索

基于可用的实测数据，以下是可行的替代计算方法：

### 方案1：基于 pump_outlet_pressure 反推（推荐）

**原理**：
- 已知：pump_outlet_pressure（泵出口压力）
- 已知：pump_head（泵扬程，可计算）
- 公式：pump_inlet_pressure = pump_outlet_pressure - pump_head

**可行性**：✅ **高**
- pump_outlet_pressure 数据完整（43200 条，100%）
- pump_head 可以通过其他方法计算（如 HEAD_COEF_V1）
- 物理原理正确，准确度高

**实施步骤**：
1. 添加新方法 `pump_inlet_pressure_method_c`
2. 依赖：{pump_outlet_pressure, pump_head}
3. 优先级：95（介于 method_a 和 method_b 之间）
4. 公式：P_in = P_out - H

**潜在问题**：
- pump_head 本身也依赖 pump_inlet_pressure（循环依赖）
- 需要先解决 pump_head 的计算问题

### 方案2：修改数据映射，使 pool_liquid_level 对所有设备可用（推荐）

**原理**：
- pool_liquid_level 是泵站级别的数据，应该对所有泵设备可用
- 当前只在 device_id=8 上有数据，需要复制到 device_id=1-6

**可行性**：✅ **高**
- pool_liquid_level 数据完整（7200 条，100%）
- 只需修改数据映射配置，无需修改计算逻辑
- method_b 可以直接使用，准确度高

**实施步骤**：
1. 检查 `configs/data_mapping.v2.json`
2. 修改 pool_liquid_level 的映射配置
3. 重新运行 ETL 流程
4. 验证 device_id=1-6 上有 pool_liquid_level 数据

**预期效果**：
- method_b 可以成功计算
- pump_inlet_pressure 有数据
- 依赖链恢复

### 方案3：使用固定估算值（兜底方案）

**原理**：
- 使用经验值或固定值估算 pump_inlet_pressure
- 例如：P_in = P_atm + 0.03 MPa（假设水池液位约3米）

**可行性**：⚠️ **中**
- 不依赖任何其他指标，一定可以计算
- 准确度低，仅作为兜底方案

**实施步骤**：
1. 添加新方法 `pump_inlet_pressure_method_fallback`
2. 依赖：[]（无依赖）
3. 优先级：50（最低）
4. 公式：P_in = 0.101325 + 0.03（MPa）

**预期效果**：
- 保证 pump_inlet_pressure 一定有值
- 下游指标可以计算
- 但准确度低，仅用于应急

---

## 📋 最终汇总

### 方法可用性汇总表

| method_id | priority | 依赖指标 | 可用性 | 失败原因 | 影响设备 |
|-----------|----------|---------|--------|---------|---------|
| pump_inlet_pressure_method_b | 100 | pool_liquid_level | ❌ 不可用 | 依赖数据在 device_id=1-6 上完全缺失 | 1,2,3,4,5,6 |
| pump_inlet_pressure_method_a | 90 | main_pipeline_inlet_pressure | ❌ 不可用 | 循环依赖 + 依赖数据缺失 | 1,2,3,4,5,6 |

### 根本原因总结

**为什么所有方法都失败了？**
1. **method_b**：依赖 pool_liquid_level，但该数据只在 device_id=8 上存在，device_id=1-6 上完全缺失
2. **method_a**：依赖 main_pipeline_inlet_pressure，但该指标本身也依赖 pump_inlet_pressure，形成循环依赖

**哪些数据缺失是关键瓶颈？**
- **pool_liquid_level**（device_id=1-6）：method_b 的关键依赖
- **main_pipeline_inlet_pressure**（device_id=1-6）：method_a 的关键依赖（但存在循环依赖）

**是否存在循环依赖？**
- ✅ **是**：pump_inlet_pressure ↔ main_pipeline_inlet_pressure

---

## 🎯 可行的解决方案（按优先级排序）

### 方案A：修改数据映射，使 pool_liquid_level 对所有 pump 设备可用

**描述**：
- 修改 `configs/data_mapping.v2.json`，将 pool_liquid_level 映射到 device_id=1-6
- 或修改 ETL 逻辑，在数据导入阶段将 device_id=8 的 pool_liquid_level 复制到 device_id=1-6

**可行性**：✅ **高**
- pool_liquid_level 数据完整（7200 条，100%）
- 只需修改配置，无需修改计算逻辑
- method_b 可以直接使用

**预期效果**：
- method_b 成功计算
- pump_inlet_pressure 有数据（准确度：high）
- 依赖链恢复：pump_head、pump_efficiency 可以计算

**实施难度**：⭐⭐（中等）

**推荐指数**：⭐⭐⭐⭐⭐（强烈推荐）

---

### 方案B：添加基于 pump_outlet_pressure 的新方法

**描述**：
- 添加新方法 `pump_inlet_pressure_method_c`
- 依赖：{pump_outlet_pressure}（假设扬程为固定值或经验值）
- 公式：P_in = P_out - H_estimated

**可行性**：⚠️ **中**
- pump_outlet_pressure 数据完整
- 但需要估算扬程，准确度降低
- 如果依赖 pump_head，会再次遇到循环依赖

**预期效果**：
- pump_inlet_pressure 有数据（准确度：medium）
- 依赖链部分恢复

**实施难度**：⭐⭐⭐（较高）

**推荐指数**：⭐⭐⭐（备选方案）

---

### 方案C：添加使用固定估算值的兜底方法

**描述**：
- 添加新方法 `pump_inlet_pressure_method_fallback`
- 依赖：[]（无依赖）
- 公式：P_in = 0.101325 + 0.03（MPa）

**可行性**：✅ **高**
- 不依赖任何数据，一定可以计算
- 准确度低，仅作为兜底方案

**预期效果**：
- pump_inlet_pressure 一定有值（准确度：low）
- 下游指标可以计算，但准确度受影响

**实施难度**：⭐（简单）

**推荐指数**：⭐⭐（仅作为兜底）

---

## 🏆 推荐方案

**推荐方案**：**方案A - 修改数据映射，使 pool_liquid_level 对所有 pump 设备可用**

**理由**：
1. ✅ **可行性高**：pool_liquid_level 数据完整，只需修改配置
2. ✅ **准确度高**：method_b 使用物理公式计算，准确度等级为 high
3. ✅ **实施简单**：无需修改代码，只需修改配置文件
4. ✅ **效果显著**：可以立即解决 pump_inlet_pressure 的计算问题，恢复依赖链
5. ✅ **符合业务逻辑**：pool_liquid_level 本来就是泵站级别的数据，应该对所有泵设备可用

**实施步骤**：
1. 检查 `configs/data_mapping.v2.json`，确认 pool_liquid_level 的映射配置
2. 修改映射配置，将 pool_liquid_level 映射到 device_id=1-6
3. 重新运行 `python -m app.cli.main run-all configs/data_mapping.v2.json`
4. 验证 pump_inlet_pressure 是否成功计算
5. 验证依赖链是否恢复（pump_head、pump_efficiency）

**预期结果**：
- pump_inlet_pressure 成功计算（device_id=1-6，每个设备 7200 条数据）
- pump_head 成功计算（依赖链恢复）
- pump_efficiency 成功计算（依赖链恢复）
- device_id=3 和 5 的计算错误大幅减少

---

**报告结束**

