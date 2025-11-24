# pump_flow_rate 重构任务文档

**创建时间**: 2025-01-14
**任务ID**: pump_flow_rate_refactor_20250114
**协议**: RIPER-5
**当前模式**: 研究 → 创新

---

## 📋 任务概述

### 任务目标
重构 `pump_flow_rate` 指标计算流程，解决硬编码阈值导致的计算失败问题，实现流水线架构。

### 实施范围
- ✅ **本次实施**: pump_flow_rate 重构
- ❌ **暂不实施**: 文档06（参数优化器增强）、文档07（最小有效频率自动学习）

### 实施条件
- 文档06和07需等待 pump_flow_rate 重构完成并通过测试验证后再进行

---

## 🔍 研究阶段分析结果

### 问题根因（已确认）
**核心问题**: 指标计算失败根因
- **数据加载阶段**: 使用 `mv_device_running_1s.running=1` 过滤（正确）
- **计算阶段**: 使用硬编码阈值 `freq>=3.0Hz, power>=0.5kW` 过滤（错误）
- **导致结果**: 停机设备（freq=0, power=0）权重为0，无法计算流量

**证据位置**:
- `app/services/calculation/calculators.py` lines 48-243
- 方法D、E中使用 `p_thr=0.5`, `f_thr=3.0` 硬编码阈值

### 现有代码结构分析

**需要重构的文件**:
1. `app/services/calculation/orchestrator.py` (2659行) - 超过600行限制
2. `app/services/calculation/method_selector.py` - 方法选择逻辑
3. `app/services/calculation/calculators.py` - 计算方法实现

**可复用的模块**:
1. `app/services/calculation/adaptive_batch.py` - 自适应批量管理器 ✅
2. `app/core/logging/setup.py` - 日志系统 ✅
3. `app/adapters/db/__init__.py` - 数据库连接池 ✅

### 设计文档完整性检查

| 文档 | 状态 | 说明 |
|------|------|------|
| 文档04 - 总体架构设计 | ✅ 完成 | 流水线架构（6阶段3层） |
| 文档05 - pump_flow_rate详细设计 | ✅ 完成 | 6种计算方法、数据流 |
| 文档08 - 数据库设计 | ✅ 完成 | 表结构、索引、分区 |
| 文档09 - 共享模块设计 | ✅ 完成 | Scheduler、DataWriter、ParameterManager |
| 文档10 - 测试方案 | ✅ 完成 | 单元测试、集成测试、性能测试 |

### 项目规则摘要

**强制规则**:
- 单文件不超过600行（不含注释和空行）
- 所有注释和日志必须使用中文
- 必须使用项目日志系统（log_activity、log_sql、log_biz）
- 禁止硬编码阈值（必须从配置或数据库加载）
- 必须使用参数化查询（禁止字符串拼接SQL）
- 测试覆盖率≥80%
- 必须使用连接池和上下文管理器
- 必须遵循六大设计原则（SOLID + LoD）

**数据库规则**:
- 数据库配置严格限制在 `configs/database.yaml`
- 所有CRUD操作必须通过 `api` schema 的存储过程
- 查询操作优先使用 `reporting` schema 的物化视图
- 时序数据查询必须包含时间范围过滤

---

## 📊 依赖关系分析

### 数据依赖
- `fact_measurements` 表：存储所有指标值
- `mv_device_running_1s` 视图：设备运行状态（1秒级）
- `calculation_parameters` 表：三级参数配置（需新建）
- `dim_metric_config` 表：指标配置
- `dim_devices` 表：设备信息

### 代码依赖
- `app/adapters/db` - 数据库连接池
- `app/core/logging/setup` - 日志系统
- `app/services/calculation/adaptive_batch` - 自适应批量管理

---

## 🎯 下一步行动

**进入创新模式**，需要确认：
1. 技术方案的可行性
2. 风险评估和缓解措施
3. 实施路径和优先级
4. 与现有系统的兼容性

---

## 📝 记忆检索结果

### 研究模式检索
- 已检索项目规则文档（.memory/规则层/）
- 已检索现有代码结构（orchestrator.py、method_selector.py、calculators.py）
- 已检索数据库表结构（fact_measurements、mv_device_running_1s）

### 记忆验证结果
- ✅ 项目规则文档存在且最新
- ✅ 现有代码文件存在
- ✅ 数据库表结构已确认
- ⚠️ calculation_parameters 表需要新建

---

## 📌 记忆更新日志

### 研究模式更新
- 记录了问题根因：硬编码阈值导致计算失败
- 记录了现有代码结构：orchestrator.py超过600行限制
- 记录了项目规则：单文件不超过600行、必须使用中文注释
- 记录了数据依赖：fact_measurements、mv_device_running_1s、calculation_parameters

---

**研究模式完成时间**: 2025-01-14
**下一模式**: 创新模式

---

## 🎨 第二阶段：创新模式完成总结

### 方案选择确认
- **选择方案**: 方案2 - 完全流水线重构
- **实施范围**: pump_flow_rate 指标（本次）
- **暂不实施**: 文档06（参数优化器增强）、文档07（最小有效频率自动学习）
- **实施周期**: 5-7天

### 核心决策理由
1. **一次性到位**: 避免方案3的"两次重构"问题
2. **长期价值**: 为后续9个指标提供统一架构
3. **技术规范**: 完全符合项目规则和六大设计原则
4. **可维护性**: 高度模块化，每个文件职责单一

### 风险缓解措施
1. **回归风险**: 保留现有代码，新架构独立实现，并行运行验证
2. **实施周期**: 分模块并行开发，设置里程碑检查点
3. **兼容性**: 复用现有数据库连接池、日志系统
4. **测试成本**: 使用 pytest fixtures 复用测试数据

### 日志系统完整设计
- **三层架构**: 应用层（文件日志）+ 数据层（calculation_logs表）+ 监控层（monitoring schema）
- **上下文传递**: 使用 Python contextvars 实现自动上下文传递
- **六阶段覆盖**: 每个流水线阶段都有明确的日志职责
- **可观测性**: 支持故障排查、性能分析、审计合规

**创新模式完成时间**: 2025-01-14
**下一模式**: 计划模式

---

## 📋 第三阶段：详细计划制定（计划模式）

### 计划制定时间
- **开始时间**: 2025-01-14 (当前)
- **计划模式**: MODE: 计划
- **协议步骤**:
  1. ✅ 记忆检索（已完成）
  2. ✅ 规则验证（已读取所有规则文档）
  3. ⏳ 详细规划（进行中）
  4. ⏳ 检查清单生成
  5. ⏳ 记忆更新

---

## 🎯 实施方案总览

### 核心目标
1. ✅ 移除硬编码阈值（f_thr, p_thr）
2. ✅ 实现完整流水线架构（6阶段3层）
3. ✅ 符合所有项目规则（单文件≤600行）
4. ✅ 完整日志输出（3层日志架构）
5. ✅ 测试覆盖率≥80%

### 实施阶段
1. **数据库改造**（0.5天）
2. **共享层实施**（2天）
3. **指标专用层实施**（2天）
4. **集成与测试**（1-2天）
5. **部署与验证**（1天）

**总计**: 5-7天

---

## 📊 第一部分：数据库改造详细方案

### 1. 新建表

#### 1.1 calculation_logs 表（分区表）

**创建原因**:
- 记录流水线每个阶段的详细日志
- 支持故障排查和性能分析
- 支持审计合规

**表结构**:
```sql
CREATE TABLE IF NOT EXISTS calculation_logs (
    log_id BIGSERIAL,
    task_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    metric_key TEXT NOT NULL,
    station_id BIGINT,
    device_id BIGINT,
    stage TEXT NOT NULL,  -- data_loader, data_filter, method_selector, calculator, validator, data_writer
    log_level TEXT NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE calculation_logs IS '计算流水线日志表（分区表，按天分区，保留30天）';
COMMENT ON COLUMN calculation_logs.log_id IS '日志ID（自增）';
COMMENT ON COLUMN calculation_logs.task_id IS '任务ID';
COMMENT ON COLUMN calculation_logs.trace_id IS '追踪ID（串联整个流程）';
COMMENT ON COLUMN calculation_logs.span_id IS '阶段ID';
COMMENT ON COLUMN calculation_logs.parent_span_id IS '父阶段ID';
COMMENT ON COLUMN calculation_logs.metric_key IS '指标键';
COMMENT ON COLUMN calculation_logs.station_id IS '泵站ID';
COMMENT ON COLUMN calculation_logs.device_id IS '设备ID';
COMMENT ON COLUMN calculation_logs.stage IS '流水线阶段';
COMMENT ON COLUMN calculation_logs.log_level IS '日志级别';
COMMENT ON COLUMN calculation_logs.message IS '日志消息';
COMMENT ON COLUMN calculation_logs.extra_data IS '额外数据（JSON格式）';
COMMENT ON COLUMN calculation_logs.created_at IS '创建时间';
```

**索引设计**:
```sql
-- 按任务查询日志
CREATE INDEX idx_calculation_logs_task_id ON calculation_logs(task_id, created_at);

-- 追踪完整流程
CREATE INDEX idx_calculation_logs_trace_id ON calculation_logs(trace_id, created_at);

-- 按设备查询日志
CREATE INDEX idx_calculation_logs_device_id ON calculation_logs(device_id, created_at);

-- 按级别查询（ERROR日志）
CREATE INDEX idx_calculation_logs_log_level ON calculation_logs(log_level, created_at);

-- 支持JSON字段查询
CREATE INDEX idx_calculation_logs_extra_data ON calculation_logs USING GIN(extra_data);
```

**分区策略**:
- 按天分区（PARTITION BY RANGE (created_at)）
- 保留30天数据
- 每天自动创建明天的分区
- 每天自动删除31天前的分区

**分区维护函数**:
```sql
CREATE OR REPLACE FUNCTION maintain_calculation_logs_partitions()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
    old_partition_name TEXT;
BEGIN
    -- 创建明天的分区
    partition_date := CURRENT_DATE + 1;
    partition_name := 'calculation_logs_' || TO_CHAR(partition_date, 'YYYYMMDD');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 day';

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF calculation_logs FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );

    -- 删除31天前的分区
    partition_date := CURRENT_DATE - 31;
    old_partition_name := 'calculation_logs_' || TO_CHAR(partition_date, 'YYYYMMDD');

    EXECUTE format('DROP TABLE IF EXISTS %I', old_partition_name);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION maintain_calculation_logs_partitions() IS '维护 calculation_logs 分区（每天执行，创建明天分区，删除31天前分区）';
```



### 2. 修改表

#### 2.1 calculation_parameters 表（已存在，验证字段）

**验证结果**: ✅ 表已存在，字段完整

**现有字段**:
- id (bigint) - 主键
- station_id (bigint) - 泵站ID（NULL表示全局）
- device_id (bigint) - 设备ID（NULL表示泵站级）
- metric_key (text) - 指标键
- method_id (text) - 方法ID
- param_name (text) - 参数名
- param_value (numeric) - 参数值
- param_type (text) - 参数类型（float, int, str）
- is_optimizable (boolean) - 是否可优化
- optimization_history (jsonb) - 优化历史
- created_at (timestamptz) - 创建时间
- updated_at (timestamptz) - 更新时间
- updated_by (text) - 更新人
- confidence_score (numeric) - 置信度分数
- last_optimized_at (timestamptz) - 最后优化时间
- optimization_count (integer) - 优化次数
- param_min (numeric) - 参数最小值
- param_max (numeric) - 参数最大值
- covariance_matrix (jsonb) - 协方差矩阵
- rls_iterations (integer) - RLS迭代次数
- last_p_trace (numeric) - 最后P矩阵迹
- param_value_text (text) - 参数值（文本格式）

**无需修改**: 表结构完整，无需修改

---

### 3. 垃圾数据库内容删除

#### 3.1 删除 f_thr 和 p_thr 参数（如果存在）

**删除原因**:
- f_thr（频率阈值）和 p_thr（功率阈值）是硬编码阈值
- 新架构使用 mv_device_running_1s.running 字段判断运行状态
- 这些参数不再需要

**删除SQL**:
```sql
-- 删除 pump_flow_rate 的 f_thr 和 p_thr 参数
DELETE FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
  AND param_name IN ('f_thr', 'p_thr');

-- 验证删除结果
SELECT COUNT(*) as deleted_count
FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate'
  AND param_name IN ('f_thr', 'p_thr');
-- 预期结果: deleted_count = 0
```

**影响范围**:
- 全局参数: f_thr, p_thr
- 泵站级参数: f_thr, p_thr（如果存在）
- 设备级参数: f_thr, p_thr（如果存在）

---

### 4. 数据库改造检查清单

#### 4.1 创建表和索引
- [ ] 1. 创建 calculation_logs 表（分区表）
- [ ] 2. 添加 calculation_logs 表注释
- [ ] 3. 添加 calculation_logs 列注释（13个列）
- [ ] 4. 创建索引 idx_calculation_logs_task_id
- [ ] 5. 创建索引 idx_calculation_logs_trace_id
- [ ] 6. 创建索引 idx_calculation_logs_device_id
- [ ] 7. 创建索引 idx_calculation_logs_log_level
- [ ] 8. 创建索引 idx_calculation_logs_extra_data (GIN)

#### 4.2 创建分区
- [ ] 9. 创建最近30天的分区（30个分区）
- [ ] 10. 验证分区创建成功（COUNT = 30）

#### 4.3 创建维护函数
- [ ] 11. 创建函数 maintain_calculation_logs_partitions()
- [ ] 12. 添加函数注释
- [ ] 13. 测试函数执行（手动调用一次）
- [ ] 14. 验证明天的分区已创建
- [ ] 15. 验证31天前的分区已删除（如果存在）

#### 4.4 删除垃圾数据
- [ ] 16. 查询 f_thr 和 p_thr 参数数量
- [ ] 17. 删除 f_thr 和 p_thr 参数
- [ ] 18. 验证删除结果（COUNT = 0）

#### 4.5 验证和测试
- [ ] 19. 测试插入日志到 calculation_logs
- [ ] 20. 测试按 task_id 查询日志
- [ ] 21. 测试按 trace_id 查询日志
- [ ] 22. 测试按 device_id 查询日志
- [ ] 23. 测试按 log_level 查询日志
- [ ] 24. 测试 extra_data JSON 查询
- [ ] 25. 测试分区查询性能（EXPLAIN ANALYZE）

---

## 🗑️ 第二部分：垃圾代码删除详细方案

### 1. 识别垃圾代码

#### 1.1 硬编码阈值代码（calculators.py）

**文件**: `app/services/calculation/calculators.py`

**位置1**: Line 60（函数文档）
```python
# ❌ 需要修改
"""
Args:
    data: expects main_pipeline_flow_rate, pump_active_power, pump_frequency
    params: optional tuning parameters alpha, beta, f_thr, p_thr  # ← 移除 f_thr, p_thr
"""
```

**修改为**:
```python
# ✅ 修改后
"""
Args:
    data: expects main_pipeline_flow_rate, pump_active_power, pump_frequency
    params: optional tuning parameters alpha, beta
"""
```

**位置2**: Line 226（函数文档）
```python
# ❌ 需要修改
"""
Args:
    data: 包含 main_pipeline_flow_rate, pump_active_power
    params: 包含 p_thr  # ← 移除 p_thr
"""
```

**修改为**:
```python
# ✅ 修改后
"""
Args:
    data: 包含 main_pipeline_flow_rate, pump_active_power
    params: 包含 alpha（功率指数）
"""
```

**位置3**: Line 234（硬编码阈值）
```python
# ❌ 需要删除
p_thr = params.get('p_thr', 0.5)
```

**位置4**: Line 237-238（阈值过滤逻辑）
```python
# ❌ 需要删除
mask = P_i >= p_thr
Q_i[mask] = Q_total[mask] * P_i[mask]
```

**修改为**:
```python
# ✅ 修改后（数据已在 DataFilter 阶段过滤，直接计算）
# 注意：数据已经过 DataFilter 过滤，只包含运行状态的设备
Q_i = Q_total * P_i  # 直接计算，无需再过滤
```

**位置5**: Line 257（函数文档）
```python
# ❌ 需要修改
"""
Args:
    data: 包含 main_pipeline_flow_rate, pump_frequency
    params: 包含 f_thr  # ← 移除 f_thr
"""
```

**修改为**:
```python
# ✅ 修改后
"""
Args:
    data: 包含 main_pipeline_flow_rate, pump_frequency
    params: 包含 beta（频率指数）
"""
```

**位置6**: Line 265（硬编码阈值）
```python
# ❌ 需要删除
f_thr = params.get('f_thr', 3.0)
```

**位置7**: Line 268-269（阈值过滤逻辑）
```python
# ❌ 需要删除
mask = f_i >= f_thr
Q_i[mask] = Q_total[mask] * f_i[mask]
```

**修改为**:
```python
# ✅ 修改后（数据已在 DataFilter 阶段过滤，直接计算）
# 注意：数据已经过 DataFilter 过滤，只包含运行状态的设备
Q_i = Q_total * f_i  # 直接计算，无需再过滤
```


#### 1.2 旧的 orchestrator.py（2659行，超过600行限制）

**文件**: `app/services/calculation/orchestrator.py`

**问题**:
- 文件过大（2659行，超过600行限制4.4倍）
- 职责不单一（包含调度、数据加载、计算、写入等多个职责）
- 违反项目规则

**处理方式**:
- ❌ 不删除整个文件（保留作为临时兼容）
- ✅ 标记为 deprecated
- ✅ 新架构实现后，逐步迁移调用方
- ✅ 最终删除（在所有调用方迁移完成后）

**迁移策略**:
1. 新架构实现完成
2. 添加 @deprecated 装饰器到旧函数
3. 更新所有调用方使用新架构
4. 验证功能一致性
5. 删除旧代码

**Deprecated 标记示例**:
```python
import warnings

def calculate_missing_metrics(*args, **kwargs):
    """
    计算缺失指标（已废弃）

    警告：此函数已废弃，请使用新的流水线架构：
    from app.services.calculation.pipeline import PumpFlowRatePipeline

    迁移指南：
    1. 创建 Pipeline 实例
    2. 调用 execute() 方法
    3. 处理返回结果
    """
    warnings.warn(
        "calculate_missing_metrics() 已废弃，请使用 PumpFlowRatePipeline",
        DeprecationWarning,
        stacklevel=2
    )
    # 保留原有实现...
```

---

### 2. 垃圾代码删除检查清单

#### 2.1 calculators.py 修改
- [ ] 1. 修改 line 60: 移除函数文档中的 f_thr, p_thr 参数说明
- [ ] 2. 删除 line 234: `p_thr = params.get('p_thr', 0.5)`
- [ ] 3. 删除 line 237-238: 功率阈值过滤逻辑
- [ ] 4. 修改 line 237-238: 改为直接计算（无阈值过滤）
- [ ] 5. 添加注释说明数据已在 DataFilter 阶段过滤
- [ ] 6. 修改 line 226: 移除函数文档中的 p_thr 参数说明
- [ ] 7. 修改 line 257: 移除函数文档中的 f_thr 参数说明
- [ ] 8. 删除 line 265: `f_thr = params.get('f_thr', 3.0)`
- [ ] 9. 删除 line 268-269: 频率阈值过滤逻辑
- [ ] 10. 修改 line 268-269: 改为直接计算（无阈值过滤）
- [ ] 11. 添加注释说明数据已在 DataFilter 阶段过滤

#### 2.2 orchestrator.py 标记
- [ ] 12. 添加 @deprecated 装饰器到 calculate_missing_metrics()
- [ ] 13. 添加废弃警告文档
- [ ] 14. 添加迁移指南
- [ ] 15. 保留原有实现（暂不删除）

#### 2.3 代码清理
- [ ] 16. 删除未使用的导入语句（运行 pylint）
- [ ] 17. 删除未使用的辅助函数（运行 pylint）
- [ ] 18. 删除未使用的变量（运行 pylint）
- [ ] 19. 运行 black 格式化代码
- [ ] 20. 运行 isort 排序导入语句

---

## 🏗️ 第三部分：流水线架构详细设计

### 1. 目录结构设计

```
app/services/calculation/
├── shared/                          # 共享层（全局单例）
│   ├── __init__.py
│   ├── scheduler.py                 # 任务调度器（~200行）
│   ├── data_writer.py               # 数据写入器（~150行）
│   ├── parameter_manager.py         # 参数管理器（~180行）
│   └── shared_services.py           # 服务管理器（~50行）
├── metrics/                         # 指标专用层
│   └── pump_flow_rate/              # pump_flow_rate 指标
│       ├── __init__.py
│       ├── pipeline.py              # 流水线编排（~150行）
│       ├── data_loader.py           # 数据加载（~200行）
│       ├── data_filter.py           # 数据过滤（~150行）
│       ├── method_selector.py       # 方法选择（~200行）
│       ├── calculator.py            # 计算执行（~300行）
│       ├── validator.py             # 结果验证（~150行）
│       └── methods/                 # 计算方法
│           ├── __init__.py
│           ├── method_a.py          # 功率×频率分摊（~100行）
│           ├── method_b.py          # 累计流量导数（~100行）
│           ├── method_c.py          # 单泵直读（~50行）
│           ├── method_d.py          # 功率分摊（~100行）
│           ├── method_e.py          # 频率分摊（~100行）
│           └── method_f.py          # 数据驱动回归（~100行）
├── orchestrator.py                  # 旧代码（标记为 deprecated）
├── method_selector.py               # 旧代码（标记为 deprecated）
├── calculators.py                   # 旧代码（修改后保留）
└── adaptive_batch.py                # 复用（无需修改）
```

**文件数量统计**:
- 共享层: 4个文件（~580行）
- 指标专用层: 13个文件（~1500行）
- 总计: 17个新文件（~2080行）

**单文件行数验证**:
- ✅ 所有文件都≤300行
- ✅ 符合项目规则（≤600行）

---

### 2. 共享层详细设计

#### 2.1 Scheduler（任务调度器）

**文件**: `app/services/calculation/shared/scheduler.py`

**职责**:
1. 任务创建和分片
2. 并行执行管理
3. 进度跟踪
4. 错误处理和重试

**类定义**:
```python
from typing import List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

@dataclass
class Task:
    """任务定义"""
    task_id: str
    metric_key: str
    station_id: int
    device_id: int
    start_time: datetime
    end_time: datetime
    priority: int = 0

@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    device_id: int
    metric_key: str
    success: bool
    results_count: int
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

class Scheduler:
    """
    任务调度器（单例）

    职责：
    - 任务创建和分片
    - 并行执行管理
    - 进度跟踪
    """

    def __init__(self, max_workers: int = 10):
        """
        初始化调度器

        Args:
            max_workers: 最大并行工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        from app.core.logging.setup import log_activity
        self.logger = log_activity

    def create_tasks(
        self,
        metric_key: str,
        device_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        time_chunk_hours: int = 1
    ) -> List[Task]:
        """
        创建任务列表

        Args:
            metric_key: 指标键
            device_ids: 设备ID列表
            start_time: 开始时间
            end_time: 结束时间
            time_chunk_hours: 时间分片大小（小时）

        Returns:
            任务列表
        """
        tasks = []

        # 时间分片
        current_time = start_time
        while current_time < end_time:
            chunk_end = min(
                current_time + timedelta(hours=time_chunk_hours),
                end_time
            )

            # 为每个设备创建任务
            for device_id in device_ids:
                task = Task(
                    task_id=str(uuid.uuid4()),
                    metric_key=metric_key,
                    station_id=self._get_station_id(device_id),
                    device_id=device_id,
                    start_time=current_time,
                    end_time=chunk_end
                )
                tasks.append(task)

            current_time = chunk_end

        self.logger(
            f"[调度] 创建任务: {len(tasks)}个",
            extra={'extra_data': {
                'metric_key': metric_key,
                'device_count': len(device_ids),
                'time_chunks': (end_time - start_time).total_seconds() / 3600 / time_chunk_hours
            }}
        )

        return tasks

    def execute_tasks(
        self,
        tasks: List[Task],
        calculator_func: Callable[[Task], TaskResult]
    ) -> List[TaskResult]:
        """
        并行执行任务

        Args:
            tasks: 任务列表
            calculator_func: 计算函数

        Returns:
            任务结果列表
        """
        results = []

        # 提交所有任务
        futures = {
            self.executor.submit(calculator_func, task): task
            for task in tasks
        }

        # 收集结果
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self.logger(
                    f"[调度] 任务失败: {task.task_id}",
                    extra={'extra_data': {
                        'device_id': task.device_id,
                        'error': str(e)
                    }}
                )
                results.append(TaskResult(
                    task_id=task.task_id,
                    device_id=task.device_id,
                    metric_key=task.metric_key,
                    success=False,
                    results_count=0,
                    error_message=str(e)
                ))

        return results

    def shutdown(self):
        """关闭调度器"""
        self.executor.shutdown(wait=True)
        self.logger("[调度] 调度器已关闭")
```

**关键特性**:
- ✅ 任务分片（按时间和设备）
- ✅ 并行执行（ThreadPoolExecutor）
- ✅ 错误处理（捕获异常，记录日志）
- ✅ 进度跟踪（as_completed）



#### 2.2 DataWriter（数据写入器）

**文件**: `app/services/calculation/shared/data_writer.py`

**职责**:
1. 批量写入 fact_measurements
2. 自适应批量大小调整
3. 错误处理和重试
4. 性能监控

**关键实现**:
```python
from typing import List
from dataclasses import dataclass
import time

@dataclass
class WriteRecord:
    """写入记录"""
    device_id: int
    metric_key: str
    timestamp: datetime
    value: float
    quality_code: int = 0

class DataWriter:
    """
    数据写入器（单例）

    职责：
    - 批量写入 fact_measurements
    - 自适应批量大小
    - 性能监控
    """

    def __init__(
        self,
        initial_batch_size: int = 1000,
        min_batch_size: int = 100,
        max_batch_size: int = 10000,
        target_duration_ms: int = 500
    ):
        self.batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_duration_ms = target_duration_ms

        from app.core.logging.setup import log_activity
        from app.adapters.db import get_connection
        self.logger = log_activity
        self.get_connection = get_connection

    def write(self, records: List[WriteRecord]) -> int:
        """
        批量写入记录

        Args:
            records: 写入记录列表

        Returns:
            成功写入的记录数
        """
        if not records:
            return 0

        total_written = 0

        # 分批写入
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            written = self._write_batch(batch)
            total_written += written

        return total_written

    def _write_batch(self, batch: List[WriteRecord]) -> int:
        """写入单个批次"""
        start_time = time.time()

        sql = """
            INSERT INTO fact_measurements (device_id, metric_key, ts_bucket, value, quality_code)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (device_id, metric_key, ts_bucket)
            DO UPDATE SET value = EXCLUDED.value, quality_code = EXCLUDED.quality_code
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                data = [(r.device_id, r.metric_key, r.timestamp, r.value, r.quality_code) for r in batch]
                cursor.executemany(sql, data)
                conn.commit()

        # 自适应调整批量大小
        duration_ms = int((time.time() - start_time) * 1000)
        self._adjust_batch_size(duration_ms)

        return len(batch)
```

**关键特性**:
- ✅ 批量写入（executemany）
- ✅ 自适应批量大小（根据耗时调整）
- ✅ 冲突处理（ON CONFLICT DO UPDATE）
- ✅ 性能监控（记录耗时）

---

#### 2.3 ParameterManager（参数管理器）

**文件**: `app/services/calculation/shared/parameter_manager.py`

**职责**:
1. 三级参数配置加载（全局 > 泵站 > 设备）
2. 参数缓存（避免重复查询）
3. 参数更新（写入数据库并清除缓存）
4. 默认值管理

**关键实现**:
```python
from typing import Dict, Optional
from functools import lru_cache

class ParameterManager:
    """
    参数管理器（单例）

    职责：
    - 三级参数配置加载（全局 > 泵站 > 设备）
    - 参数缓存
    - 默认值管理
    """

    def __init__(self):
        from app.core.logging.setup import log_activity
        from app.adapters.db import get_connection
        self.logger = log_activity
        self.get_connection = get_connection

        # 默认参数（移除 f_thr 和 p_thr）
        self.default_params = {
            'pump_flow_rate': {
                'method_a': {'alpha': 1.0, 'beta': 1.0},
                'method_b': {'smooth_window': 5},
                'method_c': {},
                'method_d': {'alpha': 1.0},
                'method_e': {'beta': 1.0},
                'method_f': {'model_type': 'linear', 'min_samples': 100},
                'validator': {
                    'min_flow': 0.0,
                    'max_flow': 200.0,
                    'max_ratio': 1.1
                }
            }
        }

        self._cache = {}

    def get_params(
        self,
        metric_key: str,
        method_id: Optional[str] = None,
        station_id: Optional[int] = None,
        device_id: Optional[int] = None
    ) -> Dict[str, float]:
        """
        获取参数（三级优先级：设备 > 泵站 > 全局）

        Args:
            metric_key: 指标键
            method_id: 方法ID（None表示全局参数）
            station_id: 泵站ID（None表示全局）
            device_id: 设备ID（None表示泵站级）

        Returns:
            参数字典
        """
        # 构造缓存键
        cache_key = f"{metric_key}:{method_id}:{station_id}:{device_id}"

        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 从数据库加载
        params = self._load_params_from_db(metric_key, method_id, station_id, device_id)

        # 如果数据库没有，使用默认值
        if not params:
            params = self._get_default_params(metric_key, method_id)

        # 缓存
        self._cache[cache_key] = params

        return params

    def _load_params_from_db(
        self,
        metric_key: str,
        method_id: Optional[str],
        station_id: Optional[int],
        device_id: Optional[int]
    ) -> Dict[str, float]:
        """从数据库加载参数（三级优先级）"""
        sql = """
            WITH param_hierarchy AS (
                SELECT
                    param_name,
                    param_value,
                    CASE
                        WHEN device_id IS NOT NULL THEN 1  -- 设备级
                        WHEN station_id IS NOT NULL THEN 2  -- 泵站级
                        ELSE 3  -- 全局级
                    END AS priority
                FROM calculation_parameters
                WHERE metric_key = %s
                  AND (method_id = %s OR method_id IS NULL)
                  AND (
                      (station_id = %s AND device_id = %s) OR
                      (station_id = %s AND device_id IS NULL) OR
                      (station_id IS NULL AND device_id IS NULL)
                  )
            )
            SELECT DISTINCT ON (param_name) param_name, param_value
            FROM param_hierarchy
            ORDER BY param_name, priority
        """

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [metric_key, method_id, station_id, device_id, station_id])
                rows = cursor.fetchall()

        return {row[0]: float(row[1]) for row in rows}
```

**关键特性**:
- ✅ 三级参数配置（设备 > 泵站 > 全局）
- ✅ 参数缓存（避免重复查询）
- ✅ 默认值管理（移除 f_thr 和 p_thr）
- ✅ SQL优化（DISTINCT ON + 优先级排序）

---

#### 2.4 SharedServices（服务管理器）

**文件**: `app/services/calculation/shared/shared_services.py`

**职责**:
1. 单例模式（确保全局唯一）
2. 生命周期管理（初始化和销毁）
3. 依赖注入（为指标模块提供共享服务）

**关键实现**:
```python
from typing import Optional

class SharedServices:
    """
    共享服务管理器（单例模式）

    职责：
    - 管理共享模块的生命周期
    - 确保全局唯一实例
    - 提供依赖注入
    """

    _instance: Optional['SharedServices'] = None
    _initialized: bool = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化（只执行一次）"""
        if SharedServices._initialized:
            return

        from app.core.logging.setup import log_activity
        self.logger = log_activity

        # 初始化共享模块
        self.scheduler = Scheduler(max_workers=10)
        self.data_writer = DataWriter(initial_batch_size=1000, target_duration_ms=500)
        self.parameter_manager = ParameterManager()

        SharedServices._initialized = True

        self.logger("[共享服务] 初始化完成")

    @classmethod
    def get_instance(cls) -> 'SharedServices':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def shutdown(self):
        """关闭所有服务"""
        self.scheduler.shutdown()
        self.logger("[共享服务] 已关闭")
```

**关键特性**:
- ✅ 单例模式（__new__ + _instance）
- ✅ 延迟初始化（__init__ 只执行一次）
- ✅ 依赖注入（提供 scheduler, data_writer, parameter_manager）
- ✅ 生命周期管理（shutdown）

---

### 3. 共享层检查清单

#### 3.1 Scheduler 实施
- [ ] 1. 创建文件 `app/services/calculation/shared/scheduler.py`
- [ ] 2. 定义 Task 数据类（7个字段）
- [ ] 3. 定义 TaskResult 数据类（7个字段）
- [ ] 4. 实现 Scheduler.__init__()
- [ ] 5. 实现 Scheduler.create_tasks()
- [ ] 6. 实现 Scheduler.execute_tasks()
- [ ] 7. 实现 Scheduler.shutdown()
- [ ] 8. 实现 Scheduler._get_station_id()（辅助方法）
- [ ] 9. 添加日志输出（3个位置）
- [ ] 10. 添加错误处理（try-except）

#### 3.2 DataWriter 实施
- [ ] 11. 创建文件 `app/services/calculation/shared/data_writer.py`
- [ ] 12. 定义 WriteRecord 数据类（5个字段）
- [ ] 13. 实现 DataWriter.__init__()
- [ ] 14. 实现 DataWriter.write()
- [ ] 15. 实现 DataWriter._write_batch()
- [ ] 16. 实现 DataWriter._adjust_batch_size()
- [ ] 17. 添加日志输出（3个位置）
- [ ] 18. 添加性能监控（记录耗时）
- [ ] 19. 添加冲突处理（ON CONFLICT DO UPDATE）

#### 3.3 ParameterManager 实施
- [ ] 20. 创建文件 `app/services/calculation/shared/parameter_manager.py`
- [ ] 21. 实现 ParameterManager.__init__()
- [ ] 22. 定义默认参数字典（移除 f_thr 和 p_thr）
- [ ] 23. 实现 ParameterManager.get_params()
- [ ] 24. 实现 ParameterManager._load_params_from_db()
- [ ] 25. 实现 ParameterManager._get_default_params()
- [ ] 26. 实现 ParameterManager.update_params()
- [ ] 27. 实现 ParameterManager.clear_cache()
- [ ] 28. 添加日志输出（2个位置）
- [ ] 29. 添加缓存机制（_cache 字典）

#### 3.4 SharedServices 实施
- [ ] 30. 创建文件 `app/services/calculation/shared/shared_services.py`
- [ ] 31. 实现 SharedServices.__new__()（单例模式）
- [ ] 32. 实现 SharedServices.__init__()（延迟初始化）
- [ ] 33. 实现 SharedServices.get_instance()
- [ ] 34. 实现 SharedServices.shutdown()
- [ ] 35. 添加日志输出（2个位置）

#### 3.5 共享层集成
- [ ] 36. 创建文件 `app/services/calculation/shared/__init__.py`
- [ ] 37. 导出 Scheduler, DataWriter, ParameterManager, SharedServices
- [ ] 38. 导出 Task, TaskResult, WriteRecord 数据类



## 🎯 第四部分：指标专用层详细设计（pump_flow_rate）

### 1. Pipeline（流水线编排）

**文件**: `app/services/calculation/metrics/pump_flow_rate/pipeline.py`

**职责**:
1. 编排6个流水线阶段的执行顺序
2. 管理上下文传递（trace_id, span_id）
3. 错误处理和日志记录
4. 返回计算结果

**关键实现**:
```python
from typing import List, Dict
from datetime import datetime
import uuid

class PumpFlowRatePipeline:
    """
    pump_flow_rate 流水线编排

    职责：
    - 编排6个阶段的执行
    - 管理上下文传递
    - 错误处理和日志
    """

    def __init__(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        param_manager
    ):
        self.device_id = device_id
        self.start_time = start_time
        self.end_time = end_time
        self.param_manager = param_manager

        # 生成 trace_id（串联整个流程）
        self.trace_id = f"trace_{device_id}_{start_time.strftime('%Y%m%d%H%M%S')}"

        from app.core.logging.setup import log_activity
        self.logger = log_activity

    def execute(self) -> List[Dict]:
        """
        执行流水线

        Returns:
            计算结果列表
        """
        self.logger(
            f"[流水线] 开始执行",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'device_id': self.device_id,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat()
            }}
        )

        try:
            # 阶段1: 数据加载
            data_loader = DataLoader(self.device_id, self.start_time, self.end_time, self.trace_id)
            df = data_loader.load()

            # 阶段2: 数据过滤
            data_filter = DataFilter(self.trace_id)
            df_filtered = data_filter.filter(df)

            # 阶段3: 方法选择
            method_selector = MethodSelector(self.trace_id)
            method_id = method_selector.select(df_filtered)

            # 阶段4: 计算执行
            calculator = Calculator(self.param_manager, self.trace_id)
            df_result = calculator.calculate(df_filtered, method_id)

            # 阶段5: 结果验证
            validator = Validator(self.param_manager, self.trace_id)
            df_valid, is_valid = validator.validate(df_result, df_filtered)

            # 转换为结果列表
            results = self._to_results(df_valid)

            self.logger(
                f"[流水线] 执行完成",
                extra={'extra_data': {
                    'trace_id': self.trace_id,
                    'device_id': self.device_id,
                    'method_id': method_id,
                    'results_count': len(results)
                }}
            )

            return results

        except Exception as e:
            self.logger(
                f"[流水线] 执行失败: {str(e)}",
                extra={'extra_data': {
                    'trace_id': self.trace_id,
                    'device_id': self.device_id,
                    'error': str(e)
                }}
            )
            raise

    def _to_results(self, df) -> List[Dict]:
        """转换 DataFrame 为结果列表"""
        return [
            {
                'timestamp': row['ts_bucket'],
                'value': row['pump_flow_rate']
            }
            for _, row in df.iterrows()
        ]
```

**关键特性**:
- ✅ 6阶段编排（DataLoader → DataFilter → MethodSelector → Calculator → Validator）
- ✅ trace_id 生成和传递（串联整个流程）
- ✅ 错误处理（try-except）
- ✅ 日志输出（开始、完成、失败）

---

### 2. DataLoader（数据加载）

**文件**: `app/services/calculation/metrics/pump_flow_rate/data_loader.py`

**职责**:
1. 加载 fact_measurements 数据
2. JOIN mv_device_running_1s（获取 running 字段）
3. 加载其他设备数据（用于分摊计算）
4. 日志记录

**关键SQL**:
```sql
-- 加载当前设备数据 + running 字段
SELECT
    fm.ts_bucket,
    fm.station_id,
    fm.device_id,
    fm.metric_id,
    fm.value,
    dr.running  -- ← 关键：从 mv_device_running_1s 获取运行状态
FROM fact_measurements fm
LEFT JOIN mv_device_running_1s dr
    ON dr.station_id = fm.station_id
   AND dr.device_id = fm.device_id
   AND dr.ts_bucket = fm.ts_bucket
WHERE fm.device_id = %s
  AND fm.ts_bucket >= %s
  AND fm.ts_bucket < %s
  AND fm.metric_id IN ('main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency', 'pump_cumulative_flow')
ORDER BY fm.ts_bucket
```

**关键特性**:
- ✅ LEFT JOIN mv_device_running_1s（获取 running 字段）
- ✅ 加载4个依赖指标（main_flow, power, frequency, cumulative_flow）
- ✅ 时间范围过滤（ts_bucket >= start AND ts_bucket < end）
- ✅ 日志记录（SQL执行时间、行数）

---

### 3. DataFilter（数据过滤）

**文件**: `app/services/calculation/metrics/pump_flow_rate/data_filter.py`

**职责**:
1. 使用 running=1 过滤（移除硬编码阈值）
2. 移除 NaN 和异常值
3. 日志记录（过滤统计）

**关键实现**:
```python
class DataFilter:
    """
    数据过滤器

    职责：
    - 使用 running=1 过滤（移除硬编码阈值）
    - 移除 NaN 和异常值
    - 日志记录
    """

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤数据

        Args:
            df: 原始数据

        Returns:
            过滤后的数据
        """
        original_count = len(df)

        # 1. 使用 running=1 过滤（移除硬编码阈值）
        df = df[df['running'] == 1]
        running_filtered = original_count - len(df)

        # 2. 移除 NaN
        df = df.dropna()
        nan_filtered = original_count - running_filtered - len(df)

        # 3. 移除负值
        df = df[df['value'] >= 0]
        negative_filtered = original_count - running_filtered - nan_filtered - len(df)

        self.logger(
            f"[数据过滤] 过滤完成",
            extra={'extra_data': {
                'original_count': original_count,
                'running_filtered': running_filtered,
                'nan_filtered': nan_filtered,
                'negative_filtered': negative_filtered,
                'final_count': len(df),
                'filter_rate': f"{(original_count - len(df)) / original_count * 100:.2f}%"
            }}
        )

        return df
```

**关键特性**:
- ✅ 使用 running=1 过滤（移除硬编码阈值 f_thr, p_thr）
- ✅ 移除 NaN 和负值
- ✅ 详细的过滤统计（原始数量、各阶段过滤数量、最终数量、过滤比例）
- ✅ 日志输出（证明移除了硬编码阈值）

---

### 4. MethodSelector（方法选择）

**文件**: `app/services/calculation/metrics/pump_flow_rate/method_selector.py`

**职责**:
1. 检查6种方法的依赖和条件
2. 按优先级选择最合适的方法
3. 日志记录（选择原因）

**方法优先级**:
| 优先级 | 方法ID | 方法名称 | 依赖条件 | 运行条件 |
|--------|--------|----------|----------|----------|
| 100 | method_a | 功率×频率分摊 | main_flow, power, frequency, other_devices | 运行泵数≥2 |
| 90 | method_b | 累计流量导数 | cumulative_flow | 累计流量有效 |
| 80 | method_c | 单泵直读 | main_flow | 运行泵数=1 |
| 70 | method_d | 功率分摊 | main_flow, power, other_devices | 运行泵数≥2 |
| 60 | method_e | 频率分摊 | main_flow, frequency, other_devices | 运行泵数≥2 |
| 50 | method_f | 数据驱动回归 | 历史数据 | 有足够历史样本 |

**关键特性**:
- ✅ 6种方法配置（优先级、依赖、条件）
- ✅ 依赖检查（检查列是否存在且有有效值）
- ✅ 条件检查（运行泵数、累计流量有效性、样本数量）
- ✅ 日志输出（可用指标、依赖检查、条件检查、选择原因）

---

### 5. 指标专用层检查清单（第一部分）

#### 5.1 Pipeline 实施
- [ ] 39. 创建目录 `app/services/calculation/metrics/pump_flow_rate/`
- [ ] 40. 创建文件 `pipeline.py`
- [ ] 41. 实现 PumpFlowRatePipeline.__init__()
- [ ] 42. 实现 PumpFlowRatePipeline.execute()
- [ ] 43. 实现 PumpFlowRatePipeline._to_results()
- [ ] 44. 生成 trace_id（格式：trace_{device_id}_{timestamp}）
- [ ] 45. 添加日志输出（3个位置：开始、完成、失败）
- [ ] 46. 添加错误处理（try-except）

#### 5.2 DataLoader 实施
- [ ] 47. 创建文件 `data_loader.py`
- [ ] 48. 实现 DataLoader.__init__()
- [ ] 49. 实现 DataLoader.load()
- [ ] 50. 实现 SQL查询（LEFT JOIN mv_device_running_1s）
- [ ] 51. 加载4个依赖指标（main_flow, power, frequency, cumulative_flow）
- [ ] 52. 加载其他设备数据（用于分摊计算）
- [ ] 53. 添加日志输出（SQL执行时间、行数、JOIN结果）
- [ ] 54. 生成 span_id（格式：span_data_loader_{uuid}）

#### 5.3 DataFilter 实施
- [ ] 55. 创建文件 `data_filter.py`
- [ ] 56. 实现 DataFilter.__init__()
- [ ] 57. 实现 DataFilter.filter()
- [ ] 58. 使用 running=1 过滤（移除硬编码阈值）
- [ ] 59. 移除 NaN 和负值
- [ ] 60. 添加日志输出（过滤统计：原始数量、各阶段过滤数量、最终数量、过滤比例）
- [ ] 61. 生成 span_id（格式：span_data_filter_{uuid}）
- [ ] 62. 添加注释说明移除了硬编码阈值

#### 5.4 MethodSelector 实施
- [ ] 63. 创建文件 `method_selector.py`
- [ ] 64. 实现 MethodSelector.__init__()
- [ ] 65. 定义6种方法配置（优先级、依赖、条件）
- [ ] 66. 实现 MethodSelector.select()
- [ ] 67. 实现 MethodSelector._check_dependencies()
- [ ] 68. 实现 MethodSelector._check_conditions()
- [ ] 69. 实现 MethodSelector._count_running_pumps()
- [ ] 70. 实现 MethodSelector._is_cumulative_flow_valid()
- [ ] 71. 添加日志输出（可用指标、依赖检查、条件检查、选择原因）
- [ ] 72. 生成 span_id（格式：span_method_selector_{uuid}）



### 6. Calculator（计算执行）

**文件**: `app/services/calculation/metrics/pump_flow_rate/calculator.py`

**职责**:
1. 根据 method_id 分发到对应的计算方法
2. 从 ParameterManager 加载参数
3. 执行计算并返回结果
4. 日志记录（参数、计算统计、异常值）

**关键实现**:
```python
class Calculator:
    """
    计算执行器

    职责：
    - 根据 method_id 分发到对应的计算方法
    - 加载参数（从 ParameterManager）
    - 执行计算
    - 日志记录
    """

    def __init__(self, param_manager, trace_id: str):
        self.param_manager = param_manager
        self.trace_id = trace_id

        from app.core.logging.setup import log_activity
        self.logger = log_activity

        # 导入6个计算方法
        from .methods import method_a, method_b, method_c, method_d, method_e, method_f

        self.methods = {
            'method_a': method_a,
            'method_b': method_b,
            'method_c': method_c,
            'method_d': method_d,
            'method_e': method_e,
            'method_f': method_f
        }

    def calculate(self, df: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        执行计算

        Args:
            df: 过滤后的数据
            method_id: 方法ID

        Returns:
            计算结果（包含 pump_flow_rate 列）
        """
        # 加载参数
        params = self.param_manager.get_params(
            metric_key='pump_flow_rate',
            method_id=method_id
        )

        self.logger(
            f"[计算执行] 开始计算",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'params': params,
                'data_count': len(df)
            }}
        )

        # 分发到对应的方法
        method_func = self.methods[method_id]
        df_result = method_func(df, params)

        # 统计
        valid_count = df_result['pump_flow_rate'].notna().sum()
        mean_value = df_result['pump_flow_rate'].mean()
        max_value = df_result['pump_flow_rate'].max()

        self.logger(
            f"[计算执行] 计算完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'valid_count': valid_count,
                'mean_value': float(mean_value),
                'max_value': float(max_value)
            }}
        )

        return df_result
```

**关键特性**:
- ✅ 方法分发（6个方法）
- ✅ 参数加载（从 ParameterManager）
- ✅ 日志输出（参数、计算统计）
- ✅ 移除硬编码阈值（参数从数据库加载）

---

### 7. Validator（结果验证）

**文件**: `app/services/calculation/metrics/pump_flow_rate/validator.py`

**职责**:
1. 范围验证（min_flow ≤ value ≤ max_flow）
2. NaN/Inf 检查
3. 物理约束验证（流量 ≤ 主管流量 × max_ratio）
4. 质量评分（0-100）
5. 日志记录

**关键实现**:
```python
class Validator:
    """
    结果验证器

    职责：
    - 范围验证
    - NaN/Inf 检查
    - 物理约束验证
    - 质量评分
    """

    def validate(
        self,
        df_result: pd.DataFrame,
        df_original: pd.DataFrame
    ) -> Tuple[pd.DataFrame, bool]:
        """
        验证结果

        Args:
            df_result: 计算结果
            df_original: 原始数据（用于物理约束验证）

        Returns:
            (验证后的数据, 是否通过验证)
        """
        # 加载验证参数
        params = self.param_manager.get_params(
            metric_key='pump_flow_rate',
            method_id='validator'
        )

        min_flow = params.get('min_flow', 0.0)
        max_flow = params.get('max_flow', 200.0)
        max_ratio = params.get('max_ratio', 1.1)

        original_count = len(df_result)

        # 1. 移除 NaN 和 Inf
        df_valid = df_result[df_result['pump_flow_rate'].notna()]
        df_valid = df_valid[~df_valid['pump_flow_rate'].isin([np.inf, -np.inf])]
        nan_filtered = original_count - len(df_valid)

        # 2. 范围验证
        df_valid = df_valid[
            (df_valid['pump_flow_rate'] >= min_flow) &
            (df_valid['pump_flow_rate'] <= max_flow)
        ]
        range_filtered = original_count - nan_filtered - len(df_valid)

        # 3. 物理约束验证（流量 ≤ 主管流量 × max_ratio）
        if 'main_pipeline_flow_rate' in df_original.columns:
            df_merged = df_valid.merge(
                df_original[['ts_bucket', 'main_pipeline_flow_rate']],
                on='ts_bucket',
                how='left'
            )
            df_valid = df_merged[
                df_merged['pump_flow_rate'] <= df_merged['main_pipeline_flow_rate'] * max_ratio
            ]
            physical_filtered = original_count - nan_filtered - range_filtered - len(df_valid)
        else:
            physical_filtered = 0

        # 4. 质量评分
        quality_score = (len(df_valid) / original_count * 100) if original_count > 0 else 0
        is_valid = quality_score >= 80.0

        self.logger(
            f"[结果验证] 验证完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'original_count': original_count,
                'nan_filtered': nan_filtered,
                'range_filtered': range_filtered,
                'physical_filtered': physical_filtered,
                'valid_count': len(df_valid),
                'quality_score': quality_score,
                'is_valid': is_valid
            }}
        )

        return df_valid, is_valid
```

**关键特性**:
- ✅ 4层验证（NaN/Inf、范围、物理约束、质量评分）
- ✅ 详细的验证统计
- ✅ 质量评分（0-100）
- ✅ 日志输出（验证规则、验证结果）

---

### 8. 指标专用层检查清单（第二部分）

#### 5.5 Calculator 实施
- [ ] 73. 创建文件 `calculator.py`
- [ ] 74. 实现 Calculator.__init__()
- [ ] 75. 定义方法映射字典（6个方法）
- [ ] 76. 实现 Calculator.calculate()
- [ ] 77. 实现方法分发逻辑
- [ ] 78. 加载参数（从 ParameterManager）
- [ ] 79. 添加日志输出（参数、计算统计）
- [ ] 80. 生成 span_id（格式：span_calculator_{uuid}）
- [ ] 81. 添加错误处理（try-except）

#### 5.6 Validator 实施
- [ ] 82. 创建文件 `validator.py`
- [ ] 83. 实现 Validator.__init__()
- [ ] 84. 实现 Validator.validate()
- [ ] 85. 实现 NaN/Inf 检查
- [ ] 86. 实现范围验证（min_flow, max_flow）
- [ ] 87. 实现物理约束验证（流量 ≤ 主管流量 × max_ratio）
- [ ] 88. 实现质量评分计算
- [ ] 89. 添加日志输出（验证规则、验证结果、质量评分）
- [ ] 90. 生成 span_id（格式：span_validator_{uuid}）



### 9. 六个计算方法详细设计

**文件**: `app/services/calculation/metrics/pump_flow_rate/methods/`

#### 9.1 Method A - 功率×频率加权分摊

**文件**: `methods/method_a.py`

**公式**: `Q_i = Q_total × (P_i^α × f_i^β) / Σ(P_j^α × f_j^β)`

**参数**:
- `alpha`: 功率指数（默认1.0，可优化）
- `beta`: 频率指数（默认1.0，可优化）

**关键实现**:
```python
def method_a(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method A: 功率×频率加权分摊

    公式: Q_i = Q_total × (P_i^α × f_i^β) / Σ(P_j^α × f_j^β)

    注意：数据已在 DataFilter 阶段使用 running=1 过滤，
         此处不再使用硬编码阈值 f_thr 和 p_thr
    """
    alpha = params.get('alpha', 1.0)
    beta = params.get('beta', 1.0)

    # 计算权重（移除硬编码阈值，直接计算）
    df['weight'] = (df['power'] ** alpha) * (df['frequency'] ** beta)

    # 按时间分组，计算总权重
    df['total_weight'] = df.groupby('ts_bucket')['weight'].transform('sum')

    # 计算流量
    df['pump_flow_rate'] = df['main_flow'] * (df['weight'] / df['total_weight'])

    return df[['ts_bucket', 'device_id', 'pump_flow_rate']]
```

**检查清单**:
- [ ] 91. 创建目录 `methods/`
- [ ] 92. 创建文件 `methods/method_a.py`
- [ ] 93. 实现 method_a() 函数
- [ ] 94. 加载参数 alpha, beta
- [ ] 95. 计算权重（移除硬编码阈值）
- [ ] 96. 添加注释说明移除了硬编码阈值
- [ ] 97. 处理除零错误（total_weight = 0）
- [ ] 98. 添加单元测试

---

#### 9.2 Method B - 累计流量导数

**文件**: `methods/method_b.py`

**公式**: `Q_i(t) = [CF_i(t) - CF_i(t-1)] / Δt`

**参数**:
- `smooth_window`: 平滑窗口大小（默认5）

**关键实现**:
```python
def method_b(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method B: 累计流量导数

    公式: Q_i(t) = [CF_i(t) - CF_i(t-1)] / Δt
    """
    smooth_window = int(params.get('smooth_window', 5))

    # 按设备排序
    df = df.sort_values(['device_id', 'ts_bucket'])

    # 计算导数
    df['cumulative_flow_diff'] = df.groupby('device_id')['cumulative_flow'].diff()
    df['time_diff'] = df.groupby('device_id')['ts_bucket'].diff().dt.total_seconds()

    # 流量 = 差值 / 时间差
    df['pump_flow_rate'] = df['cumulative_flow_diff'] / df['time_diff']

    # 平滑处理
    df['pump_flow_rate'] = df.groupby('device_id')['pump_flow_rate'].transform(
        lambda x: x.rolling(window=smooth_window, min_periods=1).mean()
    )

    return df[['ts_bucket', 'device_id', 'pump_flow_rate']]
```

**检查清单**:
- [ ] 99. 创建文件 `methods/method_b.py`
- [ ] 100. 实现 method_b() 函数
- [ ] 101. 加载参数 smooth_window
- [ ] 102. 计算累计流量差值
- [ ] 103. 计算时间差
- [ ] 104. 计算导数
- [ ] 105. 实现平滑处理
- [ ] 106. 添加单元测试

---

#### 9.3 Method C - 单泵直读

**文件**: `methods/method_c.py`

**公式**: `Q_i = Q_total`（运行泵数=1时）

**参数**: 无

**关键实现**:
```python
def method_c(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method C: 单泵直读

    公式: Q_i = Q_total（运行泵数=1时）
    """
    # 直接使用主管流量
    df['pump_flow_rate'] = df['main_flow']

    return df[['ts_bucket', 'device_id', 'pump_flow_rate']]
```

**检查清单**:
- [ ] 107. 创建文件 `methods/method_c.py`
- [ ] 108. 实现 method_c() 函数
- [ ] 109. 直接使用主管流量
- [ ] 110. 添加单元测试

---

#### 9.4 Method D - 功率加权分摊

**文件**: `methods/method_d.py`

**公式**: `Q_i = Q_total × P_i^α / Σ(P_j^α)`

**参数**:
- `alpha`: 功率指数（默认1.0，可优化）

**关键实现**:
```python
def method_d(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method D: 功率加权分摊

    公式: Q_i = Q_total × P_i^α / Σ(P_j^α)

    注意：数据已在 DataFilter 阶段使用 running=1 过滤，
         此处不再使用硬编码阈值 p_thr
    """
    alpha = params.get('alpha', 1.0)

    # 计算权重（移除硬编码阈值，直接计算）
    df['weight'] = df['power'] ** alpha

    # 按时间分组，计算总权重
    df['total_weight'] = df.groupby('ts_bucket')['weight'].transform('sum')

    # 计算流量
    df['pump_flow_rate'] = df['main_flow'] * (df['weight'] / df['total_weight'])

    return df[['ts_bucket', 'device_id', 'pump_flow_rate']]
```

**检查清单**:
- [ ] 111. 创建文件 `methods/method_d.py`
- [ ] 112. 实现 method_d() 函数
- [ ] 113. 加载参数 alpha
- [ ] 114. 计算权重（移除硬编码阈值 p_thr）
- [ ] 115. 添加注释说明移除了硬编码阈值
- [ ] 116. 处理除零错误
- [ ] 117. 添加单元测试

---

#### 9.5 Method E - 频率加权分摊

**文件**: `methods/method_e.py`

**公式**: `Q_i = Q_total × f_i^β / Σ(f_j^β)`

**参数**:
- `beta`: 频率指数（默认1.0，可优化）

**关键实现**:
```python
def method_e(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method E: 频率加权分摊

    公式: Q_i = Q_total × f_i^β / Σ(f_j^β)

    注意：数据已在 DataFilter 阶段使用 running=1 过滤，
         此处不再使用硬编码阈值 f_thr
    """
    beta = params.get('beta', 1.0)

    # 计算权重（移除硬编码阈值，直接计算）
    df['weight'] = df['frequency'] ** beta

    # 按时间分组，计算总权重
    df['total_weight'] = df.groupby('ts_bucket')['weight'].transform('sum')

    # 计算流量
    df['pump_flow_rate'] = df['main_flow'] * (df['weight'] / df['total_weight'])

    return df[['ts_bucket', 'device_id', 'pump_flow_rate']]
```

**检查清单**:
- [ ] 118. 创建文件 `methods/method_e.py`
- [ ] 119. 实现 method_e() 函数
- [ ] 120. 加载参数 beta
- [ ] 121. 计算权重（移除硬编码阈值 f_thr）
- [ ] 122. 添加注释说明移除了硬编码阈值
- [ ] 123. 处理除零错误
- [ ] 124. 添加单元测试

---

#### 9.6 Method F - 数据驱动回归

**文件**: `methods/method_f.py`

**公式**: `Q_i = f(P_i, f_i, Q_total)` （线性回归或其他模型）

**参数**:
- `model_type`: 模型类型（默认'linear'）
- `min_samples`: 最小样本数（默认100）

**关键实现**:
```python
def method_f(df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
    """
    Method F: 数据驱动回归

    公式: Q_i = f(P_i, f_i, Q_total)
    """
    model_type = params.get('model_type', 'linear')
    min_samples = int(params.get('min_samples', 100))

    # 加载历史数据（从数据库）
    # 训练模型
    # 预测流量

    # 简化实现（使用线性回归）
    from sklearn.linear_model import LinearRegression

    # 特征: power, frequency, main_flow
    X = df[['power', 'frequency', 'main_flow']].values

    # 如果有历史标签数据，训练模型
    # 否则，使用默认模型或回退到其他方法

    # 预测
    # df['pump_flow_rate'] = model.predict(X)

    # 暂时回退到 method_a
    from .method_a import method_a
    return method_a(df, {'alpha': 1.0, 'beta': 1.0})
```

**检查清单**:
- [ ] 125. 创建文件 `methods/method_f.py`
- [ ] 126. 实现 method_f() 函数
- [ ] 127. 加载参数 model_type, min_samples
- [ ] 128. 实现历史数据加载
- [ ] 129. 实现模型训练
- [ ] 130. 实现预测
- [ ] 131. 实现回退逻辑（样本不足时）
- [ ] 132. 添加单元测试

---

#### 9.7 Methods 模块集成
- [ ] 133. 创建文件 `methods/__init__.py`
- [ ] 134. 导出6个方法函数
- [ ] 135. 添加模块文档



## 🔧 第五部分：参数配置详细方案

### 1. 参数定义（移除 f_thr 和 p_thr）

**12个参数**（原14个，移除2个）:

| 参数名 | 类型 | 默认值 | 说明 | 适用方法 |
|--------|------|--------|------|----------|
| alpha | float | 1.0 | 功率指数 | method_a, method_d |
| beta | float | 1.0 | 频率指数 | method_a, method_e |
| smooth_window | int | 5 | 平滑窗口大小 | method_b |
| model_type | string | 'linear' | 模型类型 | method_f |
| min_samples | int | 100 | 最小样本数 | method_f |
| min_flow | float | 0.0 | 最小有效流量 | validator |
| max_flow | float | 200.0 | 最大有效流量 | validator |
| max_ratio | float | 1.1 | 最大流量比例 | validator |
| ~~f_thr~~ | ~~float~~ | ~~3.0~~ | ~~频率阈值~~ | ~~已删除~~ |
| ~~p_thr~~ | ~~float~~ | ~~0.5~~ | ~~功率阈值~~ | ~~已删除~~ |

---

### 2. 参数初始化SQL

**全局级参数**（适用于所有泵站和设备）:

```sql
-- 插入全局级参数（station_id = NULL, device_id = NULL）
INSERT INTO calculation_parameters (
    metric_key, method_id, param_name, param_value,
    station_id, device_id, created_at, updated_at
) VALUES
    -- Method A 参数
    ('pump_flow_rate', 'method_a', 'alpha', 1.0, NULL, NULL, NOW(), NOW()),
    ('pump_flow_rate', 'method_a', 'beta', 1.0, NULL, NULL, NOW(), NOW()),

    -- Method B 参数
    ('pump_flow_rate', 'method_b', 'smooth_window', 5, NULL, NULL, NOW(), NOW()),

    -- Method D 参数
    ('pump_flow_rate', 'method_d', 'alpha', 1.0, NULL, NULL, NOW(), NOW()),

    -- Method E 参数
    ('pump_flow_rate', 'method_e', 'beta', 1.0, NULL, NULL, NOW(), NOW()),

    -- Method F 参数
    ('pump_flow_rate', 'method_f', 'model_type', 'linear', NULL, NULL, NOW(), NOW()),
    ('pump_flow_rate', 'method_f', 'min_samples', 100, NULL, NULL, NOW(), NOW()),

    -- Validator 参数
    ('pump_flow_rate', 'validator', 'min_flow', 0.0, NULL, NULL, NOW(), NOW()),
    ('pump_flow_rate', 'validator', 'max_flow', 200.0, NULL, NULL, NOW(), NOW()),
    ('pump_flow_rate', 'validator', 'max_ratio', 1.1, NULL, NULL, NOW(), NOW())
ON CONFLICT (metric_key, method_id, param_name, station_id, device_id)
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    updated_at = NOW();

COMMENT ON COLUMN calculation_parameters.param_name IS '参数名称（已移除 f_thr 和 p_thr）';
```

**泵站级参数示例**（覆盖全局参数）:

```sql
-- 为泵站14设置特定参数
INSERT INTO calculation_parameters (
    metric_key, method_id, param_name, param_value,
    station_id, device_id, created_at, updated_at
) VALUES
    ('pump_flow_rate', 'method_a', 'alpha', 1.2, 14, NULL, NOW(), NOW()),
    ('pump_flow_rate', 'method_a', 'beta', 0.8, 14, NULL, NOW(), NOW())
ON CONFLICT (metric_key, method_id, param_name, station_id, device_id)
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    updated_at = NOW();
```

**设备级参数示例**（覆盖泵站和全局参数）:

```sql
-- 为设备105设置特定参数
INSERT INTO calculation_parameters (
    metric_key, method_id, param_name, param_value,
    station_id, device_id, created_at, updated_at
) VALUES
    ('pump_flow_rate', 'validator', 'max_flow', 150.0, 14, 105, NOW(), NOW())
ON CONFLICT (metric_key, method_id, param_name, station_id, device_id)
DO UPDATE SET
    param_value = EXCLUDED.param_value,
    updated_at = NOW();
```

---

### 3. 参数配置检查清单

- [ ] 136. 执行全局级参数初始化SQL
- [ ] 137. 验证全局级参数插入成功（COUNT = 10）
- [ ] 138. 验证 f_thr 和 p_thr 不存在（COUNT = 0）
- [ ] 139. 测试参数加载（全局级）
- [ ] 140. 测试参数加载（泵站级覆盖）
- [ ] 141. 测试参数加载（设备级覆盖）
- [ ] 142. 测试三级优先级（设备 > 泵站 > 全局）
- [ ] 143. 测试参数缓存机制
- [ ] 144. 测试参数更新和缓存清除

---

## 📝 第六部分：日志系统详细设计

### 1. 应用层日志扩展

**文件**: `app/core/logging/setup.py`（扩展现有日志系统）

**新增功能**:
1. 支持 trace_id 和 span_id 上下文传递
2. 支持结构化日志（extra_data）
3. 支持日志写入 calculation_logs 表

**关键实现**:
```python
import contextvars

# 上下文变量
trace_id_var = contextvars.ContextVar('trace_id', default=None)
span_id_var = contextvars.ContextVar('span_id', default=None)

def log_calculation(
    message: str,
    trace_id: str = None,
    span_id: str = None,
    parent_span_id: str = None,
    metric_key: str = None,
    station_id: int = None,
    device_id: int = None,
    stage: str = None,
    log_level: str = 'INFO',
    extra_data: dict = None
):
    """
    记录计算日志（同时写入文件和数据库）

    Args:
        message: 日志消息
        trace_id: 追踪ID
        span_id: 阶段ID
        parent_span_id: 父阶段ID
        metric_key: 指标键
        station_id: 泵站ID
        device_id: 设备ID
        stage: 阶段名称
        log_level: 日志级别
        extra_data: 额外数据（JSON）
    """
    # 1. 写入文件日志
    log_activity(message, extra={'extra_data': extra_data})

    # 2. 写入数据库日志
    from app.adapters.db import get_connection

    sql = """
        INSERT INTO calculation_logs (
            task_id, trace_id, span_id, parent_span_id,
            metric_key, station_id, device_id, stage,
            log_level, message, extra_data
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, [
                None,  # task_id（可选）
                trace_id,
                span_id,
                parent_span_id,
                metric_key,
                station_id,
                device_id,
                stage,
                log_level,
                message,
                json.dumps(extra_data) if extra_data else None
            ])
            conn.commit()
```

---

### 2. 完整日志输出示例

**单个设备的端到端日志追踪**:

```
[流水线] 开始执行
  trace_id: trace_105_20250114100000
  device_id: 105
  start_time: 2025-01-14 10:00:00
  end_time: 2025-01-14 11:00:00

  [数据加载] 进入阶段
    span_id: span_data_loader_abc123
    parent_span_id: trace_105_20250114100000

  [数据加载] SQL执行
    sql_duration_ms: 245
    rows_loaded: 3600

  [数据加载] JOIN结果
    running_field_present: true
    running_1_count: 2400
    running_0_count: 1200

  [数据加载] 完成
    final_rows: 3600

  [数据过滤] 进入阶段
    span_id: span_data_filter_def456
    parent_span_id: trace_105_20250114100000

  [数据过滤] 过滤条件
    filter_by: running=1
    note: 已移除硬编码阈值 f_thr 和 p_thr

  [数据过滤] 过滤统计
    original_count: 3600
    running_filtered: 1200
    nan_filtered: 50
    negative_filtered: 10
    final_count: 2340
    filter_rate: 35.00%

  [数据过滤] 完成

  [方法选择] 进入阶段
    span_id: span_method_selector_ghi789
    parent_span_id: trace_105_20250114100000

  [方法选择] 可用指标
    main_flow: true
    power: true
    frequency: true
    cumulative_flow: false

  [方法选择] 依赖检查
    method_a: dependencies_met=true, conditions_met=true
    method_b: dependencies_met=false (cumulative_flow missing)
    method_c: dependencies_met=true, conditions_met=false (running_pumps=3)
    method_d: dependencies_met=true, conditions_met=true
    method_e: dependencies_met=true, conditions_met=true
    method_f: dependencies_met=false (insufficient samples)

  [方法选择] 方法选择
    selected_method: method_a
    reason: 最高优先级且满足所有条件

  [方法选择] 完成

  [计算执行] 进入阶段
    span_id: span_calculator_jkl012
    parent_span_id: trace_105_20250114100000

  [计算执行] 参数加载
    method_id: method_a
    alpha: 1.2
    beta: 0.8
    note: 参数从数据库加载，无硬编码阈值

  [计算执行] 计算统计
    valid_count: 2340
    mean_value: 45.6
    max_value: 89.3

  [计算执行] 完成

  [结果验证] 进入阶段
    span_id: span_validator_mno345
    parent_span_id: trace_105_20250114100000

  [结果验证] 验证规则
    min_flow: 0.0
    max_flow: 200.0
    max_ratio: 1.1

  [结果验证] 验证结果
    original_count: 2340
    nan_filtered: 0
    range_filtered: 5
    physical_filtered: 12
    valid_count: 2323
    quality_score: 99.27%
    is_valid: true

  [结果验证] 完成

[流水线] 执行完成
  trace_id: trace_105_20250114100000
  device_id: 105
  method_id: method_a
  results_count: 2323
```

---

### 3. 日志系统检查清单

- [ ] 145. 扩展 app/core/logging/setup.py
- [ ] 146. 实现 log_calculation() 函数
- [ ] 147. 实现 trace_id 上下文变量
- [ ] 148. 实现 span_id 上下文变量
- [ ] 149. 实现日志写入 calculation_logs 表
- [ ] 150. 测试日志写入（文件 + 数据库）
- [ ] 151. 测试 trace_id 传递
- [ ] 152. 测试 span_id 生成
- [ ] 153. 测试日志查询（按 trace_id）
- [ ] 154. 测试日志查询（按 device_id）
- [ ] 155. 验证完整日志输出（端到端）



## 🧪 第七部分：测试方案详细设计

### 1. 单元测试方案

**测试框架**: pytest + pytest-cov

**测试覆盖目标**: ≥ 80%

#### 1.1 共享层单元测试

**文件**: `tests/unit/calculation/shared/test_scheduler.py`

**测试用例**:
- [ ] 156. test_scheduler_create_tasks（创建任务）
- [ ] 157. test_scheduler_execute_tasks（执行任务）
- [ ] 158. test_scheduler_parallel_execution（并行执行）
- [ ] 159. test_scheduler_error_handling（错误处理）
- [ ] 160. test_scheduler_shutdown（关闭）

**文件**: `tests/unit/calculation/shared/test_data_writer.py`

**测试用例**:
- [ ] 161. test_data_writer_write（批量写入）
- [ ] 162. test_data_writer_adaptive_batch_size（自适应批量大小）
- [ ] 163. test_data_writer_conflict_handling（冲突处理）
- [ ] 164. test_data_writer_empty_records（空记录）

**文件**: `tests/unit/calculation/shared/test_parameter_manager.py`

**测试用例**:
- [ ] 165. test_parameter_manager_get_params_global（全局级参数）
- [ ] 166. test_parameter_manager_get_params_station（泵站级参数）
- [ ] 167. test_parameter_manager_get_params_device（设备级参数）
- [ ] 168. test_parameter_manager_priority（三级优先级）
- [ ] 169. test_parameter_manager_cache（缓存机制）
- [ ] 170. test_parameter_manager_default_params（默认参数）

---

#### 1.2 指标专用层单元测试

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/test_data_loader.py`

**测试用例**:
- [ ] 171. test_data_loader_load（数据加载）
- [ ] 172. test_data_loader_join_running（JOIN mv_device_running_1s）
- [ ] 173. test_data_loader_time_range（时间范围过滤）
- [ ] 174. test_data_loader_empty_result（空结果）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/test_data_filter.py`

**测试用例**:
- [ ] 175. test_data_filter_running_filter（running=1 过滤）
- [ ] 176. test_data_filter_no_hardcoded_thresholds（验证移除硬编码阈值）
- [ ] 177. test_data_filter_nan_removal（NaN 移除）
- [ ] 178. test_data_filter_negative_removal（负值移除）
- [ ] 179. test_data_filter_statistics（过滤统计）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/test_method_selector.py`

**测试用例**:
- [ ] 180. test_method_selector_method_a（选择 method_a）
- [ ] 181. test_method_selector_method_b（选择 method_b）
- [ ] 182. test_method_selector_method_c（选择 method_c）
- [ ] 183. test_method_selector_priority（优先级）
- [ ] 184. test_method_selector_dependencies（依赖检查）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/test_calculator.py`

**测试用例**:
- [ ] 185. test_calculator_dispatch（方法分发）
- [ ] 186. test_calculator_parameter_loading（参数加载）
- [ ] 187. test_calculator_no_hardcoded_thresholds（验证移除硬编码阈值）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/test_validator.py`

**测试用例**:
- [ ] 188. test_validator_range_validation（范围验证）
- [ ] 189. test_validator_nan_inf_check（NaN/Inf 检查）
- [ ] 190. test_validator_physical_constraints（物理约束）
- [ ] 191. test_validator_quality_score（质量评分）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/methods/test_method_a.py`

**测试用例**:
- [ ] 192. test_method_a_calculation（计算正确性）
- [ ] 193. test_method_a_no_hardcoded_thresholds（验证移除硬编码阈值）
- [ ] 194. test_method_a_parameters（参数使用）
- [ ] 195. test_method_a_zero_weight（除零处理）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/methods/test_method_d.py`

**测试用例**:
- [ ] 196. test_method_d_calculation（计算正确性）
- [ ] 197. test_method_d_no_p_thr（验证移除 p_thr）
- [ ] 198. test_method_d_parameters（参数使用）

**文件**: `tests/unit/calculation/metrics/pump_flow_rate/methods/test_method_e.py`

**测试用例**:
- [ ] 199. test_method_e_calculation（计算正确性）
- [ ] 200. test_method_e_no_f_thr（验证移除 f_thr）
- [ ] 201. test_method_e_parameters（参数使用）

---

### 2. 集成测试方案

**文件**: `tests/integration/calculation/test_pump_flow_rate_pipeline.py`

**测试用例**:
- [ ] 202. test_pipeline_end_to_end（端到端流程）
- [ ] 203. test_pipeline_with_real_data（真实数据）
- [ ] 204. test_pipeline_logging（日志输出）
- [ ] 205. test_pipeline_trace_id（trace_id 传递）
- [ ] 206. test_pipeline_error_handling（错误处理）
- [ ] 207. test_pipeline_multiple_devices（多设备）

---

### 3. 性能测试方案

**文件**: `tests/performance/test_pump_flow_rate_performance.py`

**测试用例**:
- [ ] 208. test_performance_single_device（单设备性能）
- [ ] 209. test_performance_100_devices（100设备性能）
- [ ] 210. test_performance_1000_devices（1000设备性能）
- [ ] 211. test_performance_memory_usage（内存使用）
- [ ] 212. test_performance_database_queries（数据库查询次数）

**性能基准**:
- 单设备计算时间: ≤ 100ms
- 100设备计算时间: ≤ 5s
- 1000设备计算时间: ≤ 30s
- 内存使用: ≤ 500MB
- 数据库查询次数: ≤ 10次/设备

---

### 4. 回归测试方案

**目标**: 确保重构不影响其他功能

**测试用例**:
- [ ] 213. test_regression_other_metrics（其他指标不受影响）
- [ ] 214. test_regression_orchestrator_deprecated（orchestrator 标记为 deprecated）
- [ ] 215. test_regression_database_schema（数据库结构不变）
- [ ] 216. test_regression_api_compatibility（API 兼容性）

---

### 5. 测试数据准备

**Mock 数据**:
```python
# tests/fixtures/pump_flow_rate_data.py

import pandas as pd
from datetime import datetime, timedelta

def create_test_data():
    """创建测试数据"""
    base_time = datetime(2025, 1, 14, 10, 0, 0)

    data = []
    for i in range(3600):  # 1小时，每秒一条
        ts = base_time + timedelta(seconds=i)

        # 设备105（运行）
        data.append({
            'ts_bucket': ts,
            'station_id': 14,
            'device_id': 105,
            'main_flow': 100.0,
            'power': 50.0,
            'frequency': 45.0,
            'cumulative_flow': 1000.0 + i * 0.1,
            'running': 1  # ← 关键：运行状态
        })

        # 设备106（停机）
        data.append({
            'ts_bucket': ts,
            'station_id': 14,
            'device_id': 106,
            'main_flow': 100.0,
            'power': 0.0,  # ← 停机
            'frequency': 0.0,  # ← 停机
            'cumulative_flow': 2000.0,
            'running': 0  # ← 关键：停机状态
        })

    return pd.DataFrame(data)
```

---

### 6. 测试执行命令

```bash
# 运行所有单元测试
pytest tests/unit/ -v --cov=app/services/calculation --cov-report=html

# 运行集成测试
pytest tests/integration/ -v

# 运行性能测试
pytest tests/performance/ -v --benchmark-only

# 运行回归测试
pytest tests/regression/ -v

# 运行所有测试
pytest tests/ -v --cov=app/services/calculation --cov-report=html --cov-report=term
```

---

## 🚀 第八部分：部署和验证方案

### 1. 部署前检查清单

- [ ] 217. 所有单元测试通过（覆盖率 ≥ 80%）
- [ ] 218. 所有集成测试通过
- [ ] 219. 性能测试达标
- [ ] 220. 回归测试通过
- [ ] 221. 代码审查通过
- [ ] 222. 文档更新完成
- [ ] 223. 数据库迁移脚本准备完成
- [ ] 224. 回滚脚本准备完成

---

### 2. 部署步骤

#### 2.1 数据库迁移
- [ ] 225. 备份 calculation_parameters 表
- [ ] 226. 创建 calculation_logs 表
- [ ] 227. 创建分区
- [ ] 228. 创建索引
- [ ] 229. 创建分区维护函数
- [ ] 230. 删除 f_thr 和 p_thr 参数
- [ ] 231. 插入新参数（12个）
- [ ] 232. 验证数据库迁移成功

#### 2.2 代码部署
- [ ] 233. 部署共享层代码
- [ ] 234. 部署指标专用层代码
- [ ] 235. 部署日志系统扩展
- [ ] 236. 标记 orchestrator.py 为 deprecated
- [ ] 237. 修改 calculators.py（移除硬编码阈值）
- [ ] 238. 重启应用服务

#### 2.3 配置更新
- [ ] 239. 更新日志配置
- [ ] 240. 更新数据库连接池配置
- [ ] 241. 更新监控配置

---

### 3. 验证步骤

#### 3.1 功能验证
- [ ] 242. 手动触发单设备计算
- [ ] 243. 验证计算结果正确性
- [ ] 244. 验证日志输出完整性
- [ ] 245. 验证 trace_id 传递
- [ ] 246. 验证参数加载（三级优先级）
- [ ] 247. 验证数据库日志写入

#### 3.2 性能验证
- [ ] 248. 监控计算耗时
- [ ] 249. 监控内存使用
- [ ] 250. 监控数据库查询次数
- [ ] 251. 监控日志写入性能

#### 3.3 并行运行验证
- [ ] 252. 新旧系统同时运行
- [ ] 253. 对比计算结果
- [ ] 254. 分析差异原因
- [ ] 255. 确认新系统结果更准确

---

### 4. 回滚策略

**触发条件**:
- 计算结果错误率 > 5%
- 性能下降 > 50%
- 系统错误率 > 1%

**回滚步骤**:
- [ ] 256. 停止新系统
- [ ] 257. 恢复 orchestrator.py（移除 deprecated 标记）
- [ ] 258. 恢复 calculators.py（恢复硬编码阈值）
- [ ] 259. 恢复 calculation_parameters 表（恢复 f_thr 和 p_thr）
- [ ] 260. 删除 calculation_logs 表（可选）
- [ ] 261. 重启应用服务
- [ ] 262. 验证回滚成功

---

### 5. 监控和观察

**监控指标**:
- 计算成功率
- 计算耗时（P50, P95, P99）
- 内存使用
- 数据库查询次数
- 日志写入速率
- 错误率

**观察期**: 7天

**每日检查**:
- [ ] 263. 检查计算成功率（目标 ≥ 95%）
- [ ] 264. 检查计算耗时（目标 P95 ≤ 5s）
- [ ] 265. 检查错误日志
- [ ] 266. 检查性能指标
- [ ] 267. 检查用户反馈

---

## 📊 总结

### 完整检查清单统计

**总计**: 267个检查项

**分类**:
- 数据库改造: 25项
- 垃圾代码删除: 20项
- 共享层实施: 38项
- 指标专用层实施: 45项
- 六个计算方法: 45项
- 参数配置: 9项
- 日志系统: 11项
- 单元测试: 46项
- 集成测试: 6项
- 性能测试: 5项
- 回归测试: 4项
- 部署和验证: 51项

---

**文档结束 - 详细计划制定完成**

