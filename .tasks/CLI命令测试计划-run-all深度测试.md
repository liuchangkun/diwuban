# CLI命令测试计划 - run-all深度测试

**文档版本**: v1.0
**创建日期**: 2025-11-02
**关联文档**: CLI命令测试计划-20251102.md

**深度验证补充文档**（2025-11-02新增）:
- 原理分析（阶段1-2）：`.tasks/CLI命令测试计划-深度验证补充-原理分析.md`
- 阶段3-4详细验证：`.tasks/CLI命令测试计划-深度验证补充-阶段3-8.md`
- 阶段5-8详细验证：`.tasks/CLI命令测试计划-深度验证补充-阶段5-8详细.md`
- 阶段6-8最终验证：`.tasks/CLI命令测试计划-深度验证补充-阶段6-8最终.md`
- 数据流图与SQL汇总：`.tasks/CLI命令测试计划-深度验证-数据流图与SQL汇总.md`

**深度验证补充说明**：
针对用户提出的"测试计划深度不足"问题，新增5个维度的深度验证：
1. **原理层面验证**：设计原理、算法验证、数据结构验证
2. **数据关系层面验证**：数据血缘追踪、外键关系验证、数据一致性验证
3. **跨阶段关联验证**：上游依赖验证、下游影响验证、跨阶段一致性验证
4. **边界条件和异常场景验证**：数据缺失、数据异常、性能边界
5. **业务逻辑验证**：物理规律验证、业务规则验证、实际案例验证

---

## 📋 run-all命令概述

### 命令签名
```bash
python -m app.cli.main run-all [mapping_file] [options]
```

### 核心参数
- `mapping_file`: 映射文件路径(默认: configs/data_mapping.v2.json)
- `--use-staging-time-range/--no-use-staging-time-range`: 自动探测时间范围(默认: true)
- `--window-start`: 起始时间(ISO8601)
- `--window-end`: 结束时间(ISO8601)
- `--summary-json`: 执行摘要输出文件
- `--with-device-running`: 启用设备运行状态计算
- `--with-presence`: 启用存在性统计
- `--device-id`: 限定设备ID

### 执行流程(9个阶段)
```
1. prepare-dim stage1 → 重建维度表
2. create-staging → 创建staging表
3. ingest-copy → CSV导入
4. merge-fact → 合并到fact_measurements
5. prepare-dim stage2 → 生成规则表
6. calculation → 缺失指标计算(10个指标)
7. device_running → 设备运行状态
8. presence → 存在性统计
9. quality_mark → 质量标注(默认关闭)
```

### 配置控制
通过 `configs/merge.yaml` 的 `run_all` 段控制每个阶段的开关

---

## 🎯 测试策略

### 测试场景
1. **完整流程测试**: 执行所有9个阶段
2. **部分流程测试**: 只执行部分阶段(通过配置控制)
3. **错误恢复测试**: 模拟中间阶段失败，验证错误处理
4. **性能测试**: 测试大数据量下的执行时间

### 验证维度
- **功能正确性**: 每个阶段是否正确执行
- **数据一致性**: 数据库状态是否符合预期
- **日志完整性**: 日志是否记录所有关键步骤
- **性能指标**: 执行时间是否合理

---

## 📊 阶段1: prepare-dim stage1 (重建维度表)

### 测试目标
验证维度表重建功能，包括备份、清空、重建、恢复全流程

### 执行前快照
```sql
-- 记录维度表行数
SELECT 'dim_stations' as table_name, COUNT(*) as row_count FROM dim_stations
UNION ALL
SELECT 'dim_devices', COUNT(*) FROM dim_devices
UNION ALL
SELECT 'dim_metric_config', COUNT(*) FROM dim_metric_config;

-- 记录所有表的行数（用于验证备份）
SELECT
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### 预期行为
1. 备份21个表
2. 清空非备份表
3. 从映射文件重建维度表
4. 恢复手动配置表
5. 重建基础配置表

### 一级验证：备份验证

#### 确认备份表清单
```sql
-- 查看代码确定应该备份哪21个表
-- 预期备份表清单（需要从代码中确认）：
-- 1. metric_quality_rules
-- 2. metric_rule_auto_baseline
-- 3. metric_rule_manual_baseline
-- 4. metric_rule_range
-- 5. metric_rule_rate_of_change
-- 6. metric_rule_consistency
-- 7. metric_rule_correlation
-- 8. device_running_thresholds
-- 9. device_phase_config
-- 10. calculation_methods
-- 11. calculation_device_params
-- 12. calculation_metric_params
-- 13-21. 其他配置表（需从代码确认）

-- 查询备份表是否存在
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename LIKE '%_backup_%'
ORDER BY tablename;
```

#### 验证备份完整性
```sql
-- 对每个备份表，验证行数是否与原表一致
-- 示例：验证metric_quality_rules的备份

-- 1. 记录原表行数（执行前）
SELECT COUNT(*) as original_count FROM metric_quality_rules;

-- 2. 执行prepare-dim stage1后，检查备份表
SELECT tablename, n_live_tup as backup_count
FROM pg_stat_user_tables
WHERE tablename LIKE 'metric_quality_rules_backup_%'
ORDER BY tablename DESC
LIMIT 1;

-- 3. 对比原表行数与备份表行数，应一致

-- 批量验证所有备份表
WITH backup_tables AS (
    SELECT
        tablename,
        REGEXP_REPLACE(tablename, '_backup_.*$', '') as original_table,
        n_live_tup as backup_count
    FROM pg_stat_user_tables
    WHERE tablename LIKE '%_backup_%'
),
original_tables AS (
    SELECT
        tablename as original_table,
        n_live_tup as original_count
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
)
SELECT
    b.tablename as backup_table,
    b.original_table,
    o.original_count,
    b.backup_count,
    CASE
        WHEN o.original_count = b.backup_count THEN '✓ 一致'
        ELSE '✗ 不一致'
    END as status
FROM backup_tables b
LEFT JOIN original_tables o ON b.original_table = o.original_table
ORDER BY b.original_table;
```

### 二级验证：清空验证
```sql
-- 验证非备份表已清空
-- 预期被清空的表（需从代码确认）：
-- - dim_stations
-- - dim_devices
-- - dim_metric_config
-- - 其他依赖表

SELECT
    tablename,
    n_live_tup as row_count,
    CASE
        WHEN n_live_tup = 0 THEN '✓ 已清空'
        ELSE '✗ 未清空'
    END as status
FROM pg_stat_user_tables
WHERE tablename IN (
    'dim_stations',
    'dim_devices',
    'dim_metric_config'
    -- 添加其他应被清空的表
)
ORDER BY tablename;
```

### 三级验证：重建验证

#### 数据量验证
```sql
-- 验证站点数据(应为3个)
SELECT COUNT(*) as station_count FROM dim_stations;
SELECT id, name FROM dim_stations ORDER BY id;

-- 验证设备数据(应为约20个)
SELECT COUNT(*) as device_count FROM dim_devices;
SELECT station_id, COUNT(*) as device_count
FROM dim_devices
GROUP BY station_id
ORDER BY station_id;

-- 验证指标配置(应为约50个)
SELECT COUNT(*) as metric_count FROM dim_metric_config;
SELECT metric_key, unit FROM dim_metric_config ORDER BY id LIMIT 10;
```

#### 数据质量验证
```sql
-- 验证站点名称与映射文件一致
-- 预期站点名称（从configs/data_mapping.v2.json）：
-- 1. 一期_供水泵房
-- 2. 二期_供水泵房
-- 3. 三期_供水泵房

SELECT id, name
FROM dim_stations
ORDER BY id;

-- 验证设备名称与映射文件一致
SELECT
    s.name as station_name,
    d.name as device_name,
    d.type as device_type,
    d.pump_type
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
ORDER BY s.name, d.name;

-- 验证指标配置的完整性
SELECT
    metric_key,
    unit,
    unit_display,
    decimals_policy,
    fixed_decimals,
    value_type,
    valid_min,
    valid_max
FROM dim_metric_config
ORDER BY metric_key
LIMIT 20;

-- 验证指标单位合理性
SELECT
    metric_key,
    unit,
    CASE
        WHEN unit IS NULL THEN '✗ 单位缺失'
        WHEN unit = '' THEN '✗ 单位为空'
        ELSE '✓ 正常'
    END as unit_status
FROM dim_metric_config
WHERE unit IS NULL OR unit = ''
ORDER BY metric_key;

-- 验证指标有效范围合理性
SELECT
    metric_key,
    valid_min,
    valid_max,
    CASE
        WHEN valid_min IS NULL AND valid_max IS NULL THEN '⚠ 无范围限制'
        WHEN valid_min IS NOT NULL AND valid_max IS NOT NULL AND valid_min >= valid_max THEN '✗ 范围配置错误'
        ELSE '✓ 正常'
    END as range_status
FROM dim_metric_config
ORDER BY metric_key;

-- 验证设备类型和泵类型
SELECT
    type as device_type,
    pump_type,
    COUNT(*) as device_count
FROM dim_devices
GROUP BY type, pump_type
ORDER BY type, pump_type;

-- 验证设备类型是否合理
SELECT
    name as device_name,
    type,
    pump_type,
    CASE
        WHEN type IS NULL THEN '✗ 类型缺失'
        WHEN type = '' THEN '✗ 类型为空'
        WHEN type LIKE '%泵%' AND pump_type IS NULL THEN '⚠ 泵类型缺失'
        ELSE '✓ 正常'
    END as type_status
FROM dim_devices
ORDER BY name;
```

#### 数据一致性验证（与映射文件对比）
```sql
-- 手动对比：打开configs/data_mapping.v2.json
-- 验证每个站点、设备、指标是否都已正确导入

-- 验证站点数量
-- 映射文件中stations数组长度应为3
SELECT COUNT(*) as db_station_count FROM dim_stations;
-- 应输出: 3

-- 验证设备数量
-- 手动统计映射文件中所有devices数组的总长度
SELECT COUNT(*) as db_device_count FROM dim_devices;
-- 应与映射文件一致

-- 验证指标数量
-- 手动统计映射文件中所有metrics数组的总长度（去重）
SELECT COUNT(*) as db_metric_count FROM dim_metric_config;
-- 应与映射文件一致

-- 验证特定站点的设备列表
-- 示例：验证"二期_供水泵房"的设备
SELECT d.name as device_name
FROM dim_devices d
JOIN dim_stations s ON d.station_id = s.id
WHERE s.name = '二期_供水泵房'
ORDER BY d.name;
-- 手动对比映射文件中该站点的devices数组
```

### 四级验证：恢复验证
```sql
-- 验证手动配置表已恢复
-- 预期恢复的表（需从代码确认）：
-- - metric_quality_rules
-- - metric_rule_auto_baseline
-- - device_running_thresholds
-- - 等

-- 对每个恢复表，验证行数是否与备份一致
WITH backup_counts AS (
    SELECT
        REGEXP_REPLACE(tablename, '_backup_.*$', '') as original_table,
        n_live_tup as backup_count
    FROM pg_stat_user_tables
    WHERE tablename LIKE '%_backup_%'
),
current_counts AS (
    SELECT
        tablename as original_table,
        n_live_tup as current_count
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
)
SELECT
    c.original_table,
    b.backup_count,
    c.current_count,
    CASE
        WHEN b.backup_count = c.current_count THEN '✓ 恢复成功'
        WHEN b.backup_count IS NULL THEN '⚠ 无备份'
        ELSE '✗ 恢复失败'
    END as restore_status
FROM current_counts c
LEFT JOIN backup_counts b ON c.original_table = b.original_table
WHERE c.original_table IN (
    'metric_quality_rules',
    'metric_rule_auto_baseline',
    'device_running_thresholds'
    -- 添加其他应恢复的表
)
ORDER BY c.original_table;
```

### 日志验证
关键日志模式:
```
[流程-开始] [维表准备]
[prepare-dim] 阶段1：维度表重建
[prepare-dim] [1/5] 备份21个表...
[prepare-dim] ✓ 备份完成：表1_backup_YYYYMMDD_HHMMSS, 表2_backup_YYYYMMDD_HHMMSS, ...
[prepare-dim] [2/5] 清空非备份表...
[prepare-dim] ✓ 清空完成：共删除 X 行
[prepare-dim] [3/5] 重建维度表...
[prepare-dim] ✓ 重建完成：站点 3 个，设备 X 个，指标 X 个
[prepare-dim] [4/5] 恢复手动配置表...
[prepare-dim] ✓ 恢复完成：表1 X行, 表2 X行, ...
[prepare-dim] [5/5] 重建基础配置表...
[prepare-dim] ✓ 重建完成
[流程-完成] [维表准备]
```

### 代码逻辑验证
- 函数: `app/services/ingest/prepare_dim/__init__.py::prepare_dim(settings, mapping_path, stage=1)`
- 关键步骤:
  1. 读取映射文件 `configs/data_mapping.v2.json`
  2. 备份21个表（创建表名_backup_时间戳）
  3. 清空非备份表（TRUNCATE）
  4. 解析 stations 数组
  5. 对每个 station:
     - 插入 dim_stations 表
     - 对每个 device:
       - 插入 dim_devices 表
       - 对每个 metric:
         - 插入 dim_metric_config 表（去重）
  6. 恢复手动配置表（从备份表复制）
  7. 重建基础配置表

### 通过标准
- [ ] 21个表备份成功，行数一致
- [ ] 非备份表已清空
- [ ] 维度表行数正确（站点3个，设备约20个，指标约50个）
- [ ] 数据内容与映射文件一致（站点名、设备名、指标名）
- [ ] 数据质量合格（单位不为空，有效范围合理，设备类型正确）
- [ ] 手动配置表恢复成功，行数与备份一致
- [ ] 日志无ERROR
- [ ] 耗时 < 30秒

---

## 📊 阶段2: create-staging

### 测试目标
验证staging表创建功能

### 执行前快照
```sql
-- 检查表是否存在
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'staging_raw'
) as staging_raw_exists;
```

### 预期行为
1. 创建 staging_raw 表(如不存在)
2. 创建 staging_rejects 表(如不存在)
3. 清空表数据(如已存在)

### 执行后验证
```sql
-- 验证表存在且为空
SELECT COUNT(*) FROM staging_raw;  -- 应为 0
SELECT COUNT(*) FROM staging_rejects;  -- 应为 0

-- 验证表结构
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'staging_raw' 
ORDER BY ordinal_position;
```

### 日志验证
```
[流程-开始] [创建staging表]
[流程-完成] [创建staging表]
```

### 代码逻辑验证
- 函数: `app/services/ingest/create_staging.py::create_staging(settings)`
- 调用: `app/adapters/db/gateway.py::create_staging_if_not_exists(conn)`
- 预期行为: 执行CREATE TABLE IF NOT EXISTS，然后TRUNCATE

### 通过标准
- [ ] staging_raw 表存在且为空
- [ ] staging_rejects 表存在且为空
- [ ] 表结构正确
- [ ] 耗时 < 5秒

---

## 📊 阶段3: ingest-copy

### 测试目标
验证CSV批量导入功能

### 执行前快照
```sql
SELECT COUNT(*) FROM staging_raw;  -- 应为 0
```

### 预期行为
1. 从映射文件读取CSV文件列表
2. 并发读取CSV文件(6个worker)
3. 使用COPY命令批量导入
4. 记录拒绝行到staging_rejects

### 执行后验证
```sql
-- 验证导入数据量
SELECT COUNT(*) as total_rows FROM staging_raw;

-- 验证数据分布
SELECT 
    station_name, 
    device_name, 
    metric_key,
    COUNT(*) as row_count
FROM staging_raw 
GROUP BY station_name, device_name, metric_key
ORDER BY station_name, device_name, metric_key
LIMIT 20;

-- 验证时间范围
SELECT 
    MIN(DataTime) as earliest, 
    MAX(DataTime) as latest,
    COUNT(DISTINCT DataTime) as unique_timestamps
FROM staging_raw;

-- 验证拒绝记录
SELECT COUNT(*) as reject_count FROM staging_rejects;
SELECT error_msg, COUNT(*) as count 
FROM staging_rejects 
GROUP BY error_msg;

-- 验证source_hint格式
SELECT DISTINCT source_hint FROM staging_raw LIMIT 10;
```

### 日志验证
```
[流程-开始] [CSV导入]
[进度] ingest-copy 开始
ingest.load.begin: files_total=256
ingest.copy.batch: file=xxx.csv, rows_loaded=2400
...
ingest.load.end: files_succeeded=256, rows_loaded=XXX
[流程-完成] [CSV导入]
```

### 代码逻辑验证
- 函数: `app/services/ingest/copy_workers.py::copy_from_mapping(settings, mapping_path)`
- 关键步骤:
  1. 读取 `configs/data_mapping.v2.json`
  2. 遍历 stations → devices → metrics → files
  3. 对每个CSV文件:
     - 读取CSV(TagName, DataTime, DataValue)
     - 验证格式
     - 生成source_hint: `data/{rel_path}|batch={run_id}|ver=2`
     - COPY到staging_raw
  4. 返回CopyStats统计

### 通过标准
- [ ] staging_raw 表有数据(预计数十万行)
- [ ] 导入成功率 > 95%
- [ ] 数据分布符合映射文件
- [ ] source_hint格式正确
- [ ] 拒绝记录有合理错误信息
- [ ] 耗时 < 120秒

---

## 📊 阶段4: merge-fact

### 测试目标
验证数据合并到fact_measurements功能

### 执行前快照
```sql
-- 记录fact_measurements行数
SELECT COUNT(*) as before_count FROM fact_measurements;

-- 记录时间范围
SELECT 
    MIN(ts_bucket) as earliest, 
    MAX(ts_bucket) as latest 
FROM fact_measurements;
```

### 预期行为
1. 自动探测staging时间范围(或使用指定窗口)
2. 时区转换(站点时区 → UTC)
3. 秒级时间对齐
4. 去重
5. UPSERT到fact_measurements

### 执行后验证
```sql
-- 验证新增数据量
SELECT COUNT(*) as after_count FROM fact_measurements;

-- 验证时间范围扩展
SELECT 
    MIN(ts_bucket) as earliest, 
    MAX(ts_bucket) as latest 
FROM fact_measurements;

-- 验证数据分布
SELECT 
    station_id, 
    device_id, 
    COUNT(*) as measurement_count
FROM fact_measurements 
GROUP BY station_id, device_id
ORDER BY station_id, device_id;

-- 验证质量状态(新导入数据应为0)
SELECT quality_status, COUNT(*) 
FROM fact_measurements 
GROUP BY quality_status;

-- 验证source_hint
SELECT DISTINCT source_hint 
FROM fact_measurements 
WHERE source_hint LIKE 'data/%'
LIMIT 10;
```

### 日志验证
```
[流程-开始] [数据合并]
[进度] 窗口探测开始
[进度] 窗口确定: start=YYYY-MM-DD HH:MM:SS+08, end=YYYY-MM-DD HH:MM:SS+08
[进度] merge-fact 开始
align.merge.window: rows_input=XXX, rows_deduped=XXX, rows_merged=XXX
[进度] merge-fact 完成 (耗时: X.XX秒)
[流程-完成] [数据合并]
```

### 代码逻辑验证
- 函数: `app/services/ingest/merge_service.py::merge_window(settings, window_start_utc, window_end_utc, device_id)`
- 关键步骤:
  1. 如果use_staging_time_range=true:
     - 查询staging_raw的MIN(DataTime), MAX(DataTime)
     - 转换为UTC时间窗口
  2. 调用 `app/adapters/db/gateway.py::run_merge_window(conn, ws, we, device_id)`
  3. 存储过程执行:
     - 从staging_raw读取数据
     - JOIN dim_stations, dim_devices, dim_metric_config获取ID
     - 时区转换
     - 秒级对齐(ts_bucket)
     - 去重(按station_id, device_id, metric_id, ts_bucket)
     - UPSERT到fact_measurements
  4. 返回MergeStats

### 通过标准
- [ ] fact_measurements 表新增数据
- [ ] 新增数据量合理(应接近staging_raw行数，考虑去重)
- [ ] 时间范围正确
- [ ] 数据分布符合预期
- [ ] 质量状态为0(未标注)
- [ ] 耗时 < 60秒

---

## 📊 阶段5: prepare-dim stage2 (生成规则表)

### 测试目标
验证规则表生成功能，确保所有规则、参数、阈值正确生成

### 前置条件
- fact_measurements表必须有数据（阶段4已完成merge-fact）
- dim_stations, dim_devices, dim_metric_config表已正确填充（阶段1已完成）

### 执行前快照
```sql
-- 记录规则表行数
SELECT 'metric_quality_rules' as table_name, COUNT(*) as row_count FROM metric_quality_rules
UNION ALL
SELECT 'metric_rule_auto_baseline', COUNT(*) FROM metric_rule_auto_baseline
UNION ALL
SELECT 'metric_rule_manual_baseline', COUNT(*) FROM metric_rule_manual_baseline
UNION ALL
SELECT 'metric_rule_range', COUNT(*) FROM metric_rule_range
UNION ALL
SELECT 'metric_rule_rate_of_change', COUNT(*) FROM metric_rule_rate_of_change
UNION ALL
SELECT 'device_running_thresholds', COUNT(*) FROM device_running_thresholds;

-- 确认fact_measurements有数据
SELECT COUNT(*) as fact_count FROM fact_measurements;
SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements;
```

### 预期行为
1. 清空规则表
2. 调用存储过程生成规则（基于fact_measurements数据）
3. 生成映射表

### 一级验证：规则表存在性
```sql
-- 验证质量规则表有数据
SELECT COUNT(*) as rule_count FROM metric_quality_rules;

-- 验证自动基线表有数据
SELECT COUNT(*) as baseline_count FROM metric_rule_auto_baseline;

-- 验证运行阈值表有数据
SELECT COUNT(*) as threshold_count FROM device_running_thresholds;

-- 验证范围规则表有数据
SELECT COUNT(*) as range_count FROM metric_rule_range;

-- 验证变化率规则表有数据
SELECT COUNT(*) as roc_count FROM metric_rule_rate_of_change;

-- 汇总所有规则表
SELECT
    'metric_quality_rules' as table_name,
    COUNT(*) as row_count,
    CASE WHEN COUNT(*) > 0 THEN '✓ 有数据' ELSE '✗ 无数据' END as status
FROM metric_quality_rules
UNION ALL
SELECT 'metric_rule_auto_baseline', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ 有数据' ELSE '✗ 无数据' END
FROM metric_rule_auto_baseline
UNION ALL
SELECT 'device_running_thresholds', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ 有数据' ELSE '✗ 无数据' END
FROM device_running_thresholds
UNION ALL
SELECT 'metric_rule_range', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ 有数据' ELSE '✗ 无数据' END
FROM metric_rule_range
UNION ALL
SELECT 'metric_rule_rate_of_change', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ 有数据' ELSE '✗ 无数据' END
FROM metric_rule_rate_of_change;
```

### 二级验证：规则完整性
```sql
-- 验证每个设备是否都有运行阈值
SELECT
    d.id as device_id,
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    CASE
        WHEN t.device_id IS NULL THEN '✗ 缺失阈值'
        ELSE '✓ 有阈值'
    END as threshold_status
FROM dim_devices d
LEFT JOIN device_running_thresholds t ON d.id = t.device_id
ORDER BY d.name;

-- 验证每个设备+指标组合是否都有质量规则
SELECT
    d.name as device_name,
    m.metric_key,
    COUNT(r.id) as rule_count,
    CASE
        WHEN COUNT(r.id) = 0 THEN '✗ 无规则'
        WHEN COUNT(r.id) > 0 THEN '✓ 有规则'
    END as rule_status
FROM dim_devices d
CROSS JOIN dim_metric_config m
LEFT JOIN metric_quality_rules r ON d.id = r.device_id AND m.id = r.metric_id
GROUP BY d.name, m.metric_key
ORDER BY d.name, m.metric_key
LIMIT 50;

-- 验证每个设备+指标组合是否都有自动基线
SELECT
    d.name as device_name,
    m.metric_key,
    b.baseline_mean,
    b.baseline_std,
    CASE
        WHEN b.device_id IS NULL THEN '✗ 无基线'
        ELSE '✓ 有基线'
    END as baseline_status
FROM dim_devices d
CROSS JOIN dim_metric_config m
LEFT JOIN metric_rule_auto_baseline b ON d.id = b.device_id AND m.id = b.metric_id
ORDER BY d.name, m.metric_key
LIMIT 50;
```

### 三级验证：参数和阈值合理性

#### 验证运行阈值合理性
```sql
-- 验证threshold_on > threshold_off
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    t.metric_key,
    CASE
        WHEN t.threshold_on IS NULL THEN '✗ threshold_on为空'
        WHEN t.threshold_off IS NULL THEN '✗ threshold_off为空'
        WHEN t.threshold_on <= t.threshold_off THEN '✗ threshold_on <= threshold_off'
        WHEN t.threshold_on <= 0 THEN '✗ threshold_on <= 0'
        WHEN t.threshold_off < 0 THEN '✗ threshold_off < 0'
        ELSE '✓ 正常'
    END as validation_status
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
ORDER BY d.name;

-- 统计阈值范围分布
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    t.threshold_on - t.threshold_off as threshold_gap
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
ORDER BY d.name;
```

#### 验证自动基线合理性
```sql
-- 验证baseline_mean > 0（对于应为正值的指标）
SELECT
    d.name as device_name,
    m.metric_key,
    b.baseline_mean,
    b.baseline_std,
    b.sample_count,
    CASE
        WHEN b.baseline_mean IS NULL THEN '✗ baseline_mean为空'
        WHEN b.baseline_std IS NULL THEN '✗ baseline_std为空'
        WHEN b.baseline_mean < 0 AND m.metric_key NOT LIKE '%温度%' THEN '⚠ baseline_mean为负'
        WHEN b.baseline_std < 0 THEN '✗ baseline_std为负'
        WHEN b.baseline_std = 0 THEN '⚠ baseline_std为0（无变化）'
        WHEN b.sample_count IS NULL OR b.sample_count < 100 THEN '⚠ 样本量不足'
        ELSE '✓ 正常'
    END as validation_status
FROM metric_rule_auto_baseline b
JOIN dim_devices d ON b.device_id = d.id
JOIN dim_metric_config m ON b.metric_id = m.id
ORDER BY d.name, m.metric_key
LIMIT 50;

-- 统计基线分布
SELECT
    m.metric_key,
    COUNT(*) as device_count,
    MIN(b.baseline_mean) as min_mean,
    MAX(b.baseline_mean) as max_mean,
    AVG(b.baseline_mean) as avg_mean,
    MIN(b.baseline_std) as min_std,
    MAX(b.baseline_std) as max_std,
    AVG(b.baseline_std) as avg_std
FROM metric_rule_auto_baseline b
JOIN dim_metric_config m ON b.metric_id = m.id
GROUP BY m.metric_key
ORDER BY m.metric_key;
```

#### 验证范围规则合理性
```sql
-- 验证range_min < range_max
SELECT
    d.name as device_name,
    m.metric_key,
    r.range_min,
    r.range_max,
    CASE
        WHEN r.range_min IS NULL THEN '✗ range_min为空'
        WHEN r.range_max IS NULL THEN '✗ range_max为空'
        WHEN r.range_min >= r.range_max THEN '✗ range_min >= range_max'
        ELSE '✓ 正常'
    END as validation_status
FROM metric_rule_range r
JOIN dim_devices d ON r.device_id = d.id
JOIN dim_metric_config m ON r.metric_id = m.id
ORDER BY d.name, m.metric_key
LIMIT 50;

-- 对比范围规则与指标配置的valid_min/max
SELECT
    d.name as device_name,
    m.metric_key,
    m.valid_min as config_min,
    m.valid_max as config_max,
    r.range_min as rule_min,
    r.range_max as rule_max,
    CASE
        WHEN r.range_min < m.valid_min THEN '⚠ rule_min < valid_min'
        WHEN r.range_max > m.valid_max THEN '⚠ rule_max > valid_max'
        ELSE '✓ 正常'
    END as consistency_status
FROM metric_rule_range r
JOIN dim_devices d ON r.device_id = d.id
JOIN dim_metric_config m ON r.metric_id = m.id
WHERE m.valid_min IS NOT NULL AND m.valid_max IS NOT NULL
ORDER BY d.name, m.metric_key
LIMIT 50;
```

### 四级验证：参数和阈值准确性（抽样验证）

#### 手动验证自动基线计算
```sql
-- 抽样：选择3-5个设备，手动计算baseline_mean和baseline_std

-- 示例1：验证1#加压泵的某个指标的基线
-- 1. 获取系统生成的基线
SELECT
    d.name as device_name,
    m.metric_key,
    b.baseline_mean as system_mean,
    b.baseline_std as system_std,
    b.sample_count,
    b.time_window_start,
    b.time_window_end
FROM metric_rule_auto_baseline b
JOIN dim_devices d ON b.device_id = d.id
JOIN dim_metric_config m ON b.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND m.metric_key = '有功功率'
LIMIT 1;

-- 2. 手动计算基线（基于fact_measurements数据）
SELECT
    AVG(f.value) as manual_mean,
    STDDEV(f.value) as manual_std,
    COUNT(*) as manual_sample_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND m.metric_key = '有功功率'
AND f.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 19:59:59+00';
-- 时间范围应与系统生成基线时使用的时间窗口一致

-- 3. 对比系统计算与手动计算
--    误差应 < 1%
--    system_mean ≈ manual_mean
--    system_std ≈ manual_std
--    sample_count应一致
```

#### 手动验证运行阈值计算
```sql
-- 抽样：验证运行阈值的计算逻辑

-- 1. 获取系统生成的阈值
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    t.metric_key
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
WHERE d.name LIKE '%1#加压泵%';

-- 2. 查看阈值计算逻辑（查看存储过程代码）
-- 预期逻辑：
--   threshold_on = baseline_mean * 0.1  （10%的基线均值）
--   threshold_off = baseline_mean * 0.05 （5%的基线均值）
-- 或其他计算公式

-- 3. 手动计算阈值
SELECT
    d.name as device_name,
    AVG(f.value) as mean_power,
    AVG(f.value) * 0.1 as calculated_threshold_on,
    AVG(f.value) * 0.05 as calculated_threshold_off
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND m.metric_key = '有功功率'
AND f.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 19:59:59+00'
GROUP BY d.name;

-- 4. 对比系统阈值与手动计算阈值
--    误差应 < 5%
```

### 五级验证：数据来源验证
```sql
-- 验证规则是基于哪个时间段的fact_measurements数据生成

-- 查询基线表中记录的时间窗口
SELECT
    MIN(time_window_start) as earliest_window_start,
    MAX(time_window_end) as latest_window_end,
    COUNT(DISTINCT time_window_start) as unique_windows
FROM metric_rule_auto_baseline
WHERE time_window_start IS NOT NULL;

-- 对比fact_measurements的时间范围
SELECT
    MIN(ts_bucket) as fact_earliest,
    MAX(ts_bucket) as fact_latest
FROM fact_measurements;

-- 验证基线时间窗口是否覆盖fact_measurements的时间范围
-- 或者是否使用了特定的时间段（例如：最近7天、最近30天）
```

### 日志验证
```
[流程-开始] [维表准备]
[prepare-dim] 阶段2：生成规则表
[prepare-dim] 清空规则表...
[prepare-dim] ✓ 清空完成：metric_quality_rules, metric_rule_auto_baseline, ...
[prepare-dim] 生成规则表...
[prepare-dim] 调用存储过程：sp_generate_quality_rules
[prepare-dim] 调用存储过程：sp_generate_auto_baseline
[prepare-dim] 调用存储过程：sp_generate_running_thresholds
[prepare-dim] ✓ 规则生成完成：质量规则 X条, 自动基线 X条, 运行阈值 X条
[prepare-dim] 生成映射表...
[prepare-dim] ✓ 映射表生成完成
[流程-完成] [维表准备]
```

### 代码逻辑验证
- 函数: `app/services/ingest/prepare_dim/__init__.py::prepare_dim(settings, mapping_path, stage=2)`
- 关键步骤:
  1. TRUNCATE规则表
  2. 调用存储过程生成规则:
     - `sp_generate_quality_rules()` - 生成质量规则
     - `sp_generate_auto_baseline()` - 生成自动基线
     - `sp_generate_running_thresholds()` - 生成运行阈值
     - `sp_generate_range_rules()` - 生成范围规则
     - `sp_generate_roc_rules()` - 生成变化率规则
  3. 生成映射表
  4. 返回统计信息

### 失败处理
```sql
-- 如果规则生成失败，分析原因

-- 原因1：fact_measurements无数据
SELECT COUNT(*) FROM fact_measurements;
-- 如果为0，说明阶段4未成功执行

-- 原因2：数据量不足，无法计算统计量
SELECT
    device_id,
    metric_id,
    COUNT(*) as sample_count
FROM fact_measurements
GROUP BY device_id, metric_id
HAVING COUNT(*) < 100
ORDER BY sample_count;
-- 如果样本量 < 100，可能无法生成可靠的基线

-- 原因3：存储过程执行错误
-- 查看日志中的详细错误信息
-- 检查存储过程是否存在
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'api'
AND routine_name LIKE 'sp_generate%';
```

### 通过标准
- [ ] 所有规则表都有数据（metric_quality_rules, metric_rule_auto_baseline, device_running_thresholds等）
- [ ] 每个设备都有运行阈值
- [ ] 每个设备+指标组合都有质量规则和自动基线（或有合理的缺失原因）
- [ ] 阈值合理性验证通过（threshold_on > threshold_off > 0）
- [ ] 基线合理性验证通过（baseline_mean合理，baseline_std > 0，sample_count充足）
- [ ] 范围规则合理性验证通过（range_min < range_max，符合valid_min/max）
- [ ] 抽样验证准确性通过（3-5个样本，误差 < 1-5%）
- [ ] 数据来源验证通过（基于正确的时间窗口）
- [ ] 日志无ERROR
- [ ] 耗时 < 60秒

---

## 📊 阶段6: calculation (缺失指标计算)

### 测试目标
验证缺失指标计算功能，确保10个计算指标正确生成

### 配置要求
- `configs/merge.yaml`: `enable_calculation: true`
- 计算指标列表: pump_flow_rate, pump_head, pump_efficiency, pump_power, pump_shaft_power, motor_efficiency, system_efficiency, specific_energy, unit_energy_consumption, energy_cost

### 执行前快照
```sql
-- 记录计算前的fact_measurements行数
SELECT COUNT(*) as before_calc FROM fact_measurements;

-- 检查计算方法配置
SELECT id, method_name, formula, input_metrics
FROM calculation_methods
ORDER BY id;

-- 检查设备参数配置
SELECT device_id, param_name, param_value
FROM calculation_device_params
ORDER BY device_id, param_name;

-- 确认需要计算的指标
SELECT metric_key
FROM dim_metric_config
WHERE metric_key IN (
    'pump_flow_rate', 'pump_head', 'pump_efficiency',
    'pump_power', 'pump_shaft_power', 'motor_efficiency',
    'system_efficiency', 'specific_energy',
    'unit_energy_consumption', 'energy_cost'
);
```

### 预期行为
1. 读取calculation_methods表获取计算方法
2. 读取calculation_device_params表获取设备参数
3. 从fact_measurements读取输入指标数据
4. 对每个设备、每个时间点执行计算
5. 将计算结果插入fact_measurements，source_hint包含"calculation_"

### 执行后验证

#### 一级验证：数据存在性
```sql
-- 验证计算指标数据已生成
SELECT COUNT(*) as after_calc
FROM fact_measurements
WHERE source_hint LIKE '%calculation_%';

-- 验证每个计算指标的数据量
SELECT
    m.metric_key,
    COUNT(*) as calc_count
FROM fact_measurements f
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE f.source_hint LIKE '%calculation_%'
GROUP BY m.metric_key
ORDER BY m.metric_key;

-- 验证每个设备的计算指标分布
SELECT
    d.name as device_name,
    m.metric_key,
    COUNT(*) as calc_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE f.source_hint LIKE '%calculation_%'
GROUP BY d.name, m.metric_key
ORDER BY d.name, m.metric_key;
```

#### 二级验证：数值合理性
```sql
-- 验证泵效率在0-100%范围内
SELECT
    MIN(value) as min_efficiency,
    MAX(value) as max_efficiency,
    AVG(value) as avg_efficiency,
    COUNT(CASE WHEN value < 0 OR value > 100 THEN 1 END) as out_of_range_count
FROM fact_measurements f
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE m.metric_key = 'pump_efficiency'
AND f.source_hint LIKE '%calculation_%';

-- 验证泵流量为正值
SELECT
    MIN(value) as min_flow,
    MAX(value) as max_flow,
    COUNT(CASE WHEN value <= 0 THEN 1 END) as negative_count
FROM fact_measurements f
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE m.metric_key = 'pump_flow_rate'
AND f.source_hint LIKE '%calculation_%';

-- 验证泵扬程为正值
SELECT
    MIN(value) as min_head,
    MAX(value) as max_head,
    COUNT(CASE WHEN value <= 0 THEN 1 END) as negative_count
FROM fact_measurements f
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE m.metric_key = 'pump_head'
AND f.source_hint LIKE '%calculation_%';
```

#### 三级验证：计算准确性（抽样验证）
```sql
-- 抽样：选择特定设备、特定时间点的数据进行手动计算验证
-- 示例：验证1#加压泵在某个时间点的泵效率计算

-- 1. 获取输入数据（流量、扬程、功率）
SELECT
    f.ts_bucket,
    m.metric_key,
    f.value
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND f.ts_bucket = '2025-05-31 18:00:00+00'
AND m.metric_key IN ('pump_flow_rate', 'pump_head', 'pump_power')
AND f.source_hint NOT LIKE '%calculation_%'
ORDER BY m.metric_key;

-- 2. 获取计算结果
SELECT
    f.ts_bucket,
    f.value as calculated_efficiency
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND f.ts_bucket = '2025-05-31 18:00:00+00'
AND m.metric_key = 'pump_efficiency'
AND f.source_hint LIKE '%calculation_%';

-- 3. 手动计算公式：效率 = (流量 * 扬程 * 9.81 * 1000) / (功率 * 3600) * 100
-- 对比手动计算结果与系统计算结果，误差应 < 1%
```

### 日志验证
```
[流程-开始] [缺失指标计算]
[进度] calculation 开始
calculation.init: methods_count=10
calculation.process: device_id=X, metric=pump_flow_rate, calculated_points=XXX
calculation.process: device_id=X, metric=pump_efficiency, calculated_points=XXX
...
calculation.complete: total_calculated_points=XXX
[流程-完成] [缺失指标计算]
```

### 代码逻辑验证
- 函数路径: `app/services/calculation/missing_metrics.py::compute_missing_metrics()`
- 关键步骤:
  1. 读取calculation_methods表
  2. 对每个计算方法:
     - 解析input_metrics（输入指标列表）
     - 从fact_measurements查询输入数据
     - 执行计算公式
     - 插入计算结果到fact_measurements
  3. 返回统计信息

### 失败处理验证
```sql
-- 检查是否有计算失败的记录（通过日志）
-- 如果某个指标计算失败，分析原因：

-- 原因1：输入数据缺失
SELECT
    d.name as device_name,
    m.metric_key,
    COUNT(*) as data_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE m.metric_key IN ('进口压力', '出口压力', '有功功率')  -- 输入指标
AND f.source_hint NOT LIKE '%calculation_%'
GROUP BY d.name, m.metric_key
ORDER BY d.name, m.metric_key;

-- 原因2：设备参数缺失
SELECT device_id, param_name
FROM calculation_device_params
WHERE device_id NOT IN (
    SELECT DISTINCT device_id FROM calculation_device_params
);

-- 原因3：计算公式异常（除零、负数开方等）
-- 需要查看日志中的详细错误信息
```

### 通过标准
- [ ] 所有10个计算指标都有数据生成
- [ ] 计算数据量合理（应接近输入数据量）
- [ ] 数值在合理范围内（效率0-100%，流量/扬程/功率>0）
- [ ] 抽样验证计算准确性，误差 < 1%
- [ ] 如有失败，有详细的错误日志和合理的失败原因
- [ ] 耗时 < 300秒

---

## 📊 阶段7: device_running (设备运行状态)

### 测试目标
验证设备运行状态判断功能，确保状态判断准确

### 配置要求
- `configs/merge.yaml`: `device_running: true`

### 执行前快照
```sql
-- 检查设备运行阈值配置
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    t.metric_key
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
ORDER BY d.name;

-- 验证阈值合理性
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    CASE
        WHEN t.threshold_on IS NULL THEN '阈值缺失'
        WHEN t.threshold_off IS NULL THEN '阈值缺失'
        WHEN t.threshold_on <= t.threshold_off THEN '阈值配置错误'
        WHEN t.threshold_on <= 0 THEN '阈值不合理'
        ELSE '正常'
    END as status
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
ORDER BY d.name;

-- 记录mv_device_running_1s表的初始状态
SELECT COUNT(*) as before_count FROM mv_device_running_1s;
```

### 预期行为
1. 读取device_running_thresholds表获取阈值
2. 从fact_measurements读取判断指标数据（通常是有功功率）
3. 对每个设备、每秒数据进行状态判断:
   - 指标值 >= threshold_on → 运行状态
   - 指标值 <= threshold_off → 停止状态
   - threshold_off < 指标值 < threshold_on → 保持上一状态
4. 更新mv_device_running_1s表

### 执行后验证

#### 一级验证：数据存在性
```sql
-- 验证mv_device_running_1s表有数据
SELECT COUNT(*) as after_count FROM mv_device_running_1s;

-- 验证每个设备的运行状态数据
SELECT
    d.name as device_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN r.is_running THEN 1 ELSE 0 END) as running_count,
    SUM(CASE WHEN NOT r.is_running THEN 1 ELSE 0 END) as stopped_count,
    ROUND(100.0 * SUM(CASE WHEN r.is_running THEN 1 ELSE 0 END) / COUNT(*), 2) as running_percentage
FROM mv_device_running_1s r
JOIN dim_devices d ON r.device_id = d.id
GROUP BY d.name
ORDER BY d.name;

-- 验证时间范围
SELECT
    MIN(ts_bucket) as earliest,
    MAX(ts_bucket) as latest,
    COUNT(DISTINCT ts_bucket) as unique_timestamps
FROM mv_device_running_1s;
```

#### 二级验证：状态判断合理性
```sql
-- 验证状态转换频率（避免频繁抖动）
WITH state_changes AS (
    SELECT
        device_id,
        ts_bucket,
        is_running,
        LAG(is_running) OVER (PARTITION BY device_id ORDER BY ts_bucket) as prev_state
    FROM mv_device_running_1s
)
SELECT
    d.name as device_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_running != prev_state THEN 1 ELSE 0 END) as state_change_count,
    ROUND(100.0 * SUM(CASE WHEN is_running != prev_state THEN 1 ELSE 0 END) / COUNT(*), 2) as change_percentage
FROM state_changes sc
JOIN dim_devices d ON sc.device_id = d.id
WHERE prev_state IS NOT NULL
GROUP BY d.name
ORDER BY d.name;

-- 如果状态转换频率 > 10%，可能存在阈值配置问题或数据抖动
```

#### 三级验证：状态判断准确性（抽样验证）
```sql
-- 抽样验证：选择3-5个时间点，逐一验证状态判断

-- 示例1：验证1#加压泵在某个时间点的状态判断
-- 1. 获取阈值配置
SELECT
    d.name as device_name,
    t.threshold_on,
    t.threshold_off,
    t.metric_key
FROM device_running_thresholds t
JOIN dim_devices d ON t.device_id = d.id
WHERE d.name LIKE '%1#加压泵%';

-- 2. 获取该时间点的判断指标值（有功功率）
SELECT
    f.ts_bucket,
    m.metric_key,
    f.value as power_value
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND f.ts_bucket = '2025-05-31 18:00:00+00'
AND m.metric_key = '有功功率';

-- 3. 获取系统判断的运行状态
SELECT
    r.ts_bucket,
    r.is_running,
    r.power_value
FROM mv_device_running_1s r
JOIN dim_devices d ON r.device_id = d.id
WHERE d.name LIKE '%1#加压泵%'
AND r.ts_bucket = '2025-05-31 18:00:00+00';

-- 4. 手动判断：
--    如果 power_value >= threshold_on → 应为运行状态(is_running=true)
--    如果 power_value <= threshold_off → 应为停止状态(is_running=false)
--    对比手动判断与系统判断，应一致
```

#### 深度分析：停止状态原因分析
```sql
-- 如果设备被判断为停止状态，详细分析原因

-- 原因1：指标值低于threshold_off
SELECT
    d.name as device_name,
    r.ts_bucket,
    r.power_value,
    t.threshold_off,
    CASE
        WHEN r.power_value <= t.threshold_off THEN '功率低于停止阈值'
        ELSE '其他原因'
    END as reason
FROM mv_device_running_1s r
JOIN dim_devices d ON r.device_id = d.id
JOIN device_running_thresholds t ON r.device_id = t.device_id
WHERE r.is_running = false
AND d.name LIKE '%1#加压泵%'
ORDER BY r.ts_bucket
LIMIT 10;

-- 原因2：数据缺失导致判断为停止
SELECT
    ts_bucket,
    COUNT(*) as data_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE d.name LIKE '%1#加压泵%'
AND m.metric_key = '有功功率'
AND ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:10:00+00'
GROUP BY ts_bucket
ORDER BY ts_bucket;

-- 原因3：时间窗口内无有效数据
SELECT
    r.ts_bucket,
    r.is_running,
    r.power_value,
    CASE
        WHEN r.power_value IS NULL THEN '数据缺失'
        WHEN r.power_value <= t.threshold_off THEN '功率低于阈值'
        ELSE '正常停止'
    END as stop_reason
FROM mv_device_running_1s r
JOIN dim_devices d ON r.device_id = d.id
JOIN device_running_thresholds t ON r.device_id = t.device_id
WHERE r.is_running = false
AND d.name LIKE '%1#加压泵%'
ORDER BY r.ts_bucket
LIMIT 20;
```

### 日志验证
```
[流程-开始] [设备运行状态]
[进度] device_running 开始
device_running.init: devices_count=XX, thresholds_loaded=XX
device_running.process: device_id=X, running_points=XXX, stopped_points=XXX
...
device_running.complete: total_points=XXX
[流程-完成] [设备运行状态]
```

### 代码逻辑验证
- 函数路径: `app/services/device_running/compute.py::compute_device_running()`
- 关键步骤:
  1. 读取device_running_thresholds表
  2. 对每个设备:
     - 从fact_measurements查询判断指标（有功功率）
     - 按时间顺序遍历数据点
     - 应用状态判断逻辑（threshold_on/off + 滞后）
     - 插入结果到mv_device_running_1s
  3. 返回统计信息

### 通过标准
- [ ] mv_device_running_1s表有数据
- [ ] 每个设备都有运行状态记录
- [ ] 阈值配置合理（threshold_on > threshold_off > 0）
- [ ] 状态转换频率合理（< 10%）
- [ ] 抽样验证状态判断准确性，3-5个样本全部正确
- [ ] 停止状态有合理的原因（功率低、数据缺失等）
- [ ] 耗时 < 120秒

---

## 📊 阶段8: presence (存在性统计)

### 测试目标
验证存在性统计功能，确保数据完整性分析准确

### 配置要求
- `configs/merge.yaml`: `presence: true`

### 执行前快照
```sql
-- 记录mv_presence_1s_any视图的初始状态
SELECT COUNT(*) as before_count_1s_any FROM mv_presence_1s_any;
```

### 预期行为
1. 从fact_measurements统计每个设备每秒的数据点数量
2. 判断存在性（有数据即存在）
3. 更新metrics_presence_per_second_device表（按设备统计）
4. mv_presence_1s_any视图自动反映最新数据（基于metrics_presence_per_second_device）

### 存在性定义验证
```sql
-- 理解存在性定义：查看代码逻辑或查询示例数据

-- 定义1：有数据即存在（最宽松）
-- 定义2：数据有效即存在（排除NULL、异常值）
-- 定义3：关键指标存在即存在（只统计特定指标）

-- 通过查询验证当前系统使用的定义
SELECT
    d.name as device_name,
    m.metric_key,
    COUNT(*) as data_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
WHERE f.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:01:00+00'
GROUP BY d.name, m.metric_key
ORDER BY d.name, m.metric_key;
```

### 执行后验证

#### 一级验证：数据存在性
```sql
-- 验证mv_presence_1s_any视图有数据
SELECT COUNT(*) as after_count_1s_any FROM mv_presence_1s_any;

-- 验证每个设备的存在性记录
SELECT
    d.name as device_name,
    COUNT(*) as total_records
FROM mv_presence_1s_any p
JOIN dim_devices d ON p.device_id = d.id
GROUP BY d.name
ORDER BY d.name;

-- 验证时间范围
SELECT
    MIN(ts_bucket) as earliest,
    MAX(ts_bucket) as latest,
    COUNT(DISTINCT ts_bucket) as unique_timestamps
FROM mv_presence_1s_any;
```

#### 二级验证：存在性比例合理性
```sql
-- 验证每个设备的存在性比例
SELECT
    d.name as device_name,
    COUNT(*) as total_seconds,
    SUM(CASE WHEN p.is_present THEN 1 ELSE 0 END) as present_seconds,
    ROUND(100.0 * SUM(CASE WHEN p.is_present THEN 1 ELSE 0 END) / COUNT(*), 2) as presence_percentage
FROM mv_presence_1s_any p
JOIN dim_devices d ON p.device_id = d.id
GROUP BY d.name
ORDER BY d.name;

-- 存在性比例应接近100%，除非有数据缺失
-- 如果存在性 < 95%，需要分析原因
```

#### 三级验证：统计准确性（抽样验证）
```sql
-- 抽样验证：选择特定时间段，手动统计存在性

-- 示例：验证1#加压泵在某个时间段的存在性
-- 1. 手动统计该时间段每秒的数据点数量
SELECT
    f.ts_bucket,
    COUNT(*) as data_points
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
WHERE d.name LIKE '%1#加压泵%'
AND f.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:05:00+00'
GROUP BY f.ts_bucket
ORDER BY f.ts_bucket;

-- 2. 获取系统统计的存在性
SELECT
    p.ts_bucket,
    p.is_present,
    p.metric_count
FROM mv_presence_1s_any p
JOIN dim_devices d ON p.device_id = d.id
WHERE d.name LIKE '%1#加压泵%'
AND p.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:05:00+00'
ORDER BY p.ts_bucket;

-- 3. 对比手动统计与系统统计
--    如果某秒有数据点，is_present应为true
--    如果某秒无数据点，is_present应为false
--    metric_count应等于手动统计的data_points
```

#### 深度分析：mv_presence_1s_any 数据结构
```sql
-- mv_presence_1s_any: 按设备+指标统计（展开available_metrics数组）
SELECT
    d.name as device_name,
    m.metric_key,
    COUNT(*) as record_count
FROM mv_presence_1s_any p
JOIN dim_devices d ON p.device_id = d.id
JOIN dim_metric_config m ON p.metric_id = m.id
GROUP BY d.name, m.metric_key
ORDER BY d.name, m.metric_key
LIMIT 20;

-- 验证逻辑：
-- mv_presence_1s_any视图基于metrics_presence_per_second_device表
-- 通过CROSS JOIN LATERAL unnest(available_metrics)展开数组
-- 每个设备每秒每个可用指标都有一条记录
```

#### 数据缺失分析
```sql
-- 如果存在性 < 100%，分析缺失原因

-- 原因1：CSV文件中该时间段无数据
-- 原因2：数据导入时被拒绝（staging_rejects）
-- 原因3：数据合并时被过滤（不符合有效范围）

-- 查询缺失时间段
SELECT
    ts_bucket
FROM generate_series(
    '2025-05-31 18:00:00+00'::timestamptz,
    '2025-05-31 19:59:59+00'::timestamptz,
    '1 second'::interval
) ts_bucket
WHERE ts_bucket NOT IN (
    SELECT DISTINCT ts_bucket
    FROM mv_presence_1s_any p
    JOIN dim_devices d ON p.device_id = d.id
    WHERE d.name LIKE '%1#加压泵%'
    AND p.is_present = true
)
ORDER BY ts_bucket
LIMIT 20;

-- 检查这些缺失时间段在fact_measurements中是否有数据
SELECT
    f.ts_bucket,
    COUNT(*) as data_count
FROM fact_measurements f
JOIN dim_devices d ON f.device_id = d.id
WHERE d.name LIKE '%1#加压泵%'
AND f.ts_bucket IN (
    -- 上面查询到的缺失时间段
    '2025-05-31 18:00:05+00',
    '2025-05-31 18:00:10+00'
)
GROUP BY f.ts_bucket;
```

### 日志验证
```
[流程-开始] [存在性统计]
[进度] presence 开始
presence.init: devices_count=XX
presence.process: device_id=X, present_points=XXX, absent_points=XXX
...
presence.complete: total_points=XXX
[流程-完成] [存在性统计]
```

### 代码逻辑验证
- 函数路径: `app/services/presence/compute.py::compute_presence()`
- 关键步骤:
  1. 从fact_measurements按设备、时间桶统计数据点
  2. 判断存在性（有数据即存在）
  3. 插入结果到metrics_presence_per_second_device（按设备统计）
  4. mv_presence_1s_any视图自动反映最新数据
  5. 返回统计信息

### 通过标准
- [ ] mv_presence_1s_any视图有数据
- [ ] 每个设备都有存在性记录
- [ ] 存在性比例合理（应接近100%，除非有数据缺失）
- [ ] 抽样验证统计准确性，3-5个样本全部正确
- [ ] mv_presence_1s_any的逻辑正确（基于metrics_presence_per_second_device）
- [ ] 如有数据缺失，有合理的原因分析
- [ ] 耗时 < 120秒

---

## 📊 阶段9: quality_mark (质量标注)

### 测试目标
验证质量标注功能（默认关闭，可选测试）

### 配置要求
- `configs/merge.yaml`: `quality_mark: true` (需手动开启)

### 预期行为
1. 读取metric_quality_rules表获取质量规则
2. 从fact_measurements读取数据
3. 应用质量规则，标注质量码
4. 更新fact_measurements.quality_codes字段

### 验证方法
（如果启用此阶段，验证方法与上述阶段类似）

---

---

## 🎯 完整流程测试

### 测试命令
```bash
python -m app.cli.main run-all \
  --summary-json temp/run_all_summary.json
```

### 预期总耗时
- 阶段1: 10-30秒
- 阶段2: < 5秒
- 阶段3: 30-120秒
- 阶段4: 30-60秒
- 阶段5: 30-60秒
- 阶段6-9: 60-300秒(可选)
- **总计**: 3-10分钟

### 最终验证
```sql
-- 验证完整数据链路
SELECT 
    s.name as station_name,
    d.name as device_name,
    m.metric_key,
    COUNT(*) as measurement_count
FROM fact_measurements f
JOIN dim_stations s ON f.station_id = s.id
JOIN dim_devices d ON f.device_id = d.id
JOIN dim_metric_config m ON f.metric_id = m.id
GROUP BY s.name, d.name, m.metric_key
ORDER BY s.name, d.name, m.metric_key
LIMIT 20;
```

### 执行摘要验证
检查 `temp/run_all_summary.json` 文件内容:
```json
{
  "prepare_dim_stage1": {"duration_s": 15.23},
  "create_staging": {"duration_s": 2.45},
  "ingest_copy": {"duration_s": 85.67},
  "merge_fact": {"duration_s": 45.89},
  "prepare_dim_stage2": {"duration_s": 38.12},
  "calculation": {"duration_s": 120.45},
  "device_running": {"duration_s": 45.23},
  "presence": {"duration_s": 30.12},
  "total_duration_s": 383.16
}
```

---

**文档结束**

