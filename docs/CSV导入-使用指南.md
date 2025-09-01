# CSV导入-使用指南（方案A + auto/direct/staging 三态）

本指南介绍如何使用 CLI 完成从 data_mapping.json 到并发 COPY 导入 staging，再到数据库端集合式合并（时间对齐/去重/UPSERT）的完整流程；并说明日志位置、背压策略、常见问题与排障。

## 目录

- 快速开始
- 目录结构与约束
- CLI 命令大全（中文说明+示例）
- 日志与观测
- 背压与性能
- 常见问题与排障

## 快速开始

1. 准备映射与 CSV（标准 schema：configs/data_mapping.v2.json）
1. 检查映射（只读）
   - `python -m app.cli.main check-mapping configs/data_mapping.v2.json`
1. 维表与建表
   - `python -m app.cli.main prepare-dim configs/data_mapping.v2.json`
   - `python -m app.cli.main create-staging`
1. 导入与合并（auto 模式按阈值自动选择 direct/staging）
   - direct（小量）示例：`python -m app.cli.main ingest-direct configs/data_mapping.v2.json`
   - staging（大吞吐）示例：`python -m app.cli.main ingest-copy configs/data_mapping.v2.json`
   - 合并：`python -m app.cli.main merge-fact --window-start 2025-08-11T00:00:00Z --window-end 2025-08-18T00:00:00Z`
1. 一键（auto 决策）
   - `python -m app.cli.main run-all configs/data_mapping.v2.json --window-start ...Z --window-end ...Z`

## 目录结构与约束

- 环境限制：当前开发环境数据库禁止修改任何表（结构/数据），仅允许变更函数/视图/触发器等对象；导入/合并等涉及写表的命令需在专用测试库运行；本地开发库仅做 dry-run/只读校验
- base_dir 固定 `data/`，禁用路径自适配（globFallback）。
- CSV 列名强制：TagName, DataTime, DataValue（大小写兼容；支持列头含 BOM）。
- 不修改现有数据库表结构（仅 staging_raw / staging_rejects 允许创建）。
- 不修改 data_mapping.v2.json 与 data/ 内容（工具不做任何写入）。
- 导入模式：默认 auto（阈值 total_mb=50/per_file_mb=10/max_file_count=20）；满足阈值倾向 direct，否则 staging；可用 `--ingest-mode` 强制。

## 命令参考（中文说明 + 示例 + 排障）

- version（打印版本/存活）

  - 用途：快速检查 CLI 是否可用
  - 示例：`python -m app.cli.main version --log-run --log-dir logs/runs/demo`
  - 排障：无

- db-ping（免密连接测试）

  - 用途：验证本机 .pgpass/pg_hba 免密是否生效
  - 示例：`python -m app.cli.main db-ping --verbose`
  - 输出（--verbose）：`host=... db=... user=p***s tz=Asia/Shanghai ver=16.3`
  - 常见错误：主机/库名/用户名不一致；.pgpass 权限不正确

- check-mapping（只读一致性检查）

  - 用途：检查映射内 CSV 路径与结构，并生成建议。支持导出与聚类统计
  - 示例：`python -m app.cli.main check-mapping config/data_mapping.json --out mapping_report.json --log-run`
  - 输出：JSON 报告（base_dir、总路径数、带 data/ 前缀数、存在数、逐条建议、group_by\_\* 聚类统计）
  - 选项：`--show-all` 展示所有聚类项（默认仅显示有缺陷项）
  - 常见错误：路径在 data/ 外或含 data/ 前缀；结构缺失 name/key/files

- prepare-dim（准备维表与映射）

  - 用途：根据 data_mapping.json 插入/更新 dim_stations、dim_devices、dim_metric_config、dim_mapping_items
  - 示例：`python -m app.cli.main prepare-dim config/data_mapping.json --log-run --log-dir logs/runs/pd01`
  - 常见错误：JSON 结构缺失 name/key/files；数据库连接失败 → 用 db-ping 验证

- create-staging（创建 staging 表）

  - 用途：创建/幂等 staging_raw 与 staging_rejects（UNLOGGED）
  - 示例：`python -m app.cli.main create-staging --log-run --log-dir logs/runs/st01`
  - 常见错误：数据库连接失败

- ingest-direct（多线程直写导入）

  - 用途：小量 CSV 直接对齐后调用 safe_upsert_measurement(\_local) UPSERT 落库（直写）
  - 示例：`python -m app.cli.main ingest-direct config/data_mapping.v2.json --log-run --log-dir logs/runs/id01`
  - 约束：适合 bytes_total ≤ 50MB、单文件 ≤ 10MB、文件数 ≤ 20 的场景
  - 常见错误：列头缺失/时间格式错误 → 落 staging_rejects 或错误日志

- ingest-copy（并发 COPY 导入）

  - 用途：将 CSV 流式写入 staging_raw，解析失败写 staging_rejects
  - 示例：`python -m app.cli.main ingest-copy config/data_mapping.v2.json --log-run --log-dir logs/runs/ic01`
  - 约束：严格 data/+相对路径，找不到文件即失败；列名不符整文件拒绝
  - 常见错误：路径带 data/ 前缀、文件不存在、CSV 列头缺失（注意 DataTime 拼写大小写，允许 DataTime/Datatime；列头可能带 BOM）

- merge-fact（集合式合并：时间对齐/去重/UPSERT）

  - 用途：将窗口内数据 JOIN 维度 → tz（优先站点 tz，否则 Asia/Shanghai）→ UTC → 秒对齐 → 去重 → UPSERT 入事实表

  - 示例：`python -m app.cli.main merge-fact --window-start 2025-08-11T00:00:00Z --window-end 2025-08-18T00:00:00Z --log-run --log-dir logs/runs/mf01`

  - 输出：sql.ndjson 中包含 db.exec.started/succeeded/failed；失败场景含 EXPLAIN 摘要（截断）

  - 分段合并：可在 configs/logging.yaml 中设置 merge.segmented.enabled=true 与 granularity（如 1h）

  - 常见错误：时间格式不正确；维表缺失导致 JOIN 失败

- run-all（一键流程）

  - 用途：prepare-dim → create-staging → ingest-copy → merge-fact
  - 示例：`python -m app.cli.main run-all config/data_mapping.json --window-start ...Z --window-end ...Z --log-run`
  - 输出：logs/runs/YYYYMMDD/\<job_id>/ 下 env.json、summary.json、app/error/sql/perf.ndjson
  - 运行快照：env.json（含 args_summary/config_snapshot/sources/ts/run_id/run_dir）

- admin-clear-db（危险）

  - 用途：清空 public 架构所有表数据（TRUNCATE + RESTART IDENTITY + CASCADE）
  - 示例：`python -m app.cli.main admin-clear-db --log-run --log-dir logs/runs/clear01`
  - 风险：不可恢复，仅限 DEV 环境

## 迁移到标准 schema（stations/devices/metrics/files）

- 标准 schema 结构

  - 顶层：`stations[]`
  - 站点：`{ name, tz? , devices[] }`
  - 设备：`{ name, type? , metrics[] }`
  - 指标：`{ key, files[] }`
  - 说明：files 为相对 `data/` 的路径，禁止包含 `data/` 前缀

- 旧 schema（字典型）示例（片段）

  - 顶层：站点名；第二层：设备名；设备下混合了元数据与指标文件数组
  - 例如：
    { "二期供水泵房": { "二期供水泵房1#泵": { "type": \["pump"\], "frequency": \["设备1_频率.csv"\], ... } } }

- 标准 schema（数组型）示例（片段）

  - 例如：
    {
    "stations": \[
    {
    "name": "二期供水泵房",
    "devices": \[
    {
    "name": "二期供水泵房1#泵",
    "type": "pump",
    "metrics": \[
    { "key": "frequency",  "files": \["设备1_频率.csv"\] },
    { "key": "voltage_a",  "files": \["设备1_A相电压.csv"\] }
    \]
    }
    \]
    }
    \]
    }

### 一键转换脚本（只读，不改原文件）

- 路径：`scripts/tools/convert_mapping_to_standard.py`
- 用法：
  - `python scripts/tools/convert_mapping_to_standard.py config/data_mapping.json configs/data_mapping.v2.json`
- 规则：
  - 仅把"值为字符串数组"的键识别为指标 files
  - 设备的 `type`（字符串或数组的首个字符串）会保留到标准 schema 的 device.type
  - 其余元数据键（如 pump_type）暂不参与导入流程
- 输出统计：会打印站点数、指标条目数、文件数，便于快速核对

### 转换后验证

- 只读检查并导出报告：
  - `python -m app.cli.main check-mapping configs/data_mapping.v2.json --out mapping_report_v2.json --log-run`
- 期望：
  - `schema.errors` 为空；`total_paths` 与 `exists_under_strict_rule` 为正且匹配实际文件数

### 使用 v2 文件跑整链

- 维表与映射：
  - `python -m app.cli.main prepare-dim configs/data_mapping.v2.json --log-run --log-dir logs/runs/pd01`
- 创建 staging：
  - `python -m app.cli.main create-staging --log-run --log-dir logs/runs/st01`
- COPY 导入：
  - `python -m app.cli.main ingest-copy configs/data_mapping.v2.json --log-run --log-dir logs/runs/ic01`
- 合并：
  - `python -m app.cli.main merge-fact --window-start ...Z --window-end ...Z --log-run --log-dir logs/runs/mf01`
- 一键：
  - `python -m app.cli.main run-all configs/data_mapping.v2.json --window-start ...Z --window-end ...Z --log-run`

### 常见问题

- 仍然报"缺少 stations 列表"：
  - 使用了旧 schema；请改用 v2 文件路径
- 路径不存在或含 data/ 前缀：
  - files 必须是相对 `data/` 的路径，且不包含 `data/` 前缀；确保文件真实存在

## 日志与观测

- 默认格式：JSON，可在 configs/logging.yaml 设置 format=text 切换为文本易读模式

- 路由：by_run（默认，多流）或 by_module（按模块写 logs/modules/<module>.log）

- 位置：`logs/runs/YYYYMMDD/<job_id>/`

- app.\*：常规事件（task.begin/progress/end、task.summary 等）

- error.\*：错误/告警（ingest.path.resolve not_found、列头缺失等）

  - sources 标注：DEFAULT|YAML|ENV|CLI；CLI 覆盖 DB DSN 需显式 --allow-cli-dsn 才生效

- sql.\*：SQL 明细（按配置 sql.text=summary|normalized|full；失败含 EXPLAIN 摘要）

- perf.\*：吞吐/批耗时/背压（p95_batch_ms、fail_rate、adjustment）

- summary.json：copy_total_ms、merge_total_ms、backpressure_events.enter/exit、tz_fallback_count

- env.json：参数与配置快照（本项目默认不脱敏，详见 logging.yaml；日志 JSON 对 datetime/Path 等类型已使用 default=str 兼容序列化）

## 导入配置项（csv/batch/error_handling/performance）

- 位置：configs/ingest.yaml（ENV 覆盖支持：INGEST\_\*）
- csv：delimiter/encoding/quote_char/escape_char/allow_bom
- batch：size/max_memory_mb/parallel_batches（与 commit_interval 协同设置：commit_interval 为全局初始批；batch.size 为每文件/每次 COPY 实际批，未接入处保留 commit_interval）
- error_handling：max_errors_per_file/error_threshold_percent/continue_on_error（达到阈值中止当前文件并计入失败）
- performance：read/write_buffer_size/connection_pool_size

详见《docs/配置说明.md》。

## 数据库连接池

项目实现了基于 psycopg 的数据库连接池管理，以提高数据库操作性能并减少连接建立/关闭的开销。

### 特性

- **连接复用**：避免频繁建立和关闭数据库连接
- **并发支持**：支持多线程并发访问
- **健康检查**：自动检测和处理连接超时、断开等问题
- **统计监控**：提供连接使用统计信息用于性能分析
- **自动恢复**：连接异常时自动重连

### 配置

- **min_size**：最小连接数，默认为 1
- **max_size**：最大连接数，默认为 10
- **max_inactive_connection_lifetime**：非活跃连接生存时间，默认为 3600 秒

### 使用

连接池在 CLI 程序启动时自动初始化，通过 `app.adapters.db.init_database()` 函数完成。在数据库操作中，优先使用连接池获取连接，未初始化时回退到直连模式。

### 日志事件

连接池相关操作会生成以下日志事件：

- `pool.initialized`：连接池初始化完成
- `pool.connection.created`：创建新连接
- `pool.connection.acquired`：获取连接成功
- `pool.connection.create_failed`：创建连接失败
- `pool.closed`：连接池关闭

## 背压与性能

- 触发阈值：p95_batch_ms > 2000ms 或 fail_rate > 1%
- 动作序列：shrink_batch(50%) → shrink_workers → recover
- 配置项：
  - ingest.commit_interval：初始批大小（行）
  - ingest.workers：线程数（当前版本以单连接 COPY 为主，后续开并发）
  - ingest.p95_window：计算 p95 时的滑动窗口批次数（默认 20）

## 常见问题与排障

- 文件找不到
  - 原因：路径不在 data/ 下或映射中包含 data/ 前缀
  - 处理：使用 check-mapping 报告修复建议；不启用路径自适配
- 列头不匹配
  - 原因：缺少 TagName/DataTime/DataValue
  - 处理：修复 CSV 列后重试；失败行会落 staging_rejects
- 合并时间格式错误
  - 原因：传入了 `...Z` 字符串；已在代码中进行规范化
- tz 缺失
  - 行为：使用默认 Asia/Shanghai 兜底，并在 summary 与 sql/perf 中可见

## 附录：数据与时间

- 合并：`ts_utc = to_timestamp(DataTime,'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE tz`
- 秒级对齐：`ts_bucket = date_trunc('second', ts_utc)`
- 窗口：`[start, end)`，可使用 UTC ISO 周界（周一 00:00:00 UTC）
