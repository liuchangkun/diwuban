# 地五班项目（中文总览）

> 文档总入口：docs/文档地图与导航.md（数据库与 scripts/sql 为唯一事实源）

## 一、项目概述

- 目标：以 PostgreSQL 16 为中心实现泵站时序数据的可靠入库、UTC 秒级对齐、汇总层加速与稳定查询
- 原则：
  - 入库写入边界：DB 函数（safe_upsert_measurement/\_local）+ 主键合并 + CHECK 兜底
  - 调度：APScheduler（不使用 Windows 计划任务）
  - 中间件：不使用 Docker/Kafka；可选 Redis 3.0.504（轻量任务/状态缓存）

## 二、快速上手

- 文档地图：docs/文档地图与导航.md（建议先读）
- 项目总纲：PROJECT_RULES.md（中文化，对齐数据库事实）
- 数据库脚本：scripts/sql/\*（唯一事实源）

## 三、核心能力（流程）

```mermaid
flowchart LR
  A[导入 CSV] --> B[UTC 秒级对齐入库]
  B --> C[汇总层 MV 刷新]
  C --> D[报表查询/CRUD]
  D --> E[观测与性能基线]
```

## 四、开发者入口

- 体系结构总览：docs/体系结构总览.md
- 架构落地计划（v1）：docs/架构落地计划_v1.md
- 表结构与数据库：docs/表结构与数据库.md
- 数据库函数参考：docs/数据库函数参考.md
- 测试指南：docs/测试指南.md
- 数据质量与校验（骨架）：docs/数据质量与校验.md
- PLAYBOOKS 使用说明：docs/PLAYBOOKS/USAGE.md

## 当前程序现状（2025-08-19）

- CLI：中文帮助完善，新增日志方案B（--log-run/--log-dir）
- check-mapping：--out 导出、--show-all 聚类开关，聚类统计按站/设/指标
- db-ping：--verbose 打印 host/db/user(脱敏)/时区/版本
- 映射：已提供转换脚本，生成标准 schema 文件 config/data_mapping.v2.json
- 文档：CSV导入-使用指南 已新增“命令参考/迁移到标准schema”章节
- 运行状态：run-all 完整成功，产出 env.json 与 summary.json；source_hint v2 与分段合并已上线
  - 已修：dim_stations tz 传参类型、dim_devices.type 默认值、dim_metric_config RETURNING id；维表策略默认值完善
- 新默认：导入模式 auto（阈值 total_mb=50/per_file_mb=10/max_file_count=20 满足倾向 direct，否则 staging）；日志默认 json，可切 text；支持按模块输出；配置拆分 configs/{logging,ingest,database}.yaml（中文注释），启动打印参数与配置快照（不脱敏）

### 环境限制（重要）

- 当前开发环境数据库严禁修改任何表（结构/数据）；仅允许修改函数、视图、触发器等对象。
- 涉及写表的导入/合并请使用专用测试库/DSN；开发库仅进行 dry-run/只读验证。
- 所有 E2E 验证必须使用标准映射 config/data_mapping.v2.json。

### 重启后快速恢复步骤

1. 打开 docs/PLAYBOOKS/SESSION_SNAPSHOT_2025-08-19.md
1. 激活 .venv；db 连通：`python -m app.cli.main db-ping --verbose`
1. 检查映射：`python -m app.cli.main check-mapping config/data_mapping.v2.json --out mapping_report_v2.json --log-run`
1. 直接执行：
   `python -m app.cli.main run-all config/data_mapping.v2.json --window-start ...Z --window-end ...Z --log-run`

## 八、本地开发规范（保存即自动 + 全绿门禁）

- 保存即自动（VSCode）：

  - 需要扩展：ms-python.black-formatter、charliermarsh.ruff、emeraldwalk.runonsave
  - 自动动作：
    - Python：Black + Ruff 修复
    - Markdown：mdformat 规范化
    - PLAYBOOKS：memory_index 刷新“最近变更”和 INDEX（仅内容变化才写入）

- 提交前（pre-commit 严格）：

  - ruff、black、mypy、bandit、mdformat、check-yaml、mixed-line-ending、memory-check、memory-index
  - 本地全量体检：pre-commit run --all-files

- CI 门禁：

  - pre-commit 全绿检查（报告上传为构件 + PR 评论摘要）

## 七、知识图谱工作流（方案A）

- 目标：将 PLAYBOOKS 与 docs 的实体与关系沉淀成图谱，便于“影响面/溯源/导航”

- 存储：docs/PLAYBOOKS/知识图谱.json（含 meta.node_count/edge_count）

- 更新：python scripts/tools/kg_update.py（仅内容变化才写入；会同步统计到 PLAYBOOKS/索引.md 顶部）

- 查询：python scripts/tools/kg_query.py nodes type=Decision | edges rel=documents | neighbors id=... hops=1

- 提醒：

  - pre-commit：kg-reminder（文档变更未更新图谱→提示）、kg-diff-check（运行将产生变化→提示）

  - CI：kg-check（PR 维度的非阻断提醒，未来可开启 STRICT=1 严格模式）

  - build-test 依赖 pre-commit，通过后才跑测试/覆盖率

- 触发词（PLAYBOOKS 三步自动化）：

  - 记录变更/更新 PLAYBOOKS/保存记忆/按照 PLAYBOOKS 流程完成/记忆和文档都更新了吗？/PLAYBOOKS

## 五、运行与测试

- 配置：.env（DB_HOST/PORT/NAME/USER/PASS 等）
- 集成测试路径：tests/integration
- 对齐回归：tests/integration/test_time_alignment_and_conflict.py（同秒合并 + 整秒自检）

## 六、知识管理（PLAYBOOKS）

### 工具与自动化（PLAYBOOKS）

- 触发词：记录变更/更新 PLAYBOOKS/保存记忆/按照 PLAYBOOKS 流程完成/记忆和文档都更新了吗？/PLAYBOOKS（同义词：记录决策/记录配置变更/记录改进/记录经验教训/记录性能基准）

- 脚本：

  - memory_index.py：生成“最近变更”摘要到 docs/文档地图与导航.md（自动注入 BEGIN/END 标记区）
  - memory_check.py：pre-commit 检查当前改动应记录的类型，输出覆盖率/缺失项

- 配置：.pre-commit-config.yaml 已包含 memory-check 钩子；PR 模板要求填写 PLAYBOOKS 类型与 ID

- 触发词：记录变更/更新 PLAYBOOKS/保存记忆/按照 PLAYBOOKS 流程完成/记忆和文档都更新了吗？/PLAYBOOKS

- 三步法：1) 更新 PLAYBOOKS；2) 保存记忆；3) 同步文档

### 行为规范（MCP 快速链接）

- 使用 MCP 工具（强制）：docs/智能助手行为控制.md#使用-mcp-工具强制规则

- 严格模式-核对清单（含 MCP 勾选）：docs/严格模式-核对清单.md

- PR 模板（含 MCP 区块）：.github/PULL_REQUEST_TEMPLATE.md

- 入口：docs/PLAYBOOKS/

## 七、致谢

- 本仓库由地五班团队维护。

## 附：PLAYBOOKS 示例记录

- 决策（DECISIONS）

```
---
id: DEC-20250816-010
date: 2025-08-16
scope: time-alignment
summary: 入库 UTC 秒级对齐 + CHECK 兜底 + UPSERT 合并
---
- 背景：写入存在毫秒与时区不一致
- 决策：DB 函数统一对齐；添加 CHECK 约束；主键合并
- 影响：查询稳定性提升，冲突合并一致
```

- 配置变更（CONFIGURATION_CHANGES）

```
---
id: CONF-20250816-008
date: 2025-08-16
module: db
summary: 新增 safe_upsert_measurement_local 与对齐 CHECK 脚本
---
- 变更内容：scripts/sql/safe_upsert_measurement_local.sql、constraints_time_alignment.sql
- 回滚方案：DROP FUNCTION / DROP CONSTRAINT
```

- 改进（IMPROVEMENTS）

```
---
id: IMP-20250816-007
date: 2025-08-16
area: docs
summary: 文档统一为中文，新增导航与质量章节
---
- 痛点：文档分散且过时
- 动作：中文化与导航整合；质量与对齐规范写入
- 效果：入口统一、事实一致、可扩展
```

## 附：env.json.sources 示例（里程碑1）

- 启动命令：`python -m app.cli.main run-all ... --log-run --log-dir logs/runs/demo --log-format text --log-routing by_module`
- 产物片段（sources 标注字段来源）：

```
{
  "logging": {"format": "text", "routing": "by_module", ...},
  "sources": {"logging": {"format": "CLI", "routing": "CLI"}, "ingest": {"workers": "YAML"}, ...}
}
```

- 更多示例：见 docs/配置与快照-示例.md（里程碑1）

- 治理：见 docs/智能助手行为控制.md（AI 助手操作边界与流程）
