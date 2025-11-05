# 【已废弃】mv_presence_1s 表全面研究报告

**研究时间**：2025-11-04
**研究模式**：严格遵守 RIPER-5 协议，只依靠代码、脚本、数据库分析
**研究对象**：数据库表 `mv_presence_1s`
**废弃时间**：2025-11-04
**废弃原因**：该表已被 `metrics_presence_per_second_device` 表完全替代，表为空且无实际使用

---

## 1. 表的当前状态

### 验证结果
- **记录数**：0 条（表为空）✅ 已验证
- **表大小**：16 kB（仅包含表结构和索引）
- **表类型**：BASE TABLE（普通表，**不是物化视图**）⚠️ 重要发现
- **所有者**：postgres
- **索引数量**：2个（主键索引 + 辅助索引）

### 重要发现
虽然表名带 `mv_` 前缀（通常表示 Materialized View），但实际上这是一个**普通表**，不是物化视图。

---

## 2. 表结构详细信息

### 字段列表

| 字段名 | 数据类型 | 约束 | 功能说明 | 是否被使用 |
|--------|---------|------|---------|-----------|
| station_id | bigint | NOT NULL, PK | 站点ID（关联 dim_stations.id） | ✅ 是 |
| device_id | bigint | NOT NULL, PK | 设备ID（关联 dim_devices.id） | ✅ 是 |
| metric_id | bigint | NOT NULL, PK | 指标ID（关联 dim_metric_config.id） | ✅ 是 |
| ts_bucket | timestamptz | NOT NULL, PK | UTC 秒级时间桶（对齐到整秒） | ✅ 是 |
| present | smallint | NOT NULL | 覆盖标记（固定为1，表示该秒该指标存在数据） | ✅ 是 |

### 索引

- **主键索引**：`mv_presence_1s_pkey` (station_id, device_id, metric_id, ts_bucket)
- **辅助索引**：`ix_mv_pres_sdm_t` (station_id, device_id, metric_id, ts_bucket)

### 表注释（完整）

```
1秒指标存在性表

用途：
  1秒指标存在性统计，支持缺失指标计算和数据完整性监控

视图类型：
  Continuous Aggregate（连续聚合）

数据来源：
  - 基表：fact_measurements
  - 聚合粒度：1秒

聚合逻辑：
  - 聚合函数：COUNT（存在性标记）
  - 聚合字段：present（固定为1）

刷新策略：
  - 刷新方式：连续聚合策略（实时刷新）
  - 刷新过程：sp_refresh_mv_running_presence

使用场景：
  - 缺失指标计算的输入
  - 数据完整性监控
  - 数据覆盖率统计
```

---

## 3. 表为空的原因分析

### 数据验证

- ✅ `fact_measurements` 表有 **634,530 条记录**（有源数据）
  - 时间范围：2025-05-31 18:00:00 到 19:59:59（2小时数据）
  - 覆盖：1个泵站、8个设备、23个指标
- ✅ `metrics_presence_per_second_device` 表有 **50,400 条记录**（有数据）
- ❌ `mv_presence_1s` 表有 **0 条记录**（空表）

### 可能的原因

#### 原因1：刷新存储过程未被调用
- **刷新逻辑**：通过存储过程 `sp_refresh_mv_running_presence` 从 `fact_measurements` 聚合数据
- **调用位置**：`app/services/run_all/orchestrator.py` 第510-517行（在质量打标前）
- **可能情况**：如果未执行完整的 `run_all` 流程，则不会调用刷新存储过程

#### 原因2：表在刷新后被清空
- 在 `prepare_dim` 阶段，`mv_presence_1s` **未被清空**（与 `mv_device_running_1s` 不同）
- 但如果手动执行了 `TRUNCATE` 或 `DELETE`，表会被清空

#### 原因3：功能被替代
- 项目中已有 `metrics_presence_per_second_device` 表存储相同的信息
- 创建了兼容视图 `mv_presence_1s_any` 来联合两个表的数据
- 可能 `mv_presence_1s` 表已不再被主动使用

---

## 4. 表的用途和功能定位

### 设计用途
- **主要功能**：1秒指标存在性统计
- **数据来源**：从 `fact_measurements` 表聚合
- **聚合粒度**：1秒
- **聚合逻辑**：记录每秒每个指标是否存在数据（present=1）

### 使用场景
1. 缺失指标计算的输入
2. 数据完整性监控
3. 数据覆盖率统计

### 在系统架构中的位置
- **数据流**：fact_measurements → sp_refresh_mv_running_presence → mv_presence_1s
- **层级**：派生数据层（从事实表聚合生成）
- **刷新策略**：手动刷新（通过存储过程）

---

## 5. 代码依赖关系分析

### 写入该表的代码位置

**创建脚本**：`scripts/sql/migrations/039_materialize_running_presence_and_stats.sql`（第12-19行）

**刷新存储过程**：`sp_refresh_mv_running_presence`（第41-68行）
- 数据来源：`fact_measurements` 表
- 写入方式：`INSERT ... ON CONFLICT DO NOTHING`（幂等）
- 参数：p_start, p_end, p_station_id, p_device_id
- SQL逻辑：
  ```sql
  INSERT INTO public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket, present)
  SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ON CONFLICT DO NOTHING;
  ```

### 调用位置

**文件**：`app/services/run_all/orchestrator.py`
**位置**：第510-517行
**时机**：在质量打标前刷新
**调用代码**：
```python
# 在质量打标前，刷新依赖的物化视图：1s存在性与60s统计
with __conn.cursor() as __cur:
    __cur.execute(
        "CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)",
        (ws, we, None, device_id),
    )
```

### 读取该表的代码位置

**兼容视图**：`mv_presence_1s_any`（`scripts/sql/migrations/041_create_mv_presence_compat.sql`）
- 联合 `mv_presence_1s` 和 `metrics_presence_per_second_device`
- 将 `metrics_presence_per_second_device` 的数组展开为行
- 提供统一的查询接口

**未发现**：在代码库中未发现直接查询 `mv_presence_1s` 表的代码

---

## 6. 字段使用情况详细分析

### 所有字段都被使用

| 字段名 | 使用场景 | 业务含义 |
|--------|---------|---------|
| station_id | 主键、过滤条件 | 标识数据所属的泵站 |
| device_id | 主键、过滤条件 | 标识数据所属的设备 |
| metric_id | 主键、过滤条件 | 标识具体的指标 |
| ts_bucket | 主键、时间范围查询 | 时间维度（秒级对齐） |
| present | 存在性标记 | 固定为1，表示该秒该指标存在数据 |

### 字段关联关系
- `station_id` → `dim_stations.id`
- `device_id` → `dim_devices.id`
- `metric_id` → `dim_metric_config.id`

### 未发现冗余字段
所有字段都有明确的用途。

---

## 7. 与其他表的关系

### 功能重叠

| 表名 | 数据结构 | 记录数 | 功能 | 优缺点 |
|------|---------|--------|------|--------|
| `mv_presence_1s` | (station_id, device_id, metric_id, ts_bucket, present) | 0 | 规范化存储（每个指标一行） | 规范化，但占用空间大 |
| `metrics_presence_per_second_device` | (station_id, device_id, ts_second, available_metrics[], need_compute_metrics[]) | 50,400 | 数组存储（每秒一行，多个指标） | 节省空间，但查询复杂 |

### 兼容视图：mv_presence_1s_any
- 联合两个表的数据
- 将 `metrics_presence_per_second_device` 的数组展开为行
- 提供统一的查询接口

---

## 8. 关键发现和问题

### 发现1：表为空但有源数据
- `fact_measurements` 有 634,530 条记录
- `mv_presence_1s` 为空
- **结论**：刷新存储过程可能未被调用，或表被清空后未重新刷新

### 发现2：功能重叠
- `mv_presence_1s` 和 `metrics_presence_per_second_device` 功能重叠
- 后者更灵活（使用数组），前者更规范化（每个指标一行）
- **结论**：可能存在设计演进，`mv_presence_1s` 可能是早期设计

### 发现3：表名误导
- 表名带 `mv_` 前缀，但实际上是普通表（BASE TABLE），不是物化视图
- **结论**：命名不规范，容易误导

### 发现4：在 prepare_dim 阶段未被清空
- `mv_device_running_1s` 在 prepare_dim 阶段被清空（第317-321行）
- `mv_presence_1s` 未被清空
- **结论**：可能导致数据不一致

---

## 9. 需要澄清的问题

### 问题1：表的实际用途
- 该表是否仍在使用？
- 是否已被 `metrics_presence_per_second_device` 替代？
- 是否应该废弃此表？

### 问题2：刷新策略
- 为什么表为空？
- 是否应该在 `run_all` 流程中自动刷新？
- 是否应该在 `prepare_dim` 阶段清空？

### 问题3：与 metrics_presence_per_second_device 的关系
- 两个表的功能重叠，是否需要保留两个表？
- 兼容视图 `mv_presence_1s_any` 的作用是什么？
- 是否应该统一使用一个表？

---

## 10. 总结

**表的基本情况**：
- `mv_presence_1s` 是一个普通表（不是物化视图），用于存储1秒指标存在性数据
- 表为空，但有完整的表结构和索引
- 所有字段都有明确的用途，未发现冗余字段

**表为空的原因**：
- 刷新存储过程可能未被调用
- 或者表被清空后未重新刷新
- 或者功能已被 `metrics_presence_per_second_device` 表替代

**建议**：
1. 确认该表是否仍在使用
2. 如果仍在使用，应在 `prepare_dim` 阶段清空，并在 `run_all` 流程中自动刷新
3. 如果已被替代，考虑废弃此表
4. 统一使用一个表存储指标存在性数据，避免功能重叠

---

**研究完成时间**：2025-11-04
**下一步**：等待用户确认，准备进入创新模式

