# pump_inlet_pressure 方法注册后深度分析报告

**生成时间**：2025-10-31 00:52:52  
**执行命令**：`python -m app.cli.main run-all configs/data_mapping.v2.json`  
**总耗时**：161.67秒  
**分析重点**：device_id=3 和 device_id=5 的计算失败原因

---

## 📊 执行概况

### 整体统计
- **文件处理**：64个CSV文件，全部成功
- **数据导入**：460,800行数据，0行拒绝
- **计算设备**：7个设备
- **成功设备**：7个
- **失败设备**：0个
- **总数据点**：67,020个
- **吞吐量**：7,364 数据点/秒

### 阶段耗时分布
| 阶段 | 耗时(秒) | 占比 |
|------|---------|------|
| prepare_dim_stage1 | 2.09 | 1.3% |
| create_staging | 0.02 | 0.0% |
| ingest_copy | 4.71 | 2.9% |
| merge_fact | 88.37 | 54.7% |
| prepare_dim_stage2 | 49.23 | 30.4% |
| device_running | 0.76 | 0.5% |
| presence | 1.91 | 1.2% |
| **calculation** | **9.12** | **5.6%** |
| **总计** | **161.67** | **100.0%** |

---

## 🔍 ERROR 统计分析

### ERROR 总数：57个

### 按设备分组统计

| 设备ID | 设备类型 | ERROR数量 | 主要失败指标 |
|--------|---------|----------|-------------|
| 1 | pump | 9 | pump_flow_rate, pump_speed, main_pipeline_inlet_pressure, pump_cumulative_flow, pump_head, main_pipeline_outlet_pressure, pump_efficiency, pump_torque |
| 2 | pump | 9 | pump_flow_rate, pump_speed, main_pipeline_inlet_pressure, pump_cumulative_flow, pump_head, main_pipeline_outlet_pressure, pump_efficiency, pump_torque |
| **3** | **pump** | **6** | **main_pipeline_inlet_pressure, pump_head, main_pipeline_outlet_pressure, pump_efficiency** |
| 4 | pump | 9 | pump_flow_rate, pump_speed, main_pipeline_inlet_pressure, pump_cumulative_flow, pump_head, main_pipeline_outlet_pressure, pump_efficiency, pump_torque |
| **5** | **pump** | **6** | **main_pipeline_inlet_pressure, pump_head, main_pipeline_outlet_pressure, pump_efficiency** |
| 6 | pump | 9 | pump_flow_rate, pump_speed, main_pipeline_inlet_pressure, pump_cumulative_flow, pump_head, main_pipeline_outlet_pressure, pump_efficiency, pump_torque |
| 7 | main_pipeline | 9 | pump_flow_rate, pump_outlet_pressure, pump_speed, pump_cumulative_flow, pump_head, main_pipeline_outlet_pressure, pump_efficiency, pump_torque |

### 按指标分组统计

| 指标 | 失败设备数 | 失败原因 |
|------|-----------|---------|
| pump_flow_rate | 5 (1,2,4,6,7) | 没有可用的计算方法 |
| pump_speed | 5 (1,2,4,6,7) | 没有可用的计算方法 |
| main_pipeline_inlet_pressure | 6 (1,2,3,4,5,6) | 没有可用的计算方法 |
| pump_cumulative_flow | 5 (1,2,4,6,7) | 没有可用的计算方法 |
| pump_head | 7 (1,2,3,4,5,6,7) | 没有可用的计算方法 |
| main_pipeline_outlet_pressure | 7 (1,2,3,4,5,6,7) | 没有可用的计算方法 |
| pump_efficiency | 7 (1,2,3,4,5,6,7) | 没有可用的计算方法 |
| pump_torque | 6 (1,2,4,5,6,7) | 没有可用的计算方法 |
| pump_outlet_pressure | 1 (7) | 没有可用的计算方法 |

---

## 🎯 关键发现

### 发现1：pump_inlet_pressure 方法注册成功但未被使用

**证据**：
- 数据库查询确认2个方法已注册（method_b 优先级100，method_a 优先级90）
- 但日志中仍然报错"main_pipeline_inlet_pressure 没有可用的计算方法"
- **pump_inlet_pressure 本身没有ERROR**（这是好消息！）

**分析**：
- pump_inlet_pressure 的注册是成功的
- 但 main_pipeline_inlet_pressure 仍然失败
- 原因：main_pipeline_inlet_pressure 的方法依赖 pump_inlet_pressure，但依赖检查失败

### 发现2：依赖链仍然断裂

**日志证据**（device_id=7, main_pipeline_inlet_pressure）：
```
方法 PIN_COEF_V1 因依赖数据无效被跳过: 需要 ['pump_inlet_pressure', 'pool_liquid_level']
依赖指标 pump_inlet_pressure 的所有数据都是NaN
```

**分析**：
- pump_inlet_pressure 虽然注册了，但**没有被计算**
- 原因：pump_inlet_pressure 只对 `allowed_device_types=['pump']` 有效
- device_id=7 的类型是 `main_pipeline`，无法使用 pump_inlet_pressure 方法
- 导致 main_pipeline_inlet_pressure 的依赖检查失败

### 发现3：device_id=3 和 device_id=5 的特殊情况

**device_id=3 的ERROR**：
1. main_pipeline_inlet_pressure - 没有可用的计算方法
2. pump_head - 没有可用的计算方法
3. main_pipeline_outlet_pressure - 没有可用的计算方法
4. pump_efficiency - 没有可用的计算方法

**device_id=3 的数据验证失败**：
- pump_flow_rate: 55.5% 有效率（3201/7200 无效）
- pump_speed: 55.5% 有效率（3201/7200 无效）
- pump_torque: 55.5% 有效率（3201/7200 无效）

**device_id=5 的ERROR**：
1. main_pipeline_inlet_pressure - 没有可用的计算方法
2. pump_head - 没有可用的计算方法
3. main_pipeline_outlet_pressure - 没有可用的计算方法
4. pump_efficiency - 没有可用的计算方法

**device_id=5 的数据验证失败**：
- pump_flow_rate: 2.2% 有效率（7044/7200 无效）
- pump_speed: 2.2% 有效率（7044/7200 无效）
- pump_torque: 2.2% 有效率（7044/7200 无效）

---

## 🔬 深度分析：为什么 device_id=3 和 5 的计算失败？

### 问题A：为什么某些指标计算失败？

#### 1. main_pipeline_inlet_pressure 失败原因

**设备1-6（pump类型）**：
- 日志显示：`main_pipeline_inlet_pressure 没有可用的计算方法`
- 原因：main_pipeline_inlet_pressure 的方法需要 pump_inlet_pressure 作为依赖
- **但 pump_inlet_pressure 没有被计算！**

**为什么 pump_inlet_pressure 没有被计算？**
- 查看日志，**没有找到 pump_inlet_pressure 的计算尝试**
- 推测：pump_inlet_pressure 不在计算指标列表中
- 验证：calculation 配置中的 metrics 列表：
  ```
  ["pump_flow_rate", "pump_head", "pump_outlet_pressure", "pump_efficiency", 
   "pump_speed", "pump_torque", "main_pipeline_inlet_pressure", 
   "main_pipeline_outlet_pressure", "pump_cumulative_flow"]
  ```
- **确认：pump_inlet_pressure 不在计算列表中！**

#### 2. pump_head 失败原因

**日志证据**（device_id=3）：
```
方法 HEAD_COEF_V1 因依赖数据无效被跳过: 需要 ['pump_outlet_pressure', 'pool_liquid_level', 'pump_flow_rate', 'main_pipeline_flow_rate']
方法 MAIN 因依赖数据无效被跳过: 需要 ['pump_outlet_pressure', 'pump_inlet_pressure']
```

**分析**：
- HEAD_COEF_V1 方法：依赖 pump_outlet_pressure（可能缺失）
- MAIN 方法：依赖 pump_inlet_pressure（未计算）
- 两个方法都无法使用 → pump_head 计算失败

#### 3. pump_efficiency 失败原因

**依赖链**：
```
pump_efficiency (EFF_SIMPLE_V1)
├── 依赖: pump_flow_rate ✅ (已计算，但有效率低)
├── 依赖: pump_head ❌ (计算失败)
└── 依赖: pump_active_power ✅ (实测数据)
```

**结论**：因为 pump_head 失败，pump_efficiency 无法计算

---

### 问题B：为什么计算成功后被质量过滤掉？

#### device_id=3 的质量过滤情况

**pump_flow_rate**：
- 总数据点：7200
- 有效数据点：3999
- 无效数据点：3201 (44.5%)
- 有效率：55.5%
- 错误原因：
  - NaN验证失败：3201 个值为NaN
  - 非负验证失败：3201 个值为负数
  - 范围验证失败：3201 个值超出范围 [0, 10000]

**分析**：
- 3201个数据点是NaN → 计算方法返回了NaN
- 推测：计算方法的依赖数据不完整或无效

#### device_id=5 的质量过滤情况

**pump_flow_rate**：
- 总数据点：7200
- 有效数据点：156
- 无效数据点：7044 (97.8%)
- 有效率：2.2%
- 错误原因：
  - NaN验证失败：7044 个值为NaN
  - 非负验证失败：7044 个值为负数
  - 范围验证失败：7044 个值超出范围 [0, 10000]

**分析**：
- 7044个数据点是NaN → 几乎所有计算都失败
- 推测：设备5的实测数据严重缺失或无效

---

## 💡 根本原因总结

### ✅ 原因1：pump_inlet_pressure 未被主动计算（已确认！）

**问题**：
- pump_inlet_pressure 方法已注册到数据库 ✅
- **但 `configs/merge.yaml` 的计算列表中没有包含 pump_inlet_pressure** ❌
- 导致 pump_inlet_pressure 从未被计算
- 所有依赖 pump_inlet_pressure 的方法都失败

**证据**：
查看 `configs/merge.yaml` 第12-23行：
```yaml
metrics:
  - pump_flow_rate
  - pump_head
  - pump_outlet_pressure
  - pump_efficiency
  - pump_speed
  - pump_torque
  - main_pipeline_inlet_pressure
  - main_pipeline_outlet_pressure
  - pump_cumulative_flow
  # ❌ pump_inlet_pressure 不在列表中！
```

**影响范围**：
- main_pipeline_inlet_pressure（依赖 pump_inlet_pressure）
- pump_head 的 MAIN 方法（依赖 pump_inlet_pressure）
- pump_efficiency（依赖 pump_head）

### 原因2：设备类型过滤导致循环依赖

**问题**：
- pump_inlet_pressure 方法只允许 `device_type='pump'`
- main_pipeline_inlet_pressure 方法依赖 pump_inlet_pressure
- 但 device_id=7 (main_pipeline) 无法计算 pump_inlet_pressure
- 导致 main_pipeline_inlet_pressure 无法计算

### 原因3：实测数据质量问题

**device_id=3**：
- 44.5% 的数据无效（3201/7200）
- 推测：实测数据中有大量缺失或异常值

**device_id=5**：
- 97.8% 的数据无效（7044/7200）
- 推测：设备5几乎没有有效的实测数据

---

## 🎯 建议的解决方案

### ✅ 方案1：将 pump_inlet_pressure 添加到计算列表（立即执行，强烈推荐）

**操作**：
- 修改 `configs/merge.yaml` 第12-23行
- 将 `pump_inlet_pressure` 添加到 metrics 列表
- **关键**：确保 pump_inlet_pressure 在 pump_head 之前（因为 pump_head 依赖它）

**修改示例**：
```yaml
metrics:
  - pump_flow_rate
  - pump_inlet_pressure    # ✅ 新增：必须在 pump_head 之前
  - pump_head
  - pump_outlet_pressure
  - pump_efficiency
  - pump_speed
  - pump_torque
  - main_pipeline_inlet_pressure
  - main_pipeline_outlet_pressure
  - pump_cumulative_flow
```

**预期效果**：
- ✅ pump_inlet_pressure 将被主动计算（对 device_id=1-6）
- ✅ pump_head 的 MAIN 方法可以使用（依赖链恢复）
- ✅ pump_efficiency 可以计算（依赖链恢复）
- ✅ device_id=3 和 5 的计算错误大幅减少

**风险评估**：
- 低风险：只是添加一个指标到计算列表
- 可回滚：如果出现问题，删除该行即可

---

### 方案2：检查实测数据质量（中期）

**操作**：
- 查询 device_id=3 和 5 的实测数据
- 检查数据完整性和有效性
- 修复数据源问题

**SQL查询示例**：
```sql
-- 检查 device_id=3 的实测数据
SELECT mc.metric_key,
       COUNT(*) as total,
       COUNT(CASE WHEN fm.value IS NOT NULL THEN 1 END) as non_null,
       COUNT(CASE WHEN fm.value IS NULL THEN 1 END) as null_count,
       AVG(fm.value) as avg_value,
       MIN(fm.value) as min_value,
       MAX(fm.value) as max_value
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.device_id = 3
  AND mc.metric_key IN ('pump_flow_rate', 'pump_speed', 'pump_torque',
                        'pump_outlet_pressure', 'pump_active_power')
GROUP BY mc.metric_key;
```

---

### 方案3：优化依赖链设计（长期）

**问题分析**：
- pump_inlet_pressure 只对 pump 类型设备有效
- main_pipeline_inlet_pressure 依赖 pump_inlet_pressure
- 但 device_id=7 (main_pipeline) 无法计算 pump_inlet_pressure
- 导致循环依赖

**建议**：
- 为 main_pipeline 类型设备添加独立的 pump_inlet_pressure 计算方法
- 或者重新设计 main_pipeline_inlet_pressure 的依赖关系
- 避免跨设备类型的依赖

---

## 📋 下一步行动

### 立即执行（优先级：高）

1. ✅ **修改 `configs/merge.yaml`**
   - 在 metrics 列表中添加 `pump_inlet_pressure`
   - 确保顺序正确（在 pump_head 之前）

2. ✅ **重新运行 run-all 命令**
   ```bash
   python -m app.cli.main run-all configs/data_mapping.v2.json
   ```

3. ✅ **验证问题是否解决**
   - 检查日志，确认 pump_inlet_pressure 被计算
   - 检查 pump_head 和 pump_efficiency 是否成功计算
   - 检查 device_id=3 和 5 的错误数量是否减少

### 后续分析（优先级：中）

4. **查询数据库，分析计算结果**
   ```sql
   -- 检查 pump_inlet_pressure 是否被计算
   SELECT device_id, COUNT(*) as count
   FROM fact_measurements fm
   JOIN dim_metric_config mc ON mc.id = fm.metric_id
   WHERE mc.metric_key = 'pump_inlet_pressure'
   GROUP BY device_id;
   ```

5. **分析实测数据质量问题**
   - 查询 device_id=3 和 5 的实测数据
   - 确定为什么有大量 NaN 值

---

## 🔍 与之前成功计算时的对比

**用户提到："昨天还可以成功计算的，今天就不行了"**

**推测原因**：
1. **可能性1**：之前的 `configs/merge.yaml` 包含了 `pump_inlet_pressure`，后来被删除了
2. **可能性2**：之前使用的是不同的配置文件或参数
3. **可能性3**：之前的数据库中已经有 pump_inlet_pressure 的计算结果（从其他来源），今天重置数据库后丢失了

**验证方法**：
- 检查 Git 历史，查看 `configs/merge.yaml` 的修改记录
- 检查之前的日志文件，确认 pump_inlet_pressure 是否被计算

---

## 📊 总结

### 核心问题
**pump_inlet_pressure 方法已注册到数据库，但未被添加到计算列表中**

### 解决方案
**修改 `configs/merge.yaml`，添加 `pump_inlet_pressure` 到 metrics 列表**

### 预期效果
- ✅ pump_inlet_pressure 被计算
- ✅ pump_head 依赖链恢复
- ✅ pump_efficiency 依赖链恢复
- ✅ device_id=3 和 5 的错误大幅减少

---

## 🔄 修改后重新运行结果（2025-10-31 01:20）

### ✅ 配置修改成功

**修改内容**：
- 在 `configs/merge.yaml` 第16行插入了 `pump_inlet_pressure`
- 更新了指标数量：从 9 项 → 10 项
- 确保了正确的依赖顺序：pump_inlet_pressure 在 pump_head 之前

### ❌ 问题仍然存在！

**执行结果**：
- run-all 命令执行成功（155.21秒）
- **但 pump_inlet_pressure 仍然没有被计算（0行数据）**
- ERROR 数量从 57 个增加到 65 个（增加了8个 pump_inlet_pressure 的ERROR）

**数据库查询结果**：
```sql
SELECT device_id, COUNT(*) FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE mc.metric_key = 'pump_inlet_pressure'
GROUP BY device_id;

结果：0 行记录
```

### 🔍 深度分析：为什么 pump_inlet_pressure 仍然失败？

**日志证据**（device_id=1）：
```
ERROR|指标 pump_inlet_pressure 没有可用的计算方法
{"可用指标": ["main_pipeline_cumulative_flow", "main_pipeline_flow_rate",
              "main_pipeline_outlet_pressure", "pool_liquid_level",
              "pump_active_power", "pump_cumulative_flow", "pump_flow_rate",
              "pump_frequency", "pump_group_outlet_pressure", "pump_head",
              "pump_inlet_pressure", "pump_outlet_pressure", "pump_speed"]}
```

**方法注册情况**：
- **method_b**（优先级100）：依赖 `pool_liquid_level`，允许设备类型 `pump`
- **method_a**（优先级90）：依赖 `main_pipeline_inlet_pressure`，允许设备类型 `pump`

**pool_liquid_level 数据分布**：
```sql
SELECT device_id, COUNT(*) FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE mc.metric_key = 'pool_liquid_level'
GROUP BY device_id;

结果：
device_id | count
----------|------
    8     | 7200
```

**🎯 根本原因确认**：

1. **method_b 失败原因**：
   - 依赖 `pool_liquid_level`
   - 但 `pool_liquid_level` 只在 device_id=8 上有数据
   - device_id=1-6（pump类型设备）上没有 `pool_liquid_level` 数据
   - 导致依赖检查失败

2. **method_a 失败原因**：
   - 依赖 `main_pipeline_inlet_pressure`
   - 但 `main_pipeline_inlet_pressure` 本身也在计算列表中
   - 可能因为计算顺序问题，`main_pipeline_inlet_pressure` 还没被计算
   - 或者 `main_pipeline_inlet_pressure` 也失败了

3. **循环依赖问题**：
   - `pump_inlet_pressure` (method_a) 依赖 `main_pipeline_inlet_pressure`
   - `main_pipeline_inlet_pressure` (PIN_COEF_V1) 依赖 `pump_inlet_pressure`
   - 形成循环依赖，导致两者都无法计算

---

## 🎯 最终解决方案

### 方案1：修改 pump_inlet_pressure 的依赖关系（推荐）

**问题分析**：
- 当前的两个方法都依赖其他计算指标或不可用的实测数据
- 需要一个不依赖其他计算指标的方法

**建议**：
1. **检查是否有其他实测数据可用**
   - 查询 device_id=1-6 上有哪些实测数据
   - 寻找可以直接用于计算 pump_inlet_pressure 的实测指标

2. **添加一个简单的估算方法**
   - 例如：使用固定值或经验公式
   - 优先级设置为最低（例如50），作为兜底方案

3. **修改 method_a 的依赖**
   - 不依赖 `main_pipeline_inlet_pressure`（避免循环依赖）
   - 改为依赖其他可用的实测数据

### 方案2：检查 pool_liquid_level 的数据映射

**问题分析**：
- `pool_liquid_level` 应该是泵站级别的数据，不是设备级别的
- 但当前只在 device_id=8 上有数据

**建议**：
1. **检查数据映射配置**
   - 查看 `configs/data_mapping.v2.json`
   - 确认 `pool_liquid_level` 是否应该映射到所有 pump 设备

2. **修改数据映射**
   - 如果 `pool_liquid_level` 是泵站级别的数据
   - 应该复制到所有 pump 设备（device_id=1-6）

### 方案3：修改计算顺序（临时方案）

**问题分析**：
- `main_pipeline_inlet_pressure` 可能在 `pump_inlet_pressure` 之后计算
- 导致 method_a 的依赖不可用

**建议**：
1. **调整 metrics 列表顺序**
   - 将 `main_pipeline_inlet_pressure` 移到 `pump_inlet_pressure` 之前
   - 但这可能导致 `main_pipeline_inlet_pressure` 失败（因为它依赖 `pump_inlet_pressure`）

2. **打破循环依赖**
   - 修改 `main_pipeline_inlet_pressure` 的方法
   - 不依赖 `pump_inlet_pressure`

---

## 📋 下一步行动（更新）

### 立即执行（优先级：高）

1. ✅ **查询 device_id=1-6 的实测数据**
   ```sql
   SELECT mc.metric_key, COUNT(*) as count
   FROM fact_measurements fm
   JOIN dim_metric_config mc ON mc.id = fm.metric_id
   WHERE fm.device_id IN (1,2,3,4,5,6)
     AND mc.is_calculated = FALSE
   GROUP BY mc.metric_key
   ORDER BY mc.metric_key;
   ```

2. ✅ **检查 pump_inlet_pressure 方法的依赖配置**
   ```sql
   SELECT method_id, method_name, dependencies, allowed_device_types
   FROM calculation_method_registry
   WHERE metric_key = 'pump_inlet_pressure'
   ORDER BY priority DESC;
   ```

3. ✅ **分析循环依赖问题**
   - 查看 `main_pipeline_inlet_pressure` 的方法配置
   - 确认是否存在循环依赖

### 后续方案（优先级：中）

4. **根据分析结果选择解决方案**
   - 如果有其他可用的实测数据 → 修改方法依赖
   - 如果 pool_liquid_level 应该在所有设备上 → 修改数据映射
   - 如果存在循环依赖 → 打破循环依赖

---

**报告结束**

