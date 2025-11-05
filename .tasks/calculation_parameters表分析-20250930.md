# calculation_parameters 表分析任务

**创建时间**：2025-09-30
**任务类型**：数据库表设计分析与优化
**当前模式**：研究

---

## 任务目标

全面分析数据库表 `calculation_parameters` 的设计合理性、使用情况和字段完整性。

**核心问题**：
- 该表目前只有全局参数，没有泵站级（station_id）或设备级（device_id）的参数配置，这种设计是否合理？
- 如果不同泵站或设备需要不同的计算参数，现有表结构能否支持？

---

## 项目规则摘要

### 数据库规范（强制）
- 所有表必须有注释（COMMENT ON TABLE）
- 关键列必须有注释（COMMENT ON COLUMN）
- 注释必须使用中文
- 表命名：小写+下划线，复数形式
- 列命名：小写+下划线
- 外键命名：引用表名_id
- 时序数据查询必须包含时间范围

### 代码规范（强制）
- 所有注释必须使用中文
- 禁止使用代码占位符
- 必须使用参数化查询

---

## 记忆检索结果

### 研究模式检索

**待检索内容**：
- calculation_parameters 表结构
- 相关的配置表设计模式
- 使用该表的代码文件和函数
- 参数读取模式

---

## 记忆验证结果

**待验证内容**：
- 表结构是否存在
- 字段列表是否准确
- 使用该表的代码文件是否存在

---

## 代码分析

### 表结构分析

**表基本信息**：
- 表名：calculation_parameters
- Schema：public
- 表注释：✅ 完整详细（包含用途、参数粒度、优先级系统、参数字典）
- 字段数量：22个
- 索引数量：8个
- 外键约束：4个（station_id、device_id、metric_key、method_id）

**字段完整性**：
- ✅ 所有22个字段都有中文注释
- ✅ 注释质量高，包含字段含义、单位、取值范围
- ✅ 表注释包含完整的参数字典（50+个参数的详细说明）

**分层参数支持**：
- ✅ **已支持分层参数**（station_id、device_id字段）
- ✅ 支持3个粒度：
  * 全局参数：station_id=NULL, device_id=NULL
  * 泵站级参数：station_id=X, device_id=NULL
  * 设备级参数：station_id=X, device_id=Y
- ✅ 唯一约束：(device_id, metric_key, method_id, param_name)

**当前数据分布**：
- 全局参数：50个（14个方法，9个指标）
- 泵站级参数：0个
- 设备级参数：0个

### 使用情况分析

**参数读取代码**（orchestrator.py）：
- ✅ **已实现6层参数优先级系统**（lines 685-823）
  1. 全局计算参数（calculation_parameters, device_id=NULL, station_id=NULL）
  2. 全局默认额定参数（global_default_rated_params）
  3. 设备额定参数（device_rated_params, device_id=X）
  3.5. 泵站级额定参数（device_rated_params, station_id=X, device_id=NULL）
  4. 泵站级计算参数（calculation_parameters, station_id=X, device_id=NULL）
  5. 设备级计算参数（calculation_parameters, device_id=X）- 最高优先级

**参数写入代码**：
- ✅ 初始化脚本：scripts/sql/adaptive/03_calculation_parameters.sql
- ✅ RLS优化算法：app/services/calculation/parameter_optimizer.py
- ✅ 迁移脚本：scripts/sql/migrations/072_add_device_level_calculation_params.sql

**参数优化功能**：
- ✅ 支持RLS算法自动优化（is_optimizable=true的参数）
- ✅ 保存优化历史（optimization_history字段，JSONB格式，保留最近10次）
- ✅ 记录置信度（confidence_score字段）
- ✅ 记录优化次数（optimization_count字段）
- ✅ 支持参数范围约束（param_min、param_max字段）

### 字段完整性分析

**核心字段**：
- id：主键，自增
- station_id：泵站ID（可空，NULL表示全局或设备级）
- device_id：设备ID（可空，NULL表示全局或泵站级）
- metric_key：指标键（外键，关联dim_metric_config）
- method_id：方法ID（外键，关联calculation_method_registry）
- param_name：参数名称（如alpha、beta、rho、g等）
- param_value：参数值（numeric类型）
- param_value_text：字符串类型参数值（param_type=string时使用）
- param_type：参数类型（numeric、integer、boolean、string）

**优化相关字段**：
- is_optimizable：是否可优化（boolean）
- optimization_history：优化历史记录（JSONB）
- confidence_score：参数置信度（0-1）
- last_optimized_at：最后优化时间
- optimization_count：优化次数
- param_min/param_max：参数范围约束
- covariance_matrix：协方差矩阵（JSONB，RLS算法使用）
- rls_iterations：RLS迭代次数
- last_p_trace：P矩阵迹（用于监控收敛）

**审计字段**：
- created_at：创建时间
- updated_at：更新时间
- updated_by：更新者（system、RLS算法、手动调整等）

---

## 关键发现

### 发现1：表设计已支持分层参数 ✅

**结论**：该表设计**完全支持**分层参数配置（全局、泵站级、设备级）

**证据**：
1. ✅ 表结构包含 station_id 和 device_id 字段（均可空）
2. ✅ 唯一约束包含 device_id：(device_id, metric_key, method_id, param_name)
3. ✅ 外键约束：station_id → dim_stations, device_id → dim_devices
4. ✅ 索引支持分层查询：idx_cp_global, idx_cp_station, idx_cp_device_metric
5. ✅ 表注释明确说明3个粒度和5层优先级系统

**表注释摘录**：
```
参数粒度：
  - 全局参数：station_id=NULL, device_id=NULL（优先级最低，第1层）
  - 泵站级参数：station_id=X, device_id=NULL（优先级中等，第4层）
  - 设备级参数：station_id=X, device_id=Y（优先级最高，第5层）
```

### 发现2：代码已实现完整的参数优先级系统 ✅

**结论**：orchestrator.py 的 load_parameters() 方法已实现6层参数优先级

**证据**：
- 第716-732行：加载全局计算参数（最低优先级）
- 第734-751行：加载全局默认额定参数
- 第753-770行：加载设备额定参数
- 第772-789行：加载泵站级额定参数
- 第791-801行：加载泵站级计算参数
- 第803-816行：加载设备级计算参数（最高优先级）

**参数覆盖逻辑**：高优先级参数覆盖低优先级参数（字典更新）

### 发现3：当前只有全局参数，未使用分层功能 ⚠️

**现状**：
- 全局参数：50个（14个方法，9个指标）
- 泵站级参数：0个
- 设备级参数：0个

**原因分析**：
1. 系统刚上线，尚未进行参数定制化
2. 全局参数已能满足当前业务需求
3. 迁移脚本072已准备好设备级参数模板（但未执行或被回滚）

**潜在问题**：
- 如果不同泵站或设备的物理特性差异较大，全局参数可能不够精确
- 例如：不同设备的电机效率（eta_motor）、滑差率（slip）、极对数（pole_pairs）可能不同

### 发现4：字段注释质量极高 ✅

**优点**：
- ✅ 所有22个字段都有中文注释
- ✅ 注释包含字段含义、单位、取值范围
- ✅ 表注释包含完整的参数字典（50+个参数的详细说明）
- ✅ 每个参数都有：物理含义、计算公式、单位、典型范围、示例值、用途、是否可优化

**示例**（alpha参数）：
```
• alpha（流量系数）
  - 物理含义：功率权重指数，反映功率变化对流量分配的影响程度
  - 计算公式：Q_i = Q_total × (P_i^alpha × f_i^beta) / Σ(P_j^alpha × f_j^beta)
  - 单位：无量纲
  - 典型范围：0.5 ~ 1.5
  - 示例值：1.0
  - 用途：用于流量分配计算，反映功率对流量的影响
  - 是否可优化：是
```

### 发现5：参数优化功能设计完善但未启用 ⚠️

**设计完善**：
- ✅ 支持RLS算法自动优化
- ✅ 保存优化历史（最近10次）
- ✅ 记录置信度和优化次数
- ✅ 支持参数范围约束
- ✅ 支持协方差矩阵和收敛监控

**未启用原因**（根据代码分析）：
- orchestrator.py 第1256行：enable_optimization=False（默认禁用）
- 第1769行：if self.enable_optimization and self.parameter_optimizer is not None（条件永远为False）

**影响**：
- 参数值一直使用初始值，未经过实际数据优化
- optimization_count、last_optimized_at等字段未被使用

---

## 需要澄清的问题

### 问题1：是否需要启用分层参数？

**背景**：
- 表设计已支持分层参数（全局、泵站级、设备级）
- 代码已实现6层参数优先级系统
- 但当前只有全局参数，未使用分层功能

**需要确认**：
1. 不同泵站或设备的物理特性是否有显著差异？
2. 是否需要为特定设备定制参数（如电机效率、滑差率）？
3. 是否需要为特定泵站定制参数（如流体密度、重力加速度）？

### 问题2：是否需要启用参数优化功能？

**背景**：
- 参数优化功能（RLS算法）已实现但未启用
- 当前参数值使用初始值，未经过实际数据优化

**需要确认**：
1. 是否需要启用参数优化功能？
2. 优化目标是什么（最小化计算误差、最大化计算成功率）？
3. 优化频率是多少（每天、每周、每月）？

### 问题3：迁移脚本072的执行状态？

**背景**：
- 迁移脚本072准备了设备级参数模板（为6台泵补充8个方法的参数）
- 但当前数据库中没有设备级参数

**需要确认**：
1. 迁移脚本072是否已执行？
2. 如果已执行，为什么没有设备级参数（是否被回滚）？
3. 如果未执行，是否需要执行？

---

## 对比分析：calculation_parameters vs device_running_thresholds

### 设计模式对比

**device_running_thresholds 表**：
- ✅ **设备级配置表**（device_id为主键，NOT NULL）
- ✅ 每个设备一行，存储该设备的运行判定阈值
- ✅ 不支持全局参数或泵站级参数
- ✅ 设计简单，适用于设备特定的阈值配置

**calculation_parameters 表**：
- ✅ **分层参数表**（支持全局、泵站级、设备级）
- ✅ 每个参数一行，支持多粒度配置
- ✅ 唯一约束：(device_id, metric_key, method_id, param_name)
- ✅ 设计复杂，适用于需要分层覆盖的参数配置

### 设计合理性评估

**结论**：calculation_parameters 表的分层设计**非常合理**

**理由**：
1. ✅ **物理常数适合全局参数**：
   - 重力加速度（g=9.80665）、流体密度（rho=1000）、大气压（P_atm=0.101325）
   - 这些参数在所有泵站和设备中都相同，全局参数避免重复配置

2. ✅ **设备特性适合设备级参数**：
   - 电机效率（eta_motor）、滑差率（slip）、极对数（pole_pairs）
   - 不同设备的电机型号不同，这些参数应该按设备定制

3. ✅ **计算系数适合优化和分层**：
   - 流量系数（alpha、beta）、扬程系数（a0-a5）
   - 可以先使用全局默认值，再通过RLS算法优化为设备级参数

4. ✅ **优先级系统支持渐进式定制**：
   - 初期：只配置全局参数，快速上线
   - 中期：为特殊设备配置设备级参数
   - 长期：通过RLS算法自动优化设备级参数

**对比 device_running_thresholds**：
- device_running_thresholds 的阈值（i_on、p_on、f_on）高度依赖设备特性，不适合全局参数
- calculation_parameters 的参数既有全局常数，也有设备特性，分层设计更合理

---

## 记忆更新日志

### 研究模式更新

**已验证的记忆**：
- ✅ calculation_parameters 表结构完整，支持分层参数
- ✅ orchestrator.py 已实现6层参数优先级系统
- ✅ 表注释质量极高，包含完整的参数字典

**新增记忆**：
- 📝 当前只有全局参数（50个），未使用分层功能
- 📝 参数优化功能已实现但未启用（enable_optimization=False）
- 📝 迁移脚本072准备了设备级参数模板但未执行

**需要澄清的问题**：
- ❓ 是否需要启用分层参数（泵站级、设备级）
- ❓ 是否需要启用参数优化功能（RLS算法）
- ❓ 迁移脚本072的执行状态


---

## 提议的解决方案

### 创新模式方案设计

用户选择：**组合C - 激进组合（高风险、高成本）**

**具体方案**：
1. **分层参数**：方案1C - 全面启用设备级参数（为所有设备配置设备级参数）
2. **参数优化**：方案2C - 全面启用参数优化（为所有可优化参数启用RLS算法）
3. **迁移脚本072**：方案3C - 修改脚本使用准确参数（从device_rated_params表获取准确的设备级参数）
4. **审计字段**：方案4C - 完善所有审计字段（updated_by、notes等）

**风险确认**：
- 当前系统只有2小时的历史数据（634,530行，8台设备，2025-05-31 18:00:00 ~ 19:59:59）
- 不满足方案建议的"至少6个月数据积累"要求（相差2160倍）
- 用户已理解并接受高风险、高成本方案
- 用户承诺逐步补充历史数据

**设备范围限定**：
- 只为水泵设备（type='pump'）和总管设备（type='main_pipeline'）配置设备级参数
- 设备ID列表：1-7（设备8为"其他"，is_active=false，不配置）
- 设备详情：
  * 设备1-6：二期供水泵房1-6#泵（type='pump', pump_type='variable_frequency'）
  * 设备7：二期供水泵房总管（type='main_pipeline'）

### 计划模式详细实施计划

（见下方详细计划）
