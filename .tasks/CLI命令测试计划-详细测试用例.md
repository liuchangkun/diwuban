# CLI命令测试计划 - 详细测试用例

**文档版本**: v1.0  
**创建日期**: 2025-11-02  
**关联文档**: CLI命令测试计划-20251102.md

---

## 📋 测试用例索引

### P0 - 关键命令 (1个)
1. [run-all](#test-run-all) - 一键执行完整流程

### P1 - 核心流程命令 (5个)
2. [version](#test-version) - 版本检查
3. [prepare-dim](#test-prepare-dim) - 准备维表
4. [create-staging](#test-create-staging) - 创建staging表
5. [ingest-copy](#test-ingest-copy) - CSV导入
6. [merge-fact](#test-merge-fact) - 合并到fact表

### P2 - 计算功能命令 (5个)
7. [calc:init-tables](#test-calc-init-tables) - 初始化计算表
8. [calc:init-methods](#test-calc-init-methods) - 初始化计算方法
9. [calc:init-params](#test-calc-init-params) - 初始化计算参数
10. [calc:init-device-params](#test-calc-init-device-params) - 初始化设备参数
11. [calc:missing-metrics](#test-calc-missing-metrics) - 计算缺失指标

### P3 - 质量控制命令 (4个)
12. [quality:codes:dist-window](#test-quality-codes-dist-window) - 质量码分布(窗口)
13. [quality:codes:dist-recent](#test-quality-codes-dist-recent) - 质量码分布(近期)
14. [quality:mark-window](#test-quality-mark-window) - 质量标注
15. [quality:full-pass](#test-quality-full-pass) - 完整质量流程

### P4 - 管理工具命令 (3个)
16. [db-ping](#test-db-ping) - 数据库连接测试
17. [check-mapping](#test-check-mapping) - 映射文件检查
18. [admin-clear-db](#test-admin-clear-db) - 清空数据库(危险)

### P5 - 数据处理命令 (3个)
19. [data-report](#test-data-report) - 数据质量报表
20. [presence:compute](#test-presence-compute) - 存在性统计
21. [missing-metrics:compute](#test-missing-metrics-compute) - 缺失指标计算

### P6 - 其他命令 (2个)
22. [baseline:auto:compute](#test-baseline-auto-compute) - 自动基线计算
23. [rules:diff:report](#test-rules-diff-report) - 规则差异报告

---

## <a id="test-version"></a>测试用例 #1: version

### 基本信息
- **命令**: `python -m app.cli.main version`
- **优先级**: P1
- **预计耗时**: < 1秒
- **依赖**: 无

### 测试目标
验证CLI环境是否正常，命令是否可执行

### 前置条件
- Python环境正常
- 项目依赖已安装

### 执行步骤
1. 打开终端
2. 切换到项目根目录
3. 执行命令: `python -m app.cli.main version`

### 预期结果
- 命令成功执行
- 输出: `ingest-cli ok`
- 退出码: 0

### 验证方法

#### 1. 日志分析
- 检查 `logs/app.log` 是否有ERROR日志
- 检查是否有数据库连接池初始化日志

#### 2. 数据库验证
- 不适用(此命令不操作数据库)

#### 3. 代码逻辑验证
- 函数路径: `app/cli/main.py::version()`
- 预期行为: 调用 `initialize_app()` 初始化日志和数据库，然后输出 "ingest-cli ok"

### 通过标准
- [ ] 命令成功执行，无异常
- [ ] 输出正确
- [ ] 无ERROR日志

---

## <a id="test-db-ping"></a>测试用例 #2: db-ping

### 基本信息
- **命令**: `python -m app.cli.main db-ping --verbose`
- **优先级**: P4
- **预计耗时**: < 2秒
- **依赖**: 数据库连接配置正确

### 测试目标
验证数据库连接是否正常

### 前置条件
- `configs/database.yaml` 配置正确
- 数据库服务运行中
- 网络连接正常

### 执行步骤
1. 执行命令: `python -m app.cli.main db-ping --verbose`

### 预期结果
- 命令成功执行
- 输出JSON格式的连接信息:
  ```json
  {
    "status": "ok",
    "database": "pump_station_optimization",
    "user": "postgres",
    "timezone": "Asia/Shanghai",
    "version": "PostgreSQL ..."
  }
  ```
- 退出码: 0

### 验证方法

#### 1. 日志分析
- 检查 `logs/db_pool.log` 是否有连接成功日志
- 检查是否有连接错误日志

#### 2. 数据库验证
```sql
-- 验证连接是否建立
SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'pump_station_optimization';
```

#### 3. 代码逻辑验证
- 函数路径: `app/services/admin/db_ping.py::run_db_ping()`
- 预期行为: 建立数据库连接，查询数据库信息，返回JSON结果

### 通过标准
- [ ] 命令成功执行
- [ ] 输出包含正确的数据库信息
- [ ] 无连接错误

---

## <a id="test-check-mapping"></a>测试用例 #3: check-mapping

### 基本信息
- **命令**: `python -m app.cli.main check-mapping configs/data_mapping.v2.json`
- **优先级**: P4
- **预计耗时**: < 5秒
- **依赖**: 映射文件存在

### 测试目标
验证映射文件格式正确，CSV文件存在

### 前置条件
- `configs/data_mapping.v2.json` 存在
- CSV文件在 `data/` 目录

### 执行步骤
1. 执行命令: `python -m app.cli.main check-mapping configs/data_mapping.v2.json`

### 预期结果
- 命令成功执行
- 输出映射文件检查结果
- 列出所有CSV文件的存在性
- 退出码: 0

### 验证方法

#### 1. 日志分析
- 检查是否有文件不存在的WARNING
- 检查是否有格式错误的ERROR

#### 2. 数据库验证
- 不适用

#### 3. 代码逻辑验证
- 函数路径: `app/services/ingest/check_mapping.py`
- 预期行为: 解析JSON，检查文件存在性，输出检查结果

### 通过标准
- [ ] 命令成功执行
- [ ] 所有CSV文件存在
- [ ] 映射格式正确

---

## <a id="test-prepare-dim"></a>测试用例 #4: prepare-dim

### 基本信息
- **命令**: `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 1`
- **优先级**: P1
- **预计耗时**: 10-30秒
- **依赖**: 数据库连接，映射文件

### 测试目标
验证维表准备功能，包括阶段1和阶段2

### 前置条件
- 数据库连接正常
- `configs/data_mapping.v2.json` 存在
- 数据库表结构已创建

### 测试场景

#### 场景1: 阶段1 - 重建维度表
**执行步骤**:
1. 记录执行前的表行数
2. 执行命令: `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 1`
3. 记录执行后的表行数

**预期结果**:
- 命令成功执行
- 输出JSON格式的执行摘要
- `dim_stations` 表有数据(3个站点)
- `dim_devices` 表有数据(约20个设备)
- `dim_metric_config` 表有数据(约50个指标)

**验证SQL**:
```sql
-- 验证站点数据
SELECT COUNT(*) FROM dim_stations;
SELECT * FROM dim_stations ORDER BY id;

-- 验证设备数据
SELECT COUNT(*) FROM dim_devices;
SELECT station_id, COUNT(*) FROM dim_devices GROUP BY station_id;

-- 验证指标配置
SELECT COUNT(*) FROM dim_metric_config;
SELECT metric_key FROM dim_metric_config ORDER BY id LIMIT 10;
```

#### 场景2: 阶段2 - 生成规则表
**前置条件**: fact_measurements 表有数据

**执行步骤**:
1. 确认 fact_measurements 表有数据
2. 执行命令: `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 2`
3. 检查规则表是否生成

**预期结果**:
- 命令成功执行
- `metric_quality_rules` 表有数据
- `metric_rule_auto_baseline` 表有数据
- `device_running_thresholds` 表有数据

**验证SQL**:
```sql
-- 验证质量规则
SELECT COUNT(*) FROM metric_quality_rules;

-- 验证自动基线
SELECT COUNT(*) FROM metric_rule_auto_baseline;

-- 验证运行阈值
SELECT COUNT(*) FROM device_running_thresholds;
```

### 验证方法

#### 1. 日志分析
- 检查 `logs/app.log` 中的流程日志
- 关键日志模式:
  ```
  [流程-开始] [维表准备]
  [prepare-dim] 阶段1：维度表重建
  [prepare-dim] [1/5] 备份21个表...
  [prepare-dim] [2/5] 清空非备份表...
  [prepare-dim] [3/5] 重建维度表...
  [prepare-dim] [4/5] 恢复手动配置表...
  [prepare-dim] [5/5] 重建基础配置表...
  [流程-完成] [维表准备]
  ```

#### 2. 数据库验证
- 执行上述验证SQL
- 对比执行前后的行数变化
- 验证数据内容是否符合映射文件

#### 3. 代码逻辑验证
- 函数路径: `app/services/ingest/prepare_dim/__init__.py::prepare_dim()`
- 阶段1逻辑:
  1. 备份21个表
  2. 清空非备份表
  3. 从映射文件重建 dim_stations, dim_devices, dim_metric_config
  4. 恢复手动配置表
  5. 重建基础配置表
- 阶段2逻辑:
  1. 清空规则表
  2. 调用存储过程生成规则
  3. 生成映射表

### 通过标准
- [ ] 命令成功执行，无异常
- [ ] 维度表数据正确
- [ ] 规则表数据生成(阶段2)
- [ ] 日志无ERROR
- [ ] 执行摘要JSON格式正确

---

## <a id="test-create-staging"></a>测试用例 #5: create-staging

### 基本信息
- **命令**: `python -m app.cli.main create-staging`
- **优先级**: P1
- **预计耗时**: < 5秒
- **依赖**: 数据库连接

### 测试目标
验证staging表创建功能

### 前置条件
- 数据库连接正常

### 执行步骤
1. 执行命令: `python -m app.cli.main create-staging`

### 预期结果
- 命令成功执行
- `staging_raw` 表存在且为空
- `staging_rejects` 表存在且为空

### 验证SQL
```sql
-- 验证表存在
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'staging_raw'
);

SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'staging_rejects'
);

-- 验证表为空
SELECT COUNT(*) FROM staging_raw;
SELECT COUNT(*) FROM staging_rejects;
```

### 验证方法

#### 1. 日志分析
- 检查 `logs/app.log` 中的流程日志
- 关键日志: `[流程-开始] [创建staging表]`, `[流程-完成] [创建staging表]`

#### 2. 数据库验证
- 执行上述验证SQL
- 确认表存在且为空

#### 3. 代码逻辑验证
- 函数路径: `app/services/ingest/create_staging.py::create_staging()`
- 预期行为: 调用 `create_staging_if_not_exists()` 创建表，如果表已存在则清空

### 通过标准
- [ ] 命令成功执行
- [ ] staging_raw 表存在且为空
- [ ] staging_rejects 表存在且为空
- [ ] 无ERROR日志

---

## <a id="test-ingest-copy"></a>测试用例 #6: ingest-copy

### 基本信息
- **命令**: `python -m app.cli.main ingest-copy configs/data_mapping.v2.json`
- **优先级**: P1
- **预计耗时**: 30-120秒
- **依赖**: staging表存在，CSV文件存在

### 测试目标
验证CSV导入功能

### 前置条件
- staging_raw 表存在
- CSV文件在 `data/` 目录
- `configs/data_mapping.v2.json` 正确

### 执行步骤
1. 执行 `create-staging` 清空staging表
2. 记录执行前的 staging_raw 行数(应为0)
3. 执行命令: `python -m app.cli.main ingest-copy configs/data_mapping.v2.json`
4. 记录执行后的 staging_raw 行数

### 预期结果
- 命令成功执行
- staging_raw 表有数据(预计数十万行)
- 输出统计信息:
  ```
  copy done: {
    'files_total': 256,
    'files_succeeded': 256,
    'files_failed': 0,
    'rows_read': ...,
    'rows_loaded': ...,
    'rows_rejected': ...
  }
  ```

### 验证SQL
```sql
-- 验证导入数据量
SELECT COUNT(*) FROM staging_raw;

-- 验证数据分布
SELECT station_name, device_name, COUNT(*) 
FROM staging_raw 
GROUP BY station_name, device_name 
ORDER BY station_name, device_name;

-- 验证时间范围
SELECT MIN(DataTime), MAX(DataTime) FROM staging_raw;

-- 验证拒绝记录
SELECT COUNT(*) FROM staging_rejects;
SELECT error_msg, COUNT(*) FROM staging_rejects GROUP BY error_msg;
```

### 验证方法

#### 1. 日志分析
- 检查 `logs/app.log` 中的导入日志
- 关键日志模式:
  ```
  [流程-开始] [CSV导入]
  [进度] ingest-copy 开始
  [进度] 文件 X/256 完成
  [流程-完成] [CSV导入]
  ```
- 检查是否有文件导入失败的ERROR

#### 2. 数据库验证
- 执行上述验证SQL
- 验证导入数据量是否合理(应与CSV文件总行数接近)
- 验证数据分布是否符合映射文件
- 检查拒绝记录的原因

#### 3. 代码逻辑验证
- 函数路径: `app/services/ingest/copy_workers.py::copy_from_mapping()`
- 预期行为:
  1. 从映射文件读取CSV文件列表
  2. 并发读取CSV文件(6个worker)
  3. 使用COPY命令批量导入到staging_raw
  4. 记录拒绝行到staging_rejects
  5. 返回统计信息

### 通过标准
- [ ] 命令成功执行
- [ ] staging_raw 表有数据
- [ ] 导入成功率 > 95%
- [ ] 拒绝记录有合理的错误信息
- [ ] 无严重ERROR日志

---

## 测试用例 #7-23

由于篇幅限制，其余测试用例将在补充文档中详细说明。每个测试用例将包含:
- 基本信息(命令、优先级、耗时、依赖)
- 测试目标
- 前置条件
- 执行步骤
- 预期结果
- 验证方法(日志分析、数据库验证、代码逻辑验证)
- 通过标准

---

**文档结束**

