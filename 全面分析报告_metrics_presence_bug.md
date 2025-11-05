# 全面分析报告：metrics_presence_per_second_device 表 Bug 调查

**日期**：2025-11-04  
**任务**：全面检索和修复 `metrics_presence_per_second_device` 表及相关表中 metric_id vs metric_key 混用的问题

---

## 一、核心问题确认

### 1.1 数据库实际情况（已验证）

**当前表中的数据**：
```sql
-- 查询结果（14400条记录全部为metric_id格式）
available_metrics: ["12", "13", "16"]  -- ❌ 错误：存储的是字符串形式的 metric_id
need_compute_metrics: []
```

**应该存储的数据**：
```sql
-- 根据 dim_metric_config 表的映射
id=12 → metric_key="pump_outlet_pressure"
id=13 → metric_key="pump_inlet_pressure"  
id=14 → metric_key="pump_flow_rate"
id=16 → metric_key="pump_head"

-- 应该存储
available_metrics: ["pump_outlet_pressure", "pump_inlet_pressure", "pump_head"]
```

**数据格式统计**：
- metric_id格式（纯数字）：14400条 ❌
- metric_key格式（字母下划线）：0条 ✅
- **结论**：100% 的数据都是错误格式！

---

## 二、所有写入路径分析

### 2.1 写入路径1：orchestrator.py（❌ 错误）

**位置**：`app/services/calculation/orchestrator.py` 第1250-1350行

**调用链**：
```
write_to_fact_measurements() 第1220-1242行
  └─> update_metrics_presence() 第1250-1350行
```

**问题代码**：
```python
# 第1275-1280行
metric_ids = []
for key in metric_keys:
    mid = metric_mapper.key_to_id(key)  # ❌ 转换为ID
    if mid is not None:
        metric_ids.append(str(mid))  # ❌ 写入的是metric_id字符串

# 第1314-1323行
rows = [
    (
        station_id,
        device_id,
        ts,
        metric_ids,  # ❌ 错误：使用metric_ids而非metric_keys
        []
    )
    for ts in timestamps
]
```

**影响范围**：
- 每次成功计算并写入 fact_measurements 后都会调用此方法
- 影响所有通过 Python 代码计算的指标

---

### 2.2 写入路径2：sync_presence_from_cagg.sql（✅ 正确）

**位置**：`scripts/sql/sync_presence_from_cagg.sql` 第28-61行

**正确实现**：
```sql
-- 第28-35行：从 fact_measurements 提取 metric_key
present AS (
  SELECT fm.station_id, fm.device_id, fm.ts_bucket AS ts, mc.metric_key
  FROM public.fact_measurements fm
  JOIN public.dim_metric_config mc ON mc.id = fm.metric_id  -- ✅ JOIN获取metric_key
  WHERE fm.ts_bucket >= (SELECT s FROM bounds) AND fm.ts_bucket < (SELECT e FROM bounds)
)

-- 第33-37行：聚合为数组
available_sec AS (
  SELECT p.station_id, p.device_id, p.ts AS ts_second,
         array_agg(DISTINCT p.metric_key ORDER BY p.metric_key) AS available_metrics  -- ✅ 使用metric_key
  FROM present p
  GROUP BY p.station_id, p.device_id, p.ts
)
```

**调用位置**：
- `app/services/reporting/presence_writer.py` 第180-206行的 `upsert_window()` 函数

---

### 2.3 写入路径3：数据库函数（✅ 正确）

**位置**：`scripts/sql/m2/007_fn_metrics_presence_per_second.sql`

**函数签名**：
```sql
CREATE OR REPLACE FUNCTION public.metrics_presence_per_second(
    _start timestamptz,
    _end   timestamptz,
    _station_name text DEFAULT NULL,
    _device_name  text DEFAULT NULL
) RETURNS TABLE (
    station text,
    device  text,
    ts_utc timestamptz,
    need_compute_metrics text[],  -- ✅ 返回metric_key数组
    available_metrics    text[]   -- ✅ 返回metric_key数组
)
```

**注意**：此函数仅用于查询，不直接写入表。

---

## 三、所有读取路径分析

### 3.1 读取路径1：missing_metrics_batch.py（期望 metric_key）

**位置**：`app/services/calculation/missing_metrics_batch.py` 第89-154行

**期望格式**：metric_key

**代码证据**：
```python
# 第129-142行
cur.execute("""
    SELECT DISTINCT unnest(need_compute_metrics) as metric_key  -- ✅ 期望metric_key
    FROM metrics_presence_per_second_device
    WHERE station_id = %s
      AND device_id = %s
      AND ts_second >= %s::timestamptz
      AND ts_second < %s::timestamptz
      AND array_length(need_compute_metrics, 1) > 0
    ORDER BY metric_key
""")
metrics = [r[0] for r in cur.fetchall()]  # ✅ 期望得到metric_key列表
```

**影响**：
- 如果读取到 metric_id（如 "12"），会被当作 metric_key 使用
- 导致后续计算方法选择失败（找不到 metric_key="12" 的计算方法）

---

### 3.2 读取路径2：generate_task2_outputs.py（期望 metric_key）

**位置**：`scripts/dev/generate_task2_outputs.py` 第118-158行

**期望格式**：metric_key

**代码证据**：
```python
# 第136-143行
cur.execute("""
    SELECT COUNT(*) FROM metrics_presence_per_second_device
    WHERE ts_second >= %(start)s AND ts_second <= %(end)s
      AND available_metrics @> %(arr)s  -- ✅ 使用数组包含操作符，期望metric_key
""", {"start": START, "end": END, "arr": [d]})  # d 是 metric_key
```

**影响**：
- 如果表中存储的是 metric_id，查询 `available_metrics @> ['pump_flow_rate']` 将返回0条记录
- 导致统计数据不准确

---

### 3.3 读取路径3：mv_presence_1s_compat 视图（期望 metric_key）

**位置**：`scripts/sql/migrations/041_create_mv_presence_compat.sql` 第28-33行

**期望格式**：metric_key

**代码证据**：
```sql
-- 第28-33行
SELECT mpps.station_id,
       mpps.device_id,
       mpps.ts_second AS ts_bucket,
       1::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) AS u(metric_key)  -- ✅ 期望metric_key
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key  -- ✅ JOIN使用metric_key
```

**影响**：
- 如果 available_metrics 存储的是 metric_id（如 "12"），JOIN 将失败
- 导致视图返回空结果

---

## 四、相关表检查

### 4.1 cagg_presence_per_second 表

**位置**：`scripts/sql/ts_cagg_presence.sql`

**表结构**：
```sql
CREATE MATERIALIZED VIEW public.cagg_presence_per_second
WITH (timescaledb.continuous) AS
SELECT
  fm.station_id,
  fm.device_id,
  time_bucket('1 second', fm.ts_bucket) AS ts_second,
  array_agg(DISTINCT mc.metric_key ORDER BY mc.metric_key) AS available_metrics  -- ✅ 使用metric_key
FROM public.fact_measurements fm
JOIN public.dim_metric_config mc ON mc.id = fm.metric_id
GROUP BY fm.station_id, fm.device_id, ts_second
```

**数据验证**：
- 查询结果：0条记录（表为空）
- **结论**：此表未被使用，不存在数据格式问题

---

### 4.2 device_metric_candidates 表

**位置**：`scripts/sql/ts_candidates.sql`

**表结构**：
```sql
CREATE TABLE IF NOT EXISTS public.device_metric_candidates (
  device_id bigint PRIMARY KEY,
  metrics   text[] NOT NULL  -- 应该存储metric_key
);
```

**数据验证**：
- 查询结果：0条记录（表为空）
- **结论**：此表未被使用，不存在数据格式问题

---

## 五、Bug 总结

### 5.1 已确认的 Bug

**Bug #1：orchestrator.py 写入错误格式**
- **位置**：`app/services/calculation/orchestrator.py` 第1275-1323行
- **问题**：将 metric_key 转换为 metric_id 字符串后写入
- **影响**：所有通过 Python 代码计算的指标都会写入错误格式
- **严重程度**：🔴 严重（导致100%数据错误）

**Bug #2：数据一致性问题**
- **问题**：同一张表中可能存在两种格式的数据（metric_id vs metric_key）
- **影响**：读取代码无法正确处理混合数据
- **严重程度**：🔴 严重（导致功能失败）

---

### 5.2 未发现的其他 Bug

**检查结果**：
1. ✅ `sync_presence_from_cagg.sql` 实现正确
2. ✅ `metrics_presence_per_second()` 函数实现正确
3. ✅ `cagg_presence_per_second` 表结构正确（虽然为空）
4. ✅ `device_metric_candidates` 表结构正确（虽然为空）
5. ✅ 所有读取路径都期望 metric_key 格式

**结论**：
- 只有 `orchestrator.py` 一个写入路径存在问题
- 其他所有代码都是正确的
- 没有发现其他表存在类似问题

---

## 六、修复方案

### 6.1 核心修改

**文件**：`app/services/calculation/orchestrator.py`

**修改位置**：第1275-1323行

**修改前**：
```python
# 第1275-1280行
metric_ids = []
for key in metric_keys:
    mid = metric_mapper.key_to_id(key)
    if mid is not None:
        metric_ids.append(str(mid))  # ❌ 错误

# 第1314-1323行
rows = [
    (
        station_id,
        device_id,
        ts,
        metric_ids,  # ❌ 错误
        []
    )
    for ts in timestamps
]
```

**修改后**：
```python
# 直接使用 metric_keys，不需要转换
# metric_keys 已经是正确的格式（如 ["pump_flow_rate", "pump_head"]）

# 第1314-1323行
rows = [
    (
        station_id,
        device_id,
        ts,
        metric_keys,  # ✅ 正确：直接使用metric_keys
        []
    )
    for ts in timestamps
]
```

---

### 6.2 数据修复

**问题**：现有14400条记录都是错误格式

**修复方案**：
1. **方案A**：清空表并重新计算
   - 优点：简单直接
   - 缺点：需要重新计算所有数据

2. **方案B**：编写数据迁移脚本
   - 优点：保留现有数据
   - 缺点：需要编写复杂的转换逻辑

**推荐**：方案A（清空表并重新计算）
- 理由：表中数据量不大（14400条），重新计算成本低
- 执行：`TRUNCATE TABLE metrics_presence_per_second_device;`

---

### 6.3 验证计划

**验证步骤**：
1. 修改代码
2. 清空表
3. 运行计算任务
4. 查询验证数据格式
5. 验证缺失指标计算功能

**验证SQL**：
```sql
-- 验证数据格式
SELECT 
    available_metrics,
    need_compute_metrics
FROM metrics_presence_per_second_device
LIMIT 10;

-- 应该看到类似：
-- available_metrics: ["pump_flow_rate", "pump_head", "pump_outlet_pressure"]
```

---

## 七、总结

### 7.1 问题根源

**唯一的 Bug 来源**：`app/services/calculation/orchestrator.py` 第1275-1323行

**错误原因**：
- 开发者误将 metric_key 转换为 metric_id 后写入
- 可能是误解了表结构设计意图

### 7.2 影响范围

**受影响的功能**：
1. 缺失指标计算功能（无法正确读取需要计算的指标）
2. 指标存在性统计（数据格式不一致）
3. 所有依赖 `metrics_presence_per_second_device` 表的下游功能

**未受影响的部分**：
1. SQL 路径写入的数据（如果有的话）
2. 其他表的数据格式
3. 数据库函数和视图的逻辑

### 7.3 修复优先级

**优先级**：🔴 最高

**理由**：
- 影响核心功能（缺失指标计算）
- 100% 的数据都是错误格式
- 修复简单（只需修改一处代码）

---

**报告完成时间**：2025-11-04  
**下一步**：等待用户确认后进入创新模式，讨论修复方案的细节。

