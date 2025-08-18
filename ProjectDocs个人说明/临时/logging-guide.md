## 日志功能规范（全面版）

本文档定义本项目的日志体系：完整、可观测、可审计、低开销，帮助用户清晰理解程序运行、快速定位问题、支持生产运维与合规审计。

### 适用范围

- 语言：Python 3.10+；框架：标准 `logging` + 适配器/队列。
- 场景：CLI、任务编排、导入/对齐/合并、特征计算、ML 流水线、服务化接口。
- 冲突裁决：以项目“最小改动、生产安全、幂等与对齐优先”原则为准。

### 目标与原则

- 结构化：日志默认 JSON；文本模式仅本地调试。
- 上下文完整：trace_id、job_id、站点/设备信息、文件/数据量、DB 指标。
- 可观测性：关键路径输出指标与分段耗时；提供 `summary` 汇总。
- 低干扰：采样与限流；异步队列落盘；失败回退同步保底。
- 合规脱敏：统一正则脱敏；禁止敏感信息泄漏。

### 等级与事件命名

- 等级：DEBUG/INFO/WARN/ERROR/CRITICAL；生产默认 INFO。
- 事件命名：`<domain>.<action>[.detail]`，如 `ingest.load.begin`、`align.merge.batch`、`task.summary`、`guardrail.stop`。

## 结构化字段规范

- 通用字段（所有日志必须具备）：
  - `ts`（ISO8601），`level`，`event`，`message`（可选简述）
  - 源信息：`logger`，`module`，`func`，`line`，`file`，`pid`，`thread`
- 关联上下文（建议统一注入）：
  - 追踪：`trace_id`，`span_id`，`request_id`，`job_id`，`batch_id`
  - 业务：`station_id`，`station_name`，`device_id`，`device_name`，`device_type`，`pump_type`，`field_key`
  - 文件：`file_path`，`file_name`，`file_hash`，`file_offset`，`bytes_read`
  - 数据量：`rows_total`，`rows_read`，`rows_loaded`，`rows_deduped`，`rows_merged`，`rows_failed`
  - 时间：`window_start`，`window_end`，`standard_time`
  - 数据库：`db_host`，`db_schema`，`sql_op`（LOAD/INSERT/UPDATE），`sql_cost_ms`，`affected_rows`
  - 重试：`attempt`，`max_attempts`，`backoff_ms`
  - 异常：`exc_type`，`exc_message`，`stack`
- 脱敏字段：账号、密码、令牌、连接串、隐私数据必须打码（见“脱敏与合规”）。

示例：

```json
{"ts":"2025-02-28T02:00:03Z","level":"INFO","event":"align.merge.batch","trace_id":"t-...","job_id":"j-...","batch_id":"b-42","station_id":12,"device_id":345,"rows_merged":50000,"sql_cost_ms":320,"affected_rows":49876}
```

## 配置与初始化

- 配置文件：`configs/logging.yaml`（示例见 `docs/templates/logging.yaml`）。
- 关键开关：
  - `format`: json|text
  - `console`: 是否输出到控制台
  - `file.enabled / path / rotate / backup_count / retention_days`
  - `performance.queue_handler`: 启用异步队列日志
  - `sampling.debug_sample_rate / loop_log_every_n`
  - `redaction.enable / patterns / replacement`
- ENV/CLI 覆盖：`LOG_LEVEL`、`LOG_FORMAT`、`LOG_FILE_PATH`、`--log-json/--no-log-json`

初始化建议（Python 代码骨架）：

```python
import logging, json, yaml
from logging.config import dictConfig

with open("configs/logging.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
# 根据 ENV/CLI 调整 cfg ...
dictConfig(cfg)
logger = logging.getLogger(__name__)
```

## 适配器与上下文传递

- 使用 `LoggerAdapter` 注入上下文（trace_id/job_id/站点/设备）。
- 在任务/线程/协程入口设置 `trace_id`，通过上下文变量传递（参考编码规范第 23 节）。

示例：

```python
import logging
from app.utils.trace import get_trace_id

class CtxAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = {"trace_id": get_trace_id()} | (kwargs.get("extra") or {})
        kwargs["extra"] = extra
        return msg, kwargs

log = CtxAdapter(logging.getLogger(__name__), {})
log.info("ingest.load.begin", extra={"file_path": str(path)})
```

## 异常与错误记录

- 统一结构：`event` 指向领域动作；异常记录 `exc_type/exc_message/stack`。
- 对可重试错误（见 MySQL 错误码矩阵）：记录 `attempt/max_attempts/backoff_ms/sql_op`。
- 对不可重试错误：输出修复建议 `hint` 与必要上下文（不含敏感）。

示例（重试 WARN → 最终 ERROR）：

```python
try:
    save_batch(rows)
except DeadlockError as e:
    log.warning("db.retry", extra={"error_code":1213, "attempt":attempt, "backoff_ms":backoff})
    raise
except Exception:
    log.error("task.fail", exc_info=True, extra={"trace_id": trace_id, "hint":"检查入参/连接"})
    raise
```

## 采样、限流与降级

- 采样：`debug_sample_rate` 控制 DEBUG 日志比例；批处理路径按 `loop_log_every_n` 每 N 条/步输出进度。
- 限流：限制单条日志大小（默认 8KB），超过截断并补 `truncated=true`；热路径合并摘要日志。
- 降级：队列溢出时记录溢出计数与丢弃率；必要时降级为同步刷盘，确保可见性。

## 背压与门禁

- 指标窗口：监测 `batch_cost_ms/merge_cost_ms/rows_*` 与失败率；
- 背压进入：失败率>阈值或 P95>阈值 → 降并发/缩小批；记录 `backpressure.enter`；
- 背压退出：连续窗口达标 → 恢复并发与批大小；记录 `backpressure.exit`；
- 停止门禁：连续窗口不达标 → 停止本站点导入，记录 `guardrail.stop`。

## 主要事件清单（建议）

- ingest.load.begin / ingest.load.end / ingest.dedup.summary
- align.merge.batch / align.conflict
- task.summary / guardrail.stop / guardrail.resume
- backpressure.enter / backpressure.exit
- quality.anomaly / calc.missing

## E2E 示例（片段）

```json
{"event":"ingest.load.begin","trace_id":"t-1","file_path":"data/a.csv","rows_total":100000}
{"event":"ingest.dedup.summary","trace_id":"t-1","rows_read":100000,"rows_deduped":95000}
{"event":"align.merge.batch","trace_id":"t-1","rows_merged":50000,"sql_cost_ms":320}
{"event":"task.summary","trace_id":"t-1","rows_total":100000,"rows_merged":98000,"failures":2}
```

## 脱敏与合规

- 统一脱敏：按配置 `redaction.patterns` 对疑似敏感内容进行替换；
- 敏感字段禁止入日志：密码、完整连接串、个人隐私数据；
- 审计：记录日志配置变更与采样/限流状态。

## 故障排查清单（速用）

- 导入慢：查看 `batch_cost_ms/merge_cost_ms`、锁等待、连接池排队；
- 冲突多：检查来源优先级与阈值、JSON 舍入策略；
- 大量重试：分析错误码分布与 backoff 是否合理；
- 队列溢出：降级为同步、提高磁盘吞吐或减少日志量；
- 无日志或字段缺失：检查 `logging.yaml` 与适配器是否正确注入上下文。

## 模板与参考

- 日志配置模板：`docs/templates/logging.yaml`
- 队列日志示例：`docs/templates/logging_queue_example.py`
- 统一 JSON 编码器：`docs/templates/json_encoder.py`
- CLI 错误输出适配：`docs/templates/cli_typer.py`

______________________________________________________________________

如需将日志与指标对接到外部平台（ELK/ClickHouse/Prometheus/Grafana），可在配置中添加相应 Handler 或采集端，遵循“结构化、低开销、脱敏优先”的原则。

## 目录

- 目标与原则
- 结构化字段规范
- 配置与初始化
- 适配器与上下文传递
- 异常与错误记录
- 采样、限流与降级
- 背压与门禁
- 主要事件清单
- E2E 示例
- 脱敏与合规
- 故障排查清单
- 字段字典与类型定义
- 采样/限流实现示例
- SQL 日志摘要构建
- 异步日志回退与关闭顺序
- 指标联动（日志→指标）
- 文本格式模板
- 日志测试与基准
- 平台与运维注意事项

## 字段字典与类型定义

- 字段类型（建议）：
  - 时间：ISO8601 字符串；或 `%Y-%m-%d %H:%M:%S`
  - 数值：整数/小数（Decimal 建议在业务中，日志中以浮点或字符串写入）
  - ID：字符串或整数，保持稳定不变更含义
  - JSON：尽量保持一层结构，避免嵌套过深
- 字段命名：小写蛇形；事件名使用点号分隔域/动作
- 保留字段：`ts`、`level`、`event`、`trace_id`、`job_id`、`station_id`、`device_id`

## 采样/限流实现示例

```python
import logging, time
from typing import Optional

class SamplingFilter(logging.Filter):
    def __init__(self, debug_rate: float = 0.0, every_n: int = 1000) -> None:
        super().__init__()
        self.debug_rate = debug_rate
        self.every_n = every_n
        self._counter = 0
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno == logging.DEBUG:
            import random
            return random.random() < self.debug_rate
        self._counter += 1
        if self.every_n > 0 and (self._counter % self.every_n == 0):
            return True
        return True
```

## SQL 日志摘要构建

- 原则：不记录完整 SQL 与参数；只记录操作类别、表、影响行数、耗时；
- 示例字段：`sql_op`（LOAD/INSERT/UPDATE/SELECT）、`tables`、`sql_cost_ms`、`affected_rows`；
- 对多表 JOIN 记录 `tables=[a,b]`，避免暴露具体条件与敏感参数。

## 异步日志回退与关闭顺序

- 启动：初始化 `QueueHandler/QueueListener`→设置 Logger → `listener.start()`；
- 运行中：若队列溢出/处理异常：记录溢出并降级为同步 `StreamHandler`；
- 退出：`listener.stop()` 后再退出进程，确保队列刷盘完成；失败时保底 `stderr` 输出最小字段集。

## 指标联动（日志→指标）

- 日志是审计与排错主渠道；指标负责趋势与告警。建议双写：关键事件同时触发指标打点。
- 关键指标：
  - 吞吐类：`rows_total/rows_loaded/rows_deduped/rows_merged`
  - 时延类：`batch_cost_ms/merge_cost_ms`
  - 质量类：`failures/retries/conflicts/anomalies`
- 打点方式：
  - 代码内通过指标客户端（如 Prometheus）递增/观测；
  - 或由日志采集端在接收端做规则解析生成指标（降低代码侵入）。

## 文本格式模板

- 调试期可使用文本格式：`[ts][level][event] message key=value ...`；
- 示例：

```
[2025-02-28T02:00:03Z][INFO][align.merge.batch] rows_merged=50000 sql_cost_ms=320 affected_rows=49876 trace_id=t-...
```

## 日志测试与基准

- 单测：使用 `caplog`（pytest）捕获日志，断言字段与条数；
- 压测：在高吞吐导入下，验证队列深度、落盘速率、丢失率；
- 回归：E2E 流程稳定输出 `summary` 及关键指标字段。

## 平台与运维注意事项

- 文件轮转策略：按天/按大小；容器内建议 stdout/stderr 交由日志系统收集。
- 采集端与索引：ELK/ClickHouse/Vector/Promtail；字段映射与索引模板需预置。
- 保留策略：按法规与业务要求设置（默认 14 天，可配置）。
