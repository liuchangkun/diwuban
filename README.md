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
