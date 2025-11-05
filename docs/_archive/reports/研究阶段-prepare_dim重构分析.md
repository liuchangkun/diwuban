# 研究阶段：prepare_dim 重构深度分析

> **研究时间**: 2025-10-18  
> **任务**: 重新设计和实现 prepare-dim 流程  
> **协议**: RIPER-5（研究-创新-计划-执行-审查）

---

## 📋 研究目标

1. 深入分析现有 prepare-dim 实现
2. 分析所有相关表的结构、依赖关系和外键约束
3. 分析现有备份/恢复机制
4. 分析计算方法的实际实现情况
5. 识别数据误删和恢复问题的根本原因

---

## 🔍 核心发现

### 1. 现有 prepare_dim 实现分析

**文件位置**: `app/services/ingest/prepare_dim/__init__.py`

**当前实现的两阶段架构**:

#### Stage 1（在 merge-fact 前执行）
```python
def prepare_dim(settings, mapping_path, stage=1):
    # 1.1 备份手动配置表（2个）
    backup_data = _backup_manual_tables(cur)
    # - dim_device_capabilities
    # - dim_metric_metadata_override
    
    # 1.2 清空依赖表（14个）
    _clear_dependent_tables(cur)
    # 清空顺序：
    # - fact_measurements（所有历史数据）⚠️
    # - completion_runs, completion_steps
    # - device_rated_params, device_running_thresholds_shadow
    # - dim_device_capabilities, dim_metric_metadata_override（已备份）
    # - metric_quality_rules_shadow, metric_rule_auto_baseline_shadow
    # - dim_devices
    # - calculation_parameters（只清空全局默认参数）
    # - dim_stations
    # - metric_calculation_order, dim_mapping_items
    # - dim_metric_config
    
    # 1.3 重建维度表（3个）
    _reload_metric_config_from_sql(cur, settings)  # dim_metric_config
    _upsert_station(cur, name)  # dim_stations
    _upsert_device(cur, station_id, name, dtype, pump_type)  # dim_devices
    
    # 1.4 恢复手动配置表（2个）
    _restore_manual_tables(cur, backup_data)
    
    # 1.5 重建基础配置表（4个）
    _rebuild_config_tables(settings, cur)
    # - calculation_method_registry（从 init_methods.sql）
    # - calculation_parameters（从 init_params.sql）
    # - device_rated_params（从 seed_device_rated_params.sql）
    # - metric_calculation_order（从 DependencyAnalyzer）
```

#### Stage 2（在 merge-fact 后执行）
```python
def prepare_dim(settings, mapping_path, stage=2):
    # 2.1 清空规则表（6个）
    _clear_rule_tables(cur)
    # - metric_rule_auto_baseline
    # - metric_rule_auto_baseline_shadow
    # - metric_quality_rules
    # - metric_quality_rules_shadow
    # - device_running_thresholds
    # - device_running_thresholds_shadow
    
    # 2.2 生成规则表（6个函数）
    _generate_rule_tables(settings)
    # 1. run_auto_baseline_b() → metric_rule_auto_baseline_shadow
    # 2. run_auto_baseline() → metric_rule_auto_baseline
    # 3. compute_metric_quality_rules_shadow() → metric_quality_rules_shadow
    # 4. run_running_thresholds_b() → device_running_thresholds_shadow
    # 5. run_running_thresholds() → device_running_thresholds
    # 6. compute_metric_quality_rules() → metric_quality_rules
```

**关键问题识别**:
1. ⚠️ **Stage 1 清空了 fact_measurements**（所有历史数据）
2. ⚠️ **备份机制仅覆盖2个表**（dim_device_capabilities, dim_metric_metadata_override）
3. ⚠️ **备份方式为内存备份**（不持久化到文件）
4. ⚠️ **没有版本管理**（无法回滚到历史版本）
5. ⚠️ **没有备份验证**（无法确认备份是否成功）

---

### 2. 外键约束分析

**查询结果**: 共28个外键约束，全部使用 `ON DELETE NO ACTION`

**关键外键关系**:

```
dim_stations (id)
  ↓ ON DELETE NO ACTION
dim_devices (station_id)
  ↓ ON DELETE NO ACTION
  ├─→ calculation_parameters (device_id)
  ├─→ completion_runs (device_id)
  ├─→ completion_steps (device_id)
  ├─→ device_rated_params (device_id) [ON DELETE CASCADE]
  ├─→ device_running_thresholds_shadow (device_id)
  ├─→ dim_device_capabilities (device_id)
  └─→ dim_metric_metadata_override (device_id)

dim_metric_config (metric_key)
  ↓ ON DELETE NO ACTION
  ├─→ calculation_method_registry (metric_key)
  ├─→ calculation_parameters (metric_key)
  ├─→ dim_mapping_items (metric_key)
  ├─→ dim_metric_metadata (metric_id)
  ├─→ dim_metric_metadata_override (metric_id)
  ├─→ metric_calculation_order (metric_key)
  ├─→ metric_quality_rules_shadow (metric_id)
  └─→ metric_rule_auto_baseline_shadow (metric_id)
```

**重要发现**:
1. ✅ **大部分外键使用 NO ACTION**（安全，不会级联删除）
2. ⚠️ **device_rated_params 使用 CASCADE**（删除设备会级联删除额定参数）
3. ⚠️ **completion_audit 和 completion_failures 使用 CASCADE**（删除运行记录会级联删除审计和失败记录）
4. ✅ **没有发现会导致 fact_measurements 被级联删除的外键**

**结论**: 外键约束不是导致数据误删的主要原因，问题在于 `_clear_dependent_tables()` 函数显式删除了 fact_measurements。

---

### 3. 计算方法实现分析

**已实现的计算方法**（从 `app/services/calculation/calculators.py`）:

#### pump_flow_rate（泵流量）- 6种方法
- ✅ method_a: 功率×频率分摊
- ✅ method_b: 累计量求导
- ✅ method_c: 单泵运行直接取总管流量
- ✅ method_d: 仅功率分摊
- ✅ method_e: 仅频率分摊
- ✅ method_f: 数据驱动回归融合

#### pump_head（泵扬程）- 2种方法
- ✅ method_main: 压力差计算
- ✅ HEAD_COEF_V1: 系数化方法

#### pump_outlet_pressure（泵出口压力）- 4种方法
- ✅ method_a: 直接读取
- ✅ method_b: 以总管出口压力代替
- ✅ method_c: 由进口压力与扬程回推
- ✅ method_d: 泵组层面近似

#### pump_efficiency（泵效率）- 1种方法
- ✅ EFF_SIMPLE_V1: 简单效率计算

#### pump_speed（泵转速）- 3种方法
- ✅ method_a: 频率比例法
- ✅ method_b: 绝对转速法（电机学）
- ✅ method_c: 一次性标定

#### pump_torque（泵扭矩）- 2种方法
- ✅ method_a: 由水力功率与转速
- ✅ method_b: 由电功率与频率

#### main_pipeline_outlet_pressure（总管出口压力）- 3种方法
- ✅ method_a: 从单泵出口压力推算
- ✅ method_b: 从泵扬程与进口压力推算
- ✅ method_c: 从多泵出口压力聚合

#### main_pipeline_inlet_pressure（总管进口压力）- 1种方法
- ✅ PIN_COEF_V1: 系数化方法

#### pump_cumulative_flow（泵累计流量）- 2种方法
- ✅ method_a: 从瞬时流量积分
- ✅ method_b: 直接读取

**总计**: 25个计算方法已实现

**SQL注册表分析**（从 `scripts/sql/calculation/init_methods.sql`）:
- 文件包含11个方法的注册（pump_flow_rate 6个 + pump_head 1个 + pump_outlet_pressure 4个）
- ⚠️ **注册表不完整**：缺少 pump_efficiency, pump_speed, pump_torque, main_pipeline_* 等方法
- ⚠️ **需要补全注册表**

---

### 4. 配置表初始化分析

#### calculation_method_registry（计算方法注册表）
- **SQL脚本**: `scripts/sql/calculation/init_methods.sql`
- **当前状态**: 0行（应有11-25行）
- **问题**: 脚本存在但未执行

#### calculation_parameters（计算参数表）
- **SQL脚本**: `scripts/sql/calculation/init_params.sql`
- **当前状态**: 0行（应有7行全局默认参数）
- **问题**: 脚本存在但未执行

#### device_rated_params（设备额定参数表）
- **SQL脚本**: `scripts/migrations/20250829_seed_device_rated_params.sql`
- **当前状态**: 0行（应有8-13行）
- **问题**: 脚本存在但未执行

**结论**: 所有配置表的SQL脚本都存在，只需要在 prepare_dim stage1 中正确执行即可。

---

### 5. run_all 流程分析

**文件位置**: `app/services/run_all/orchestrator.py`

**配置文件**: `configs/merge.yaml`

**当前流程**:
```yaml
run_all:
  prepare_dim: true         # 阶段1：重建维度表（在 merge-fact 前）
  create_staging: true
  ingest_copy: true
  merge_fact: true
  prepare_dim_stage2: true  # 阶段2：生成规则表（在 merge-fact 后）
  enable_calculation: true  # 启用缺失指标计算
  device_running: true
  presence: true
  quality_mark: false
```

**执行顺序**:
1. prepare_dim(stage=1) → 重建维度表
2. create_staging → 创建暂存表
3. ingest_copy → 导入数据到暂存表
4. merge_fact → 合并数据到 fact_measurements
5. prepare_dim(stage=2) → 生成规则表
6. calculation → 计算缺失指标
7. device_running → 计算设备运行状态
8. presence → 计算存在性统计
9. quality_mark → 质量标注

**关键问题**:
- ⚠️ **prepare_dim(stage=1) 清空了 fact_measurements**
- ⚠️ **如果 merge_fact 失败，历史数据将丢失**
- ⚠️ **没有回滚机制**

---

### 6. 备份需求分析

根据任务要求，需要备份的表共17个：

#### A类：手动配置表（6个）
1. dim_device_capabilities（设备能力表）
2. dim_metric_metadata_override（指标元数据覆盖表）
3. pump_characteristic_curves（水泵特性曲线表）
4. quality_code_dict（质量代码字典表）
5. calculation_validation_config（计算验证配置表）
6. metric_capability_policy（指标能力策略表）

#### B类：配置表（4个）
7. calculation_parameters（计算参数表）
8. device_rated_params（设备额定参数表）
9. calculation_method_registry（计算方法注册表）
10. metric_calculation_order（指标计算顺序表）

#### C类：维度表（1个）
11. dim_metric_config（指标配置维度表）

#### D类：规则表（6个）
12. metric_rule_auto_baseline（自动基线表）
13. metric_rule_auto_baseline_shadow（自动基线影子表）
14. metric_quality_rules（质量规则表）
15. metric_quality_rules_shadow（质量规则影子表）
16. device_running_thresholds（运行阈值表）
17. device_running_thresholds_shadow（运行阈值影子表）

**当前备份覆盖率**: 2/17 = 11.8%

---

## 🚨 问题诊断

### 问题1：fact_measurements 被误删 ⚠️ **严重**

**根本原因**:
- `_clear_dependent_tables()` 函数在第1层就删除了 fact_measurements
- 这是显式的 DELETE 操作，不是外键级联删除

**代码位置**: `app/services/ingest/prepare_dim/__init__.py:521-537`

```python
# 第1层：依赖 dim_devices 和 dim_metric_config 的表
tables_layer1 = [
    "fact_measurements",  # ⚠️ 这里删除了所有历史数据
    "completion_runs",
    "completion_steps",
    ...
]

for table in tables_layer1:
    cur.execute(f"DELETE FROM {table}")
```

**影响范围**:
- ❌ 所有历史测量数据丢失
- ❌ 无法恢复（没有备份）
- ❌ 规则表无法生成（依赖历史数据）

**解决方案**:
- ✅ **不应该清空 fact_measurements**
- ✅ **如果必须清空，应该先备份**

---

### 问题2：备份机制不完整 ⚠️ **严重**

**当前备份**:
- 仅备份2个表（dim_device_capabilities, dim_metric_metadata_override）
- 使用内存备份（不持久化）
- 没有版本管理
- 没有备份验证

**缺失的备份**:
- 15个表没有备份
- fact_measurements 没有备份
- 配置表没有备份
- 规则表没有备份

**解决方案**:
- ✅ 实现文件备份系统
- ✅ 实现版本管理（保留60个版本）
- ✅ 实现备份验证
- ✅ 实现增量备份（只备份变化的表）

---

### 问题3：配置表未初始化 ⚠️ **中等**

**问题**:
- calculation_method_registry: 0行（应有11-25行）
- calculation_parameters: 0行（应有7行）
- device_rated_params: 0行（应有8-13行）
- metric_calculation_order: 0行（应有>0行）

**原因**:
- SQL脚本存在但未执行
- `_rebuild_config_tables()` 函数可能执行失败

**解决方案**:
- ✅ 验证SQL脚本路径
- ✅ 添加错误处理和日志
- ✅ 验证执行结果

---

## 📊 数据依赖关系图

```
[配置文件]
  ├─→ data_mapping.v2.json → dim_stations, dim_devices
  ├─→ dim_metric_config.sql → dim_metric_config
  ├─→ init_methods.sql → calculation_method_registry
  ├─→ init_params.sql → calculation_parameters
  └─→ seed_device_rated_params.sql → device_rated_params

[维度表]
  dim_stations → dim_devices → [多个依赖表]
  dim_metric_config → [多个依赖表]

[事实表]
  fact_measurements ⭐⭐⭐⭐⭐ [核心数据，不应清空]

[规则表]（依赖 fact_measurements）
  fact_measurements → metric_rule_auto_baseline → metric_quality_rules
  fact_measurements → device_running_thresholds
```

---

## 🎯 关键洞察

1. **fact_measurements 不应该被清空**
   - 这是核心数据表
   - 规则表的生成依赖它
   - 清空它会导致数据丢失

2. **备份系统需要重新设计**
   - 当前备份覆盖率仅11.8%
   - 需要文件备份而非内存备份
   - 需要版本管理和验证

3. **配置表初始化需要修复**
   - SQL脚本存在但未正确执行
   - 需要添加错误处理和验证

4. **外键约束不是问题**
   - 大部分使用 NO ACTION（安全）
   - 没有导致 fact_measurements 被级联删除的外键

5. **计算方法实现完整**
   - 25个方法已实现
   - 但注册表不完整（需要补全）

---

## 📝 下一步行动

### 立即行动（研究阶段完成后）
1. ✅ 进入创新模式，讨论备份系统设计方案
2. ✅ 讨论 prepare_dim 流程重构方案
3. ✅ 讨论外键约束处理策略

### 待确认问题
1. ❓ **是否真的需要清空 fact_measurements？**
   - 如果不需要，直接移除清空逻辑
   - 如果需要，必须先备份

2. ❓ **备份格式选择？**
   - SQL脚本（pg_dump）
   - 二进制备份（pg_dump -Fc）
   - CSV导出

3. ❓ **版本管理策略？**
   - 保留60个版本
   - 按时间戳命名
   - 自动清理旧版本

---

**研究阶段完成** ✅

准备进入创新模式，讨论解决方案。

