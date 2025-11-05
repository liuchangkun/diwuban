# MCP 工具使用指南（实战版）

> 面向在本仓协作的 AI 助手与开发者，目标：更高效、更安全、更可追溯。

## 1. 工具总览（你已安装）

- Context 7：库/框架文档检索
- Playwright：网页取证（只读）
- Sequential thinking：任务分解与反思
- Postgres：只读 SQL 探针
- Time：时间/时区
- Memory：长期记忆
- TaskManager：任务流与审批

## 2. 使用原则（强制）

- 单次高信号：每阶段只做一次高质量信息获取，避免重复调用
- 安全-by-default：默认只读验证；高风险操作须授权口令并保留审计
- 逐步推进：建立任务清单，小步实施；失败≤2次退避并请求澄清
- 审计可追溯：关键操作在 PR/PLAYBOOKS 留痕（工具/目的/输入/结论）

### 2.1 强制最低要求（与 rules.yml / ide_rules.toml 对齐）

- 必用工具：Context 7 + Sequential thinking（最低要求）
- 复杂任务：必须使用 TaskManager 管理任务流（Investigate → 实施 → 验证 → 同步 → 审批）。标记完成后必须等待审批（approve_task_completion），不得跳过
- 数据库验证：必须使用 Postgres（只读查询）并以“表数据”为准进行结果确认，严禁依赖日志输出或经验判断
- 修改前置：进行任何代码/文档修改前，必须先使用 codebase-retrieval 获取上下文与受影响范围（一次高信号检索）
- 并行优先：多个互不依赖的只读操作应并行执行；存在依赖关系或可能冲突时再顺序化

### 2.2 默认工具集与按场景必用

- Context 7：获取权威库/框架 API 文档片段；二次检索需带新问题/新 topic
- Postgres（只读）：任何需要“验证/对账/统计口径确认”的场景必须使用；限制时间/对象范围，避免全表扫描
- TaskManager：当改动涉及多文件/跨层/≥3 步时，必须拆解并跟踪进度
- Memory：记录长期有效的信息（阈值、目录、命名、约定、决策）；临时信息不入库
- Time：时区/窗口换算；统一以 UTC 存储、按需本地化（Asia/Shanghai 等）
- Playwright（只读）：外部文档取证（页面版本/段落/截图），禁止登录与表单提交

### 2.3 一次高信号检索与节流

- 每个阶段仅做一次“高质量检索”，直接服务于下一步；避免同质反复
- 同一库的再次 get-library-docs 必须具备新的 topic 或新的问题焦点
- tokens 建议：满足当前推进所需即可（通常 2k–5k），避免无上限拉取
- 不确定或多解先澄清；若两次尝试仍失败，暂停并请求决策/授权

## 3. 工具分场景用法与示例

### 3.1 Context 7
- 先调用 resolve-library-id，再 get-library-docs（带 topic/tokens）
- 示例：检索“FastAPI 路由”片段用于比对
```
resolve-library-id: { libraryName: "fastapi" }
get-library-docs: { context7CompatibleLibraryID: "/tiangolo/fastapi", topic: "routing", tokens: 4000 }
```
- 注意：一次检索仅拉取推进所需的片段；同库多次检索需有新问题

### 3.2 Sequential thinking
- 触发：多文件/跨层改动；>2 次编辑/验证；用户要求计划或进度
- 用法：先建“Investigate”任务为 IN_PROGRESS；每完成一个子任务再切换状态
- 产出：方案假设→验证→修正，直到“满意+可执行”

### 3.3 Playwright（只读）
- 用途：核对外部文档版本、变更记录、下载链接；保留截图或关键信息
- 准则：只访问公开页面；避免登录/表单提交；导航→等待→截图/文本→退出
- 示例：抓取某文档页标题与版本段落
```
browser_navigate: { url: "https://example.com/docs" }
browser_snapshot: {}
```

### 3.4 Postgres（只读）
- 用途：只读查询/EXPLAIN/SHOW，验证窗口数据或 SQL 估算
- 准则：限定窗口（时间/设备），limit；严禁 DDL/DML
- 示例：
```
query_postgres: { sql: "SELECT count(*) FROM schema.table WHERE ts BETWEEN '...+08' AND '...+08' LIMIT 1;" }
```

### 3.5 Time
- 场景：窗口推导、时区换算；示例：
```
get_current_time: { timezone: "Asia/Shanghai" }
convert_time: { source_timezone: "Asia/Shanghai", time: "14:00", target_timezone: "UTC" }
```

### 3.6 Memory（长期记忆）
- 何时记：对后续协作有长期价值（阈值、目录、命名、约定、决策）
- 示例：
```
remember: { memory: "CI 覆盖率阈值为 80%，不得低于" }
```

### 3.7 TaskManager（任务与审批）
- 工作流：request_planning → get_next_task → mark_task_done → 等待 approve_task_completion → 下一个任务 → 最后 approve_request_completion
- 强约束：标记完成后必须等待审批，不得跳过

## 4. 常见红线与防误触

- 禁止：安装依赖、写数据库、访问 venv/ 与 data/、长耗时外部调用
- 禁止：直接编辑包清单；依赖变更需授权且使用包管理器命令
- 禁止：扫描 venv/ 与 data/ 目录；检索/查看仅限代码与文档目录

## 5. 任务执行模版（可复制）

1) Investigate：
- 目标：确认受影响文件/函数/配置；用 Context 7 补齐 API 细节
- 动作：view/grep-search/codebase-retrieval；必要时 Playwright 取证

2) 实施：
- 动作：str-replace-editor 小步修改（≤150 行/次）；必要时 save-file 新建

3) 验证：
- 动作：launch-process 跑单测/静态检查/最小 E2E；总结命令、cwd、退出码、关键日志

4) 同步：
- 动作：更新 docs/ 与 PLAYBOOKS；Memory 保存关键记忆

5) 审批（如启用 TaskManager）：
- 动作：mark_task_done → 等待 approve_task_completion；全部完成后 approve_request_completion

## 6. 失败与退避

- 同类操作最多两次尝试；仍失败需暂停并请求澄清/授权
- 记录失败命令与关键日志，便于排查与复盘

## 7. 并行与节流（执行配方）

- 何时并行：多个互不依赖的只读操作（view 多文件、针对不同问题的 codebase-retrieval、web-search/web-fetch 取证）
- 何时顺序：后续步骤依赖前一步产出（A 的输出决定 B 的输入）、可能冲突的同文件多处编辑
- 建议策略：
  - 先计划（列出所需信息/文件/接口），一轮批量只读调研；结束后再进入修改
  - 修改→验证→同步 分批小步推进，每次修改≤150 行；跨文件先边界确认再分步

## 8. 验证与产出规范（以“表数据”为准）

- 验证种类：单测/静态检查/最小 E2E（只读）；总结命令、cwd、退出码、关键日志
- 成功判定：退出码=0 且日志无明显错误；若失败≤2次后暂停并请求澄清/授权
- 数据库验证（只读示例）：

```sql
SELECT COUNT(*) FROM public.fact_measurements WHERE ts_bucket BETWEEN now()-interval '1 hour' AND now();
SELECT MIN(ts_bucket), MAX(ts_bucket) FROM reporting.mv_measurements_hourly;
```

- 审计与沉淀：完成后更新 docs/ 与 PLAYBOOKS；用 Memory 记录长期有效的阈值/约定/决策

## 9. 常见误用与反例

- 未做前置检索（codebase-retrieval）即直接修改
- 用日志结论替代表数据验证（Postgres 只读查询才是标准）
- 标记任务完成后未等待审批（TaskManager 流程被跳过）
- 同一库反复 get-library-docs 且无新问题/新 topic
- 直接编辑包清单/安装依赖；变更依赖不走包管理器命令
- 对外暴露内部推理全文（公开输出以结论与证据为主）

## 10. 交叉引用

- ADR：docs/ADR/ADR-2025-09-02-enable-mcp-default.md（启用 MCP 作为默认流程）
- 行为：docs/智能助手行为控制.md（使用 MCP 工具 强制规则）
- 质量门：rules/rules.yml、rules/ide_rules.toml（强制最低要求与流程阶段）
- PR 模板：.github/PULL_REQUEST_TEMPLATE.md（MCP 勾选区与豁免说明）
- 核对清单：docs/严格模式-核对清单.md（MCP 流程核对项）


