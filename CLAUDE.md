# 项目上下文配置 (CLAUDE.md)

> **重要**: 本文件将自动加载到 Claude Code 的上下文中,确保 AI 助手充分了解项目背景和工作规范。

---

## 📋 项目概览

### 基本信息
- **项目名称**: 狄留班泵站数据分析系统
- **技术栈**: Python 3.10+ / PostgreSQL 16 / FastAPI
- **项目类型**: 工业数据采集、计算、分析与优化系统
- **数据规模**: 超大规模时序数据(秒级采集,多泵站并发)
- **开发模式**: 个人开发者,强调渐进式开发和严格质量控制

### 核心业务领域
1. **数据采集与ETL**: CSV批量导入 → staging → 秒级对齐合并
2. **指标计算引擎**: 泵流量/扬程/效率/功率等30+派生指标
3. **特性曲线拟合**: QH/QP/QEta等曲线,支持188种拟合方法
4. **运行优化**: 基于特性曲线的泵组优化调度
5. **异常检测与质量管理**: 多层质量验证,阈值学习,异常告警

---

## 🏗️ 项目架构

### 目录结构
```
diliuban/
├── app/
│   ├── adapters/        # 适配器层(DB/FS/Logging)
│   ├── services/        # 业务服务层
│   │   ├── calculation/ # 指标计算
│   │   ├── characteristic_curves/  # 特性曲线拟合
│   │   ├── ingest/      # 数据导入
│   │   └── run_all/     # 调度编排
│   ├── core/            # 核心工具(配置/日志/错误处理)
│   ├── models/          # 数据模型
│   └── cli/             # 命令行入口
├── configs/             # YAML配置文件(database/logging/ingest等)
├── scripts/             # 数据库脚本/工具脚本
│   ├── sql/             # DDL/存储过程/视图
│   └── tools/           # 辅助工具
├── docs/                # 项目文档
│   ├── PLAYBOOKS/       # 变更记录/决策记录
│   ├── 编码规范.md
│   ├── 智能助手执行规则.md
│   └── MCP工具使用指南.md
├── tests/               # 测试用例
└── 特性曲线开发/        # 特性曲线系统设计文档
```

### 架构原则
- **数据库为中心**: 复杂计算在PostgreSQL存储过程中完成
- **分层架构**: adapters ← services ← cli,严格单向依赖
- **配置外置**: 所有配置统一在 `configs/*.yaml`,禁止硬编码
- **类型安全**: 100%类型注解,启用mypy strict模式

---

## ⚙️ 开发环境配置

### Python环境
```bash
# 使用虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 数据库配置
```yaml
# configs/database.yaml
host: localhost
port: 5432
database: diliuban
# 注意: 用户名/密码通过环境变量或密钥管理工具注入,不写在代码中
```

### 关键命令
```bash
# 运行测试
pytest tests/ -v

# 代码质量检查
ruff check app/
black app/ --check
mypy app/

# 启动调度器
python -m app.cli.main run-all --window-start 2025-01-01 --window-end 2025-01-02
```

---

## 📐 编码规范 (强制遵守)

### 类型注解
```python
# ✅ 正确: 完整类型注解
def calculate_efficiency(
    flow: float,
    head: float,
    power: float
) -> dict[str, float]:
    """计算泵效率

    Args:
        flow: 流量 (m³/h)
        head: 扬程 (m)
        power: 功率 (kW)

    Returns:
        包含效率值和质量等级的字典
    """
    ...

# ❌ 错误: 缺少类型注解
def calculate_efficiency(flow, head, power):
    ...
```

### SQL 参数化
```python
# ✅ 正确: 使用 %s 占位符
sql = "SELECT * FROM fact WHERE ts_bucket >= %s AND ts_bucket < %s"
cursor.execute(sql, (start_ts, end_ts))

# ❌ 错误: 字符串拼接
sql = f"SELECT * FROM fact WHERE ts_bucket >= '{start_ts}'"
```

### 异常处理
```python
# ✅ 正确: 捕获具体异常
try:
    result = db.execute(sql)
except psycopg.OperationalError as e:
    logger.error("数据库连接失败", extra={"error": str(e)})
    raise

# ❌ 错误: 裸 except
try:
    result = db.execute(sql)
except:
    pass
```

### 文档字符串
```python
# ✅ 正确: Google 风格 docstring
def merge_window(
    window_start: str,
    window_end: str,
    station_name: str | None = None
) -> dict[str, int]:
    """合并时间窗口内的暂存数据到事实表

    Args:
        window_start: 窗口开始时间 (ISO格式)
        window_end: 窗口结束时间 (ISO格式)
        station_name: 可选的站点过滤条件

    Returns:
        包含 rows_input/rows_deduped/rows_merged 的统计字典

    Raises:
        ValueError: 窗口时间格式不正确
        DatabaseError: 数据库操作失败

    Example:
        >>> stats = merge_window("2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z")
        >>> print(stats['rows_merged'])
        15234
    """
    ...
```

---

## 🔒 安全约束 (严格禁止)

### 禁止操作
- ❌ 访问 `venv/`, `data/`, `.venv/` 目录
- ❌ 在代码中硬编码DSN/密码/token
- ❌ 通过CLI/ENV覆盖数据库配置 (仅允许YAML)
- ❌ 未经授权的数据库迁移/删除操作
- ❌ 直接安装/卸载Python包 (需明确确认)

### 风险分级
- **低风险** (默认允许): 查看代码、文档编辑、运行单元测试
- **中风险** (需确认): 修改代码、变更配置、生成新脚本
- **高风险** (需授权口令): 安装依赖、数据库DDL、推送代码

### 授权口令模板
```
我确认授权你执行【具体操作】;
允许使用【资源/权限】;
仅在【环境/范围】;
若失败请停止并告知。
```

---

## 🛠️ MCP 工具使用规范

### 强制使用的工具
1. **Context7**: 获取库文档 (如 pandas/sklearn API)
2. **Sequential thinking**: 复杂任务分解与反思
3. **Postgres MCP**: 数据库只读验证 (必须以表数据为准)
4. **Memory**: 记录长期有效的阈值/约定/决策

### 工作流程
```
1. Investigate (调研)
   └─ 使用 codebase-retrieval 确认受影响文件
   └─ 使用 Context7 补齐 API 细节

2. 实施 (小步修改)
   └─ str-replace-editor 修改代码 (≤150行/次)
   └─ 必要时 save-file 创建新文件

3. 验证 (只读检查)
   └─ pytest 运行单元测试
   └─ Postgres MCP 查询表数据验证结果
   └─ 记录命令/cwd/退出码/关键日志

4. 同步 (文档与记忆)
   └─ 更新 docs/ 和 PLAYBOOKS/
   └─ Memory 保存关键决策
```

### 失败退避策略
- 同类操作失败 ≤ 2次 → 暂停并请求澄清
- 记录失败命令与日志,便于排查

---

## 📝 日志规范

### 结构化日志格式
```python
logger.info(
    "合并窗口完成",
    extra={
        "event": "merge.window.completed",
        "window_start": window_start,
        "window_end": window_end,
        "rows_merged": stats['rows_merged'],
        "cost_ms": elapsed_ms,
        "run_id": run_id
    }
)
```

### 事件命名规则
- 格式: `<domain>.<action>[.detail]`
- 示例: `db.exec.started`, `merge.window.completed`, `calc.metric.failed`

### 敏感信息脱敏
```python
# ✅ 正确: 脱敏处理
logger.info("连接数据库", extra={"host": "***", "port": 5432})

# ❌ 错误: 泄露敏感信息
logger.info(f"DSN: postgresql://user:password@host:5432/db")
```

---

## 📚 核心文档索引

### 必读规范
- [编码规范](docs/编码规范.md) - SOLID原则/类型注解/SQL规范
- [智能助手执行规则](docs/智能助手执行规则.md) - AI行为约束
- [MCP工具使用指南](docs/MCP工具使用指南.md) - 工具流程/最佳实践
- [日志规范](docs/日志规范.md) - 日志格式/事件定义
- [行为约束](docs/行为约束.md) - 安全/审计/回滚

### 业务领域文档
- [数据库设计](scripts/sql/README.md) - Schema/分区/索引
- [特性曲线系统](特性曲线开发/开发文档/) - 曲线拟合架构
- [计算指标参考](docs/计算指标参考.md) - 30+指标定义与公式

### 变更记录
- [PLAYBOOKS](docs/PLAYBOOKS/) - 所有变更/决策/错误修复记录

---

## 🎯 常见任务快速参考

### 添加新的计算指标
1. 在 `app/services/calculation/metrics/` 创建新模块
2. 实现 `Calculator` 类 (参考现有指标结构)
3. 在数据库添加对应的存储过程 (可选)
4. 编写单元测试 `tests/unit/services/calculation/`
5. 更新文档 `docs/计算指标参考.md`

### 修复数据质量问题
1. 检查 `app/services/calculation/shared/parameter_manager.py` 阈值配置
2. 查看数据库表 `device_running_thresholds` 的阈值设置
3. 调整验证逻辑 `app/services/calculation/metrics/*/validator.py`
4. 回归测试确保不影响其他指标

### 优化数据库查询
1. 使用 `EXPLAIN ANALYZE` 分析慢查询
2. 检查分区裁剪是否生效
3. 确认索引命中 (BRIN/BTREE)
4. 考虑添加物化视图 (MV)

---

## ⚡ 性能与资源约束

### 数据库连接池
```yaml
# configs/database.yaml
pool:
  min_size: 2
  max_size: 10
  max_inactive_connection_lifetime: 3600
```

### 批量操作限制
- 单次 COPY 批大小: ≤ 50,000 行
- 并发导入线程: ≤ 4 (自适应调整)
- 事务超时: 30秒 (可配置)

### 背压控制
- P95 延迟 > 2s → 降低并发度
- 失败率 > 1% → 缩小批次
- 锁等待次数 > 阈值 → 暂停并告警

---

## 🧪 测试策略

### 测试分层
- **单元测试**: 业务逻辑/计算公式 (coverage ≥ 80%)
- **集成测试**: 数据库交互/ETL流程
- **E2E测试**: 完整窗口计算验证

### 运行测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/unit/services/calculation/ -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

---

## 🚨 常见陷阱与注意事项

### ⚠️ 时区处理
- CSV 输入: 本地时间 (Asia/Shanghai)
- 数据库存储: UTC 时间戳
- 对齐基准: 秒级 `ts_bucket` (UTC)
- **禁止在 Python 端做时区转换**, 统一在数据库 SQL 中完成

### ⚠️ 空值处理
```python
# ✅ 正确: 显式处理 NULL
value = row.get('metric_value')
if value is None:
    logger.warning("指标值为空", extra={"row_id": row['id']})
    continue

# ❌ 错误: 假设值总是存在
result = row['metric_value'] * 2  # 可能 TypeError
```

### ⚠️ 浮点数精度
```python
# ✅ 正确: 使用 Decimal 处理金额/关键数值
from decimal import Decimal
efficiency = Decimal(str(calculated_value)).quantize(Decimal('0.01'))

# ❌ 错误: 直接使用 float 可能丢失精度
efficiency = round(calculated_value, 2)  # 不够准确
```

---

## 📞 获取帮助

### 内部资源
- 查看 `docs/` 目录下的详细文档
- 搜索 `docs/PLAYBOOKS/` 的历史变更记录
- 运行 `python -m app.cli.main --help` 查看命令帮助

### 外部参考
- PostgreSQL 16 文档: https://www.postgresql.org/docs/16/
- FastAPI 文档: https://fastapi.tiangolo.com/
- Pydantic V2: https://docs.pydantic.dev/latest/

---

## 🔄 版本历史

- **2025-12-16**: 初始版本,整合项目核心规范与最佳实践

---

**最后更新**: 2025-12-16
**维护者**: 个人开发者
**状态**: ✅ 活跃维护
