# dim_metric_config 依赖关系分析报告

## 📋 文档信息

**分析日期**：2025-10-27  
**分析目标**：识别所有与 `dim_metric_config.metric_key` 和 `dim_metric_config.id` 关联的数据库表  
**扫描范围**：所有schema（public、monitoring、reporting等）  
**文档版本**：v1.0

---

## 🔍 全面扫描结果

### 扫描统计

| 维度 | 数量 | 说明 |
|------|------|------|
| **总表数** | 23个 | 包含 metric_id 或 metric_key 的所有基础表 |
| **配置数据表** | 10个 | 影响程序如何运行的参数和规则 |
| **历史数据表** | 7个 | 记录程序运行结果的数据 |
| **物化视图** | 2个 | 从基础表计算得出的数据 |
| **映射表** | 1个 | 数据映射关系表 |
| **Shadow表** | 2个 | 影子输出表（用于对比和验证） |
| **已有外键的表** | 8个 | 已配置 ON UPDATE CASCADE ON DELETE CASCADE |
| **缺少外键的配置表** | 4个 | 需要添加外键约束 |

---

## 📊 完整表分类清单

### 分类1：配置数据（需要跟随ID变化）- 10个

| 表名 | 关联列 | 当前外键状态 | 记录数 | 优先级 | 风险说明 |
|------|--------|-------------|--------|--------|---------|
| **calculation_method_registry** | metric_key | ✅ 有外键CASCADE | 28 | - | 无风险 |
| **calculation_parameters** | metric_key | ✅ 有外键CASCADE | 38 | - | 无风险 |
| **calculation_validation_config** | metric_key | ❌ 无外键 | 50 | **P0** | **ID变化后验证失效** |
| **metric_calculation_order** | metric_key | ✅ 有外键CASCADE | 21 | - | 无风险 |
| **metric_capability_policy** | metric_key | ❌ 无外键 | 53 | **P1** | ID变化后能力判定失效 |
| **metric_quality_rules** | metric_id | ❌ 无外键 | 0 | **P1** | ID变化后质量评价失效 |
| **metric_rule_auto_baseline** | metric_id | ❌ 无外键 | 0 | **P1** | ID变化后基线生成失效 |
| **metric_anomaly_strategy** | metric_id | ❌ 无外键 | 0 | **P1** | ID变化后异常检测失效 |
| **dim_metric_metadata** | metric_id | ✅ 有外键CASCADE | 0 | - | 无风险 |
| **dim_metric_metadata_override** | metric_id | ✅ 有外键CASCADE | 0 | - | 无风险 |

**小计**：10个配置表，其中4个缺少外键约束

---

### 分类2：历史数据（不需要跟随ID变化）- 7个

| 表名 | 关联列 | 当前外键状态 | 记录数 | 说明 |
|------|--------|-------------|--------|------|
| **fact_measurements** | metric_id | ❌ 无外键 | 0 | 历史数据，保留历史ID是合理的 |
| **completion_steps** | metric_id | ❌ 无外键 | 5 | 完成步骤记录，历史数据 |
| **calculation_failures_log** | metric_key | ❌ 无外键 | 0 | 计算失败日志，历史数据 |
| **optimization_history** | metric_key | ❌ 无外键 | 2 | 优化历史记录，历史数据 |
| **quality_eval_by_device_metric** | metric_id | ❌ 无外键 | 0 | 质量评价统计，报表数据 |
| **staging_raw** | metric_key | ❌ 无外键 | 0 | 导入暂存原始数据 |
| **staging_rejects** | metric_key | ❌ 无外键 | 0 | 导入拒收记录 |

**小计**：7个历史数据表，不需要外键约束

---

### 分类3：物化视图（不需要外键约束）- 2个

| 表名 | 关联列 | 说明 |
|------|--------|------|
| **mv_metric_60s_stats** | metric_id | 60s窗口基础统计，定期刷新 |
| **mv_presence_1s** | metric_id | 秒级覆盖结果，定期刷新 |

**小计**：2个物化视图，定期刷新时自动更新

---

### 分类4：映射表（已有外键）- 1个

| 表名 | 关联列 | 当前外键状态 | 记录数 | 说明 |
|------|--------|-------------|--------|------|
| **dim_mapping_items** | metric_key | ✅ 有外键CASCADE | 0 | 数据映射关系表 |

---

### 分类5：Shadow表（已有外键）- 2个

| 表名 | 关联列 | 当前外键状态 | 记录数 | 说明 |
|------|--------|-------------|--------|------|
| **metric_quality_rules_shadow** | metric_id | ✅ 有外键CASCADE | 54 | 影子输出：方案B质量规则参数 |
| **metric_rule_auto_baseline_shadow** | metric_id | ✅ 有外键CASCADE | 54 | 影子输出：方案B自动基线 |

---

## 🎯 业务逻辑详细分析

### 配置数据表详细分析

#### 1. calculation_method_registry（已有外键 - 无风险）

**表用途**：计算方法注册表，记录每个指标的所有计算方法

**在系统中的作用**：
1. **方法选择**：程序读取该表选择最合适的计算方法
2. **依赖分析**：程序读取该表分析指标依赖关系
3. **计算顺序**：程序根据该表确定指标计算顺序

**代码使用证据**：
- `app/services/calculation/method_selector.py::MethodSelector._load_methods_from_db()` - 加载计算方法注册表
- `app/services/calculation/dependency_analyzer.py::DependencyAnalyzer._load_methods_from_db()` - 加载方法依赖关系

**如果metric_key不同步会导致什么问题**：
- ❌ 程序无法找到指标的计算方法
- ❌ 计算流程完全失效
- ❌ 所有依赖该指标的计算都会失败

**当前状态**：✅ 已有外键约束（ON UPDATE CASCADE ON DELETE CASCADE），无风险

---

#### 2. calculation_parameters（已有外键 - 无风险）

**表用途**：计算参数表，存储每个设备每个指标每个方法的参数

**在系统中的作用**：
1. **参数加载**：程序读取该表加载计算参数（5层参数优先级）
2. **参数优化**：程序更新该表保存优化后的参数
3. **参数管理**：程序通过该表管理不同层级的参数

**代码使用证据**：
- `app/services/calculation/orchestrator.py::Orchestrator.load_parameters()` - 加载计算参数（5层优先级）

**5层参数优先级**：
1. 全局计算参数（calculation_parameters, device_id=NULL, station_id=NULL）
2. 全局默认额定参数（global_default_rated_params）
3. 设备额定参数（device_rated_params, device_id=X）
4. 泵站级计算参数（calculation_parameters, station_id=X, device_id=NULL）
5. 设备级计算参数（calculation_parameters, device_id=X）

**如果metric_key不同步会导致什么问题**：
- ❌ 程序无法加载正确的计算参数
- ❌ 计算结果不准确
- ❌ 参数优化失效

**当前状态**：✅ 已有外键约束（ON UPDATE CASCADE ON DELETE CASCADE），无风险

---

#### 3. calculation_validation_config（P0 - 立即执行）

**表用途**：计算结果验证配置表

**在系统中的作用**：
1. **结果验证**：程序读取该表的验证规则验证计算结果
2. **异常检测**：程序根据验证规则检测计算异常
3. **质量保证**：程序通过验证规则保证计算质量

**代码使用证据**：
- `app/services/calculation/validator.py::Validator._load_validation_config()` - 加载验证配置（支持层级）

**验证配置优先级**：
- 设备级 > 站点级 > 全局级

**如果metric_key不同步会导致什么问题**：
- ❌ 程序无法验证计算结果
- ❌ 错误的计算结果可能被接受
- ❌ 数据质量无法保证

**当前状态**：❌ 无外键约束，**P0优先级（立即执行）**

---

#### 4. metric_calculation_order（已有外键 - 无风险）

**表用途**：指标计算顺序表，记录指标的依赖关系和拓扑排序结果

**在系统中的作用**：
1. **计算顺序**：程序读取该表确定指标计算顺序
2. **依赖管理**：程序根据该表管理指标依赖关系
3. **循环检测**：程序通过该表检测循环依赖

**代码使用证据**：
- `app/services/calculation/dependency_analyzer.py::DependencyAnalyzer.save_calculation_order()` - 保存计算顺序

**如果metric_key不同步会导致什么问题**：
- ❌ 程序无法确定正确的计算顺序
- ❌ 依赖指标可能在被依赖指标之后计算
- ❌ 计算结果不正确

**当前状态**：✅ 已有外键约束（ON UPDATE CASCADE ON DELETE CASCADE），无风险

---

#### 5. metric_capability_policy（P1 - 1个月内）

**表用途**：指标获取/计算能力策略表，记录每个metric_key的获取情况和是否需要计算

**在系统中的作用**：
1. **能力判定**：程序读取该表判断指标是否可以获取或需要计算
2. **策略管理**：程序根据该表管理指标的获取和计算策略
3. **资源优化**：程序通过该表优化计算资源分配

**字段说明**：
- `acquisition_status`：获取情况（不能/可能/可以）
- `compute_flag`：是否计算（需要/不需要）

**如果metric_key不同步会导致什么问题**：
- ❌ 程序无法判断指标是否需要计算
- ❌ 可能尝试计算无法计算的指标
- ❌ 可能忽略需要计算的指标

**当前状态**：❌ 无外键约束，**P1优先级（1个月内）**

---

#### 6. metric_quality_rules（P1 - 1个月内）

**表用途**：度量质量规则阈值（手工覆盖）

**在系统中的作用**：
1. **质量评价**：程序读取该表的阈值判断数据质量
2. **异常检测**：程序读取该表的规则参数检测数据异常
3. **数据过滤**：程序根据质量规则过滤无效数据

**代码使用证据**：
- `app/services/rules/metric_quality_rules.py::compute_metric_quality_rules()` - 基于自动基线填充/补全质量规则

**如果metric_id不同步会导致什么问题**：
- ❌ 程序无法应用正确的质量规则
- ❌ 数据质量评价失效
- ❌ 异常数据可能被接受

**当前状态**：❌ 无外键约束，**P1优先级（1个月内）**

---

#### 7. metric_rule_auto_baseline（P1 - 1个月内）

**表用途**：自动基线，从历史有效数据计算出的缺省阈值

**在系统中的作用**：
1. **基线生成**：程序从历史数据计算自动基线
2. **规则补全**：程序使用自动基线补全质量规则
3. **阈值建议**：程序提供自动计算的阈值建议

**代码使用证据**：
- `app/services/rules/auto_baseline.py::run_auto_baseline()` - 调用存储过程刷新自动基线
- `app/services/rules/metric_quality_rules.py::compute_metric_quality_rules()` - 使用自动基线填充质量规则

**如果metric_id不同步会导致什么问题**：
- ❌ 程序无法生成正确的自动基线
- ❌ 质量规则补全失效
- ❌ 阈值建议不准确

**当前状态**：❌ 无外键约束，**P1优先级（1个月内）**

---

#### 8. metric_anomaly_strategy（P1 - 1个月内）

**表用途**：异常判定策略声明，为每个指标定义采用的判定方法与关键参数来源

**在系统中的作用**：
1. **异常检测**：程序读取该表的策略进行异常检测
2. **策略管理**：程序根据该表管理异常判定策略
3. **参数配置**：程序通过该表配置异常检测参数

**策略类型**：
- `work_condition`：工况策略
- `physics`：物理策略
- `residual`：残差策略
- `hybrid`：混合策略

**如果metric_id不同步会导致什么问题**：
- ❌ 程序无法应用正确的异常检测策略
- ❌ 异常检测失效
- ❌ 异常数据可能被忽略

**当前状态**：❌ 无外键约束，**P1优先级（1个月内）**

---

#### 9. dim_metric_metadata（已有外键 - 无风险）

**表用途**：全局指标物理元数据表，存储单位、分辨率、物理边界等

**在系统中的作用**：
1. **元数据管理**：程序读取该表获取指标元数据
2. **单位转换**：程序使用该表的单位信息进行转换
3. **边界检查**：程序使用该表的物理边界进行检查

**代码使用证据**：
- `scripts/sql/migrations/022_alter_sp_refresh_metric_rule_auto_baseline_meta.sql` - 存储过程使用元数据
- `app/services/rules/auto_baseline_b.py` - 使用 v_effective_metric_metadata 视图

**如果metric_id不同步会导致什么问题**：
- ❌ 程序无法获取正确的指标元数据
- ❌ 单位转换失效
- ❌ 边界检查不准确

**当前状态**：✅ 已有外键约束（ON UPDATE CASCADE ON DELETE CASCADE），无风险

---

#### 10. dim_metric_metadata_override（已有外键 - 无风险）

**表用途**：指标元数据覆盖表，可按站点/设备粒度覆盖全局默认

**在系统中的作用**：
1. **元数据覆盖**：程序读取该表获取特定站点/设备的元数据覆盖
2. **优先级管理**：程序按优先级（设备 > 站点 > 全局）应用元数据
3. **精细化配置**：程序通过该表实现精细化的元数据配置

**优先级**：设备 > 站点 > 全局

**如果metric_id不同步会导致什么问题**：
- ❌ 程序无法应用正确的元数据覆盖
- ❌ 特定站点/设备的配置失效
- ❌ 元数据不准确

**当前状态**：✅ 已有外键约束（ON UPDATE CASCADE ON DELETE CASCADE），无风险

---

## 📝 外键需求分析

### 需要添加外键的表（4个）

| 表名 | 关联列 | 目标表 | 目标列 | 优先级 | 记录数 | 风险等级 |
|------|--------|--------|--------|--------|--------|---------|
| **calculation_validation_config** | metric_key | dim_metric_config | metric_key | **P0** | 50 | **极高** |
| **metric_capability_policy** | metric_key | dim_metric_config | metric_key | **P1** | 53 | 高 |
| **metric_quality_rules** | metric_id | dim_metric_config | id | **P1** | 0 | 高 |
| **metric_rule_auto_baseline** | metric_id | dim_metric_config | id | **P1** | 0 | 高 |
| **metric_anomaly_strategy** | metric_id | dim_metric_config | id | **P1** | 0 | 高 |

### 不需要外键的表（12个）

**历史数据表（7个）**：
- fact_measurements, completion_steps, calculation_failures_log, optimization_history, quality_eval_by_device_metric, staging_raw, staging_rejects

**物化视图（2个）**：
- mv_metric_60s_stats, mv_presence_1s

**其他（3个）**：
- dim_metric_config（维度表本身）

---

## 🎯 优先级建议

### P0优先级（立即执行）- 1个表

**calculation_validation_config**：
- **风险等级**：极高
- **影响范围**：计算结果验证失效
- **业务影响**：错误的计算结果可能被接受，数据质量无法保证
- **建议**：立即添加外键约束

### P1优先级（1个月内）- 3个表

**metric_capability_policy**：
- **风险等级**：高
- **影响范围**：指标能力判定失效
- **业务影响**：可能尝试计算无法计算的指标，或忽略需要计算的指标

**metric_quality_rules**：
- **风险等级**：高
- **影响范围**：质量评价失效
- **业务影响**：数据质量评价不准确，异常数据可能被接受

**metric_rule_auto_baseline**：
- **风险等级**：高
- **影响范围**：基线生成失效
- **业务影响**：质量规则补全失效，阈值建议不准确

**metric_anomaly_strategy**：
- **风险等级**：高
- **影响范围**：异常检测失效
- **业务影响**：异常数据可能被忽略

---

## 📊 完整统计

### 表分类统计

| 分类 | 数量 | 需要外键 | 已有外键 | 缺少外键 | 优先级 |
|------|------|---------|---------|---------|--------|
| **配置数据表** | 10个 | 10个 | 6个 | 4个 | P0: 1个, P1: 3个 |
| **历史数据表** | 7个 | 0个 | 0个 | 0个 | 无需操作 |
| **物化视图** | 2个 | 0个 | 0个 | 0个 | 无需操作 |
| **映射表** | 1个 | 1个 | 1个 | 0个 | 无风险 |
| **Shadow表** | 2个 | 2个 | 2个 | 0个 | 无风险 |

### 外键约束统计

| 维度 | 数量 | 百分比 |
|------|------|--------|
| **需要外键的配置表** | 10个 | 100% |
| **已有外键的配置表** | 6个 | 60% |
| **缺少外键的配置表** | 4个 | 40% |
| **P0优先级** | 1个 | 10% |
| **P1优先级** | 3个 | 30% |

---

**文档版本**：v1.0  
**分析日期**：2025-10-27  
**状态**：✅ 依赖关系分析完成  
**下一步**：创建SQL脚本，为缺少外键的配置表添加外键约束

