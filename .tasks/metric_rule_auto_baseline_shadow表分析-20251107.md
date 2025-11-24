# metric_rule_auto_baseline_shadow 表深度分析报告

**任务日期**: 2025-11-07
**分析人员**: AI
**任务状态**: 研究模式 - 数据收集完成

---

## 📋 任务目标

分析 `metric_rule_auto_baseline_shadow` 表的以下方面：
1. 数据生成逻辑（数据来源、生成逻辑、触发条件）
2. 表的作用和用途
3. 写入数据的代码位置
4. 读取数据的代码位置
5. 与 `metric_rule_auto_baseline` 表的关系和区别
6. 删除影响评估

---

## 🔍 研究模式分析结果

### 1. 表结构对比

#### metric_rule_auto_baseline（正式表）
- **主键**: `baseline_id` (bigserial)
- **核心字段**: station_id (可空), device_id (可空), metric_id (必填)
- **外键**: station_id, device_id, metric_id 都有外键约束
- **特点**: 有自增主键，允许 station_id 和 device_id 为空（支持全局基线）

#### metric_rule_auto_baseline_shadow（影子表）
- **主键**: 复合主键 (station_id, device_id, metric_id, lookback_days, method, version)
- **核心字段**: station_id (必填), device_id (必填), metric_id (必填)
- **外键**: station_id, device_id, metric_id 都有外键约束
- **特点**: 无自增主键，所有维度字段都是必填，主键包含方法和版本信息

**关键差异**：
- 正式表支持全局基线（station_id/device_id可空），影子表不支持
- 影子表主键包含 method 和 version，支持多版本对比
- 影子表有 remark 字段，正式表没有

---

### 2. 数据生成逻辑

#### 数据来源
**源表**: `public.fact_measurements`

**数据筛选条件**（优先级从高到低）：
1. **优先**: 质量=0 + phase=1（稳态片段）
2. **回退**: 质量=0 + running=1（运行状态）
3. **兜底**: 质量=0（仅质量合格）

#### 生成算法
**方法**: STL（Seasonal-Trend decomposition using Loess）时间序列分解

**处理流程**：
1. 查询实际数据时间范围
2. 根据 lookback_days 计算时间窗口
3. 加载符合条件的时序数据
4. 按 (station_id, device_id, metric_id) 分组
5. 对每组数据：
   - 重采样到 60s 间隔
   - 线性插值填充缺失值
   - 执行 STL 分解（提取趋势、季节性、残差）
   - 在残差上计算稳健统计量（分位数、MAD）
   - 计算跳变阈值、变化率阈值、平台期阈值
6. 写入 `metric_rule_auto_baseline_shadow` 表

**小样本处理**：
- 如果数据点 < 30，从 `metric_rule_auto_baseline` 复制基线到影子表

---

### 3. 触发条件和调用方式

#### CLI命令触发
```bash
# 方式1：显式指定输出到影子表
python -m app.cli.main baseline:auto:compute --output shadow --lookback-days 30

# 方式2：使用STL方法（自动输出到影子表）
python -m app.cli.main baseline:auto:compute --method stl --lookback-days 30
```

#### 代码调用位置
**主要调用点**: `app/cli/main.py::cmd_baseline_auto_compute()` (第565-618行)
- 判断条件: `method == "stl"` 或 `output == "shadow"`
- 调用函数: `app/services/rules/auto_baseline_b.py::run_auto_baseline_b()`

**自动化流程调用**: `app/services/run_all/refresh_all.py` (第132-165行)
- 在 `run-all` 流程中自动执行
- 步骤名称: "baseline_shadow"

---

### 4. 表的作用和用途

#### 核心用途
**实验性基线验证表**：用于存储基于 STL 分解的自动基线结果，供对照和验证使用

#### 设计目的
1. **不污染正式表**: 实验性算法结果写入影子表，不影响生产环境
2. **多版本对比**: 支持同时存储多个版本的基线（通过 version 字段）
3. **算法验证**: 对比 STL 方法（方案B）与 robust 方法（方案A）的效果
4. **安全测试**: 在影子表验证通过后，可手动迁移到正式表

#### 当前状态
**数据状态**: 表为空（0行）
**备份记录**: 所有备份文件显示表为空

---

### 5. 写入数据的代码

#### 唯一写入位置
**文件**: `app/services/rules/auto_baseline_b.py`
**函数**: `run_auto_baseline_b()`
**写入语句**: 第249-257行、第328-336行、第404-412行

**写入逻辑**：
```python
INSERT INTO public.metric_rule_auto_baseline_shadow(
  station_id, device_id, metric_id, lookback_days, method, version,
  p05, p95, median, mad, spike_abs, roc_abs, roc_ratio, 
  flatline_eps, flatline_delta, computed_at, remark
) VALUES (...)
ON CONFLICT (station_id, device_id, metric_id, lookback_days, method, version) 
DO UPDATE SET ...
```

**特点**: 使用 UPSERT 语句，避免重复插入

---

### 6. 读取数据的代码

#### 读取位置
**测试代码**: `tests/test_auto_baseline_investigation.py` (第255-266行)
- 用途: 测试和对比方案A和方案B的结果
- 查询: 显示前5行详细数据

**文档引用**:
- `.memory/数据层/数据表清单.md` (第1137-1172行)
- `.tasks/数据库表使用情况调查报告-20250117.md` (第376-393行)

#### 重要发现
**⚠️ 没有生产代码读取此表**：
- 质量规则生成服务不使用此表
- 质量判定服务不使用此表
- 报表和API不使用此表
- 仅用于测试和对比验证

---

## 📊 记忆检索结果

**已读取规则文档**:
- ✅ `.memory/规则层/项目规则.md`
- ✅ `.memory/规则层/数据库规范.md`

**已检索代码**:
- ✅ 表创建脚本
- ✅ 写入代码
- ✅ 读取代码
- ✅ CLI命令
- ✅ 自动化流程

**已查询数据库**:
- ✅ 表结构对比
- ✅ 外键约束
- ✅ 数据行数（0行）

---

## 🔄 与 metric_rule_auto_baseline 表的关系

### 数据流向关系

```
fact_measurements (原始数据)
    ↓
    ├─→ [方案A: robust方法] → metric_rule_auto_baseline (正式表)
    │   - 使用存储过程 sp_refresh_metric_rule_auto_baseline
    │   - 基于分位数和MAD的稳健统计
    │   - 直接写入生产表
    │
    └─→ [方案B: STL方法] → metric_rule_auto_baseline_shadow (影子表)
        - 使用Python STL分解
        - 基于残差的稳健统计
        - 写入影子表供验证
```

### 小样本回退机制

当影子表数据不足时（< 30个数据点），会从正式表复制基线：
```python
# 代码位置: app/services/rules/auto_baseline_b.py 第232-244行
SELECT p05, p95, median, mad, spike_abs, roc_abs, roc_ratio,
       flatline_eps, flatline_delta
FROM public.metric_rule_auto_baseline
WHERE station_id IS NOT DISTINCT FROM %s
  AND device_id IS NOT DISTINCT FROM %s
  AND metric_id = %s
  AND lookback_days = %s
```

**这是唯一的数据交互点**：影子表会读取正式表的数据作为兜底。

---

## ⚠️ 删除影响评估

### 直接影响

#### 1. 代码层面
**受影响代码**:
- ✅ `app/services/rules/auto_baseline_b.py` - 写入失败
- ✅ `app/cli/main.py::cmd_baseline_auto_compute()` - 命令失败
- ✅ `app/services/run_all/refresh_all.py` - 自动化流程失败
- ✅ `tests/test_auto_baseline_investigation.py` - 测试失败

**影响程度**: 🟡 中等
- 不影响生产功能（无生产代码读取此表）
- 影响实验性功能和测试

#### 2. 功能层面
**受影响功能**:
- ❌ STL方法基线计算（方案B）
- ❌ 多版本基线对比验证
- ❌ 自动化流程中的影子基线步骤

**影响程度**: 🟢 低
- 正式基线计算（方案A）不受影响
- 质量规则生成不受影响
- 质量判定不受影响

#### 3. 数据层面
**数据丢失风险**: 🟢 无风险
- 表当前为空（0行）
- 所有备份文件显示表为空
- 无历史数据积累

### 间接影响

#### 1. 备份系统
**受影响位置**:
- `app/services/ingest/prepare_dim/__init__.py` (第1199行)
- `scripts/test_prepare_dim_backup.py` (第56行)

**影响**: 备份列表中包含此表，删除后需更新备份配置

#### 2. 文档和记忆
**需要更新的文档**:
- `.memory/数据层/数据表清单.md`
- `docs/database_dictionary.md`
- `docs/CLI指令使用手册.md`

---

## 🎯 删除建议

### 建议：✅ 可以删除

**理由**：
1. **无生产依赖**: 没有生产代码读取此表
2. **无数据积累**: 表为空，无历史数据
3. **功能可替代**: STL方法可以直接写入正式表
4. **维护成本**: 减少表数量，简化架构

### 删除前提条件

1. **确认无隐藏依赖**:
   - ✅ 已检索所有代码引用
   - ✅ 已确认无视图依赖
   - ✅ 已确认无存储过程依赖

2. **确认数据状态**:
   - ✅ 表为空（0行）
   - ✅ 所有备份为空

3. **确认功能替代**:
   - ✅ 方案A（正式表）功能完整
   - ✅ 可以将STL方法直接写入正式表

### 删除步骤

1. **备份当前状态**（虽然为空，但保持流程完整性）
2. **删除表**：`DROP TABLE public.metric_rule_auto_baseline_shadow CASCADE;`
3. **删除迁移脚本**：`scripts/sql/migrations/025_create_metric_rule_auto_baseline_shadow.sql`
4. **删除相关代码**：
   - `app/services/rules/auto_baseline_b.py`（或修改为写入正式表）
   - `app/cli/main.py` 中的 `--output shadow` 选项
   - `app/services/run_all/refresh_all.py` 中的影子基线步骤
5. **更新备份配置**：从备份列表中移除此表
6. **更新文档**：删除所有相关文档说明

---

---

## 🎯 核心发现：两个表的实际用途

### 完整数据流向图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     数据源：fact_measurements                        │
│                    (原始测量数据，quality_status=0)                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │  方案A: robust方法     │   │  方案B: STL方法        │
    │  (存储过程计算)        │   │  (Python计算)          │
    └───────────┬───────────┘   └───────────┬───────────┘
                │                           │
                ▼                           ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │ metric_rule_auto_     │   │ metric_rule_auto_     │
    │ baseline (正式表)      │   │ baseline_shadow       │
    │ - p05, p95, median    │   │ (影子表)              │
    │ - spike_abs, roc_abs  │   │ - 相同字段结构         │
    │ - flatline_eps        │   │ - 实验性算法结果       │
    └───────────┬───────────┘   └───────────────────────┘
                │
                │ compute_metric_quality_rules()
                │ (读取baseline,填充规则表)
                ▼
    ┌───────────────────────┐
    │ metric_quality_rules  │
    │ (质量规则表)           │
    │ - value_min, value_max│
    │ - spike_abs, roc_abs  │
    │ - flatline_eps        │
    └───────────┬───────────┘
                │
                │ sp_mark_quality_window_vfast()
                │ (读取规则,执行质量检查)
                ▼
    ┌───────────────────────┐
    │ fact_measurements     │
    │ (更新质量标注)         │
    │ - quality_status      │
    │ - quality_codes[]     │
    └───────────────────────┘
```

### 关键功能：质量检查系统

**metric_rule_auto_baseline 表被以下功能使用**：

#### 1. 质量规则生成
**函数**: `compute_metric_quality_rules()`
**文件**: `app/services/rules/metric_quality_rules.py` (已编译为 .pyc)

**逻辑**：
```python
# 伪代码
SELECT * FROM metric_rule_auto_baseline
WHERE station_id = ? AND device_id = ? AND metric_id = ?

# 如果 metric_quality_rules 中不存在该规则
INSERT INTO metric_quality_rules (
    value_min = baseline.p05,
    value_max = baseline.p95,
    spike_abs = baseline.spike_abs,
    roc_abs = baseline.roc_abs,
    flatline_eps = baseline.flatline_eps
) VALUES (...)

# 如果已存在但字段为NULL
UPDATE metric_quality_rules
SET value_min = baseline.p05 WHERE value_min IS NULL
```

**调用位置**：
- CLI命令: `python -m app.cli.main rules:quality:compute`
- 自动化流程: `app/services/run_all/refresh_all.py`

---

#### 2. 质量检查执行
**存储过程**: `sp_mark_quality_window_vfast()`
**文件**: `scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql`

**逻辑**：
```sql
-- 步骤1: 从 metric_quality_rules 读取规则参数
SELECT value_min, value_max, spike_abs, roc_abs, flatline_eps
FROM public.metric_quality_rules r
WHERE r.metric_id = fp.metric_id
  AND (r.device_id = fp.device_id OR r.device_id IS NULL)
  AND (r.station_id = fp.station_id OR r.station_id IS NULL)
ORDER BY (r.device_id IS NOT NULL) DESC, (r.station_id IS NOT NULL) DESC
LIMIT 1

-- 步骤2: 执行质量检查
-- 101: 物理越界检查
UPDATE fact_measurements
SET quality_codes = array_append(quality_codes, 101),
    quality_status = 2
WHERE value < value_min OR value > value_max

-- 111: 异常跳变检查
UPDATE fact_measurements
SET quality_codes = array_append(quality_codes, 111),
    quality_status = GREATEST(quality_status, 1)
WHERE ABS(value - prev_value) > spike_abs

-- 121: 平台期检查
UPDATE fact_measurements
SET quality_codes = array_append(quality_codes, 121),
    quality_status = GREATEST(quality_status, 1)
WHERE stddev_window < flatline_eps
```

**调用位置**：
- CLI命令: `python -m app.cli.main quality:mark`
- 自动化流程: `app/services/run_all/refresh_all.py`
- Python包装: `app/services/quality/mark_window.py::mark_quality_window()`

---

#### 3. 视图合并（手动规则 + 自动基线）
**视图**: `v_effective_metric_rules`
**文件**: `scripts/sql/migrations/035_drop_recreate_v_effective_metric_rules.sql`

**逻辑**：
```sql
CREATE VIEW public.v_effective_metric_rules AS
SELECT
  COALESCE(r.station_id, b.station_id) AS station_id,
  COALESCE(r.device_id,  b.device_id)  AS device_id,
  COALESCE(r.metric_id,  b.metric_id)  AS metric_id,
  -- 手工规则优先，否则采用自动基线
  COALESCE(r.value_min, b.p05) AS value_min,
  COALESCE(r.value_max, b.p95) AS value_max,
  COALESCE(r.spike_abs, b.spike_abs) AS spike_abs,
  COALESCE(r.roc_abs,   b.roc_abs)   AS roc_abs,
  COALESCE(r.flatline_eps, b.flatline_eps) AS flatline_eps
FROM public.metric_quality_rules r
FULL JOIN public.metric_rule_auto_baseline b
  ON r.metric_id = b.metric_id
 AND (r.station_id IS NOT DISTINCT FROM b.station_id)
 AND (r.device_id  IS NOT DISTINCT FROM b.device_id);
```

**用途**: 提供统一的规则查询接口（手动优先，自动兜底）

---

### 影子表的用途

**metric_rule_auto_baseline_shadow 表**：
- ❌ **不被任何生产功能使用**
- ✅ 仅用于测试和对比验证（`tests/test_auto_baseline_investigation.py`）
- ✅ 存储实验性STL算法结果
- ✅ 当前为空（0行）

---

## 🔄 下一步：进入创新模式

研究模式已完成，将自动进入创新模式，讨论删除方案和替代方案。

