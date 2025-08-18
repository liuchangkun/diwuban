## Python 编码规范（全面版）

本文档定义本项目的 Python 编码规范，目标是：高可读、易维护、强稳定、生产可用。优先保证：单一职责、清晰边界、结构化日志、参数化 SQL、类型与文档齐备、测试与门禁完整。

### 适用范围

- **语言与版本**: Python 3.10+。
- **对象**: 代码、文档、脚本、测试、CI 配置。
- **冲突裁决**: 以“最小改动、生产安全、幂等与对齐优先”为准；通用规范与项目规则不一致时，以项目规则为准。

### 与 08-code-conventions 映射（速查）

| 本指南章节                     | 08-code-conventions 节点           |
| ------------------------------ | ---------------------------------- |
| 1 设计原则与模块边界           | 1 设计与原则、2 文件与模块         |
| 2 目录与文件                   | 2 文件与模块                       |
| 3 命名规范                     | 5 命名规范                         |
| 4 导入、格式化与行宽           | 6 导入顺序与格式化、40 配置        |
| 5 类型与静态检查               | 7 静态与类型检查                   |
| 6 函数与类设计（含 Docstring） | 3 函数与类、4 注释与文档           |
| 7 错误处理与异常               | 8 错误处理与异常                   |
| 8 日志与可观察性               | 9 日志与结构化输出、10 日志规则    |
| 9 SQL 与数据访问               | 10 SQL 与数据访问                  |
| 10 并发与资源管理              | 11 并发与资源、20 并发与连接池     |
| 11 配置与全局状态              | 19 配置访问与全局状态、配置规范    |
| 12 时间、时区与精度            | 26 时间与时区                      |
| 13 文件与路径                  | 27 文件与路径、34 跨平台           |
| 14 JSON 与序列化               | 28 JSON、精度与单位转换            |
| 15 重试与超时                  | 29 重试与超时、44 重试矩阵         |
| 16 测试与覆盖率                | 13 测试与覆盖率、23 测试与 DB mock |
| 17 pre-commit 与 CI            | 14 pre-commit 与 CI                |
| 18 安全与脱敏                  | 37 秘密检测与脱敏、21 安全         |
| 20 提交与评审                  | 17 提交与评审                      |
| 21 缩进与换行                  | 18 缩进与换行                      |
| 22 输入校验与数据模型          | 25 输入校验与数据模型              |
| 23 trace_id 传递               | 41 trace_id 传递                   |
| 30 异步编程                    | 11 并发与资源（扩展）              |
| 31 CLI 规范                    | 22 CLI 模板、48/04 CLI 规范        |
| 32 子进程与外部命令            | 34 跨平台（扩展安全）              |
| 33 性能分析与基准              | 23 性能与 SLO（扩展）              |
| 35 缓存、幂等与重复保护        | 20/40 并发与幂等                   |
| 36 包导出与 __all__            | 33 包结构与 __init__、2 模块边界   |
| 49 Do/Don't                    | 24 反模式清单                      |

> 若存在差异，以项目规则为准；本指南提供可复制模板与示例以加速落地。

### 快速检查清单（必过）

- 命名清晰、函数单一职责、无魔法常量。
- 参数校验、类型注解、异常边界明确；无裸 except。
- 日志结构化且不含敏感信息；关键路径有指标。
- SQL 使用参数化，占位符 `%s`；无拼接 SQL。
- IO/DB 使用上下文管理器；连接从池借还。
- 统一时间格式 `%Y-%m-%d %H:%M:%S`，仅秒级；不做时区转换。
- JSON 写入前统一舍入与精度；序列化使用紧凑分隔。
- 依赖版本固定；pre-commit 启用格式化与 lint。
- 单元/集成测试覆盖关键路径；CI 门禁开启。

## 1. 设计原则与模块边界

- **单一职责（SRP）**: 每个模块/类/函数只承担一类职责；超出即拆分。
- **KISS/最少惊讶**: 避免魔法与隐式副作用；API 行为直观一致。
- **DRY**: 去重共性逻辑，抽到 `app/utils/` 或独立函数。
- **模块边界**: 领域聚焦；跨层访问走网关（如 `app/db/`）。
- **公开接口最小化**: 模块对外 API 控制在 3-7 个，内部成员前缀 `_`。

## 2. 目录与文件

- 单文件建议 ≤ 500 行；>800 行应拆分（生成代码例外）。
- 文件头必须含模块职责/依赖/最小示例 Docstring。
- 路径使用 `pathlib.Path`；禁止未校验的自由拼接路径。

示例（文件头部 Docstring）:

```python
"""
模块: csv_loader
职责: 使用 LOAD DATA LOCAL INFILE 将 CSV 导入临时表并提供去重视图。
依赖: app/db/mysql_pool, app/db/sql_snippets
用法:
    loader = CsvLoader(conn_pool)
    with loader.load_to_temp("data/a.csv") as tmp:
        loader.dedup_seconds(tmp)
"""
```

## 3. 命名规范

- 模块/包: 小写蛇形；类: 大驼峰；函数/变量: 小写蛇形；常量: 全大写下划线。
- 命名表达含义而非实现细节：`load_csv_to_temp_table` 优于 `handle_file`。
- 外部语义包含单位或维度：如 `flow_rate_m3h`。

## 4. 导入、格式化与行宽

- 导入顺序：标准库 → 第三方 → 本地；每组内字母序；禁止 `from x import *`。
- 行宽 ≤ 100；UTF-8；换行 `\n`；与 Black/Isort/ruff 配置一致。

示例（isort 配置片段）:

```ini
[tool.isort]
profile = "black"
line_length = 100
```

## 5. 类型与静态检查

- 对外 API 必须类型注解；内部可依靠推断。
- 关键模块启用 mypy；避免 `Any` 与不安全转换。

## 6. 函数与类设计

- 函数 ≤ 50 行（建议），>80 行需拆分；圈复杂度 ≤ 10。
- 参数 ≤ 5；超出请封装为配置/数据类（`dataclasses`/`pydantic`）。
- 返回值明确；错误使用异常或 Result 对象，不用魔法值。
- 类以组合优先，避免深层继承；构造后处于可用状态。

Docstring 模板（Google 风格）:

```python
def merge_json_fields(existing: dict, patch: dict) -> dict:
    """使用 JSON_MERGE_PATCH 语义合并字段。

    Args:
        existing: 现有 JSON。
        patch: 待合并片段。

    Returns:
        合并后的 JSON（不修改入参）。

    Raises:
        ValueError: 非法字段名或类型不满足约束时。
    """
```

## 7. 错误处理与异常

- 禁止裸 `except:`；仅捕获已知异常类型；不得吞异常。
- 边界层（CLI/任务入口）做兜底捕获，记录上下文与入参摘要。
- 可重试与不可重试错误分流；对 MySQL 参见项目错误码矩阵。

示例：

```python
try:
    save_batch(rows)
except DeadlockError as e:
    logger.warning("db.retry", extra={"error_code": 1213, "attempt": attempt})
    raise
except Exception:
    logger.error("task.fail", exc_info=True, extra={"trace_id": trace_id})
    raise
```

## 8. 日志与可观察性

- 使用结构化日志；禁止输出敏感信息（密码/连接串/PII）。
- 关键路径记录指标：`rows_* / cost_ms / affected_rows`；支持采样与限流。
- 日志字段：`ts/level/event/message`、上下文（trace_id/job_id/station_id/device_id 等）。
- 日志配置由 `configs/logging.yaml` 控制；支持 ENV/CLI 覆盖。

示例：

```python
log = with_ctx({"trace_id": trace_id, "job_id": job_id})
log.info("ingest.load.begin", extra={"file_path": str(path)})
```

## 9. SQL 与数据访问

- 严禁字符串拼接 SQL；统一参数化，占位符 `%s`。
- 小批次事务提交；单事务耗时超阈自动拆分。

示例：

```python
sql = (
    "SELECT standard_time FROM aligned_data "
    "WHERE device_id=%s AND standard_time BETWEEN %s AND %s"
)
cursor.execute(sql, (device_id, since_dt, until_dt))
```

## 10. 并发与资源管理

- IO 密集优先线程/协程；CPU 密集优先进程。
- 连接/游标/文件使用上下文管理器，异常也能释放；连接从池借还。
- 并发与批次遵循自适应规则与性能门禁，避免长事务与锁冲突。

## 11. 配置与全局状态

- 通过集中 settings/配置对象注入依赖；禁止在业务代码散落读取 ENV。
- 禁止可变全局单例；需要缓存使用受控 LRU 或上下文绑定。

## 12. 时间、时区与精度

- 统一使用 `%Y-%m-%d %H:%M:%S`；仅秒级；不做时区转换。
- JSON 写入前按字段统一舍入（电气/工艺 2 位；比率/频率 3 位）。

## 13. 文件与路径

- 使用 `pathlib.Path`；读取 CSV 指定 `encoding="utf-8", newline=""`。
- 大文件流式/分块处理，避免整文件读入内存。

## 14. JSON 与序列化

- 使用 `json.dumps(obj, ensure_ascii=False, separators=(",", ":"))` 紧凑序列化。
- 禁止在日志/异常中输出大 JSON；必要时截断并标注 `truncated`。

## 15. 重试与超时

- 仅对幂等步骤重试；指数退避带抖动；设置 IO/DB 超时。

示例（tenacity）:

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(0.2, 2.0))
def write_batch(rows):
    ...
```

## 16. 测试与覆盖率

- 公共函数/模块必须有单元测试，覆盖典型与边界场景。
- 集成/E2E：关键业务链路小样本跑通；断点续跑与幂等路径需覆盖。
- 覆盖率目标：核心模块 ≥ 80%。

## 17. pre-commit 与 CI

- 启用 `black/isort/ruff/mypy/secret-scan`；CI 执行 lint/type/test 与小样本 e2e（dry-run）。

示例（.pre-commit-config.yaml 片段）:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks: [{id: black}]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks: [{id: isort}]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.2
    hooks: [{id: ruff}]
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks: [{id: detect-secrets, args: ["--baseline", ".secrets.baseline"]}]
```

## 18. 安全与脱敏

- 绝不提交凭据；日志与异常中统一脱敏（见 `configs/logging.yaml`）。
- 文件与输入来自白名单路径（`configs/app.yaml` `security.allow_paths`）。
- SQL 参数化、最小权限、连接凭据使用 `.env`/环境变量注入。

## 19. 文档与示例

- README 包含环境准备、运行命令（含 `--dry-run/--resume`）、性能建议、常见错误排查。
- CLI 命令自带 `--help` 完整说明；示例命令可直接复制运行。

## 20. 提交与评审

- 小步提交：单次提交聚焦单一改动；提交信息用“动词+范围+结果”。
- 评审检查：单一职责、完整注释、批量导入、幂等与对齐策略、测试覆盖。

## 21. 缩进与换行（强约束）

- 保持文件现有缩进字符（tab vs 空格）与宽度，不转换、不混用；不增加无意义缩进层级。
- 换行统一 `\n`（Windows 工具需兼容），避免混入 `\r\n`。

## 22. 输入校验与数据模型

- 推荐 `dataclasses` 或 `pydantic` 描述入参；入口先校验，再执行业务。

示例：

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ImportArgs:
    station_name: str
    since: datetime
    until: datetime
```

## 23. trace_id 传递

- 使用 `contextvars` 维护 `trace_id`；日志适配器读取，保证多线程/协程一致。

示例：

```python
import contextvars
trace_id_var = contextvars.ContextVar("trace_id", default=None)

def set_trace_id(tid: str):
    trace_id_var.set(tid)

def get_trace_id() -> str | None:
    return trace_id_var.get()
```

## 24. 熔断与降级

- 仅在幂等点重试；对持续失败的下游启用熔断与冷却；必要时降级或只读。

## 25. 大文件处理与内存守护

- 流式/分块读取；构造中间集合前估算大小与上限，必要时落盘临时文件。

## 26. 依赖与版本固定

- 使用 `requirements.in` + `pip-tools` 生成 `requirements.txt`；最小升级，保留回滚方案。

示例：

```bash
pip-compile requirements.in -o requirements.txt
pip-sync requirements.txt
```

## 27. 包结构与导入

- 禁止跨层相对导入（`from ..x import y`）；优先绝对导入；`__main__` 仅做 CLI 解析与调度。

## 28. 弃用与兼容

- 对外 API 弃用以装饰器提示，并在文档标注 Sunset；保持向后兼容期与迁移指引。

## 29. 提交前 Checklist（最小集）

- [ ] 类型/静态检查通过（ruff/mypy/black/isort）
- [ ] 单元/小样本 e2e 通过
- [ ] SQL 参数化、无裸 except、无明文敏感信息
- [ ] 日志/指标/错误码符合规范
- [ ] 文档已更新（必要时）

______________________________________________________________________

以上规范覆盖 Python 编程关键方面，结合本项目的“最小改动、生产安全、幂等对齐”原则，确保代码质量与可维护性。在规范与项目规则冲突时，以项目规则为准。

## 30. 异步编程与取消（async/await）

- 优先使用 `asyncio`/异步客户端处理 IO 密集；避免在协程中执行阻塞操作。
- 使用异步上下文管理器/迭代器（如异步 DB/HTTP 客户端）。
- 必须支持取消：捕获 `asyncio.CancelledError` 做资源清理后 `raise` 传递。
- 为异步任务设置超时：`asyncio.wait_for` 或客户端超时参数，避免悬挂。
- 并发控制：使用 `asyncio.Semaphore`/有界连接池限制并发。

示例（取消安全）:

```python
async def worker():
    try:
        await do_io()
    except asyncio.CancelledError:
        await cleanup()
        raise
```

## 31. CLI 规范与退出码/输出标准化

- CLI 首选 `typer`；`--help` 明确参数与示例；支持 `--dry-run/--resume`。
- 退出码遵循项目规范（参考 48）：
  - 0：成功；1：未知错误；2：配置/校验失败；3：下游/环境不可用；4：输入无效。
- 标准输出：
  - 人类可读提示 + 机器可读摘要（JSON，一行）共存；日志走 stderr/文件。
- 错误消息标准化（参考 57）：结构化字段包含 `error_code`、`message`、`hint`、`context`、`trace_id`。

示例（标准化错误 JSON）:

```json
{"error_code": "CFG_SCHEMA", "message": "mapping 校验失败", "hint": "修复缺失字段", "context": {"file": "configs/app.yaml"}}
```

## 32. 子进程与外部命令安全

- 能不用外部命令就不用；优先纯 Python/库。
- 必须使用列表形式的 `subprocess.run([...], check=True, text=True)`；禁用 `shell=True`（除非白名单命令且严格转义）。
- 设置超时 `timeout=` 与资源限制；捕获并标准化错误输出。
- 将敏感参数通过环境变量或临时文件传递，不写入命令行历史。

## 33. 性能分析与基准

- 轻量分析优先：`time.perf_counter()` 与窗口统计；避免在热路径频繁打点。
- 深度分析使用 `cProfile`/`py-spy`/`viztracer`，对问题段采样而非全程。
- 基准测试隔离测试数据、固定随机种子、记录环境与版本快照。

示例（monotonic 计时）:

```python
from time import perf_counter
start = perf_counter()
try:
    do_work()
finally:
    cost_ms = (perf_counter() - start) * 1000
```

## 34. MySQL 交互与重试矩阵指引

- 区分可重试（如 1213/1205/2006/2013）与不可重试（如 1064/1146/1054/1364/1062）。
- 可重试采用指数退避+抖动；不可重试立即失败并输出标准化错误。
- 事务粒度小批；避免跨大时间窗的写入；读写分离遵循项目规则。
- 所有 SQL 必须参数化；严禁把变量插入 SQL 字符串。

## 35. 缓存、幂等与重复保护

- 仅对纯函数或强幂等接口做缓存；明确失效策略与上限。
- 关键写路径添加幂等键（如 `(device_id, standard_time)`）；重复请求需安全覆盖或忽略。
- 并发下使用去重/防抖（如在任务层记录指纹/断点），避免重复执行。

## 36. 包导出与 `__all__`

- 包内 `__init__.py` 仅导出稳定 API：`__all__ = ["ClassA", "func_b"]`。
- 避免在导入期执行重 IO/重计算；保持导入幂等且轻量。

## 37. 测试细则（补充）

- 单元测试遵循 Given-When-Then 结构；断言具备清晰失败信息。
- DB/外部依赖在单测中 mock；集成测试使用临时库或容器。
- 为易错分支（异常路径/重试/超时/取消）提供专门用例。

## 38. 随机性与可复现

- 使用固定随机种子；记录版本/依赖快照；涉及时间使用可注入的时钟接口。

## 39. 国际化与本地化

- 源码统一 UTF-8；对外展示字符串避免硬编码中文，使用可替换消息模板。

## 40. 注释质量与文档链接

- 注释写“为什么/约束/边界”，不复述代码；必要时链接到规则文档（mdc 链接）。

## 41. 数值与精度（Decimal 优先）

- 严禁在业务数值（金额/计量/电气/工艺等）中使用二进制浮点 `float` 做累计或比较。
- 输入解析→先转 `Decimal(str(value))`；统一量纲与舍入后再写入/比较。
- 统一舍入规则：默认为四舍五入 `ROUND_HALF_UP`；按字段精度选择量化步长，如 `0.01`。

示例（统一舍入）:

```python
from decimal import Decimal, ROUND_HALF_UP, getcontext
getcontext().prec = 28

def round_kpa(v: str | float | int) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

- SQL 参数传 `Decimal` 与列类型一致（DECIMAL），避免隐式类型转换与精度丢失。
- 阈值比较前先做同一舍入，减少“近似差异”导致的冲突放大。

## 42. 类型建模进阶（Enum/TypedDict/Protocol）

- 枚举：稳定有限集合用 `Enum`；严禁魔法字符串散落。
- 结构化字典：使用 `TypedDict` 定义键/值类型；对外 API 使用 dataclass/pydantic。
- 接口抽象：用 `Protocol` 定义可替换实现，降低耦合便于测试。

示例：

```python
from enum import Enum
from typing import Protocol, TypedDict

class PumpType(Enum):
    VARIABLE_FREQUENCY = "variable_frequency"
    SOFT_START = "soft_start"

class Row(TypedDict):
    device_id: int
    standard_time: str
    value: float

class Merger(Protocol):
    def merge(self, rows: list[Row]) -> int: ...
```

## 43. 依赖注入与可测试性

- 服务对象通过构造函数注入配置与网关（DB/HTTP/FS）；严禁在业务逻辑中散落读取 ENV。
- 对外仅暴露少量方法；其余私有化以约束使用面。

示例：

```python
class ImportService:
    def __init__(self, settings: dict, db_gateway):
        self.settings = settings
        self.db = db_gateway
    def run_batch(self, batch: list[dict]) -> int:
        return self.db.merge(batch)
```

## 44. 线程/进程安全

- 线程：避免跨线程共享不可重入对象（DB 连接/游标/会话）；每线程各自借还连接。
- 进程：DB 连接不跨进程复用；子进程内重建连接与池。
- 锁与并发：倾向无锁并发（局部变量/消息队列）；必要时使用 `threading.Lock`/`asyncio.Lock` 精准保护最小临界区。

## 45. ExitStack 与资源清理

- 多资源组合管理使用 `contextlib.ExitStack`，保证异常时全部释放。

示例：

```python
from contextlib import ExitStack

with ExitStack() as stack:
    f = stack.enter_context(open(path, "r", encoding="utf-8"))
    conn = stack.enter_context(pool.connection())
    do_work(f, conn)
```

## 46. 自定义 JSON 编码器

- 对 `Decimal`/`datetime`/`Enum` 等自定义序列化器，集中实现并复用；禁止临时 `default=str` 造成歧义。

示例：

```python
import json
from decimal import Decimal
from enum import Enum
from datetime import datetime

def dumps_compact(obj: object) -> str:
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(o, Enum):
            return o.value
        raise TypeError(f"Type not serializable: {type(o)!r}")
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=default)
```

## 47. CLI→配置映射与覆盖

- 优先级：CLI > ENV > `configs/app.yaml` > 默认值；启动加载后打印脱敏快照。
- CLI 选项命名与配置字段一一对应：如 `--concurrency` → `ingest.concurrency.max_workers`。
- 强校验：类型/范围/依赖项，失败即退出并给出修复建议 JSON（参见 31/57）。

## 48. 开关位与灰度放量

- 所有新能力必须受开关控制，默认关闭；支持站点/设备维度的白名单。
- 放量策略：小流量→按站点/时间段→全量；异常即回退；记录 `feature_flag` 字段于日志。

## 49. Do / Don't（速查）

- SQL：
  - Do：`cursor.execute(sql, (a, b))`；小批事务；EXPLAIN 慢查询
  - Don't：字符串拼接 SQL；大事务跨多窗口；在循环内逐行 INSERT
- 日志：
  - Do：结构化、采样、限流、脱敏；关键路径指标
  - Don't：敏感信息、巨大 JSON、热路径频繁日志
- 时间/精度：
  - Do：固定格式 `%Y-%m-%d %H:%M:%S`；`Decimal` 舍入
  - Don't：`float` 叠加比较；隐式时区转换

## 50. 模块模板（增强版）

```python
"""模块职责与用法简述。
依赖: app/db/gateway
示例:
    svc = Service(settings, db)
    affected = svc.public_api(rows)
"""
from __future__ import annotations
from typing import Iterable, Sequence

__all__ = ["Service"]

class Service:
    def __init__(self, settings: dict, db_gateway) -> None:
        self.settings = settings
        self.db = db_gateway

    def public_api(self, rows: Sequence[dict]) -> int:
        """处理一批数据并返回影响行数。"""
        return self.db.merge(rows)
```

## 51. 日志适配器与上下文传递

- 使用 `logging.LoggerAdapter` 携带关联上下文（trace_id/job_id/station_id 等）。
- 生产默认异步落盘：`QueueHandler/QueueListener`；异常路径可回退同步。
- 统一在入口设置 `trace_id`（见 23），中间层使用适配器扩展。

示例：

```python
import logging
logger = logging.getLogger(__name__)

class CtxAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = {"trace_id": get_trace_id()} | (kwargs.get("extra") or {})
        kwargs["extra"] = extra
        return msg, kwargs

log = CtxAdapter(logger, {})
log.info("ingest.load.begin", extra={"file_path": str(path)})
```

## 52. 错误码与重试策略（对照）

- 统一错误消息结构：`error_code/message/hint/context/trace_id`（见 31/57）。
- 重试策略（示例）：

| 错误码              | 级别     | 策略                     |
| ------------------- | -------- | ------------------------ |
| 1213/1205/2006/2013 | 可重试   | 指数退避+抖动，最多 5 次 |
| 1062                | 幂等冲突 | 记录并跳过/合并          |
| 1064/1146/1054/1364 | 不可重试 | 立即失败，输出修复建议   |

- 日志必须带 `attempt/max_attempts/backoff_ms/sql_op`。## 53. 安全编码（输入、路径、敏感信息）
- 路径仅来自白名单（`configs/app.yaml` `security.allow_paths`）；禁止拼接未校验用户输入。
- 对外部输入严格校验（长度/格式/范围/枚举）；失败走标准化错误输出。
- 敏感信息仅从环境变量/密管注入；日志中统一脱敏（见日志规则）。

## 54. 度量指标与背压

- 关键指标：吞吐（行/秒）、P95 批次耗时、失败率、锁等待次数、连接池排队时间。
- 背压策略：连续窗口超阈则降并发/减小提交行数；恢复条件满足再回升（见并发规范）。
- 输出 `task.summary` 与 `backpressure.enter/exit` 事件，附调整参数与窗口统计。

## 55. 影子运行与灰度验证

- 配置更新/算法切换先进行影子运行：不落库，仅生成对比指标与差异报告。
- 灰度后逐步放量，出现回退指标立即回滚并记录事件。## 56. 任务编排与可取消性
- 任务应可中断与恢复（断点/指纹见项目规范）；长任务分批提交、阶段化日志与指标。
- 统一捕获系统信号，优雅退出并输出 `task.summary`。

## 57. 错误消息标准化（细则）

- 结构字段：`error_code`(枚举)、`message`(人类可读)、`hint`(修复建议)、`context`(关键参数)、`trace_id`。
- 输出示例：

```json
{"error_code":"CFG_SCHEMA","message":"配置校验失败","hint":"修复字段缺失","context":{"file":"configs/app.yaml"}}
```

- CLI 出错时：stderr 输出人类提示；stdout 输出单行 JSON 摘要；退出码按 31。

## 58. 并行策略与资源上限

- 全局并发/单站点并发/批大小遵循配置与自适应策略；任何时刻超过锁等待阈值优先减小提交行数。
- 网络/文件/DB 连接上限需在配置中可控；默认保守值，逐步加压。

## 59. 领域字典与单位校验

- 字段键必须来源于统一字典；单位在 `field_units` 登记，新增字段先更新字典与单位表。
- 导入前进行单位统一与转换（如 kW→W，MPa→kPa，L/s→m3/h）。

## 60. 变更记录与回滚

- 每次变更提供“变更说明”：问题/原因/对策/验证/影响/回滚。
- 回滚策略预先设计：如何恢复旧版本/配置、如何清理或纠偏数据；脚本放 `scripts/rollback_*`。## P0. 日志配置模板（logging.yaml）

```yaml
level: INFO
format: json           # json|text
console: true
file:
  enabled: true
  path: logs/app.log
  rotate: daily        # daily|size
  max_bytes: 10485760  # 10MB，仅在 rotate=size 有效
  backup_count: 10
  retention_days: 14
sampling:
  debug_sample_rate: 0.0
  loop_log_every_n: 1000
context:
  include_fields: [trace_id, job_id, batch_id, station_id, device_id, file_path]
  include_sql_cost: true
  include_stack: true
redaction:
  enable: true
  patterns:
    - '(?i)(password|passwd|pwd|secret|token)=[^&\s]+'
  replacement: '***'
performance:
  queue_handler: true   # 启用异步队列日志
  flush_on_exit: true
```

## P0. CLI 模板与错误输出适配器（typer）

```python
import json
import sys
import typer
from typing import Any

app = typer.Typer()

class ExitCode:
    OK = 0
    UNKNOWN = 1
    CONFIG = 2
    DOWNSTREAM = 3
    INVALID_INPUT = 4

def print_error_json(error_code: str, message: str, hint: str = "", context: dict[str, Any] | None = None):
    obj = {"error_code": error_code, "message": message}
    if hint:
        obj["hint"] = hint
    if context:
        obj["context"] = context
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")

@app.command()
def import_station(name: str, concurrency: int = 4, dry_run: bool = False) -> None:
    try:
        if not name:
            raise ValueError("name is empty")
        # 执行业务...
        typer.echo(f"导入站点: {name}, 并发: {concurrency}, dry_run={dry_run}")
        raise typer.Exit(ExitCode.OK)
    except ValueError as e:
        typer.echo("参数错误: " + str(e), err=True)
        print_error_json("INVALID_INPUT", str(e), hint="检查 --name 参数")
        raise typer.Exit(ExitCode.INVALID_INPUT)
    except Exception as e:
        typer.echo("执行失败: " + str(e), err=True)
        print_error_json("UNKNOWN", "执行失败", context={"name": name})
        raise typer.Exit(ExitCode.UNKNOWN)

if __name__ == "__main__":
    app()
```

## P0. SQL 反例与改写对照

- 反例：字符串拼接 SQL（SQL 注入/解析错误/缓存失效）

```python
# Bad
cursor.execute(f"SELECT * FROM t WHERE id={user_id} AND name='{name}'")
```

- 改写：参数化 + 列表显式选择

```python
# Good
sql = "SELECT id, name FROM t WHERE id=%s AND name=%s"
cursor.execute(sql, (user_id, name))
```

- 反例：循环逐行 INSERT

```python
# Bad
for row in rows:
    cursor.execute("INSERT INTO t(a,b) VALUES(%s,%s)", (row[0], row[1]))
```

- 改写：批量导入到临时表 → 一次性合并

```python
# Good
# 使用 LOAD DATA LOCAL INFILE / executemany 批量，然后合并
```

- 反例：大事务跨多时间窗/设备

```python
# Bad: 事务过大易锁等待/回滚成本高
```

- 改写：小批事务 + 超阈自动拆分

```python
# Good: 控制每次影响行数与耗时
```

## P0. MySQL 错误码→重试策略表

| 错误码                      | 类型          | 策略           | Backoff（示例）                        |
| --------------------------- | ------------- | -------------- | -------------------------------------- |
| 1213 (Deadlock)             | 可重试        | 重试           | 初始 200ms、倍率 2.0、抖动 ±50%、≤5 次 |
| 1205 (Lock wait timeout)    | 可重试        | 重试           | 同上                                   |
| 2006/2013 (Lost connection) | 可重试        | 重建连接后重试 | 初始 500ms、倍率 1.5、≤5 次            |
| 1062 (Duplicate entry)      | 幂等冲突      | 跳过/合并      | 记录冲突上下文                         |
| 1064/1146/1054/1364         | 语法/对象缺失 | 不重试         | 立即失败，输出修复建议                 |

- 日志字段：`error_code/attempt/max_attempts/backoff_ms/sql_op/summary_sql`（摘要化，不含敏感）。

## P1. 项目异常层次建议

```python
class AppError(Exception):
    """项目基础异常。"""

class ConfigError(AppError):
    pass

class RetryableDbError(AppError):
    pass

class NonRetryableDbError(AppError):
    pass

class ValidationError(AppError):
    pass

class IdempotencyConflict(AppError):
    pass
```

- 捕获边界：
  - 业务层抛出上述异常；
  - 入口层统一捕获并映射到退出码/标准化错误输出（见 CLI 模板）。

## P1. 测试样板与目录规范

- 目录建议：

```
tests/
  unit/
  integration/
  e2e/
  conftest.py
```

- pytest fixture 示例：

```python
import pytest

@pytest.fixture()
def fake_db():
    class FakeDb:
        def merge(self, rows):
            return len(rows)
    return FakeDb()

def test_merge(fake_db):
    assert fake_db.merge([{"a":1}]) == 1
```

- 覆盖典型：重试/超时/取消/断点续跑/幂等冲突/异常路径。

## P1. pyproject.toml 推荐片段

```toml
[tool.black]
line-length = 100

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_unused_ignores = true
warn_return_any = true
no_implicit_optional = true
strict_optional = true
```

## P1. 日志 QueueHandler/QueueListener 最小示例

```python
import logging
import logging.handlers
from queue import Queue

queue: Queue = Queue(maxsize=10000)
handler = logging.handlers.QueueHandler(queue)
listener = logging.handlers.QueueListener(queue, logging.StreamHandler())

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

listener.start()
try:
    logger.info("align.merge.batch", extra={"rows_merged": 50000})
finally:
    listener.stop()
```

## P1. 性能门禁参数表（建议默认）

| 指标         | 目标/阈值                 | 策略                           |
| ------------ | ------------------------- | ------------------------------ |
| 吞吐         | ≥ 50,000 行/秒            | 未达标：降并发/更小批次        |
| P95 批次耗时 | ≤ 2,000 ms                | 超阈：批次拆分/降并发 50%      |
| 失败率       | ≤ 1%（停止阈 2%）         | 超阈：背压/暂停站点            |
| 单事务耗时   | ≤ 2,000 ms（硬 5,000 ms） | 超阈：自动拆分批次             |
| 锁等待       | 接近 0                    | 升高：先减小提交行数，再降并发 |

- 参数来源：`configs/app.yaml`，CLI 可覆盖；日志输出窗口统计与调整记录。## 常见反例 Top 10（含修正）

1. SQL 字符串拼接 → 参数化

```python
# Bad
cursor.execute(f"SELECT * FROM t WHERE id={user_id} AND name='{name}'")
# Good
sql = "SELECT id,name FROM t WHERE id=%s AND name=%s"
cursor.execute(sql, (user_id, name))
```

2. 循环逐行 INSERT → 批量/临时表合并

```python
# Bad
for r in rows:
    cursor.execute("INSERT INTO t(a,b) VALUES(%s,%s)", (r[0], r[1]))
# Good（示意）
# LOAD DATA LOCAL INFILE → tmp_raw → 一次性合并
```

3. 金额/计量用 float → 使用 Decimal 与统一舍入

```python
# Bad
v = 0.1 + 0.2  # 0.30000000000000004
# Good
from decimal import Decimal, ROUND_HALF_UP
v = (Decimal("0.1") + Decimal("0.2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

4. 裸 except 吞异常 → 捕获特定异常并记录上下文

```python
# Bad
try:
    do_work()
except:
    pass
# Good
try:
    do_work()
except DeadlockError as e:
    logger.warning("db.retry", extra={"error_code":1213})
    raise
except Exception:
    logger.error("task.fail", exc_info=True, extra={"trace_id": trace_id})
    raise
```

5. 在协程内执行阻塞 IO → 使用异步客户端或线程池

```python
# Bad
async def handler():
    with open(path) as f:  # 阻塞
        return f.read()
# Good
async def handler():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, Path(path).read_text)
```

6. 日志包含敏感信息 → 统一脱敏与结构化

```python
# Bad
logger.info(f"db_password={pwd}")
# Good
logger.info("db.connect", extra={"host": host, "user": user})
```

7. 子进程 shell=True 注入风险 → 显式列表 + 超时

```python
# Bad
subprocess.run("cat * | grep x", shell=True)
# Good
subprocess.run(["grep", "x", str(file)], check=True, text=True, timeout=10)
```

8. 大事务/跨分区写入 → 小批次 + 自动拆分

```python
# Bad
with conn:
    for row in giant_rows:
        cursor.execute(...)
# Good
for batch in batched(rows, size=50000):
    with conn:
        cursor.executemany(sql, batch)
```

9. 未设超时与取消 → wait_for 与 CancelledError 处理

```python
# Bad
await client.get(url)
# Good
try:
    await asyncio.wait_for(client.get(url, timeout=10), timeout=12)
except asyncio.TimeoutError:
    ...
except asyncio.CancelledError:
    await cleanup()
    raise
```

10. 时钟用 time.time → 使用 monotonic 计时

```python
# Bad
start = time.time()
# Good
from time import perf_counter
start = perf_counter()
```
