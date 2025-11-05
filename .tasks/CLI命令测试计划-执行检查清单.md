# CLI命令测试计划 - 执行检查清单

**文档版本**: v1.0  
**创建日期**: 2025-11-02  
**关联文档**: CLI命令测试计划-20251102.md

---

## 📋 检查清单说明

本文档提供按顺序执行的详细检查清单，每个检查项都是原子性的、可执行的。

**执行原则**:
1. 严格按照顺序执行
2. 每个检查项完成后标记 ✅
3. 如果检查项失败，标记 ❌ 并记录原因
4. 每个阶段完成后请求用户确认
5. 禁止跳过任何检查项

---

## 🔧 阶段0: 环境准备

### 检查项 0.1: 验证Python环境
- [ ] 执行命令: `python --version`
- [ ] 验证Python版本 >= 3.11
- [ ] 记录Python版本号

### 检查项 0.2: 验证项目依赖
- [ ] 执行命令: `python -m app.cli.main version`
- [ ] 验证输出: `ingest-cli ok`
- [ ] 验证退出码: 0

### 检查项 0.3: 验证数据库连接
- [ ] 执行命令: `python -m app.cli.main db-ping --verbose`
- [ ] 验证输出包含: `"status": "ok"`
- [ ] 验证数据库名称: `pump_station_optimization`
- [ ] 记录数据库版本

### 检查项 0.4: 验证配置文件
- [ ] 检查文件存在: `configs/database.yaml`
- [ ] 检查文件存在: `configs/merge.yaml`
- [ ] 检查文件存在: `configs/data_mapping.v2.json`
- [ ] 检查文件存在: `configs/system.yaml`
- [ ] 检查文件存在: `configs/ingest.yaml`

### 检查项 0.5: 验证CSV数据文件
- [ ] 执行命令: `python -m app.cli.main check-mapping configs/data_mapping.v2.json`
- [ ] 验证所有CSV文件存在
- [ ] 记录CSV文件总数

### 检查项 0.6: 记录数据库初始状态
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements;`
- [ ] 记录初始行数: ___________
- [ ] 执行SQL: `SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements;`
- [ ] 记录时间范围: ___________ ~ ___________

---

## 🧪 阶段1: 基础命令测试 (P4优先级)

### 检查项 1.1: 测试 version 命令
- [ ] 执行命令: `python -m app.cli.main version`
- [ ] 验证输出: `ingest-cli ok`
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证无ERROR日志

### 检查项 1.2: 测试 db-ping 命令
- [ ] 执行命令: `python -m app.cli.main db-ping --verbose`
- [ ] 验证JSON输出格式正确
- [ ] 验证status字段为"ok"
- [ ] 检查日志文件: `logs/db_pool.log`

### 检查项 1.3: 测试 check-mapping 命令
- [ ] 执行命令: `python -m app.cli.main check-mapping configs/data_mapping.v2.json`
- [ ] 验证所有CSV文件检查通过
- [ ] 验证映射格式正确
- [ ] 记录文件总数: ___________

---

## 🔄 阶段2: 核心流程命令测试 (P1优先级)

### 检查项 2.1: 测试 prepare-dim stage1
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_stations;`
- [ ] 记录执行前行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_devices;`
- [ ] 记录执行前行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_metric_config;`
- [ ] 记录执行前行数: ___________

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 1`
- [ ] 记录开始时间: ___________
- [ ] 等待命令完成
- [ ] 记录结束时间: ___________
- [ ] 计算耗时: ___________ 秒

**日志验证**:
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[流程-开始] [维表准备]`
- [ ] 验证包含: `[prepare-dim] 阶段1：维度表重建`
- [ ] 验证包含: `[流程-完成] [维表准备]`
- [ ] 验证无ERROR日志

**数据库验证**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_stations;`
- [ ] 验证行数 = 3
- [ ] 执行SQL: `SELECT id, name FROM dim_stations ORDER BY id;`
- [ ] 验证站点名称正确
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_devices;`
- [ ] 验证行数 >= 15
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_metric_config;`
- [ ] 验证行数 >= 40

**代码逻辑验证**:
- [ ] 查看源代码: `app/services/ingest/prepare_dim/__init__.py`
- [ ] 确认阶段1逻辑: 备份→清空→重建→恢复→重建配置
- [ ] 验证数据库状态符合代码逻辑

### 检查项 2.2: 测试 create-staging
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_raw;`
- [ ] 记录执行前行数: ___________

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main create-staging`
- [ ] 记录开始时间: ___________
- [ ] 等待命令完成
- [ ] 记录结束时间: ___________

**日志验证**:
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[流程-开始] [创建staging表]`
- [ ] 验证包含: `[流程-完成] [创建staging表]`
- [ ] 验证无ERROR日志

**数据库验证**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_raw;`
- [ ] 验证行数 = 0
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_rejects;`
- [ ] 验证行数 = 0

### 检查项 2.3: 测试 ingest-copy
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_raw;`
- [ ] 验证行数 = 0

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main ingest-copy configs/data_mapping.v2.json`
- [ ] 记录开始时间: ___________
- [ ] 等待命令完成(预计30-120秒)
- [ ] 记录结束时间: ___________
- [ ] 计算耗时: ___________ 秒

**日志验证**:
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[流程-开始] [CSV导入]`
- [ ] 验证包含: `ingest.load.begin`
- [ ] 验证包含: `ingest.load.end`
- [ ] 验证包含: `[流程-完成] [CSV导入]`
- [ ] 验证无严重ERROR日志

**数据库验证**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_raw;`
- [ ] 记录导入行数: ___________
- [ ] 验证行数 > 100,000
- [ ] 执行SQL: `SELECT MIN(DataTime), MAX(DataTime) FROM staging_raw;`
- [ ] 记录时间范围: ___________ ~ ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_rejects;`
- [ ] 记录拒绝行数: ___________
- [ ] 执行SQL: `SELECT error_msg, COUNT(*) FROM staging_rejects GROUP BY error_msg;`
- [ ] 分析拒绝原因

**代码逻辑验证**:
- [ ] 查看源代码: `app/services/ingest/copy_workers.py`
- [ ] 确认导入逻辑: 读取CSV→验证→COPY→记录拒绝
- [ ] 验证导入数据量符合CSV文件总行数

### 检查项 2.4: 测试 merge-fact
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements;`
- [ ] 记录执行前行数: ___________
- [ ] 执行SQL: `SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements;`
- [ ] 记录执行前时间范围: ___________ ~ ___________

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main merge-fact --use-staging-time-range`
- [ ] 记录开始时间: ___________
- [ ] 等待命令完成(预计30-60秒)
- [ ] 记录结束时间: ___________
- [ ] 计算耗时: ___________ 秒

**日志验证**:
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[流程-开始] [数据合并]`
- [ ] 验证包含: `[进度] 窗口探测开始`
- [ ] 验证包含: `[进度] 窗口确定`
- [ ] 验证包含: `align.merge.window`
- [ ] 验证包含: `[流程-完成] [数据合并]`
- [ ] 验证无ERROR日志

**数据库验证**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements;`
- [ ] 记录执行后行数: ___________
- [ ] 计算新增行数: ___________ (应接近staging_raw行数)
- [ ] 执行SQL: `SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements;`
- [ ] 记录执行后时间范围: ___________ ~ ___________
- [ ] 执行SQL: `SELECT quality_status, COUNT(*) FROM fact_measurements GROUP BY quality_status;`
- [ ] 验证新数据quality_status = 0

**代码逻辑验证**:
- [ ] 查看源代码: `app/services/ingest/merge_service.py`
- [ ] 确认合并逻辑: 窗口探测→时区转换→去重→UPSERT
- [ ] 验证新增数据量符合预期(考虑去重)

### 检查项 2.5: 测试 prepare-dim stage2
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_quality_rules;`
- [ ] 记录执行前行数: ___________

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 2`
- [ ] 记录开始时间: ___________
- [ ] 等待命令完成(预计30-60秒)
- [ ] 记录结束时间: ___________

**日志验证**:
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[prepare-dim] 阶段2：生成规则表`
- [ ] 验证无ERROR日志

**数据库验证**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_quality_rules;`
- [ ] 验证行数 > 0
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_rule_auto_baseline;`
- [ ] 验证行数 > 0
- [ ] 执行SQL: `SELECT COUNT(*) FROM device_running_thresholds;`
- [ ] 验证行数 > 0

---

## 🎯 阶段3: run-all完整流程测试 (P0优先级)

### 检查项 3.1: 准备run-all测试环境
- [ ] 读取配置文件: `configs/merge.yaml`
- [ ] 确认 `run_all.reset_db: false`
- [ ] 确认 `run_all.reset_logs: true`
- [ ] 确认各阶段开关状态:
  - [ ] prepare_dim: ___________
  - [ ] create_staging: ___________
  - [ ] ingest_copy: ___________
  - [ ] merge_fact: ___________
  - [ ] prepare_dim_stage2: ___________
  - [ ] enable_calculation: ___________
  - [ ] device_running: ___________
  - [ ] presence: ___________
  - [ ] quality_mark: ___________

### 检查项 3.2: 执行run-all命令
**执行前快照**:
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements;`
- [ ] 记录执行前行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_stations;`
- [ ] 记录dim_stations行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM staging_raw;`
- [ ] 记录staging_raw行数: ___________
- [ ] 备份日志目录(可选)

**执行命令**:
- [ ] 执行命令: `python -m app.cli.main run-all --summary-json temp/run_all_summary.json`
- [ ] 记录开始时间: ___________
- [ ] 监控命令执行(预计3-10分钟)
- [ ] 等待命令完成
- [ ] 记录结束时间: ___________
- [ ] 计算总耗时: ___________ 秒

### 检查项 3.3: 验证run-all日志（一级验证）
- [ ] 检查日志文件: `logs/app.log`
- [ ] 验证包含: `[进度] prepare-dim stage1 开始`
- [ ] 验证包含: `[进度] prepare-dim stage1 完成`
- [ ] 验证包含: `[进度] create-staging 开始`
- [ ] 验证包含: `[进度] create-staging 完成`
- [ ] 验证包含: `[进度] ingest-copy 开始`
- [ ] 验证包含: `[进度] ingest-copy 完成`
- [ ] 验证包含: `[进度] merge-fact 开始`
- [ ] 验证包含: `[进度] merge-fact 完成`
- [ ] 验证包含: `[进度] prepare-dim stage2 开始`
- [ ] 验证包含: `[进度] prepare-dim stage2 完成`
- [ ] 验证包含: `[进度] calculation 开始` (如启用)
- [ ] 验证包含: `[进度] calculation 完成` (如启用)
- [ ] 验证包含: `[进度] device_running 开始` (如启用)
- [ ] 验证包含: `[进度] device_running 完成` (如启用)
- [ ] 验证包含: `[进度] presence 开始` (如启用)
- [ ] 验证包含: `[进度] presence 完成` (如启用)
- [ ] 验证无严重ERROR日志
- [ ] 记录WARNING数量: ___________
- [ ] 分析WARNING原因: ___________

### 检查项 3.4: 验证run-all数据库状态（二级验证）

#### 维度表验证
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_stations;`
- [ ] 记录执行后行数: ___________ (应为3)
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_devices;`
- [ ] 记录执行后行数: ___________ (应为约20)
- [ ] 执行SQL: `SELECT COUNT(*) FROM dim_metric_config;`
- [ ] 记录执行后行数: ___________ (应为约50)

#### 事实表验证
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements;`
- [ ] 记录执行后行数: ___________
- [ ] 计算新增行数: ___________ (执行后 - 执行前)
- [ ] 验证数据量增加
- [ ] 执行SQL: `SELECT MIN(ts_bucket), MAX(ts_bucket) FROM fact_measurements;`
- [ ] 记录时间范围: ___________ ~ ___________
- [ ] 执行SQL: `SELECT station_id, device_id, COUNT(*) FROM fact_measurements GROUP BY station_id, device_id ORDER BY station_id, device_id;`
- [ ] 验证数据分布合理

#### 规则表验证
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_quality_rules;`
- [ ] 记录行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_rule_auto_baseline;`
- [ ] 记录行数: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM device_running_thresholds;`
- [ ] 记录行数: ___________

#### 计算指标验证（如启用calculation）
- [ ] 执行SQL: `SELECT COUNT(*) FROM fact_measurements WHERE source_hint LIKE '%calculation_%';`
- [ ] 记录计算指标数量: ___________
- [ ] 执行SQL: `SELECT m.metric_key, COUNT(*) FROM fact_measurements f JOIN dim_metric_config m ON f.metric_id = m.id WHERE f.source_hint LIKE '%calculation_%' GROUP BY m.metric_key;`
- [ ] 验证10个计算指标都有数据

#### 运行状态验证（如启用device_running）
- [ ] 执行SQL: `SELECT COUNT(*) FROM mv_device_running_1s;`
- [ ] 记录行数: ___________
- [ ] 执行SQL: `SELECT device_id, SUM(CASE WHEN is_running THEN 1 ELSE 0 END) as running_count FROM mv_device_running_1s GROUP BY device_id;`
- [ ] 验证每个设备都有运行状态数据

#### 存在性验证（如启用presence）
- [ ] 执行SQL: `SELECT COUNT(*) FROM mv_presence_1s_any;`
- [ ] 记录行数: ___________
- [ ] 执行SQL: `SELECT device_id, ROUND(100.0 * SUM(CASE WHEN is_present THEN 1 ELSE 0 END) / COUNT(*), 2) as presence_pct FROM mv_presence_1s_any GROUP BY device_id;`
- [ ] 验证存在性比例合理

### 检查项 3.5: 验证run-all执行摘要
- [ ] 检查文件存在: `temp/run_all_summary.json`
- [ ] 读取JSON内容
- [ ] 验证包含各阶段耗时:
  - [ ] prepare_dim_stage1.duration_s: ___________
  - [ ] create_staging.duration_s: ___________
  - [ ] ingest_copy.duration_s: ___________
  - [ ] merge_fact.duration_s: ___________
  - [ ] prepare_dim_stage2.duration_s: ___________
  - [ ] calculation.duration_s: ___________ (如启用)
  - [ ] device_running.duration_s: ___________ (如启用)
  - [ ] presence.duration_s: ___________ (如启用)
- [ ] 验证total_duration_s字段: ___________
- [ ] 验证总耗时合理（3-10分钟）

### 检查项 3.6: 深度验证 - prepare-dim stage1（三级验证）

#### 备份验证
- [ ] 执行SQL: `SELECT tablename FROM pg_tables WHERE tablename LIKE '%_backup_%' ORDER BY tablename;`
- [ ] 记录备份表数量: ___________
- [ ] 验证备份表数量 >= 21
- [ ] 抽样验证3个备份表的行数与原表一致

#### 数据质量验证
- [ ] 执行SQL: `SELECT id, name FROM dim_stations ORDER BY id;`
- [ ] 验证站点名称与映射文件一致
- [ ] 执行SQL: `SELECT s.name, d.name, d.type FROM dim_devices d JOIN dim_stations s ON d.station_id = s.id ORDER BY s.name, d.name LIMIT 20;`
- [ ] 验证设备名称与映射文件一致
- [ ] 执行SQL: `SELECT metric_key, unit, valid_min, valid_max FROM dim_metric_config WHERE unit IS NULL OR unit = '';`
- [ ] 验证无单位缺失的指标

### 检查项 3.7: 深度验证 - prepare-dim stage2（三级验证）

#### 阈值合理性验证
- [ ] 执行SQL: `SELECT d.name, t.threshold_on, t.threshold_off FROM device_running_thresholds t JOIN dim_devices d ON t.device_id = d.id WHERE t.threshold_on <= t.threshold_off OR t.threshold_on <= 0;`
- [ ] 验证无不合理的阈值配置
- [ ] 记录不合理阈值数量: ___________

#### 基线合理性验证
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_rule_auto_baseline WHERE baseline_mean IS NULL OR baseline_std IS NULL;`
- [ ] 记录基线缺失数量: ___________
- [ ] 执行SQL: `SELECT COUNT(*) FROM metric_rule_auto_baseline WHERE baseline_std < 0 OR (baseline_mean < 0 AND metric_id NOT IN (SELECT id FROM dim_metric_config WHERE metric_key LIKE '%温度%'));`
- [ ] 记录不合理基线数量: ___________

#### 抽样验证基线准确性
- [ ] 选择1#加压泵的"有功功率"指标
- [ ] 执行SQL获取系统基线: `SELECT baseline_mean, baseline_std FROM metric_rule_auto_baseline b JOIN dim_devices d ON b.device_id = d.id JOIN dim_metric_config m ON b.metric_id = m.id WHERE d.name LIKE '%1#加压泵%' AND m.metric_key = '有功功率';`
- [ ] 记录系统基线: mean=___________, std=___________
- [ ] 执行SQL手动计算: `SELECT AVG(value), STDDEV(value) FROM fact_measurements f JOIN dim_devices d ON f.device_id = d.id JOIN dim_metric_config m ON f.metric_id = m.id WHERE d.name LIKE '%1#加压泵%' AND m.metric_key = '有功功率';`
- [ ] 记录手动计算: mean=___________, std=___________
- [ ] 计算误差: ___________% (应 < 1%)

### 检查项 3.8: 深度验证 - calculation（三级验证，如启用）

#### 数据存在性验证
- [ ] 执行SQL: `SELECT m.metric_key, COUNT(*) FROM fact_measurements f JOIN dim_metric_config m ON f.metric_id = m.id WHERE f.source_hint LIKE '%calculation_%' GROUP BY m.metric_key ORDER BY m.metric_key;`
- [ ] 验证10个计算指标都有数据:
  - [ ] pump_flow_rate: ___________
  - [ ] pump_head: ___________
  - [ ] pump_efficiency: ___________
  - [ ] pump_power: ___________
  - [ ] pump_shaft_power: ___________
  - [ ] motor_efficiency: ___________
  - [ ] system_efficiency: ___________
  - [ ] specific_energy: ___________
  - [ ] unit_energy_consumption: ___________
  - [ ] energy_cost: ___________

#### 数值合理性验证
- [ ] 执行SQL: `SELECT MIN(value), MAX(value), COUNT(CASE WHEN value < 0 OR value > 100 THEN 1 END) FROM fact_measurements f JOIN dim_metric_config m ON f.metric_id = m.id WHERE m.metric_key = 'pump_efficiency' AND f.source_hint LIKE '%calculation_%';`
- [ ] 验证泵效率在0-100%范围内
- [ ] 记录超范围数量: ___________

#### 抽样验证计算准确性
- [ ] 选择1#加压泵在某个时间点验证泵效率计算
- [ ] 执行SQL获取输入数据: `SELECT m.metric_key, f.value FROM fact_measurements f JOIN dim_devices d ON f.device_id = d.id JOIN dim_metric_config m ON f.metric_id = m.id WHERE d.name LIKE '%1#加压泵%' AND f.ts_bucket = '2025-05-31 18:00:00+00' AND m.metric_key IN ('pump_flow_rate', 'pump_head', 'pump_power') AND f.source_hint NOT LIKE '%calculation_%';`
- [ ] 记录输入: flow=___________, head=___________, power=___________
- [ ] 执行SQL获取计算结果: `SELECT value FROM fact_measurements f JOIN dim_devices d ON f.device_id = d.id JOIN dim_metric_config m ON f.metric_id = m.id WHERE d.name LIKE '%1#加压泵%' AND f.ts_bucket = '2025-05-31 18:00:00+00' AND m.metric_key = 'pump_efficiency' AND f.source_hint LIKE '%calculation_%';`
- [ ] 记录系统计算: ___________
- [ ] 手动计算: efficiency = (flow * head * 9.81 * 1000) / (power * 3600) * 100 = ___________
- [ ] 计算误差: ___________% (应 < 1%)

### 检查项 3.9: 深度验证 - device_running（三级验证，如启用）

#### 状态分布验证
- [ ] 执行SQL: `SELECT d.name, SUM(CASE WHEN r.is_running THEN 1 ELSE 0 END) as running, SUM(CASE WHEN NOT r.is_running THEN 1 ELSE 0 END) as stopped, ROUND(100.0 * SUM(CASE WHEN r.is_running THEN 1 ELSE 0 END) / COUNT(*), 2) as running_pct FROM mv_device_running_1s r JOIN dim_devices d ON r.device_id = d.id GROUP BY d.name ORDER BY d.name;`
- [ ] 记录每个设备的运行比例
- [ ] 验证运行比例合理

#### 状态转换频率验证
- [ ] 执行SQL: `WITH state_changes AS (SELECT device_id, ts_bucket, is_running, LAG(is_running) OVER (PARTITION BY device_id ORDER BY ts_bucket) as prev_state FROM mv_device_running_1s) SELECT d.name, COUNT(*) as total, SUM(CASE WHEN is_running != prev_state THEN 1 ELSE 0 END) as changes, ROUND(100.0 * SUM(CASE WHEN is_running != prev_state THEN 1 ELSE 0 END) / COUNT(*), 2) as change_pct FROM state_changes sc JOIN dim_devices d ON sc.device_id = d.id WHERE prev_state IS NOT NULL GROUP BY d.name ORDER BY d.name;`
- [ ] 记录状态转换频率
- [ ] 验证转换频率 < 10%

#### 抽样验证状态判断准确性
- [ ] 选择1#加压泵在某个时间点验证状态判断
- [ ] 执行SQL获取阈值: `SELECT threshold_on, threshold_off FROM device_running_thresholds t JOIN dim_devices d ON t.device_id = d.id WHERE d.name LIKE '%1#加压泵%';`
- [ ] 记录阈值: on=___________, off=___________
- [ ] 执行SQL获取功率值: `SELECT value FROM fact_measurements f JOIN dim_devices d ON f.device_id = d.id JOIN dim_metric_config m ON f.metric_id = m.id WHERE d.name LIKE '%1#加压泵%' AND f.ts_bucket = '2025-05-31 18:00:00+00' AND m.metric_key = '有功功率';`
- [ ] 记录功率: ___________
- [ ] 执行SQL获取系统判断: `SELECT is_running FROM mv_device_running_1s r JOIN dim_devices d ON r.device_id = d.id WHERE d.name LIKE '%1#加压泵%' AND r.ts_bucket = '2025-05-31 18:00:00+00';`
- [ ] 记录系统判断: ___________
- [ ] 手动判断: 如果功率 >= threshold_on → 运行，如果功率 <= threshold_off → 停止
- [ ] 验证系统判断与手动判断一致

### 检查项 3.10: 深度验证 - presence（三级验证，如启用）

#### 存在性比例验证
- [ ] 执行SQL: `SELECT d.name, COUNT(*) as total, SUM(CASE WHEN p.is_present THEN 1 ELSE 0 END) as present, ROUND(100.0 * SUM(CASE WHEN p.is_present THEN 1 ELSE 0 END) / COUNT(*), 2) as presence_pct FROM mv_presence_1s_any p JOIN dim_devices d ON p.device_id = d.id GROUP BY d.name ORDER BY d.name;`
- [ ] 记录每个设备的存在性比例
- [ ] 验证存在性比例 >= 95%

#### 抽样验证存在性统计准确性
- [ ] 选择1#加压泵在某个时间段验证存在性
- [ ] 执行SQL手动统计: `SELECT ts_bucket, COUNT(*) as data_points FROM fact_measurements f JOIN dim_devices d ON f.device_id = d.id WHERE d.name LIKE '%1#加压泵%' AND f.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:00:10+00' GROUP BY ts_bucket ORDER BY ts_bucket;`
- [ ] 记录手动统计结果
- [ ] 执行SQL获取系统统计: `SELECT ts_bucket, is_present, metric_count FROM mv_presence_1s_any p JOIN dim_devices d ON p.device_id = d.id WHERE d.name LIKE '%1#加压泵%' AND p.ts_bucket BETWEEN '2025-05-31 18:00:00+00' AND '2025-05-31 18:00:10+00' ORDER BY ts_bucket;`
- [ ] 记录系统统计结果
- [ ] 验证手动统计与系统统计一致

---

## 📊 阶段4: 计算功能命令测试 (P2优先级)

### 检查项 4.1-4.5: 测试calc:*命令
详细检查项将在执行阶段补充

---

## 🔍 阶段5: 质量控制命令测试 (P3优先级)

### 检查项 5.1-5.4: 测试quality:*命令
详细检查项将在执行阶段补充

---

## 📝 阶段6: 数据处理命令测试 (P5优先级)

### 检查项 6.1-6.3: 测试数据处理命令
详细检查项将在执行阶段补充

---

## ✅ 最终验证

### 检查项 7.1: 生成测试报告
- [ ] 汇总所有测试结果
- [ ] 统计通过/失败数量
- [ ] 记录所有发现的问题
- [ ] 创建测试报告文档

### 检查项 7.2: 清理测试环境
- [ ] 清理临时文件
- [ ] 备份测试日志
- [ ] 恢复数据库状态(如需要)

---

**检查清单结束**

**执行状态**: 待执行  
**预计总耗时**: 30-60分钟  
**下一步**: 进入执行阶段，按顺序执行所有检查项

