# 深入研究报告：mv_device_running_1s表生成逻辑

**研究时间**：2025-11-11
**研究对象**：mv_device_running_1s表的running字段生成机制

---

## 📋 研究目标

分析mv_device_running_1s表的running字段是如何生成的，以及为什么用户手动修改后仍然无法解决计算失败问题。

---

## 🔍 表结构

### mv_device_running_1s表

**字段**：
```sql
station_id    bigint NOT NULL
device_id     bigint NOT NULL
ts_bucket     timestamptz NOT NULL
running       smallint NOT NULL  -- 0=停止, 1=运行
phase         smallint NOT NULL  -- 0=停止, 1=运行, 2=启动中, 3=停止中
phase_type    text               -- 阶段类型（可选）

PRIMARY KEY (station_id, device_id, ts_bucket)
```

---

## 🔧 生成机制

### 方法1：基于fn_running_state_1s函数（推荐）

**存储过程**：`sp_refresh_mv_running_phase`

**调用链**：
1. 调用 `fn_running_state_1s(station_id, device_id, start_ts, end_ts)`
2. 函数返回每秒的 `is_running` 状态
3. 识别启动边沿和停止边沿
4. 围绕边沿扩展phase标记
5. 写入 `mv_device_running_1s` 表

**核心逻辑**：`scripts/sql/m1/010_fn_running_state_1s.sql`

---

## 📊 fn_running_state_1s函数详解

### 输入参数

```sql
p_station_id  bigint        -- 站点ID
p_device_id   bigint        -- 设备ID
p_start_ts    timestamptz   -- 开始时间
p_end_ts      timestamptz   -- 结束时间
```

### 返回字段

```sql
ts_bucket   timestamptz         -- 秒级时间戳
is_running  boolean             -- 是否运行
max_i       double precision    -- 三相电流最大值
p           double precision    -- 有功功率
f           double precision    -- 频率
source      text                -- 数据来源（'det'=检测, 'hold'=延续）
```

### 判断逻辑

#### 步骤1：读取阈值配置

从 `device_running_thresholds` 表读取设备的阈值配置：

```sql
SELECT * FROM device_running_thresholds WHERE device_id = p_device_id
```

**设备1的配置**：
```
enable_i = true   (启用电流判断)
enable_p = false  (禁用功率判断)
enable_f = false  (禁用频率判断)
i_on = 541.12 A   (电流开启阈值)
i_off = 265.28 A  (电流关闭阈值)
grace_hold_secs = 30  (缺报延续30秒)
```

#### 步骤2：获取原始数据

从 `fact_measurements` 表获取电流、功率、频率数据：

```sql
SELECT fm.ts_bucket, mc.metric_key, fm.value
FROM fact_measurements fm
JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.station_id = p_station_id
  AND fm.device_id = p_device_id
  AND fm.ts_bucket >= p_start_ts AND fm.ts_bucket < p_end_ts
  AND mc.metric_key IN ('pump_current_a', 'pump_current_b', 'pump_current_c', 
                        'pump_active_power', 'pump_frequency')
```

**设备1的数据（2025-10-23 10:48:08）**：
```
pump_current_a = 0 A
pump_current_b = 0 A
pump_current_c = 0 A
pump_active_power = 0 kW
pump_frequency = 0 Hz
```

#### 步骤3：计算三相电流最大值

```sql
max_i = GREATEST(COALESCE(ia, 0), COALESCE(ib, 0), COALESCE(ic, 0))
```

**设备1的结果**：
```
max_i = GREATEST(0, 0, 0) = 0 A
```

#### 步骤4：判断开启和关闭条件

**开启条件（on_hit）**：任一启用信号 ≥ 开启阈值
```sql
on_hit = (enable_i AND max_i >= i_on) 
      OR (enable_p AND p >= p_on) 
      OR (enable_f AND f >= f_on)
```

**设备1的判断**：
```
on_hit = (true AND 0 >= 541.12)     -- ❌ false
      OR (false AND 0 >= 318.08)    -- ❌ false (未启用)
      OR (false AND 0 >= 50.13)     -- ❌ false (未启用)
      = false
```

**关闭条件（off_hit）**：所有启用信号 ≤ 关闭阈值
```sql
off_hit = (NOT enable_i OR max_i <= i_off)
      AND (NOT enable_p OR p <= p_off)
      AND (NOT enable_f OR f <= f_off)
```

**设备1的判断**：
```
off_hit = (NOT true OR 0 <= 265.28)   -- ✅ true (0 <= 265.28)
      AND (NOT false OR 0 <= 222.72)  -- ✅ true (NOT false = true)
      AND (NOT false OR 0 <= 46.08)   -- ✅ true (NOT false = true)
      = true
```

#### 步骤5：状态机逻辑（滞回）

**递归逻辑**：
```sql
CASE
  WHEN prev_state = true  THEN (NOT off_hit)  -- 运行中 → 除非满足关闭条件才停止
  WHEN prev_state = false THEN on_hit          -- 停止中 → 满足开启条件才运行
END
```

**设备1的状态转换**：
```
初始状态: false (停止)
on_hit = false → 保持停止状态
off_hit = true → 确认停止状态

最终状态: is_running = false
```

#### 步骤6：缺报延续（grace_hold）

如果当前秒没有任何数据（has_any=false），且在grace_hold_secs秒内，则沿用上一秒状态。

**设备1的情况**：
- has_any = true（有数据，虽然都是0）
- 不触发缺报延续

---

## 🎯 关键发现

### 发现1：mv_device_running_1s表的running字段是基于电流/功率/频率阈值计算的

**不是**基于 `device_running` 指标！

**生成逻辑**：
1. 从 `device_running_thresholds` 表读取阈值配置
2. 从 `fact_measurements` 表读取电流、功率、频率数据
3. 使用滞回逻辑判断运行状态
4. 写入 `mv_device_running_1s` 表

### 发现2：设备1的running=1是用户手动修改的，不是系统计算的

**系统计算的结果应该是**：
- max_i = 0 A < i_on = 541.12 A
- on_hit = false
- off_hit = true
- is_running = false
- **running = 0** ❌

**用户手动修改为**：
- **running = 1** ✅

**结论**：用户的修改覆盖了系统的计算结果

### 发现3：用户修改running=1后，为什么计算仍然失败？

**原因**：计算阶段使用的是**硬编码的阈值**（freq>=3.0, power>=0.5），而不是mv_device_running_1s表的running字段。

**两套独立的判断标准**：
1. **数据加载阶段**：使用 `mv_device_running_1s.running = 1`（用户可控）
2. **计算阶段**：使用硬编码阈值 `freq>=3.0, power>=0.5`（用户不可控）

---

## 📌 正确的生成逻辑

### 推荐方法：使用sp_refresh_mv_running_phase存储过程

**调用示例**：
```sql
CALL sp_refresh_mv_running_phase(
    p_station_id := 1,
    p_device_id := 1,
    p_start_ts := '2025-10-23 10:00:00+08',
    p_end_ts := '2025-10-23 11:00:00+08'
);
```

**效果**：
- 自动计算设备1在该时间段的运行状态
- 基于device_running_thresholds表的阈值配置
- 使用滞回逻辑避免抖动
- 支持缺报延续（grace_hold_secs）
- 识别启动/停止阶段（phase字段）

---

## 🔧 device_running_thresholds表配置

### 设备1-6的配置

| 设备ID | enable_i | enable_p | enable_f | i_on (A) | i_off (A) | p_on (kW) | p_off (kW) | f_on (Hz) | f_off (Hz) |
|--------|----------|----------|----------|----------|-----------|-----------|------------|-----------|------------|
| 1      | ✅ true  | ❌ false | ❌ false | 541.12   | 265.28    | 318.08    | 222.72     | 50.13     | 46.08      |
| 2      | ✅ true  | ❌ false | ❌ false | 470.08   | -156.48   | 297.92    | 140.48     | 49.41     | 43.33      |
| 3      | ✅ true  | ❌ false | ❌ false | 0.17     | 0.15      | 236.32    | 142.88     | 46.96     | 42.97      |
| 4      | ✅ true  | ❌ false | ❌ false | 376.16   | 305.76    | 224.16    | 219.68     | 46.54     | 45.54      |
| 5      | ✅ true  | ❌ false | ❌ false | 0.17     | 0.15      | 18.48     | -3.60      | 32.73     | -2.94      |
| 6      | ✅ true  | ❌ false | ❌ false | 530.08   | 237.60    | 329.92    | 206.40     | 50.25     | 45.67      |

**观察**：
- 所有设备都只启用电流判断（enable_i=true）
- 功率和频率判断都被禁用（enable_p=false, enable_f=false）
- 设备3和设备5的电流阈值非常低（0.17 A / 0.15 A）

---

**研究完成时间**：2025-11-11
**结论**：mv_device_running_1s表的running字段是基于电流/功率/频率阈值计算的，用户手动修改只影响数据加载阶段，不影响计算阶段的硬编码阈值过滤
**下一步**：所有深入研究任务已完成，可以进入创新模式讨论解决方案

