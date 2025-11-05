# calculation_parameters 表深度验证报告

**创建时间**：2025-11-04
**任务类型**：研究模式 - 验证用户假设
**协议**：RIPER-5 - 研究模式

---

## 任务目标

验证用户关于 prepare_dim 阶段和 calculation_parameters 表处理行为的假设，并深入分析参数完整性问题。

---

## 用户假设清单

### 假设1：prepare_dim-2 阶段把参数恢复默认值
**用户声称**："prepare_dim-2 阶段把参数恢复默认值"

### 假设2：prepare_dim 阶段只是备份、清空、恢复
**用户声称**："在 prepare_dim 阶段只是备份、清空、恢复"

---

## 核心发现

### 发现1：用户假设1 **完全错误** ❌

**用户声称**："prepare_dim-2 阶段把参数恢复默认值"

**实际情况**：prepare_dim-2 阶段**完全不涉及** calculation_parameters 表

**证据**：
1. **代码证据**（`app/services/ingest/prepare_dim/__init__.py` 第1465-1510行）：
   ```python
   # 阶段2：规则生成（在 merge-fact 后执行）
   if execute_stage2:
       _act.info("[prepare-dim] 阶段2：规则生成")
       
       # 2.1 清空规则表
       # 2.2 生成规则表
       # 2.3 生成映射表（dim_mapping_items）
   ```

2. **阶段2的实际操作**（第1467-1510行）：
   - 前置检查：验证 fact_measurements 表是否有数据
   - 清空规则表（6个表）：
     * metric_rule_auto_baseline
     * metric_rule_auto_baseline_shadow
     * metric_quality_rules
     * metric_quality_rules_shadow
     * device_running_thresholds
     * device_running_thresholds_shadow
   - 生成规则表（调用存储过程）
   - 生成映射表（dim_mapping_items）

3. **calculation_parameters 表不在阶段2的处理范围内**：
   - 阶段2只处理规则表（D类表）
   - calculation_parameters 是配置表（B类表）
   - 阶段2的代码中**没有任何**对 calculation_parameters 表的操作

**结论**：用户假设1 **完全错误**。prepare_dim-2 阶段**不会**修改 calculation_parameters 表，更不会"恢复默认值"。

---

### 发现2：用户假设2 **部分错误** ⚠️

**用户声称**："在 prepare_dim 阶段只是备份、清空、恢复"

**实际情况**：prepare_dim 阶段**不是**简单的"备份、清空、恢复"，而是"备份、清空、重建、不恢复"

**证据**：
1. **阶段1的实际流程**（`app/services/ingest/prepare_dim/__init__.py` 第1193-1462行）：
   ```
   1.1 备份21个表（包括 calculation_parameters）
   1.2 清空非备份表
   1.3 重建维度表（dim_stations, dim_devices, dim_metric_config）
   1.4 执行自适应SQL脚本（4个文件）
       - 01_metric_config_related.sql
       - 02_device_related.sql
       - 03_calculation_parameters.sql  ← 关键！
       - 04_metadata_override.sql（跳过）
   1.5 恢复手动配置表（9个表）
       - dim_metric_metadata_override
       - pump_characteristic_curves
       - quality_code_dict
       - calculation_validation_config
       - metric_capability_policy
       - metric_anomaly_strategy
       - device_metric_candidates
       - dim_metric_metadata
       - optimization_history
   1.6 恢复配置表（4个表）
       - calculation_method_registry
       - metric_calculation_order
       - device_rated_params
       - dim_device_capabilities
   ```

2. **关键发现**：calculation_parameters 表**不在恢复列表中** ❌

   **证据**（第1383-1394行）：
   ```python
   # 定义需要恢复的手动配置表（不包括自适应SQL脚本生成的表）
   manual_config_tables = [
       "dim_metric_metadata_override",
       "pump_characteristic_curves",
       "quality_code_dict",
       "calculation_validation_config",
       "metric_capability_policy",
       "metric_anomaly_strategy",
       "device_metric_candidates",
       "dim_metric_metadata",
       "optimization_history",
   ]
   ```

   **注意**：calculation_parameters **不在** manual_config_tables 列表中！

3. **calculation_parameters 表的实际处理流程**：
   ```
   步骤1：备份（第1213行）
       └─ BackupManager.backup_tables() 备份到 backups/calculation_parameters/
   
   步骤2：清空（第359行）
       └─ DELETE FROM calculation_parameters
   
   步骤3：重建（第1368行）
       └─ 执行 scripts/sql/adaptive/03_calculation_parameters.sql
          ├─ TRUNCATE TABLE calculation_parameters CASCADE（第17行）
          └─ INSERT INTO calculation_parameters (...)
             -- 重新生成全局参数（从 dim_metric_config 和 calculation_method_registry 关联）
   
   步骤4：不恢复备份 ❌
       └─ calculation_parameters 不在 manual_config_tables 列表中
   ```

4. **为什么不恢复备份？**（来自 `.tasks/4个表的备份恢复策略对比-2025-11-02.md`）：
   - ✅ **设备ID可能变化**：备份中的device_id可能与新导入的dim_devices不一致
   - ✅ **自适应关联**：使用 `station_name + device_name` 定位设备，适应设备ID变化
   - ✅ **完全重建**：确保参数与当前设备完全对应
   - ✅ **支持三级参数体系**：全局级、泵站级、设备级参数

**结论**：用户假设2 **部分错误**。prepare_dim 阶段**不是**"备份、清空、恢复"，而是"备份、清空、重建（通过自适应SQL脚本）、不恢复备份"。

---

### 发现3：calculation_parameters 表的参数来源 ✅

**数据来源**：`scripts/sql/adaptive/03_calculation_parameters.sql`

**脚本逻辑**（第10-325行）：
1. **清空表**（第17行）：
   ```sql
   TRUNCATE TABLE calculation_parameters CASCADE;
   ```

2. **重新生成全局参数**（第20-300行）：
   - 类型0：全局物理常数和高级方法参数（HEAD_COEF_V1, PIN_COEF_V1）
   - 类型1：全局默认参数（pump_flow_rate_method_a, pump_head_method_main, pump_speed_method_a/b/c, pump_torque_method_a/b, EFF_SIMPLE_V1, pump_inlet_pressure_method_b, pump_outlet_pressure_method_c, main_pipeline_inlet_pressure_method_b, main_pipeline_outlet_pressure_method_b）

3. **参数生成方式**：
   - 使用 `SELECT ... FROM dim_metric_config mc WHERE mc.metric_key = '...'` 自适应关联
   - 如果 dim_metric_config 中没有对应的 metric_key，则不生成参数
   - 参数值是硬编码的默认值（如 alpha=1.0, beta=1.0, rho=1000.0, g=9.80665）

4. **设备级参数示例**（第301-321行，已注释）：
   ```sql
   -- 示例：为特定设备设置 pump_flow_rate 方案A 的参数
   -- INSERT INTO calculation_parameters (...)
   -- SELECT ... FROM dim_devices d
   -- WHERE s.name = '二期供水泵房' AND d.name = '二期供水泵房1#泵'
   ```

**关键发现**：
- ✅ 脚本只生成**全局参数**（station_id=NULL, device_id=NULL）
- ✅ 脚本**不生成**设备级参数（需要手动添加或通过迁移脚本）
- ✅ 脚本只为**部分方法**生成参数（14个方法），不是所有方法（28个方法）

---

### 发现4：缺少参数的计算方法 ⚠️

**系统中启用的计算方法**：28个（来自 calculation_method_registry 表）

**当前有参数的计算方法**：14个（来自 calculation_parameters 表）

**缺少参数的计算方法**：14个 ❌

**详细清单**：

| 方法ID | 指标 | 方法代码 | 优先级 | 状态 |
|--------|------|----------|--------|------|
| main_pipeline_inlet_pressure_method_c | main_pipeline_inlet_pressure | C | 80 | ❌ 缺少参数 |
| main_pipeline_inlet_pressure_method_a | main_pipeline_inlet_pressure | A | 100 | ❌ 缺少参数 |
| main_pipeline_outlet_pressure_method_c | main_pipeline_outlet_pressure | C | 80 | ❌ 缺少参数 |
| main_pipeline_outlet_pressure_method_a | main_pipeline_outlet_pressure | A | 100 | ❌ 缺少参数 |
| pump_cumulative_flow_method_b | pump_cumulative_flow | B | 90 | ❌ 缺少参数 |
| pump_cumulative_flow_method_a | pump_cumulative_flow | A | 100 | ❌ 缺少参数 |
| pump_flow_rate_method_e | pump_flow_rate | E | 60 | ❌ 缺少参数 |
| pump_flow_rate_method_d | pump_flow_rate | D | 70 | ❌ 缺少参数 |
| pump_flow_rate_method_c | pump_flow_rate | C | 80 | ❌ 缺少参数 |
| pump_flow_rate_method_b | pump_flow_rate | B | 90 | ❌ 缺少参数 |
| pump_inlet_pressure_method_a | pump_inlet_pressure | A | 90 | ❌ 缺少参数 |
| pump_outlet_pressure_method_d | pump_outlet_pressure | D | 70 | ❌ 缺少参数 |
| pump_outlet_pressure_method_b | pump_outlet_pressure | B | 90 | ❌ 缺少参数 |
| pump_outlet_pressure_method_a | pump_outlet_pressure | A | 100 | ❌ 缺少参数 |

**有参数的计算方法**：14个 ✅

| 方法ID | 指标 | 方法代码 | 优先级 | 参数数量 | 可优化参数数量 |
|--------|------|----------|--------|----------|----------------|
| main_pipeline_inlet_pressure_method_b | main_pipeline_inlet_pressure | B | 90 | 3 | 0 |
| PIN_COEF_V1 | main_pipeline_inlet_pressure | PIN_COEF_V1 | 110 | 8 | 4 |
| main_pipeline_outlet_pressure_method_b | main_pipeline_outlet_pressure | B | 90 | 2 | 0 |
| EFF_SIMPLE_V1 | pump_efficiency | EFF_SIMPLE_V1 | 100 | 4 | 2 |
| pump_flow_rate_method_a | pump_flow_rate | A | 100 | 4 | 4 |
| pump_head_method_main | pump_head | MAIN | 100 | 4 | 1 |
| HEAD_COEF_V1 | pump_head | HEAD_COEF_V1 | 110 | 10 | 6 |
| pump_inlet_pressure_method_b | pump_inlet_pressure | B | 100 | 3 | 0 |
| pump_outlet_pressure_method_c | pump_outlet_pressure | C | 80 | 2 | 0 |
| pump_speed_method_c | pump_speed | C | 80 | 2 | 2 |
| pump_speed_method_b | pump_speed | B | 90 | 2 | 1 |
| pump_speed_method_a | pump_speed | A | 100 | 2 | 0 |
| pump_torque_method_b | pump_torque | B | 90 | 2 | 1 |
| pump_torque_method_a | pump_torque | A | 100 | 2 | 0 |

---

### 发现5：可优化参数的完整性分析 ✅

**当前可优化参数总数**：21个（来自 calculation_parameters 表）

**详细清单**：

| 方法ID | 参数名 | 当前值 | 可优化 | 参数范围 | 置信度 | 优化次数 |
|--------|--------|--------|--------|----------|--------|----------|
| EFF_SIMPLE_V1 | eta_max | 0.85 | ✅ | 无 | 0.5 | 0 |
| EFF_SIMPLE_V1 | eta_motor | 0.92 | ✅ | 无 | 0.5 | 0 |
| HEAD_COEF_V1 | a0 | 50.0 | ✅ | [0.0, 100.0] | 0.5 | 0 |
| HEAD_COEF_V1 | a1 | -0.01 | ✅ | [-1.0, 1.0] | 0.5 | 0 |
| HEAD_COEF_V1 | a2 | -0.0001 | ✅ | [-0.01, 0.01] | 0.5 | 0 |
| HEAD_COEF_V1 | a3 | 0.0 | ✅ | [-10.0, 10.0] | 0.5 | 0 |
| HEAD_COEF_V1 | a4 | 0.0 | ✅ | [-10.0, 10.0] | 0.5 | 0 |
| HEAD_COEF_V1 | a5 | 0.0 | ✅ | [-1.0, 1.0] | 0.5 | 0 |
| PIN_COEF_V1 | b0 | 101325.0 | ✅ | [50000.0, 200000.0] | 0.5 | 0 |
| PIN_COEF_V1 | b1 | 1.0 | ✅ | [0.5, 1.5] | 0.5 | 0 |
| PIN_COEF_V1 | b2 | 0.0 | ✅ | [0.0, 100.0] | 0.5 | 0 |
| PIN_COEF_V1 | b3 | 0.0 | ✅ | [0.0, 1000.0] | 0.5 | 0 |
| pump_flow_rate_method_a | alpha | 1.0 | ✅ | 无 | 0.5 | 0 |
| pump_flow_rate_method_a | beta | 1.0 | ✅ | 无 | 0.5 | 0 |
| pump_flow_rate_method_a | f_thr | 3.0 | ✅ | 无 | 0.5 | 0 |
| pump_flow_rate_method_a | p_thr | 0.5 | ✅ | 无 | 0.5 | 0 |
| pump_head_method_main | b_H | 0.0 | ✅ | 无 | 0.5 | 0 |
| pump_speed_method_b | slip | 0.02 | ✅ | 无 | 0.5 | 0 |
| pump_speed_method_c | calibration_a | 30.0 | ✅ | 无 | 0.5 | 0 |
| pump_speed_method_c | calibration_b | 0.0 | ✅ | 无 | 0.5 | 0 |
| pump_torque_method_b | slip | 0.02 | ✅ | 无 | 0.5 | 0 |

**关键观察**：
1. ✅ 所有可优化参数的 `optimization_count = 0`（从未被优化过）
2. ✅ 所有可优化参数的 `last_optimized_at = NULL`（从未被优化过）
3. ✅ 所有可优化参数的 `confidence_score = 0.5`（默认置信度）
4. ⚠️ 部分可优化参数缺少参数范围约束（param_min, param_max = NULL）
   - EFF_SIMPLE_V1 的 eta_max, eta_motor
   - pump_flow_rate_method_a 的 alpha, beta, f_thr, p_thr
   - pump_head_method_main 的 b_H
   - pump_speed_method_b 的 slip
   - pump_speed_method_c 的 calibration_a, calibration_b
   - pump_torque_method_b 的 slip

---

### 发现6：参数优化器的实现分析 ✅

**文件**：`app/services/calculation/parameter_optimizer.py`

**关键发现**：
1. ✅ RLS算法已完整实现（第56-200行）
2. ✅ 参数约束检查已实现（使用 param_min, param_max）
3. ✅ 置信度计算已实现（基于R²和样本数）
4. ✅ 优化历史记录已实现（保存到 optimization_history 表和 calculation_parameters.optimization_history 字段）
5. ✅ 协方差矩阵保存已实现（保存到 calculation_parameters.covariance_matrix 字段）

**参数优化器不检查 is_optimizable 字段** ⚠️

**证据**：
- 在 `parameter_optimizer.py` 中搜索 `is_optimizable` 或 `可优化`，**没有找到任何匹配**
- 参数优化器的 `optimize_parameters()` 方法接受 `current_params` 字典作为输入，不检查参数是否可优化
- 是否优化参数由**调用者**（orchestrator.py）决定，而非参数优化器本身

**调用者的责任**（orchestrator.py）：
- 在调用 `parameter_optimizer.optimize_parameters()` 前，应该过滤出 `is_optimizable=true` 的参数
- 当前 orchestrator.py 的 `enable_optimization=False`，所以参数优化功能未启用

---

## 问题汇总

### 问题1：prepare_dim-2 阶段的参数处理行为验证

**用户声称**："prepare_dim-2 阶段把参数恢复默认值"

**验证结果**：❌ **完全错误**

**实际行为**：
- prepare_dim-2 阶段**完全不涉及** calculation_parameters 表
- prepare_dim-2 阶段只处理规则表（D类表）：
  * metric_rule_auto_baseline
  * metric_rule_auto_baseline_shadow
  * metric_quality_rules
  * metric_quality_rules_shadow
  * device_running_thresholds
  * device_running_thresholds_shadow

**证据**：`app/services/ingest/prepare_dim/__init__.py` 第1465-1510行

---

### 问题2：prepare_dim 阶段的参数处理行为验证

**用户声称**："在 prepare_dim 阶段只是备份、清空、恢复"

**验证结果**：⚠️ **部分错误**

**实际行为**：
- prepare_dim 阶段**不是**"备份、清空、恢复"
- 实际流程是"备份、清空、重建（通过自适应SQL脚本）、不恢复备份"

**详细流程**：
1. 备份 calculation_parameters 表
2. 清空 calculation_parameters 表
3. 执行 `scripts/sql/adaptive/03_calculation_parameters.sql` 重新生成全局参数
4. **不恢复备份**（calculation_parameters 不在 manual_config_tables 列表中）

**为什么不恢复备份？**
- 设备ID可能变化（备份中的device_id可能与新导入的dim_devices不一致）
- 自适应关联（使用 station_name + device_name 定位设备）
- 完全重建（确保参数与当前设备完全对应）

**证据**：`app/services/ingest/prepare_dim/__init__.py` 第1366-1394行

---

### 问题3：calculation_parameters 表的参数完整性分析

**系统中启用的计算方法**：28个

**当前有参数的计算方法**：14个

**缺少参数的计算方法**：14个 ❌

**缺少参数的方法清单**：
1. main_pipeline_inlet_pressure_method_c
2. main_pipeline_inlet_pressure_method_a
3. main_pipeline_outlet_pressure_method_c
4. main_pipeline_outlet_pressure_method_a
5. pump_cumulative_flow_method_b
6. pump_cumulative_flow_method_a
7. pump_flow_rate_method_e
8. pump_flow_rate_method_d
9. pump_flow_rate_method_c
10. pump_flow_rate_method_b
11. pump_inlet_pressure_method_a
12. pump_outlet_pressure_method_d
13. pump_outlet_pressure_method_b
14. pump_outlet_pressure_method_a

**这些方法是否需要参数？** ✅ **已验证**

**验证结果**：
- ✅ **不需要参数的方法**（9个）：
  1. pump_inlet_pressure_method_a - 直接使用 main_pipeline_inlet_pressure
  2. pump_outlet_pressure_method_a - 直接读取传感器数据
  3. pump_outlet_pressure_method_b - 直接使用 main_pipeline_outlet_pressure
  4. pump_flow_rate_method_c - 直接使用 main_pipeline_flow_rate
  5. main_pipeline_inlet_pressure_method_a - 直接使用 pump_inlet_pressure
  6. main_pipeline_inlet_pressure_method_c - 聚合多泵数据（mean）
  7. main_pipeline_outlet_pressure_method_a - 直接使用 pump_outlet_pressure
  8. main_pipeline_outlet_pressure_method_c - 聚合多泵数据（max）
  9. pump_cumulative_flow_method_b - 累计量求导（无参数）

- ⚠️ **需要参数的方法**（5个）：
  1. pump_flow_rate_method_d - 需要 p_thr（功率阈值）
  2. pump_flow_rate_method_e - 需要 f_thr（频率阈值）
  3. pump_outlet_pressure_method_d - 需要参数（未找到实现代码，需要进一步确认）
  4. pump_cumulative_flow_method_a - 需要参数（未找到实现代码，需要进一步确认）

**证据**：
- `app/services/calculation/calculators.py` 第190-273行：
  - pump_flow_rate_method_c: `params: 空（此方法不需要参数）`
  - pump_flow_rate_method_d: `params: 包含 p_thr`
  - pump_flow_rate_method_e: `params: 包含 f_thr`
- `app/services/calculation/methods/pump_inlet_pressure.py` 第13-39行：
  - pump_inlet_pressure_method_a: `params: 空（不需要参数）`
- `app/services/calculation/calculators.py` 第701-724行：
  - main_pipeline_outlet_pressure_method_a: `params: 空（不需要参数）`
- `app/services/calculation/calculators.py` 第862-885行：
  - main_pipeline_inlet_pressure_method_a: `params: 空（不需要参数）`
- `app/services/calculation/calculators.py` 第936-960行：
  - main_pipeline_inlet_pressure_method_c: `params: 包含 aggregation_method（默认'mean'）`

**结论**：
- ✅ 14个缺少参数的方法中，**9个方法不需要参数**（设计如此）
- ⚠️ **5个方法需要补充参数**：
  * pump_flow_rate_method_d（需要 p_thr）
  * pump_flow_rate_method_e（需要 f_thr）
  * pump_outlet_pressure_method_d（需要确认）
  * pump_cumulative_flow_method_a（需要确认）
  * main_pipeline_inlet_pressure_method_c（需要 aggregation_method，但有默认值）

---

### 问题4：可优化参数的完整性分析

**当前可优化参数总数**：21个

**缺少参数范围约束的可优化参数**：11个 ⚠️

**详细清单**：
1. EFF_SIMPLE_V1.eta_max
2. EFF_SIMPLE_V1.eta_motor
3. pump_flow_rate_method_a.alpha
4. pump_flow_rate_method_a.beta
5. pump_flow_rate_method_a.f_thr
6. pump_flow_rate_method_a.p_thr
7. pump_head_method_main.b_H
8. pump_speed_method_b.slip
9. pump_speed_method_c.calibration_a
10. pump_speed_method_c.calibration_b
11. pump_torque_method_b.slip

**风险**：
- 参数优化时，如果没有参数范围约束，可能收敛到不合理的值
- 建议为所有可优化参数设置合理的参数范围约束

---

### 问题5：缺失参数的添加策略

**当前系统中已有的参数生成机制**：
1. ✅ `scripts/sql/adaptive/03_calculation_parameters.sql`（prepare_dim 阶段自动执行）
2. ✅ `scripts/sql/calculation/init_params.sql`（手动执行）
3. ✅ `scripts/sql/migrations/072_add_device_level_calculation_params.sql`（迁移脚本，添加设备级参数）

**是否需要重复造轮子？** ❌ **不需要**

**现有机制是否足够？** ⚠️ **部分足够**

**改进建议方向**（研究模式不提供具体方案）：
- `03_calculation_parameters.sql` 只为14个方法生成参数，需要补充其他14个方法的参数
- 需要确认这14个方法是否真的需要参数（可能有些方法不需要参数）
- 需要为缺少参数范围约束的可优化参数补充约束

---

## 记忆更新日志

### 已验证的记忆
- ✅ prepare_dim-2 阶段**不涉及** calculation_parameters 表
- ✅ prepare_dim 阶段**不恢复** calculation_parameters 表的备份
- ✅ calculation_parameters 表通过 `03_calculation_parameters.sql` 重新生成
- ✅ 系统中有28个启用的计算方法，但只有14个方法有参数

### 新增记忆
- 📝 用户假设1（prepare_dim-2 恢复默认值）**完全错误**
- 📝 用户假设2（prepare_dim 只是备份、清空、恢复）**部分错误**
- 📝 缺少参数的计算方法：14个
- 📝 缺少参数范围约束的可优化参数：11个

### 需要澄清的问题
- ❓ 缺少参数的14个方法是否真的需要参数？
- ❓ 如果需要参数，应该在哪里添加？（03_calculation_parameters.sql？新的迁移脚本？）
- ❓ 缺少参数范围约束的11个可优化参数，应该设置什么范围？

---

## 下一步行动

**研究模式已完成**，准备进入**创新模式**。

**创新模式将讨论**：
1. 如何补充缺少参数的14个计算方法？
2. 如何为缺少参数范围约束的11个可优化参数补充约束？
3. 是否需要修改 `03_calculation_parameters.sql` 脚本？
4. 是否需要创建新的迁移脚本？

---

**文档结束**

