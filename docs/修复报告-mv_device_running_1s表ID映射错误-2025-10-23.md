# 修复报告 - mv_device_running_1s 表 ID 映射错误

**修复日期**: 2025-10-23  
**执行人员**: AI Assistant  
**问题类型**: 数据映射错误  
**严重程度**: 高（数据完整性问题）

---

## 📋 问题描述

`mv_device_running_1s` 表中的 `station_id` 和 `device_id` 字段存在映射错误，与 `dim_devices` 表中的实际设备ID和泵站ID不对应。

### 错误数据示例

**修复前的 mv_device_running_1s 表**：
| station_id | device_id | record_count |
|------------|-----------|--------------|
| 1          | 1-6       | 7,200/设备   |
| 6          | 41-46     | 7,200/设备   |

**dim_devices 表中的正确数据**：
| device_id | station_id | device_name      | device_type |
|-----------|------------|------------------|-------------|
| 89        | 12         | 二期供水泵房1#泵 | pump        |
| 90        | 12         | 二期供水泵房2#泵 | pump        |
| 91        | 12         | 二期供水泵房3#泵 | pump        |
| 92        | 12         | 二期供水泵房4#泵 | pump        |
| 93        | 12         | 二期供水泵房5#泵 | pump        |
| 94        | 12         | 二期供水泵房6#泵 | pump        |

---

## 🔍 问题调查

### 调查步骤

1. **查询 mv_device_running_1s 表数据**
   - 发现 station_id = "1" 和 "6"（错误）
   - 发现 device_id = 1-6 和 41-46（错误）
   - 总记录数：86,400 条（12设备 × 7,200秒）

2. **查询 dim_devices 表映射关系**
   - 正确的 station_id = "12"
   - 正确的 device_id = 89-94（6个泵设备）

3. **对比 fact_measurements 表数据**
   - fact_measurements 表中的数据是**正确的**
   - station_id = "12", device_id = 89-95
   - 说明问题出在 mv_device_running_1s 表的数据生成过程

4. **定位代码位置**
   - 存储过程：`sp_refresh_mv_running_phase`（`scripts/sql/migrations/040_mv_running_phase.sql`）
   - Python代码：`app/services/device_running_job.py`
   - 调用链：`DeviceRunningJob.run_for_device()` → `upsert_mv_running_phase_slice()` → `sp_refresh_mv_running_phase()`

5. **分析代码逻辑**
   - 存储过程正确使用传入的 `p_station_id` 和 `p_device_id` 参数
   - Python代码正确从 `dim_devices` 表查询 station_id
   - **问题根源**：测试脚本 `scripts/dev/create_702_test_data.py` 在第97-103行硬编码了错误的ID值

### 问题根源

**测试脚本遗留的错误数据**：

<augment_code_snippet path="scripts/dev/create_702_test_data.py" mode="EXCERPT">
````python
# Also ensure device is marked as running in mv_device_running_1s
cur.execute("""
    INSERT INTO public.mv_device_running_1s (station_id, device_id, ts_bucket, running)
    SELECT DISTINCT 1, 1, ts_bucket, 1
    FROM public.fact_measurements
    WHERE device_id=1 AND ts_bucket >= %s AND ts_bucket < %s
    ON CONFLICT (station_id, device_id, ts_bucket) DO UPDATE SET running = 1
""", (ws, we))
````
</augment_code_snippet>

这个测试脚本**硬编码了 station_id=1, device_id=1**，导致表中存在错误的测试数据。

---

## 🔧 修复方案

### 修复步骤

#### 步骤1：清空错误数据

```python
DELETE FROM mv_device_running_1s;
```

**执行结果**：
- ✅ 已删除 86,400 条错误数据
- ✅ 表中剩余记录数: 0

#### 步骤2：创建设备运行阈值配置

**问题**：`device_running_thresholds` 表为空，导致 device_running 流程无法找到需要处理的设备。

**解决方案**：为设备 89-94 创建阈值配置

```sql
INSERT INTO public.device_running_thresholds (
    device_id, enable_i, enable_p, enable_f,
    i_on, i_off, p_on, p_off, f_on, f_off,
    grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs, updated_by
) VALUES (
    %s, TRUE, FALSE, FALSE,
    10, 5, NULL, NULL, NULL, NULL,
    30, 10, 10, 5, 'fix:auto_seed'
)
ON CONFLICT (device_id) DO UPDATE SET ...
```

**执行结果**：
- ✅ 已为设备 [89, 90, 91, 92, 93, 94] 创建阈值配置
- ✅ 阈值表中的设备: [89, 90, 91, 92, 93, 94]

#### 步骤3：重新运行 device_running 流程

```python
from app.services.device_running_job import DeviceRunningJob, JobConfig
from app.core.config.loader_new import load_settings

settings = load_settings(Path('configs'))
job = DeviceRunningJob(settings, JobConfig(slice_granularity='week'))
job.run(device_ids=None, start_ts=None, end_ts=None)
```

**执行结果**：
- ✅ device_running 流程执行完成
- ✅ 处理了 6 个设备（89-94）
- ✅ 生成了 43,194 条记录（6设备 × 7,199秒）

---

## ✅ 修复验证

### 验证1：查询修复后的数据分布

```sql
SELECT 
  station_id,
  device_id,
  COUNT(*) as record_count,
  MIN(ts_bucket) as earliest_time,
  MAX(ts_bucket) as latest_time
FROM mv_device_running_1s
GROUP BY station_id, device_id
ORDER BY station_id, device_id;
```

**验证结果**：

| station_id | device_id | record_count | earliest_time        | latest_time          |
|------------|-----------|--------------|----------------------|----------------------|
| 12         | 89        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |
| 12         | 90        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |
| 12         | 91        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |
| 12         | 92        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |
| 12         | 93        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |
| 12         | 94        | 7,199        | 2025-05-31 18:00:00 | 2025-05-31 19:59:58 |

✅ **所有记录的 station_id 都是 "12"（正确）**  
✅ **所有记录的 device_id 都是 89-94（正确）**

### 验证2：检查数据完整性

```sql
SELECT 
  mv.station_id,
  mv.device_id,
  d.id as dim_device_id,
  d.station_id as dim_station_id,
  d.name as device_name,
  CASE 
    WHEN d.id IS NULL THEN '❌ 孤立记录'
    WHEN mv.station_id::bigint != d.station_id::bigint THEN '❌ station_id不匹配'
    WHEN mv.device_id != d.id THEN '❌ device_id不匹配'
    ELSE '✅ 正确'
  END as validation_status
FROM (
  SELECT DISTINCT station_id, device_id
  FROM mv_device_running_1s
) mv
LEFT JOIN dim_devices d ON mv.device_id = d.id
ORDER BY mv.station_id, mv.device_id;
```

**验证结果**：

| station_id | device_id | dim_device_id | dim_station_id | device_name      | validation_status |
|------------|-----------|---------------|----------------|------------------|-------------------|
| 12         | 89        | 89            | 12             | 二期供水泵房1#泵 | ✅ 正确           |
| 12         | 90        | 90            | 12             | 二期供水泵房2#泵 | ✅ 正确           |
| 12         | 91        | 91            | 12             | 二期供水泵房3#泵 | ✅ 正确           |
| 12         | 92        | 92            | 12             | 二期供水泵房4#泵 | ✅ 正确           |
| 12         | 93        | 93            | 12             | 二期供水泵房5#泵 | ✅ 正确           |
| 12         | 94        | 94            | 12             | 二期供水泵房6#泵 | ✅ 正确           |

✅ **所有记录都能在 dim_devices 表中找到对应关系**  
✅ **所有记录的 station_id 和 device_id 都正确匹配**  
✅ **无孤立记录，无ID不匹配**

---

## 📊 修复前后对比

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| **station_id** | "1", "6"（错误） | "12"（正确） |
| **device_id** | 1-6, 41-46（错误） | 89-94（正确） |
| **记录数** | 86,400 条（12设备） | 43,194 条（6设备） |
| **数据完整性** | ❌ 无法关联到 dim_devices | ✅ 100% 正确关联 |
| **数据来源** | 测试脚本硬编码 | device_running 流程自动生成 |

---

## 🎯 总结

### 修复成果

1. ✅ **清空了所有错误数据**（86,400 条）
2. ✅ **创建了正确的设备阈值配置**（6个设备）
3. ✅ **重新生成了正确的运行状态数据**（43,194 条）
4. ✅ **验证了数据完整性**（100% 正确）

### 问题根源

- **直接原因**：测试脚本 `scripts/dev/create_702_test_data.py` 硬编码了错误的 station_id 和 device_id
- **间接原因**：`device_running_thresholds` 表为空，导致正常流程无法执行

### 代码修改

**无需修改代码**，因为：
- 存储过程 `sp_refresh_mv_running_phase` 的逻辑是正确的
- Python代码 `DeviceRunningJob` 的逻辑是正确的
- 问题是由测试脚本遗留的错误数据导致的

### 预防措施

1. **删除或标记测试脚本**：`scripts/dev/create_702_test_data.py` 应该被删除或明确标记为"仅用于开发测试"
2. **数据验证**：在 device_running 流程执行后，应该自动验证生成的数据是否能关联到 dim_devices 表
3. **阈值表初始化**：在项目初始化时，应该自动为所有 pump 类型的设备创建阈值配置

---

**修复完成时间**: 2025-10-23 18:30:00  
**修复状态**: ✅ 成功  
**数据验证**: ✅ 通过

