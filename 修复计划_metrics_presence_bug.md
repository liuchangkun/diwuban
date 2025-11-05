# 修复计划：metrics_presence_per_second_device 表 Bug

**日期**：2025-11-04  
**模式**：计划模式  
**方案**：方案C（混合方案）

---

## 一、项目规则验证

### 1.1 编码规范验证 ✅

- ✅ 修改符合单一职责原则（SRP）：只修改错误的转换逻辑
- ✅ 修改符合开闭原则（OCP）：不影响其他代码
- ✅ 日志记录：保留现有日志记录
- ✅ 错误处理：保留现有错误处理
- ✅ 注释：使用中文注释说明修改原因

### 1.2 数据库规范验证 ✅

- ✅ 表结构：`metrics_presence_per_second_device` 表的 `available_metrics` 和 `need_compute_metrics` 字段类型为 `text[]`
- ✅ 数据格式：应存储 `metric_key`（如 "pump_flow_rate"），而非 `metric_id`（如 "14"）
- ✅ 数据一致性：修复后所有写入路径都使用 `metric_key` 格式
- ✅ SQL脚本：`sync_presence_from_cagg.sql` 已验证正确，可直接使用

---

## 二、架构概述

### 2.1 问题根源

**唯一的Bug位置**：`app/services/calculation/orchestrator.py` 第1275-1323行

**错误逻辑**：
```python
# 第1275-1280行：错误地将 metric_key 转换为 metric_id 字符串
metric_ids = []
for key in metric_keys:
    mid = metric_mapper.key_to_id(key)  # ❌ 不应该转换
    if mid is not None:
        metric_ids.append(str(mid))  # ❌ 不应该写入ID

# 第1319行：使用错误的 metric_ids
metric_ids,  # ❌ 应该使用 metric_keys
```

**正确逻辑**：
- `metric_keys` 参数已经是正确的格式（如 `["pump_flow_rate", "pump_head"]`）
- 应该直接使用 `metric_keys`，不需要任何转换

### 2.2 修复策略

**方案C（混合方案）**：
1. 修改 `orchestrator.py` 代码（删除转换逻辑）
2. 清空 `metrics_presence_per_second_device` 表
3. 调用 `presence_writer.py` 的 `upsert_window()` 方法，执行 `sync_presence_from_cagg.sql`
4. 验证数据格式和完整性

**优势**：
- 利用现有正确逻辑（`sync_presence_from_cagg.sql`）
- 从 `fact_measurements` 重新生成数据，无需重新计算
- 快速恢复数据，风险可控

---

## 三、详细更改计划

### 更改1：修改 orchestrator.py 代码

**文件**：`app/services/calculation/orchestrator.py`

**理由**：删除错误的 metric_key → metric_id 转换逻辑，直接使用 metric_keys

**具体更改**：
1. **删除第1275-1286行**：删除 `metric_ids` 列表构建逻辑
2. **修改第1288-1291行**：日志记录改为使用 `metric_keys`
3. **修改第1319行**：将 `metric_ids` 改为 `metric_keys`
4. **添加注释**：说明修改原因

**涉及的函数/类**：
- 函数：`update_metrics_presence(self, station_id: int, device_id: int, metric_keys: List[str], timestamps: np.ndarray) -> int`
- 类：`CalculationOrchestrator`

**依赖关系**：
- 依赖：`metric_keys` 参数（由调用方传入）
- 影响：写入 `metrics_presence_per_second_device` 表的数据格式

**修改前后对比**：
```python
# 修改前（第1275-1286行）
metric_ids = []
for key in metric_keys:
    mid = metric_mapper.key_to_id(key)
    if mid is not None:
        metric_ids.append(str(mid))
    else:
        logger.warning(f"无法找到metric_key={key}的metric_id")

if not metric_ids:
    logger.warning("没有有效的metric_id")
    return 0

# 修改后（删除上述代码，直接使用 metric_keys）
# 无需转换，metric_keys 已经是正确的格式
```

```python
# 修改前（第1288-1291行）
logger.info(
    f"更新指标可用性：station_id={station_id}, device_id={device_id}, "
    f"metrics={len(metric_ids)}, timepoints={len(timestamps)}"
)

# 修改后
logger.info(
    f"更新指标可用性：station_id={station_id}, device_id={device_id}, "
    f"metrics={len(metric_keys)}, timepoints={len(timestamps)}"
)
```

```python
# 修改前（第1314-1323行）
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

# 修改后
rows = [
    (
        station_id,
        device_id,
        ts,
        metric_keys,  # ✅ 正确
        []
    )
    for ts in timestamps
]
```

---

### 更改2：记录修复前数据量

**文件**：无（数据库查询）

**理由**：用户要求对比修复前后的数据量

**具体更改**：
1. 查询修复前的总记录数
2. 查询修复前的数据格式分布
3. 记录到验证报告中

**SQL查询**：
```sql
-- 查询总记录数
SELECT COUNT(*) FROM metrics_presence_per_second_device;

-- 查询数据格式分布（metric_id vs metric_key）
SELECT 
    CASE 
        WHEN available_metrics::text ~ '^\{[0-9,]+\}$' THEN 'metric_id格式'
        ELSE 'metric_key格式'
    END AS 数据格式,
    COUNT(*) AS 记录数
FROM metrics_presence_per_second_device
WHERE array_length(available_metrics, 1) > 0
GROUP BY 1;
```

---

### 更改3：清空表

**文件**：无（数据库操作）

**理由**：清空错误数据，准备重新生成

**具体更改**：
1. 执行 `TRUNCATE TABLE metrics_presence_per_second_device;`
2. 验证表已清空

**SQL语句**：
```sql
TRUNCATE TABLE metrics_presence_per_second_device;
```

**验证SQL**：
```sql
SELECT COUNT(*) FROM metrics_presence_per_second_device;
-- 应该返回 0
```

---

### 更改4：重新生成数据

**文件**：无（调用现有代码）

**理由**：使用正确的SQL脚本从 fact_measurements 重新生成数据

**具体更改**：
1. 查询 `fact_measurements` 表的时间范围
2. 调用 `presence_writer.upsert_window()` 方法
3. 传入完整时间范围参数

**调用方式**：
```python
from app.services.reporting.presence_writer import upsert_window
from app.adapters.db import get_connection
from datetime import datetime

# 查询时间范围
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT MIN(ts_bucket), MAX(ts_bucket)
            FROM fact_measurements
        """)
        start_time, end_time = cur.fetchone()

# 重新生成数据
with get_connection() as conn:
    affected = upsert_window(
        conn=conn,
        start=start_time,
        end=end_time,
        station_id=None,  # 所有泵站
        device_id=None    # 所有设备
    )
    conn.commit()
    print(f"重新生成 {affected} 条记录")
```

**依赖关系**：
- 依赖：`fact_measurements` 表数据完整
- 依赖：`sync_presence_from_cagg.sql` 脚本正确
- 影响：`metrics_presence_per_second_device` 表数据

---

### 更改5：验证数据格式

**文件**：无（数据库查询）

**理由**：验证修复后的数据格式是否正确

**具体更改**：
1. 查询修复后的总记录数
2. 查询修复后的数据格式
3. 抽样检查数据内容
4. 对比修复前后的数据量

**验证SQL**：
```sql
-- 1. 查询总记录数
SELECT COUNT(*) FROM metrics_presence_per_second_device;

-- 2. 查询数据格式（应该全部是 metric_key 格式）
SELECT 
    available_metrics,
    need_compute_metrics
FROM metrics_presence_per_second_device
WHERE array_length(available_metrics, 1) > 0
LIMIT 10;

-- 3. 验证数据格式（应该包含字母和下划线，不应该是纯数字）
SELECT 
    CASE 
        WHEN available_metrics::text ~ '^\{[0-9,]+\}$' THEN 'metric_id格式（错误）'
        WHEN available_metrics::text ~ '\{[a-z_,]+\}' THEN 'metric_key格式（正确）'
        ELSE '其他格式'
    END AS 数据格式,
    COUNT(*) AS 记录数
FROM metrics_presence_per_second_device
WHERE array_length(available_metrics, 1) > 0
GROUP BY 1;

-- 4. 抽样检查具体数据
SELECT 
    station_id,
    device_id,
    ts_second,
    available_metrics,
    need_compute_metrics
FROM metrics_presence_per_second_device
ORDER BY ts_second DESC
LIMIT 20;
```

**预期结果**：
- 总记录数应该与修复前相近（可能略有差异）
- 所有 `available_metrics` 应该是 metric_key 格式（如 `["pump_flow_rate", "pump_head"]`）
- 不应该出现纯数字格式（如 `["12", "13"]`）

---

## 四、实施检查清单

### 阶段1：准备工作

1. ✅ 读取所有规则文档（核心原则、编码规范、数据库规范）
2. ✅ 验证函数签名：`update_metrics_presence()` 方法
3. ✅ 验证SQL脚本：`sync_presence_from_cagg.sql`
4. ✅ 验证调用方法：`presence_writer.upsert_window()`

### 阶段2：记录修复前状态

5. 查询修复前的总记录数，记录到验证报告
6. 查询修复前的数据格式分布，记录到验证报告
7. 抽样保存修复前的数据样本（前20条），记录到验证报告

### 阶段3：修改代码

8. 修改 `app/services/calculation/orchestrator.py` 第1275-1286行：删除 `metric_ids` 列表构建逻辑
9. 修改 `app/services/calculation/orchestrator.py` 第1288-1291行：日志记录改为使用 `metric_keys`
10. 修改 `app/services/calculation/orchestrator.py` 第1319行：将 `metric_ids` 改为 `metric_keys`
11. 添加注释说明修改原因（在第1275行之前）

### 阶段4：清空表

12. 执行 `TRUNCATE TABLE metrics_presence_per_second_device;`
13. 验证表已清空（COUNT应该为0）

### 阶段5：重新生成数据

14. 查询 `fact_measurements` 表的时间范围（MIN和MAX的ts_bucket）
15. 调用 `presence_writer.upsert_window()` 方法，传入完整时间范围
16. 记录重新生成的记录数

### 阶段6：验证数据

17. 查询修复后的总记录数
18. 查询修复后的数据格式分布（应该全部是 metric_key 格式）
19. 抽样检查修复后的数据内容（前20条）
20. 对比修复前后的数据量差异
21. 验证 `available_metrics` 字段不包含纯数字
22. 验证 `available_metrics` 字段包含字母和下划线

### 阶段7：功能验证

23. 验证缺失指标计算功能是否正常（读取 `need_compute_metrics` 字段）
24. 验证数组包含操作符 `@>` 是否正常工作
25. 验证兼容视图 `mv_presence_1s_compat` 是否返回正确结果

### 阶段8：生成验证报告

26. 汇总所有验证结果
27. 生成完整的验证报告
28. 标记修复是否成功

---

## 五、错误处理策略

### 5.1 代码修改阶段

**可能的错误**：
- 文件编辑失败

**处理策略**：
- 使用 `str-replace-editor` 工具，确保精确匹配
- 如果失败，检查行号是否正确
- 如果仍然失败，手动查看文件内容

### 5.2 清空表阶段

**可能的错误**：
- 表被锁定，无法TRUNCATE

**处理策略**：
- 检查是否有其他进程正在使用该表
- 等待锁释放后重试
- 如果无法TRUNCATE，使用 `DELETE FROM metrics_presence_per_second_device;`

### 5.3 重新生成数据阶段

**可能的错误**：
- `fact_measurements` 表为空
- SQL脚本执行失败
- 时间范围过大导致超时

**处理策略**：
- 检查 `fact_measurements` 表是否有数据
- 如果时间范围过大，分批执行（按月或按周）
- 增加超时时间配置

### 5.4 验证阶段

**可能的错误**：
- 数据量差异过大
- 数据格式仍然错误

**处理策略**：
- 如果数据量差异>10%，检查 `fact_measurements` 表数据完整性
- 如果数据格式仍然错误，检查SQL脚本是否正确执行
- 如果问题持续，回滚修改并重新分析

---

## 六、测试方法

### 6.1 单元测试

**不需要编写新的单元测试**（本次修复只是删除错误逻辑）

### 6.2 集成测试

**测试场景1**：验证写入数据格式
```python
# 调用 update_metrics_presence() 方法
orchestrator.update_metrics_presence(
    station_id=1,
    device_id=1,
    metric_keys=["pump_flow_rate", "pump_head"],
    timestamps=np.array([datetime.now()])
)

# 查询数据库验证
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT available_metrics
            FROM metrics_presence_per_second_device
            WHERE station_id = 1 AND device_id = 1
            ORDER BY ts_second DESC
            LIMIT 1
        """)
        result = cur.fetchone()
        assert "pump_flow_rate" in result[0]  # 应该包含 metric_key
        assert "pump_head" in result[0]
        assert "14" not in result[0]  # 不应该包含 metric_id
```

**测试场景2**：验证缺失指标计算功能
```python
from app.services.calculation.missing_metrics_batch import _fetch_metrics_for_device_window

# 调用缺失指标计算功能
metrics = _fetch_metrics_for_device_window(
    station_id=1,
    device_id=1,
    start_time=start,
    end_time=end
)

# 验证返回的是 metric_key 列表
assert all(isinstance(m, str) and "_" in m for m in metrics)
```

---

## 七、回滚计划

如果修复失败，执行以下回滚步骤：

1. **恢复代码**：使用 Git 恢复 `orchestrator.py` 文件
2. **恢复数据**：如果有备份，恢复 `metrics_presence_per_second_device` 表数据
3. **重新分析**：重新分析问题根源，制定新的修复方案

**备份建议**：
- 在修改代码前，使用 Git 创建分支
- 在清空表前，导出表数据（可选，因为数据可以重新生成）

---

## 八、完成标准

修复完成的标准：

1. ✅ 代码修改完成，删除了错误的转换逻辑
2. ✅ 表已清空并重新生成数据
3. ✅ 数据格式验证通过（100% 是 metric_key 格式）
4. ✅ 数据量对比合理（差异<10%）
5. ✅ 缺失指标计算功能验证通过
6. ✅ 数组包含操作符验证通过
7. ✅ 兼容视图验证通过
8. ✅ 生成完整的验证报告

---

**计划完成时间**：2025-11-04  
**下一步**：等待用户确认后进入执行模式

