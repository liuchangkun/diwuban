# 计划文档：删除 mv_presence_1s 表（方案1：直接删除）

**计划时间**：2025-11-04  
**计划模式**：严格遵守 RIPER-5 协议计划模式规则  
**选定方案**：方案1 - 直接删除表（激进方案）

---

## 📋 执行前置条件确认

### 已读取的规则文档
- ✅ `.augment/规则/模式模块/规则-模式3-计划.md`
- ✅ `.memory/规则层/编码规范.md` (1406行)
- ✅ `.memory/规则层/质量标准.md` (636行)
- ✅ `.memory/规则层/数据库规范.md` (825行)
- ✅ `.memory/规则层/项目规则.md`

### 已完成的影响分析
- ✅ 数据库层面：表依赖关系、视图依赖、存储过程依赖
- ✅ 存储过程层面：`sp_refresh_mv_running_presence` 完整定义
- ✅ 视图层面：`mv_presence_1s_any` 完整定义
- ✅ Python代码层面：`orchestrator.py`、`prepare_dim/__init__.py`
- ✅ 文档层面：所有引用 `mv_presence_1s` 的文档

---

## 🎯 总体目标

**核心目标**：彻底删除 `mv_presence_1s` 表及其所有相关代码，完全依赖 `metrics_presence_per_second_device` 表。

**预期收益**：
1. 消除技术债务（空表占用资源）
2. 简化系统架构（减少冗余表）
3. 提升查询性能（移除 UNION 开销）
4. 节省存储空间（避免重复数据）

---

## 📊 全面影响分析结果

### 1. 数据库层面影响

#### 1.1 表依赖关系
**查询结果**：
- ✅ 无外键约束依赖
- ✅ 无触发器依赖
- ✅ 有1个视图依赖：`mv_presence_1s_any`
- ✅ 有1个存储过程依赖：`sp_refresh_mv_running_presence`

#### 1.2 表结构信息
```sql
-- 表名：public.mv_presence_1s
-- 表类型：BASE TABLE（普通表，非物化视图）
-- 记录数：0条（空表）
-- 表大小：16 kB
-- 主键：(station_id, device_id, metric_id, ts_bucket)
-- 索引：
--   1. mv_presence_1s_pkey (PRIMARY KEY)
--   2. ix_mv_pres_sdm_t (INDEX)
```

#### 1.3 CASCADE 删除影响
**分析结论**：
- ❌ 不使用 `DROP TABLE ... CASCADE`（会级联删除视图）
- ✅ 先手动删除视图，再删除表
- ✅ 先修改存储过程，再删除表

### 2. 存储过程层面影响

#### 2.1 sp_refresh_mv_running_presence 存储过程

**当前定义**（完整）：
```sql
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $procedure$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;

  -- 存在性（需要删除）
  INSERT INTO public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket, present)
  SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ON CONFLICT DO NOTHING;
$procedure$
```

**修改策略**：
- ✅ 保留存储过程（仍需刷新 `mv_device_running_1s`）
- ✅ 删除存储过程中的 `mv_presence_1s` 相关逻辑（第二个 INSERT 语句）
- ✅ 更新存储过程注释

**修改后定义**：
```sql
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $procedure$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;
$procedure$
```

**调用位置**：
- `app/services/run_all/orchestrator.py` 第510-517行
- `scripts/dev/run_vfast_full_device_daily.py` 第44-47行
- `scripts/dev/run_vfast_minutes.py` 第53行

**影响评估**：
- ✅ 存储过程仍然有效（刷新 `mv_device_running_1s`）
- ✅ 调用代码无需修改（存储过程签名不变）
- ✅ 功能完整性不受影响

### 3. 视图层面影响

#### 3.1 mv_presence_1s_any 视图

**当前定义**（完整）：
```sql
CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
SELECT station_id, device_id, metric_id, ts_bucket, present
FROM public.mv_presence_1s
UNION
SELECT mpps.station_id,
       mpps.device_id,
       mc.id AS metric_id,
       mpps.ts_second AS ts_bucket,
       (1)::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) u(metric_key)
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key;
```

**修改策略**：
- ✅ 简化视图定义（移除 UNION，仅基于 `metrics_presence_per_second_device`）
- ✅ 保留视图名称（向后兼容）
- ✅ 保留视图字段结构（向后兼容）

**修改后定义**：
```sql
CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
SELECT mpps.station_id,
       mpps.device_id,
       mc.id AS metric_id,
       mpps.ts_second AS ts_bucket,
       (1)::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) u(metric_key)
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key;
```

**性能影响**：
- ✅ 移除 UNION 操作（性能提升）
- ✅ 减少表扫描（从2个表减少到1个表）
- ✅ 查询计划简化

**使用位置**：
- `scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql` 第1557行
- `.tasks/CLI命令测试计划-run-all深度测试.md` 多处引用

**影响评估**：
- ✅ 视图消费者无需修改（视图签名不变）
- ✅ 查询结果一致（因为 `mv_presence_1s` 为空）
- ✅ 性能提升（移除 UNION 开销）

### 4. Python代码层面影响

#### 4.1 orchestrator.py

**文件路径**：`app/services/run_all/orchestrator.py`

**当前代码**（第510-520行）：
```python
# 在质量打标前，刷新依赖的物化视图：1s存在性与60s统计（按窗口与设备）
try:
    from app.adapters.db.gateway import get_conn as _get_conn

    with _get_conn(settings) as __conn:
        with __conn.cursor() as __cur:
            __cur.execute(
                "CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)",
                (ws, we, None, device_id),
            )
            __cur.execute(
                "CALL public.sp_refresh_mv_metric_60s_stats(%s,%s,%s,%s)",
                (ws, we, None, device_id),
            )
        __conn.commit()
except Exception:
    pass
```

**修改策略**：
- ✅ 保留存储过程调用（仍需刷新 `mv_device_running_1s`）
- ✅ 更新注释（移除"1s存在性"描述）

**修改后代码**：
```python
# 在质量打标前，刷新依赖的物化视图：运行状态与60s统计（按窗口与设备）
try:
    from app.adapters.db.gateway import get_conn as _get_conn

    with _get_conn(settings) as __conn:
        with __conn.cursor() as __cur:
            __cur.execute(
                "CALL public.sp_refresh_mv_running_presence(%s,%s,%s,%s)",
                (ws, we, None, device_id),
            )
            __cur.execute(
                "CALL public.sp_refresh_mv_metric_60s_stats(%s,%s,%s,%s)",
                (ws, we, None, device_id),
            )
        __conn.commit()
except Exception:
    pass
```

**影响评估**：
- ✅ 功能完整性不受影响
- ✅ 仅注释修改，无逻辑变更

#### 4.2 prepare_dim/__init__.py

**文件路径**：`app/services/ingest/prepare_dim/__init__.py`

**当前代码**（第317-321行）：
```python
# mv_device_running_1s: 设备运行状态表（派生数据，可重新生成）
cur.execute("DELETE FROM mv_device_running_1s")
deleted = cur.rowcount
total_deleted += deleted
_act.info(f"[清空表] mv_device_running_1s: {deleted} 行（派生数据，将在 device_running 阶段重新生成）")
```

**修改策略**：
- ❌ **不添加**清空逻辑（表删除后会导致 prepare_dim 失败）
- ✅ 在执行迁移脚本前，手动运行一次 `prepare_dim` 清空表
- ✅ 删除表后，无需在 `prepare_dim` 中清空

**影响评估**：
- ✅ 避免删除表后 `prepare_dim` 命令失败
- ✅ 符合项目清理策略

### 5. 测试代码层面影响

**检索结果**：
- ❌ 未发现直接测试 `mv_presence_1s` 表的测试代码
- ✅ 测试计划文档中有引用（`.tasks/CLI命令测试计划-run-all深度测试.md`）

**修改策略**：
- ✅ 更新测试计划文档，移除 `mv_presence_1s` 相关测试
- ✅ 保留 `mv_presence_1s_any` 视图的测试（视图仍然存在）

### 6. 文档层面影响

**需要更新的文档**：

1. **数据表清单**：`.memory/数据层/数据表清单.md`
   - 删除 `mv_presence_1s` 表的条目（第675-699行）

2. **视图清单**：`.memory/数据层/视图清单.md`
   - 更新 `mv_presence_1s_any` 视图的说明（第145-165行）

3. **存储过程清单**：`.memory/数据层/存储过程清单.md`
   - 更新 `sp_refresh_mv_running_presence` 存储过程的说明

4. **测试计划**：`.tasks/CLI命令测试计划-run-all深度测试.md`
   - 更新阶段8的测试内容（第1507-1718行）

5. **研究报告**：`研究报告_mv_presence_1s表分析.md`
   - 添加"已废弃"标记

6. **技术参考文档**：`docs/缺失计算修复/06-技术参考/数据库函数和存储过程.md`
   - 更新 `sp_refresh_mv_running_presence` 的说明（第372-373行）

7. **注释脚本**：`scripts/migrations/20250922_add_comments_batch_1.sql`
   - 删除 `mv_presence_1s` 表的注释（第32-50行）

8. **注释脚本**：`scripts/migrations/20250922_add_comments_batch_2.sql`
   - 更新 `sp_refresh_mv_running_presence` 的注释（第193-200行）

9. **迁移脚本注释**：`scripts/sql/migrations/058_add_remaining_comments.sql`
   - 更新存储过程注释（第1684-1714行）

10. **原始迁移脚本**：`scripts/sql/migrations/039_materialize_running_presence_and_stats.sql`
   - **⚠️ 重要**：在脚本开头添加废弃警告注释
   - **说明**：此脚本创建了 `mv_presence_1s` 表，需要标记为部分废弃

### 7. 配置和脚本层面影响

**检索结果**：
- ❌ 未发现配置文件引用 `mv_presence_1s`
- ❌ 未发现清理脚本引用 `mv_presence_1s`
- ❌ 未发现备份脚本引用 `mv_presence_1s`
- ❌ 未发现监控脚本引用 `mv_presence_1s`
- ❌ 未发现定时任务引用 `mv_presence_1s`

---

## 📝 详细技术规范

### 规范1：数据库迁移脚本

**文件路径**：`scripts/sql/migrations/074_drop_mv_presence_1s.sql`（新建）

**迁移脚本编号说明**：
- 当前最新迁移脚本：073
- 新迁移脚本编号：074

**完整内容**：
```sql
-- =====================================================================
-- 迁移脚本：删除 mv_presence_1s 表
-- 用途：彻底删除 mv_presence_1s 表及其相关依赖
-- 原因：该表已被 metrics_presence_per_second_device 表完全替代
-- 创建日期：2025-11-04
-- =====================================================================

BEGIN;

-- 步骤1：简化 mv_presence_1s_any 视图（移除对 mv_presence_1s 的依赖）
DROP VIEW IF EXISTS public.mv_presence_1s_any;

CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
SELECT mpps.station_id,
       mpps.device_id,
       mc.id AS metric_id,
       mpps.ts_second AS ts_bucket,
       (1)::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) u(metric_key)
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key;

COMMENT ON VIEW public.mv_presence_1s_any IS '1秒存在性聚合视图

用途：聚合1秒级指标存在性，支持快速查询

数据来源：metrics_presence_per_second_device（展开 available_metrics 数组）

使用场景：数据完整性监控、覆盖率统计

使用示例：
  SELECT * FROM mv_presence_1s_any
  WHERE device_id = 121
    AND ts_bucket >= ''2025-09-01T00:00:00Z''
  ORDER BY ts_bucket;

注意事项：
  - 本视图已简化，仅基于 metrics_presence_per_second_device 表
  - mv_presence_1s 表已废弃并删除
';

-- 步骤2：修改 sp_refresh_mv_running_presence 存储过程（移除对 mv_presence_1s 的写入）
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $procedure$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;
$procedure$;

COMMENT ON PROCEDURE public.sp_refresh_mv_running_presence(timestamptz, timestamptz, bigint, bigint) IS '刷新运行状态物化视图

用途：
  刷新 mv_device_running_1s 物化视图

输入参数：
  - p_start (timestamptz)：开始时间（UTC）
  - p_end (timestamptz)：结束时间（UTC）
  - p_station_id (bigint, DEFAULT NULL)：泵站ID过滤
  - p_device_id (bigint, DEFAULT NULL)：设备ID过滤

返回值：
  - void

业务逻辑：
  - 删除既有窗口数据
  - 重新计算运行状态
  - 写入物化视图

使用场景：
  - 物化视图增量刷新
  - 数据修正后重新计算

使用示例：
  -- 刷新全部数据
  CALL sp_refresh_mv_running_presence(''2025-09-01T00:00:00Z'', ''2025-09-02T00:00:00Z'', NULL, NULL);

注意事项：
  - 会删除既有窗口的数据
  - 建议在数据修正后执行
  - mv_presence_1s 表已废弃，不再刷新
';

-- 步骤3：删除 mv_presence_1s 表
DROP TABLE IF EXISTS public.mv_presence_1s;

-- 步骤4：验证删除结果
DO $$
BEGIN
    -- 验证表已删除
    IF to_regclass('public.mv_presence_1s') IS NOT NULL THEN
        RAISE EXCEPTION 'mv_presence_1s 表删除失败';
    END IF;
    
    -- 验证视图仍然存在
    IF to_regclass('public.mv_presence_1s_any') IS NULL THEN
        RAISE EXCEPTION 'mv_presence_1s_any 视图不存在';
    END IF;
    
    RAISE NOTICE '[验证] mv_presence_1s 表已成功删除';
    RAISE NOTICE '[验证] mv_presence_1s_any 视图已简化';
    RAISE NOTICE '[验证] sp_refresh_mv_running_presence 存储过程已更新';
END $$;

COMMIT;
```

**验证方法**：
```sql
-- 验证表已删除
SELECT to_regclass('public.mv_presence_1s');  -- 应返回 NULL

-- 验证视图仍然存在
SELECT to_regclass('public.mv_presence_1s_any');  -- 应返回 'public.mv_presence_1s_any'

-- 验证视图定义不包含 mv_presence_1s
SELECT definition FROM pg_views WHERE viewname = 'mv_presence_1s_any';
-- 应不包含 "FROM public.mv_presence_1s"

-- 验证存储过程定义不包含 mv_presence_1s
SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'sp_refresh_mv_running_presence';
-- 应不包含 "INSERT INTO public.mv_presence_1s"
```

---

## ✅ 完整检查清单（按执行顺序）

### 阶段0：准备工作（优先级：P0）

- [ ] **0.1** 确定迁移脚本编号
  - **验证方法**：查看 `scripts/sql/migrations/` 目录，确认最新编号为 073
  - **新脚本编号**：074

- [ ] **0.2** 手动清空 `mv_presence_1s` 表（可选，确保表为空）
  - **执行SQL**：`DELETE FROM mv_presence_1s;`
  - **验证方法**：`SELECT COUNT(*) FROM mv_presence_1s;` 返回 0
  - **说明**：表已经为空，此步骤可跳过

### 阶段1：数据库修改（优先级：P0）

- [ ] **1.1** 执行迁移脚本 `scripts/sql/migrations/074_drop_mv_presence_1s.sql`
  - **验证方法**：查询 `to_regclass('public.mv_presence_1s')` 返回 NULL
  - **回滚方法**：执行 `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql` 重建表

- [ ] **1.2** 验证视图 `mv_presence_1s_any` 已简化
  - **验证方法**：查询视图定义不包含 "FROM public.mv_presence_1s"
  - **回滚方法**：执行 `scripts/sql/migrations/041_create_mv_presence_compat.sql` 恢复原视图

- [ ] **1.3** 验证存储过程 `sp_refresh_mv_running_presence` 已更新
  - **验证方法**：查询存储过程定义不包含 "INSERT INTO public.mv_presence_1s"
  - **回滚方法**：执行 `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql` 恢复原存储过程

### 阶段2：Python代码修改（优先级：P1）

- [ ] **2.1** 修改 `app/services/run_all/orchestrator.py` 第504行注释
  - **文件路径**：`app/services/run_all/orchestrator.py`
  - **行号范围**：504
  - **修改内容**：将"1s存在性与60s统计"改为"运行状态与60s统计"
  - **验证方法**：grep "运行状态与60s统计" app/services/run_all/orchestrator.py
  - **回滚方法**：恢复原注释

- [ ] **2.2** ~~修改 `app/services/ingest/prepare_dim/__init__.py` 添加清空逻辑~~（已取消）
  - **说明**：表删除后，无需在 `prepare_dim` 中清空
  - **状态**：跳过此步骤

### 阶段3：文档更新（优先级：P2）

- [ ] **3.1** 更新 `.memory/数据层/数据表清单.md`
  - **文件路径**：`.memory/数据层/数据表清单.md`
  - **行号范围**：675-699
  - **修改内容**：删除 `mv_presence_1s` 表的条目
  - **验证方法**：grep "mv_presence_1s" .memory/数据层/数据表清单.md（应无结果）
  - **回滚方法**：恢复删除的内容

- [ ] **3.2** 更新 `.memory/数据层/视图清单.md`
  - **文件路径**：`.memory/数据层/视图清单.md`
  - **行号范围**：145-165
  - **修改内容**：更新 `mv_presence_1s_any` 视图的说明
  - **验证方法**：查看视图说明是否提及"仅基于 metrics_presence_per_second_device"
  - **回滚方法**：恢复原说明

- [ ] **3.3** 更新 `.tasks/CLI命令测试计划-run-all深度测试.md`
  - **文件路径**：`.tasks/CLI命令测试计划-run-all深度测试.md`
  - **行号范围**：1507-1718
  - **修改内容**：移除 `mv_presence_1s` 相关测试，保留 `mv_presence_1s_any` 测试
  - **验证方法**：grep "mv_presence_1s[^_]" .tasks/CLI命令测试计划-run-all深度测试.md（应无结果）
  - **回滚方法**：恢复原测试内容

- [ ] **3.4** 更新 `docs/缺失计算修复/06-技术参考/数据库函数和存储过程.md`
  - **文件路径**：`docs/缺失计算修复/06-技术参考/数据库函数和存储过程.md`
  - **行号范围**：372-373
  - **修改内容**：更新 `sp_refresh_mv_running_presence` 的说明
  - **验证方法**：查看说明是否提及"仅刷新 mv_device_running_1s"
  - **回滚方法**：恢复原说明

- [ ] **3.5** 更新 `研究报告_mv_presence_1s表分析.md`
  - **文件路径**：`研究报告_mv_presence_1s表分析.md`
  - **行号范围**：1
  - **修改内容**：在标题添加"【已废弃】"标记
  - **验证方法**：查看标题是否包含"【已废弃】"
  - **回滚方法**：删除标记

- [ ] **3.6** 更新 `scripts/sql/migrations/039_materialize_running_presence_and_stats.sql`
  - **文件路径**：`scripts/sql/migrations/039_materialize_running_presence_and_stats.sql`
  - **行号范围**：1-2（在 BEGIN 之前插入）
  - **修改内容**：添加废弃警告注释
  - **验证方法**：查看脚本开头是否包含废弃警告
  - **回滚方法**：删除添加的注释

### 阶段4：测试验证（优先级：P0）

- [ ] **4.1** 单元测试：验证视图查询正常
  - **测试SQL**：`SELECT COUNT(*) FROM mv_presence_1s_any;`
  - **预期结果**：返回记录数（基于 metrics_presence_per_second_device）
  - **失败处理**：检查视图定义是否正确

- [ ] **4.2** 单元测试：验证存储过程调用正常
  - **测试SQL**：`CALL sp_refresh_mv_running_presence('2025-05-31 18:00:00', '2025-05-31 19:00:00', NULL, NULL);`
  - **预期结果**：执行成功，无错误
  - **失败处理**：检查存储过程定义是否正确

- [ ] **4.3** 集成测试：运行 `run-all` 命令
  - **测试命令**：`python -m app.cli.main run-all configs/data_mapping.v2.json`
  - **预期结果**：执行成功，无错误
  - **失败处理**：检查日志，定位错误原因

- [ ] **4.4** 性能测试：对比视图查询性能
  - **测试SQL**：`EXPLAIN ANALYZE SELECT * FROM mv_presence_1s_any WHERE device_id = 5 AND ts_bucket >= '2025-05-31 18:00:00' AND ts_bucket < '2025-05-31 19:00:00';`
  - **预期结果**：查询时间减少（移除 UNION 开销）
  - **失败处理**：分析查询计划，优化索引

- [ ] **4.5** 数据一致性验证：对比视图结果
  - **测试SQL**：
    ```sql
    -- 对比简化前后的视图结果
    SELECT COUNT(*) FROM mv_presence_1s_any;
    -- 应与 metrics_presence_per_second_device 展开后的记录数一致
    ```
  - **预期结果**：记录数一致
  - **失败处理**：检查视图定义逻辑

---

## 🔄 回滚策略

### 完整回滚脚本

**文件路径**：`scripts/sql/rollback/rollback_drop_mv_presence_1s.sql`（新建）

**完整内容**：
```sql
-- =====================================================================
-- 回滚脚本：恢复 mv_presence_1s 表
-- 用途：回滚删除 mv_presence_1s 表的操作
-- 创建日期：2025-11-04
-- =====================================================================

BEGIN;

-- 步骤1：重建 mv_presence_1s 表
CREATE TABLE IF NOT EXISTS public.mv_presence_1s (
  station_id bigint NOT NULL,
  device_id  bigint NOT NULL,
  metric_id  bigint NOT NULL,
  ts_bucket  timestamptz NOT NULL,
  present    smallint NOT NULL,
  PRIMARY KEY (station_id, device_id, metric_id, ts_bucket)
);

CREATE INDEX IF NOT EXISTS ix_mv_pres_sdm_t ON public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket);

COMMENT ON TABLE public.mv_presence_1s IS '1秒指标存在性表

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
';

-- 步骤2：恢复 sp_refresh_mv_running_presence 存储过程
CREATE OR REPLACE PROCEDURE public.sp_refresh_mv_running_presence(
  IN p_start timestamptz,
  IN p_end   timestamptz,
  IN p_station_id bigint DEFAULT NULL,
  IN p_device_id  bigint DEFAULT NULL
)
LANGUAGE sql
AS $procedure$
  -- 运行态（device_running==1）
  INSERT INTO public.mv_device_running_1s(station_id, device_id, ts_bucket, running)
  SELECT f.station_id, f.device_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  JOIN public.dim_metric_config mc ON mc.id=f.metric_id AND mc.metric_key='device_running'
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
    AND f.value=1
  ON CONFLICT DO NOTHING;

  -- 存在性
  INSERT INTO public.mv_presence_1s(station_id, device_id, metric_id, ts_bucket, present)
  SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, 1
  FROM public.fact_measurements f
  WHERE f.ts_bucket>=p_start AND f.ts_bucket<p_end
    AND (p_station_id IS NULL OR f.station_id=p_station_id)
    AND (p_device_id  IS NULL OR f.device_id=p_device_id)
  ON CONFLICT DO NOTHING;
$procedure$;

-- 步骤3：恢复 mv_presence_1s_any 视图
DROP VIEW IF EXISTS public.mv_presence_1s_any;

CREATE OR REPLACE VIEW public.mv_presence_1s_any AS
SELECT station_id, device_id, metric_id, ts_bucket, present
FROM public.mv_presence_1s
UNION
SELECT mpps.station_id,
       mpps.device_id,
       mc.id AS metric_id,
       mpps.ts_second AS ts_bucket,
       (1)::smallint AS present
FROM public.metrics_presence_per_second_device mpps
CROSS JOIN LATERAL unnest(mpps.available_metrics) u(metric_key)
JOIN public.dim_metric_config mc ON mc.metric_key = u.metric_key;

-- 步骤4：验证回滚结果
DO $$
BEGIN
    -- 验证表已恢复
    IF to_regclass('public.mv_presence_1s') IS NULL THEN
        RAISE EXCEPTION 'mv_presence_1s 表恢复失败';
    END IF;
    
    -- 验证视图已恢复
    IF to_regclass('public.mv_presence_1s_any') IS NULL THEN
        RAISE EXCEPTION 'mv_presence_1s_any 视图恢复失败';
    END IF;
    
    RAISE NOTICE '[验证] mv_presence_1s 表已成功恢复';
    RAISE NOTICE '[验证] mv_presence_1s_any 视图已恢复';
    RAISE NOTICE '[验证] sp_refresh_mv_running_presence 存储过程已恢复';
END $$;

COMMIT;
```

### 回滚触发条件

1. **数据库迁移失败**：迁移脚本执行出错
2. **视图查询失败**：`mv_presence_1s_any` 视图查询报错
3. **存储过程调用失败**：`sp_refresh_mv_running_presence` 调用报错
4. **集成测试失败**：`run-all` 命令执行失败
5. **性能严重下降**：视图查询性能下降超过50%

### 回滚验证方法

```sql
-- 验证表已恢复
SELECT COUNT(*) FROM pg_tables WHERE tablename = 'mv_presence_1s';  -- 应返回 1

-- 验证视图已恢复
SELECT definition FROM pg_views WHERE viewname = 'mv_presence_1s_any';
-- 应包含 "FROM public.mv_presence_1s UNION"

-- 验证存储过程已恢复
SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'sp_refresh_mv_running_presence';
-- 应包含 "INSERT INTO public.mv_presence_1s"
```

---

## 📊 风险评估和缓解措施

### 风险1：视图查询失败

**风险等级**：🔴 高

**风险描述**：简化后的 `mv_presence_1s_any` 视图查询失败

**缓解措施**：
1. 在测试环境先验证视图定义
2. 执行迁移前备份视图定义
3. 准备回滚脚本

**监控方法**：
- 监控视图查询错误日志
- 监控视图查询性能

**应急预案**：
- 立即执行回滚脚本
- 恢复原视图定义

### 风险2：存储过程调用失败

**风险等级**：🟡 中

**风险描述**：修改后的 `sp_refresh_mv_running_presence` 存储过程调用失败

**缓解措施**：
1. 在测试环境先验证存储过程定义
2. 执行迁移前备份存储过程定义
3. 准备回滚脚本

**监控方法**：
- 监控存储过程调用错误日志
- 监控 `mv_device_running_1s` 表的数据更新

**应急预案**：
- 立即执行回滚脚本
- 恢复原存储过程定义

### 风险3：集成测试失败

**风险等级**：🟡 中

**风险描述**：`run-all` 命令执行失败

**缓解措施**：
1. 在测试环境先运行完整的 `run-all` 流程
2. 准备回滚脚本
3. 准备应急联系人

**监控方法**：
- 监控 `run-all` 命令的返回码
- 监控日志中的错误信息

**应急预案**：
- 立即执行回滚脚本
- 分析错误日志，定位问题

### 风险4：性能下降

**风险等级**：🟢 低

**风险描述**：视图查询性能下降

**缓解措施**：
1. 在测试环境先进行性能测试
2. 准备性能基准数据
3. 准备索引优化方案

**监控方法**：
- 监控视图查询时间
- 监控数据库CPU和内存使用率

**应急预案**：
- 分析查询计划，优化索引
- 如果性能下降严重，执行回滚脚本

### 风险5：数据不一致

**风险等级**：🟢 低

**风险描述**：视图结果与预期不一致

**缓解措施**：
1. 在测试环境先验证视图结果
2. 准备数据一致性验证脚本
3. 准备回滚脚本

**监控方法**：
- 定期执行数据一致性验证脚本
- 监控视图记录数变化

**应急预案**：
- 立即执行回滚脚本
- 分析视图定义逻辑

---

## 📅 执行时间估算

| 阶段 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 阶段0 | 准备工作 | 5分钟 | 无 |
| 阶段1 | 数据库迁移 | 5分钟 | 阶段0 |
| 阶段2 | Python代码修改 | 5分钟 | 阶段1 |
| 阶段3 | 文档更新 | 25分钟 | 阶段2 |
| 阶段4 | 测试验证 | 30分钟 | 阶段3 |
| **总计** | | **70分钟** | |

---

## ✅ 计划完成确认

- ✅ 已读取所有规则文档
- ✅ 已完成全面影响分析（7个维度）
- ✅ 已创建详尽的技术规范
- ✅ 已创建完整的检查清单（按执行顺序）
- ✅ 已创建回滚策略和脚本
- ✅ 已创建测试验证方案
- ✅ 已创建风险评估和缓解措施
- ✅ 已验证所有函数签名和表结构的准确性
- ❌ 禁止任何代码实现（严格遵守计划模式规则）

---

**计划完成时间**：2025-11-04  
**下一步**：等待用户确认，准备进入执行模式


