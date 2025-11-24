# pump_flow_rate 迁移计划研究任务

**创建日期**：2025-11-11
**任务类型**：研究 → 创新 → 计划 → 执行 → 审查
**当前模式**：研究
**状态**：进行中

---

## 📋 任务目标

基于最新的混合架构详细设计文档（`缺失指标计算改造\01-架构设计\混合架构详细设计.md`），重新编写 `pump_flow_rate` 指标的完整迁移计划。

**核心要求**：
1. 完整删除所有旧代码、配置和数据库内容
2. 实现生产就绪的完整代码（不使用占位符）
3. 提供详细的数据库改造方案
4. 包含完整的验证和优化方案
5. 提供详细的实施步骤

---

## 🔍 研究阶段记录

### 步骤1: 规则文档读取 ✅

**已读取文件**：
- `规则/核心模块/规则-核心原则.md` ✅
- `规则/模式模块/规则-模式1-研究.md` ✅
- `规则/核心模块/规则-记忆系统.md` ✅

**关键规则摘要**：
1. 禁止使用代码占位符（除非计划明确要求）
2. 禁止修改不相关的代码
3. 必须完整删除废弃内容
4. 所有代码必须是生产就绪的
5. 必须使用中文注释和日志

---

### 步骤2: 架构文档分析 ✅

**已读取文件**：
- `缺失指标计算改造\01-架构设计\混合架构详细设计.md` ✅ (1307行)

**核心架构要点**：
1. **混合架构**：管道框架 + 策略模式
2. **五大核心问题解决**：
   - 问题1：人为配置计算顺序（不使用依赖分析器）
   - 问题2：指标独立的数据获取
   - 问题3：指标独立的方法选择
   - 问题4：指标独立的验证规则
   - 问题5：指标独立的优化策略

3. **核心组件**：
   - `MetricPipelineOrchestrator`：管道编排器
   - `MetricStrategy`：策略基类
   - `FilterConfig`：过滤配置
   - `CalculationContext`：计算上下文
   - `MetricResult`：计算结果
   - `ValidationResult`：验证结果

4. **pump_flow_rate 特性**：
   - 不需要 running=1 过滤
   - 不需要 freq>=3.0 过滤
   - 不需要 power>=0.5 过滤
   - 5个计算方法（A/B/C/D/E）
   - 独立的验证规则
   - 独立的优化策略（3σ方法 + 移动平均）

---

### 步骤3: 现有代码分析 ✅

**已检索文件**：
- `app/services/calculation/calculators.py` ✅
- `app/services/calculation/orchestrator.py` ✅
- `scripts/sql/calculation/init_methods.sql` ✅
- `缺失指标计算改造/02-实施计划/阶段1-pump_flow_rate迁移计划.md` ✅

**需要删除的代码**：

#### Python 代码（app/services/calculation/calculators.py）
1. `calculate_pump_flow_rate_method_a` (行48-101)
2. `calculate_pump_flow_rate_method_b` (行158-187)
3. `calculate_pump_flow_rate_method_c` (行190-211)
4. `calculate_pump_flow_rate_method_d` (行214-242)
5. `calculate_pump_flow_rate_method_e` (行245-273)
6. `calculate_pump_flow_rate_method_f` (行276-310)
7. CALCULATOR_REGISTRY 中的6个条目 (行1114-1119)

#### Python 代码（app/services/calculation/orchestrator.py）
1. `_prepare_flow_rate_share` 函数 (行1635-1787)
2. 该函数的所有调用点

#### 测试代码
1. `tests/unit/services/calculation/test_calculators_functions.py` 中的 `TestPumpFlowRateCalculations` 类

#### 配置文件
1. `configs/merge.yaml` - 注释掉 pump_flow_rate
2. `configs/compute.example.yaml` - 注释掉 pump_flow_rate

---

### 步骤4: 数据库结构分析 ✅

**已查询表结构**：
- `calculation_method_registry` ✅
- `calculation_parameters` ✅
- `calculation_validation_config` ✅
- `dim_metric_config` ✅
- `fact_measurements` ✅

**需要删除的数据库记录**：
1. `calculation_method_registry` - 6条记录（method_a到method_f）
2. `calculation_parameters` - 所有 metric_key='pump_flow_rate' 的记录
3. `calculation_validation_config` - 所有 metric_key='pump_flow_rate' 的记录

**需要保留的表**：
- `dim_metric_config` - 保留 pump_flow_rate 记录，只修改元数据
- `fact_measurements` - 保留所有历史数据

---

## 📊 关键发现

### 发现1：旧架构的核心问题
- 使用硬编码的过滤逻辑（freq>=3.0, power>=0.5）
- 计算方法分散在多个函数中
- 缺乏统一的验证和优化机制
- 依赖 `_prepare_flow_rate_share` 预处理数据

### 发现2：新架构的优势
- 完全独立的策略类
- 灵活的过滤配置
- 统一的验证和优化流程
- 支持配置文件驱动

### 发现3：迁移的关键挑战
1. 需要完整实现5个计算方法
2. 需要实现权重总和查询逻辑
3. 需要实现分片计算逻辑
4. 需要实现完整的日志记录
5. 需要实现数据库写入逻辑

---

### 步骤5: 旧代码深度分析 ✅

**_prepare_flow_rate_share 函数分析**（行1635-1787）：

**核心逻辑**：
1. 加载参数：alpha=1.0, beta=1.0, f_thr=3.0, p_thr=0.5
2. 计算当前设备权重：`weight_i = power^alpha * freq^beta`
3. 过滤条件：`freq >= f_thr AND power >= p_thr`
4. 查询数据库获取所有设备的权重总和
5. 计算份额：`share = weight_i / weight_total`
6. 将份额存储在 `data['__pump_flow_rate_share']` 中

**关键问题**：
1. ❌ 硬编码过滤逻辑（freq>=3.0, power>=0.5）
2. ❌ 依赖 `mv_device_running_1s.running=1` 过滤
3. ❌ 需要额外的数据库查询获取权重总和
4. ❌ 逻辑分散在两个地方（orchestrator + calculators）

**现有参数配置**（来自数据库）：
- method_a: alpha=1.0, beta=1.0, f_thr=3.0, p_thr=0.5（全部可优化）
- method_b: 无参数
- method_c: 无参数
- method_d: 无参数
- method_e: 无参数
- method_f: 需要训练数据（未实现）

**现有验证规则**（来自数据库）：
1. not_nan (priority=10)
2. not_inf (priority=10)
3. non_negative (priority=20)
4. range: min=0, max=10000 (priority=30)

---

### 步骤6: 关键技术决策 ✅

**决策1：权重总和查询方式**
- 旧方式：在 orchestrator 中查询数据库
- 新方式：在策略类中实现 `_query_weight_total()` 方法
- 优势：逻辑集中，易于测试和维护

**决策2：过滤逻辑**
- 旧方式：硬编码 freq>=3.0, power>=0.5
- 新方式：通过 FilterConfig 配置，pump_flow_rate 不使用这些过滤
- 优势：灵活可配置，符合业务需求

**决策3：分片计算**
- 需要实现：按时间分片查询权重总和
- 原因：避免一次性加载所有时间点的数据
- 方案：使用 unique_ts 批量查询

**决策4：日志记录**
- 需要记录：数据加载、方法选择、计算执行、验证结果、写入结果
- 格式：使用结构化日志（extra_data）
- 级别：INFO（正常流程）、WARNING（异常情况）、ERROR（错误）

---

## 🎯 研究总结

### 核心发现

**1. 旧架构的根本问题**：
- 过滤逻辑硬编码在两个地方（数据加载 + 计算阶段）
- 导致停机设备（freq=0, power=0）无法参与计算
- 逻辑分散，难以维护和测试

**2. 新架构的解决方案**：
- 完全独立的策略类，逻辑集中
- 灵活的过滤配置，pump_flow_rate 不使用硬编码过滤
- 统一的验证和优化流程

**3. 迁移的关键任务**：
1. 删除旧代码（6个函数 + _prepare_flow_rate_share）
2. 删除数据库记录（6个方法 + 参数 + 验证规则）
3. 实现新的策略类（PumpFlowRateStrategy）
4. 实现5个计算方法（A/B/C/D/E）
5. 实现权重总和查询逻辑
6. 实现验证规则
7. 实现优化策略
8. 编写完整的测试
9. 编写数据库迁移脚本
10. 编写配置文件

---

## 🔄 下一步行动

**研究阶段完成** ✅

**准备进入创新模式**：
1. 讨论多种实现方案
2. 评估各方案的优缺点
3. 选择最佳方案
4. 确保方案符合项目规则

---

## 📝 记忆检索结果

**已检索记忆**：
- 指标计算失败根因：mv_device_running_1s.running=1只控制数据加载，计算阶段使用硬编码阈值(freq>=3.0Hz,power>=0.5kW)过滤，导致停机设备(freq=0,power=0)权重为0无法计算

---

## 📊 上下文状态

- **Token使用**: 66,348 / 200,000 (33.2%)
- **对话轮次**: 1轮
- **已读文件**: 10个
  - 规则文档: 3个
  - 架构文档: 1个
  - 代码文件: 2个（详细分析）
  - 计划文档: 2个
  - 其他文档: 2个
- **数据库查询**: 3次
- **任务文件**: 已创建并更新

