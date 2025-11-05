# CLI指令使用手册

**版本**: v1.0  
**更新日期**: 2025-10-20  
**适用环境**: 开发环境、生产环境

---

## 📋 目录

1. [核心流程指令](#核心流程指令)
2. [数据处理指令](#数据处理指令)
3. [质量控制指令](#质量控制指令)
4. [规则管理指令](#规则管理指令)
5. [计算功能指令](#计算功能指令)
6. [管理工具指令](#管理工具指令)
7. [执行顺序说明](#执行顺序说明)

---

## 核心流程指令

### 1. version

**功能描述**: 打印版本信息和存活检查

**完整语法**:
```bash
python -m app.cli.main version
```

**影响的数据库表**: 无

**执行顺序**: 独立指令，可随时执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main version
# 输出: ingest-cli ok
```

**注意事项**:
- 用于验证CLI环境是否正常
- 不需要数据库连接

---

### 2. prepare-dim

**功能描述**: 准备维表与映射（两阶段执行）

**完整语法**:
```bash
python -m app.cli.main prepare-dim <mapping_file> [--stage <1|2>]
```

**影响的数据库表**:
- **阶段1**（merge-fact前）:
  - `dim_stations` - 泵站维度表
  - `dim_devices` - 设备维度表
  - `dim_metric_config` - 指标配置维度表
  - `calculation_method_registry` - 计算方法注册表
  - `calculation_parameters` - 计算参数表
  - `device_rated_params` - 设备额定参数表
  - `dim_device_capabilities` - 设备能力表
  - `metric_calculation_order` - 指标计算顺序表
- **阶段2**（merge-fact后）:
  - `metric_rule_auto_baseline` - 自动基线表
  - `metric_rule_auto_baseline_shadow` - 自动基线影子表
  - `device_running_thresholds` - 运行阈值表
  - `device_running_thresholds_shadow` - 运行阈值影子表
  - `metric_quality_rules` - 质量规则表
  - `metric_quality_rules_shadow` - 质量规则影子表

**执行顺序**:
- 阶段1：在 `merge-fact` 之前执行
- 阶段2：在 `merge-fact` 之后执行

**参数说明**:
- `mapping_file`: data_mapping.json 文件路径（相对仓库根）
- `--stage`: 可选，执行阶段（1=阶段1，2=阶段2，不指定=完整流程）

**示例用法**:
```bash
# 只执行阶段1（重建维度表）
python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 1

# 只执行阶段2（生成规则表）
python -m app.cli.main prepare-dim configs/data_mapping.v2.json --stage 2

# 执行完整流程（两个阶段）
python -m app.cli.main prepare-dim configs/data_mapping.v2.json
```

**注意事项**:
- **前置条件**: 
  - 阶段1：数据库已创建所有表结构
  - 阶段2：`fact_measurements` 表必须有数据
- **副作用**: 
  - 阶段1会清空并重建维度表和配置表
  - 阶段2会清空并重新生成规则表
- **常见错误**: 
  - JSON结构缺失 name/key/files
  - 数据库连接失败
  - 阶段2执行时 fact_measurements 表为空

---

### 3. create-staging

**功能描述**: 创建/幂等 staging_raw 与 staging_rejects 表（UNLOGGED）

**完整语法**:
```bash
python -m app.cli.main create-staging
```

**影响的数据库表**:
- `staging_raw` - 导入暂存原始数据表
- `staging_rejects` - 导入拒收记录表

**执行顺序**: 在 `ingest-copy` 之前执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main create-staging
```

**注意事项**:
- **前置条件**: 数据库连接正常
- **副作用**: 如果表已存在，会清空表数据
- **性能**: 使用 UNLOGGED 表，提升导入性能但不保证持久性
- **常见错误**: 数据库连接失败

---

### 4. ingest-copy

**功能描述**: 并发 COPY 导入 CSV 到 staging_raw

**完整语法**:
```bash
python -m app.cli.main ingest-copy <mapping_file>
```

**影响的数据库表**:
- `staging_raw` - 导入暂存原始数据表
- `staging_rejects` - 导入拒收记录表

**执行顺序**: 在 `create-staging` 之后、`merge-fact` 之前执行

**参数说明**:
- `mapping_file`: data_mapping.json 文件路径

**示例用法**:
```bash
python -m app.cli.main ingest-copy configs/data_mapping.v2.json
```

**注意事项**:
- **前置条件**: 
  - `create-staging` 已执行
  - CSV文件存在且格式正确
- **副作用**: 向 staging_raw 表插入大量数据
- **性能**: 使用并发COPY，速度快
- **常见错误**: 
  - 路径带 data/ 前缀
  - 文件不存在
  - CSV列头缺失

---

### 5. merge-fact

**功能描述**: 集合式合并：tz→UTC→秒级对齐→去重→UPSERT

**完整语法**:
```bash
python -m app.cli.main merge-fact --window-start <start_time> --window-end <end_time>
```

**影响的数据库表**:
- `fact_measurements` - 时序事实表（主要）
- `staging_raw` - 读取数据源

**执行顺序**: 在 `ingest-copy` 之后、`prepare-dim --stage 2` 之前执行

**参数说明**:
- `--window-start`: 起始时间（ISO8601格式，如 '2025-02-28 00:00:00+08'）
- `--window-end`: 结束时间（ISO8601格式）

**示例用法**:
```bash
python -m app.cli.main merge-fact \
  --window-start '2025-02-28 00:00:00+08' \
  --window-end '2025-02-28 23:59:59+08'
```

**注意事项**:
- **前置条件**: 
  - `staging_raw` 表有数据
  - 时间格式正确
- **副作用**: 向 fact_measurements 表插入/更新大量数据
- **时间处理**: 
  - 输入支持 ISO8601（可带时区）
  - 未带时区按系统默认时区解析
  - 内部统一转换为 UTC
  - 对外展示统一为 +08 格式
- **常见错误**: 时间格式不正确

---

### 6. run-all

**功能描述**: 一键执行完整流程

**完整语法**:
```bash
python -m app.cli.main run-all [mapping_file] [options]
```

**影响的数据库表**: 所有表（根据配置文件 `configs/merge.yaml` 决定）

**执行顺序**: 自动按依赖顺序执行所有步骤

**参数说明**:
- `mapping_file`: data_mapping.json 文件路径（默认: configs/data_mapping.v2.json）
- `--use-staging-time-range/--no-use-staging-time-range`: 自动探测staging时间范围（默认: true）
- `--window-start`: 起始时间（ISO8601）
- `--window-end`: 结束时间（ISO8601）
- `--summary-json`: 将执行摘要写入JSON文件
- `--with-device-running`: 合并后追加设备运行状态落地
- `--with-presence`: 合并后按窗口执行 presence:compute
- `--device-id`: 可选，限定设备ID
- `--quality-codes`: 仅执行该子集质量码
- `--quality-diag-level`: 质量诊断级别（off|brief|full）
- `--quality-parallel`: 质量标注设备并行度（默认: 4）

**示例用法**:
```bash
# 使用默认配置执行完整流程
python -m app.cli.main run-all

# 指定时间窗口
python -m app.cli.main run-all \
  --no-use-staging-time-range \
  --window-start '2025-02-28 00:00:00+08' \
  --window-end '2025-02-28 23:59:59+08'

# 保存执行摘要
python -m app.cli.main run-all --summary-json temp/run_all_summary.json
```

**注意事项**:
- **前置条件**: 
  - 数据库已创建所有表结构
  - CSV文件存在
  - 配置文件 `configs/merge.yaml` 正确
- **副作用**: 
  - 可能清空日志目录（根据配置）
  - 可能清空数据库（根据配置）
  - 执行所有配置的流程步骤
- **配置控制**: 通过 `configs/merge.yaml` 控制执行哪些步骤
- **执行流程**（默认）:
  1. prepare-dim stage1
  2. create-staging
  3. ingest-copy
  4. merge-fact
  5. prepare-dim stage2
  6. device_running（可选）
  7. calculation（可选）
  8. presence（可选）
  9. quality_mark（可选）

---

## 数据处理指令

### 7. data-report

**功能描述**: 生成数据质量报表（覆盖/越界/拒绝统计）

**完整语法**:
```bash
python -m app.cli.main data-report --window-start <start> --window-end <end> [options]
```

**影响的数据库表**: 
- 读取 `fact_measurements`
- 读取 `staging_rejects`

**执行顺序**: 在 `merge-fact` 之后执行

**参数说明**:
- `--window-start`: 起始时间（ISO8601）
- `--window-end`: 结束时间（ISO8601）
- `--expected-interval`: 期望采样间隔（秒），默认1
- `--top-k`: 各榜单TopN数量，默认100
- `--group-by`: 直方图分组维度（metric|device|station|source|batch），默认metric

**示例用法**:
```bash
python -m app.cli.main data-report \
  --window-start '2025-02-28 00:00:00+08' \
  --window-end '2025-02-28 23:59:59+08' \
  --expected-interval 1 \
  --top-k 50 \
  --group-by device
```

**注意事项**:
- **前置条件**: fact_measurements 表有数据
- **输出**: JSON格式的数据质量报告
- **用途**: 数据质量分析、覆盖率统计、异常检测

---

### 8. presence:compute

**功能描述**: 统计每秒×站×设备的已有/需要计算指标名

**完整语法**:
```bash
python -m app.cli.main presence:compute [options]
```

**影响的数据库表**:
- `metrics_presence_per_second_device` - 存在性统计表
- `mv_presence_1s` - 存在性物化视图

**执行顺序**: 在 `merge-fact` 之后执行

**参数说明**:
- `--station-name`: 限定站点名称
- `--station-id`: 按站点ID过滤
- `--device-id`: 按设备ID过滤
- `--start`: 起始时间（ISO8601）
- `--end`: 结束时间（ISO8601）
- `--batch-days`: 按天分片大小，默认1
- `--rolling-days`: 增量时回退刷新近N天，默认7
- `--dry-run`: 仅显示计划，不执行写入

**示例用法**:
```bash
# 全量计算
python -m app.cli.main presence:compute

# 指定时间范围
python -m app.cli.main presence:compute \
  --start '2025-02-28 00:00:00+08' \
  --end '2025-02-28 23:59:59+08'

# 试运行
python -m app.cli.main presence:compute --dry-run
```

**注意事项**:
- **前置条件**: fact_measurements 表有数据
- **副作用**: 向 metrics_presence_per_second_device 表插入数据
- **增量模式**: 如果表已有数据，自动增量+滚动7天

---

### 9. missing-metrics:compute

**功能描述**: 批量计算缺失指标

**完整语法**:
```bash
python -m app.cli.main missing-metrics:compute [options]
```

**影响的数据库表**:
- `fact_measurements` - 写入计算结果（quality_status=1）

**执行顺序**: 在 `merge-fact` 和 `prepare-dim --stage 2` 之后执行

**参数说明**:
- `--start`: 起始时间（ISO8601，默认取fact表最早时间）
- `--end`: 结束时间（ISO8601，默认取fact表最晚时间）
- `--station-id`: 可选，限定站点ID
- `--device-id`: 可选，限定设备ID
- `--window-hours`: 时间分片粒度（小时），默认1
- `--concurrency`: 并发度（线程数），默认3
- `--dry-run/--no-dry-run`: 仅试运行，不写库
- `--filter-running/--no-filter-running`: 按运行态过滤，默认true
- `--filter-quality/--no-filter-quality`: 仅使用质量=0的原始数据，默认true
- `--limit-devices`: 限设备数量（排障用）
- `--limit-windows-per-device`: 每设备限窗口数（排障用）

**示例用法**:
```bash
# 全量计算
python -m app.cli.main missing-metrics:compute

# 指定时间范围和并发度
python -m app.cli.main missing-metrics:compute \
  --start '2025-02-28 00:00:00+08' \
  --end '2025-02-28 23:59:59+08' \
  --window-hours 2 \
  --concurrency 4

# 试运行
python -m app.cli.main missing-metrics:compute --dry-run
```

**注意事项**:
- **前置条件**: 
  - fact_measurements 表有原始数据
  - calculation_method_registry 表已初始化
  - calculation_parameters 表已初始化
- **副作用**: 向 fact_measurements 表插入计算结果
- **性能**: 使用并发计算，建议并发度≤连接池max
- **质量标记**: 计算结果的 quality_status=1

---

## 质量控制指令

### 10. baseline:auto:compute

**功能描述**: 计算并刷新自动基线

**完整语法**:
```bash
python -m app.cli.main baseline:auto:compute [options]
```

**影响的数据库表**:
- `metric_rule_auto_baseline` - 自动基线表（正式）
- `metric_rule_auto_baseline_shadow` - 自动基线影子表

**执行顺序**: 在 `merge-fact` 之后执行

**参数说明**:
- `--lookback-days`: 回溯天数，默认30
- `--station-id`: 可选，限定站点ID
- `--device-id`: 可选，限定设备ID
- `--method`: 基线算法（robust|stl），默认robust
- `--output`: 输出目标（table|shadow），默认table

**示例用法**:
```bash
# 使用默认参数计算基线
python -m app.cli.main baseline:auto:compute

# 指定回溯天数和算法
python -m app.cli.main baseline:auto:compute \
  --lookback-days 60 \
  --method stl

# 写入影子表
python -m app.cli.main baseline:auto:compute --output shadow
```

**注意事项**:
- **前置条件**: fact_measurements 表有足够的历史数据
- **副作用**: 清空并重新生成基线表
- **算法**: 
  - robust: 分位/MAD方法
  - stl: 趋势季节分解+残差稳健
- **数据要求**: 仅使用质量=0且稳态数据

---

### 11. quality:mark-window

**功能描述**: 在时间窗内执行首批质量标注规则

**完整语法**:
```bash
python -m app.cli.main quality:mark-window --start <start> --end <end> [options]
```

**影响的数据库表**:
- `fact_measurements` - 更新 quality_codes 字段

**执行顺序**: 在 `merge-fact` 和 `baseline:auto:compute` 之后执行

**参数说明**:
- `--start`: UTC起始时间（YYYY-MM-DDTHH:MM:SSZ）
- `--end`: UTC结束时间（YYYY-MM-DDTHH:MM:SSZ）
- `--station-id`: 可选，限定站点ID
- `--device-id`: 可选，限定设备ID

**示例用法**:
```bash
python -m app.cli.main quality:mark-window \
  --start '2025-02-28T00:00:00Z' \
  --end '2025-02-28T23:59:59Z'
```

**注意事项**:
- **前置条件**:
  - fact_measurements 表有数据
  - metric_rule_auto_baseline 表已生成
- **副作用**: 更新 fact_measurements 表的 quality_codes 字段
- **质量规则**: 越界/跳变/平台期/状态矛盾/功率因数/液位守恒

---

### 12. quality:full-pass

**功能描述**: 一键执行完整质量流程

**完整语法**:
```bash
python -m app.cli.main quality:full-pass --start <start> --end <end> [options]
```

**影响的数据库表**:
- `metric_rule_auto_baseline` - 自动基线表
- `fact_measurements` - 质量标注

**执行顺序**: 在 `merge-fact` 之后执行

**参数说明**:
- `--start`: UTC起始时间
- `--end`: UTC结束时间
- `--lookback-days`: 自动基线回溯天数，默认30
- `--station-id`: 可选，限定站点ID
- `--device-id`: 可选，限定设备ID

**示例用法**:
```bash
python -m app.cli.main quality:full-pass \
  --start '2025-02-28T00:00:00Z' \
  --end '2025-02-28T23:59:59Z' \
  --lookback-days 30
```

**注意事项**:
- **执行顺序**:
  1. device-phase:compute（生成相位）
  2. baseline:auto:compute（刷新自动基线）
  3. quality:mark-window（标注质量）
- **前置条件**: fact_measurements 表有足够的历史数据

---

## 规则管理指令

### 13. quality:codes:dist-window

**功能描述**: 按时间窗导出质量码分布

**完整语法**:
```bash
python -m app.cli.main quality:codes:dist-window --start <start> --end <end> [options]
```

**影响的数据库表**: 读取 `fact_measurements`

**执行顺序**: 在质量标注之后执行

**参数说明**:
- `--start`: 起始时间（ISO8601）
- `--end`: 结束时间（ISO8601）
- `--out-dir`: 输出目录，默认 reports/

**示例用法**:
```bash
python -m app.cli.main quality:codes:dist-window \
  --start '2025-02-28 00:00:00+08' \
  --end '2025-02-28 23:59:59+08' \
  --out-dir reports
```

**注意事项**:
- **输出格式**: JSON和CSV
- **用途**: 质量码分布分析

---

### 14. quality:codes:dist-recent

**功能描述**: 基于 quality_profile_log 的近期质量码命中分布

**完整语法**:
```bash
python -m app.cli.main quality:codes:dist-recent [options]
```

**影响的数据库表**: 读取 `quality_profile_log`

**执行顺序**: 独立指令

**参数说明**:
- `--hours-24/--no-hours-24`: 是否包含近24小时汇总，默认true
- `--days-7/--no-days-7`: 是否包含近7天汇总，默认true
- `--out-dir`: 输出目录，默认 reports/

**示例用法**:
```bash
python -m app.cli.main quality:codes:dist-recent \
  --hours-24 \
  --days-7 \
  --out-dir reports
```

**注意事项**:
- **输出格式**: JSON
- **用途**: 近期质量趋势分析

---

### 15. rules:diff:report

**功能描述**: 生成A（正式）与B（影子）的差异报告

**完整语法**:
```bash
python -m app.cli.main rules:diff:report [options]
```

**影响的数据库表**:
- 读取 `metric_rule_auto_baseline`
- 读取 `metric_rule_auto_baseline_shadow`

**执行顺序**: 在基线计算之后执行

**参数说明**:
- `--method`: 影子算法方法，默认 stl_residual
- `--version`: 影子版本标识，默认 vB_shadow
- `--out-dir`: 可选，将CSV详情写入该目录
- `--top-k`: TopK差异清单数量，默认20

**示例用法**:
```bash
python -m app.cli.main rules:diff:report \
  --method stl_residual \
  --version vB_shadow \
  --out-dir reports \
  --top-k 50
```

**注意事项**:
- **用途**: 对比正式表和影子表的差异
- **输出**: JSON格式的差异报告

---

## 计算功能指令

### 16. calc init-tables

**功能描述**: 初始化计算相关数据库表

**完整语法**:
```bash
python -m app.cli.main calc init-tables
```

**影响的数据库表**:
- `metric_calculation_order` - 指标计算顺序表
- `calculation_method_registry` - 计算方法注册表
- `calculation_parameters` - 计算参数表
- `calculation_validation_config` - 验证配置表
- `calculation_failures_log` - 计算失败日志表
- `calculation_performance_metrics` - 计算性能指标表

**执行顺序**: 在数据库初始化之后执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main calc init-tables
```

**注意事项**:
- **前置条件**: 数据库连接正常
- **副作用**: 创建计算相关表结构
- **SQL文件**: `scripts/sql/calculation/create_tables.sql`

---

### 17. calc init-methods

**功能描述**: 初始化计算方法注册表

**完整语法**:
```bash
python -m app.cli.main calc init-methods
```

**影响的数据库表**:
- `calculation_method_registry` - 计算方法注册表

**执行顺序**: 在 `calc init-tables` 之后执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main calc init-methods
```

**注意事项**:
- **前置条件**: calculation_method_registry 表已创建
- **副作用**: 插入27个计算方法
- **SQL文件**: `scripts/sql/calculation/init_methods.sql`
- **验证**: 执行后会显示每个指标的方法数量

---

### 18. calc init-params

**功能描述**: 初始化计算参数表

**完整语法**:
```bash
python -m app.cli.main calc init-params
```

**影响的数据库表**:
- `calculation_parameters` - 计算参数表

**执行顺序**: 在 `calc init-methods` 之后执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main calc init-params
```

**注意事项**:
- **前置条件**:
  - calculation_parameters 表已创建
  - calculation_method_registry 表已初始化
- **副作用**: 插入全局默认参数
- **SQL文件**: `scripts/sql/calculation/init_params.sql`
- **验证**: 执行后会显示录入的全局默认参数数量

---

### 19. calc init-device-params

**功能描述**: 初始化设备额定参数表

**完整语法**:
```bash
python -m app.cli.main calc init-device-params
```

**影响的数据库表**:
- `device_rated_params` - 设备额定参数表

**执行顺序**: 在 `prepare-dim --stage 1` 之后执行

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main calc init-device-params
```

**注意事项**:
- **前置条件**:
  - device_rated_params 表已创建
  - dim_devices 表已有数据
- **副作用**: 插入设备额定参数
- **SQL文件**: `scripts/migrations/20250829_seed_device_rated_params.sql`

---

### 20. calc missing-metrics

**功能描述**: 计算缺失指标（calc子命令版本）

**完整语法**:
```bash
python -m app.cli.main calc missing-metrics [options]
```

**影响的数据库表**:
- `fact_measurements` - 写入计算结果

**执行顺序**: 在 `merge-fact` 之后执行

**参数说明**: 与 `missing-metrics:compute` 相同

**示例用法**:
```bash
python -m app.cli.main calc missing-metrics \
  --start '2025-02-28 00:00:00+08' \
  --end '2025-02-28 23:59:59+08'
```

**注意事项**: 与 `missing-metrics:compute` 功能相同

---

## 管理工具指令

### 21. db-ping

**功能描述**: 免密连接测试

**完整语法**:
```bash
python -m app.cli.main db-ping [--verbose]
```

**影响的数据库表**: 无（只读）

**执行顺序**: 独立指令，可随时执行

**参数说明**:
- `--verbose`: 打印脱敏连接信息与数据库/时区信息

**示例用法**:
```bash
# 简单测试
python -m app.cli.main db-ping

# 详细信息
python -m app.cli.main db-ping --verbose
```

**注意事项**:
- **用途**: 验证数据库连接是否正常
- **输出**: JSON格式的连接信息
- **常见错误**:
  - .pgpass 未生效/权限不正确
  - host/db/user 与实际不符

---

### 22. check-mapping

**功能描述**: 只读一致性检查与路径建议

**完整语法**:
```bash
python -m app.cli.main check-mapping <mapping_file> [options]
```

**影响的数据库表**: 无（只读）

**执行顺序**: 独立指令，可随时执行

**参数说明**:
- `mapping_file`: data_mapping.json 文件路径
- `--out`: 将检查报告写入到该路径（JSON）
- `--show-all`: 展示全部检查结果（默认只展示缺陷项）

**示例用法**:
```bash
# 控制台输出
python -m app.cli.main check-mapping configs/data_mapping.v2.json

# 导出JSON
python -m app.cli.main check-mapping configs/data_mapping.v2.json \
  --out mapping_report.json

# 显示全部
python -m app.cli.main check-mapping configs/data_mapping.v2.json --show-all
```

**注意事项**:
- **检查项**:
  - 是否含 data/ 前缀
  - 文件是否存在
  - schema 必填项（stations/devices/metrics/files/key/name）
- **输出**: 仅输出建议，不修改文件
- **常见错误**:
  - 路径带 data/ 前缀
  - 文件不存在
  - 结构缺失 key/files/name

---

### 23. admin-clear-db

**功能描述**: 危险：清空 public 架构所有表数据

**完整语法**:
```bash
python -m app.cli.main admin-clear-db
```

**影响的数据库表**: 所有表（TRUNCATE + RESTART IDENTITY + CASCADE）

**执行顺序**: 独立指令，仅限开发环境

**参数说明**: 无参数

**示例用法**:
```bash
python -m app.cli.main admin-clear-db
```

**注意事项**:
- **⚠️ 危险操作**: 不可恢复
- **仅限DEV**: 确保连接到开发数据库
- **副作用**: 清空所有表数据并重置自增ID
- **用途**: 开发环境重置数据库

---

## 执行顺序说明

### 完整流程执行顺序

```
1. prepare-dim --stage 1
   ↓
2. create-staging
   ↓
3. ingest-copy
   ↓
4. merge-fact
   ↓
5. prepare-dim --stage 2
   ↓
6. device_running（可选）
   ↓
7. calculation（可选）
   ↓
8. presence:compute（可选）
   ↓
9. quality:mark-window（可选）
```

### run-all 自动执行流程

`run-all` 指令会根据 `configs/merge.yaml` 配置自动执行以下步骤：

```yaml
run_all:
  prepare_dim: true              # 阶段1：重建维度表
  create_staging: true           # 创建staging表
  ingest_copy: true              # CSV导入
  merge_fact: true               # 合并到fact_measurements
  prepare_dim_stage2: true       # 阶段2：生成规则表
  device_running: true           # 设备运行状态计算
  enable_calculation: true       # 缺失指标计算
  presence: true                 # 存在性统计
  quality_mark: false            # 质量标注（默认关闭）
```

### 独立指令

以下指令可以独立执行，不依赖其他指令：

- `version` - 版本检查
- `db-ping` - 数据库连接测试
- `check-mapping` - 映射文件检查
- `quality:codes:dist-recent` - 近期质量码分布
- `admin-clear-db` - 清空数据库（危险）

---

## 附录

### 时间格式说明

所有时间参数支持 ISO8601 格式：

```bash
# 带时区
'2025-02-28 00:00:00+08'
'2025-02-28T00:00:00+08:00'
'2025-02-28T00:00:00Z'  # UTC

# 不带时区（按系统默认时区解析）
'2025-02-28 00:00:00'
'2025-02-28T00:00:00'
```

### 配置文件说明

- **`configs/merge.yaml`**: run-all 流程配置
- **`configs/logging.yaml`**: 日志配置
- **`configs/database.yaml`**: 数据库配置
- **`configs/data_mapping.v2.json`**: 数据映射配置

### 日志文件位置

- **`logs/app.log`**: 应用日志
- **`logs/error.log`**: 错误日志
- **`logs/sql.log`**: SQL日志
- **`logs/anomaly_diagnosis.log`**: 异常诊断日志
- **`logs/db_pool.log`**: 数据库连接池日志

---

**文档结束**

