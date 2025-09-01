# PR 标题

请简述本次改动的目的与范围。

> 变更说明（必填）：Why/What/Impact/Risk/Rollback + 受影响对象清单（文件/函数）

## 规则合规清单（PROJECT_RULES 索引 + 子文档）

- [ ] 文档地图与导航（docs/文档地图与导航.md）
- [ ] 表结构与数据库（docs/表结构与数据库.md）
- [ ] 数据库函数参考（docs/数据库函数参考.md）
- [ ] 数据质量与校验（docs/数据质量与校验.md）
- [ ] 泵站时间对齐实现（docs/泵站时间对齐实现.md）
- [ ] 项目技术选型（docs/项目技术选型.md）
- [ ] 测试指南（docs/测试指南.md）
- [ ] 体系结构总览（docs/体系结构总览.md）
- [ ] 架构落地计划_v1（docs/架构落地计划_v1.md）
- [ ] 扩展文档（如 数据清理指南/可视化/泵组优化 等）

## 自检项

- [ ] pre-commit 全绿（本地 `pre-commit run --all-files` 通过）
- [ ] PLAYBOOKS 已更新（并已刷新“最近变更”与 INDEX）
- [ ] 文档已对齐（与数据库/脚本一致；必要时更新 docs/ 与 README 索引）
- [ ] 未访问 venv/.venv 目录
- [ ] 数据库/日志配置：仅 YAML 来源（configs/database.yaml、configs/logging.yaml）；无 ENV/CLI/代码覆盖；无 DSN 拼接
- [ ] 数据文件来源全部由 config/data_mapping.json 驱动
- [ ] 若变更对齐/派生/拟合策略，已增加 version 并更新文档

## 文档/经验库更新（中文化与 PLAYBOOKS 要求）

- [ ] 关联 PLAYBOOKS 类型与 ID：DEC / CONF / IMP / LES / BENCH（例如 DEC-20250816-010）
- [ ] 链接中文记录文档：docs/PLAYBOOKS/决策记录.md / 配置变更记录.md / 改进与优化记录.md / 经验教训.md / 性能基准.md
- [ ] 如属重大设计变更：已新增/更新 ADR（附链接）

## 默认不跟踪目录提醒（重要）

- ProjectDocs/ 与 data/ 默认不纳入版本控制与索引；如确需提交，请在此说明原因与范围，并提供豁免说明：
  - [ ] 本次 PR 需要提交 ProjectDocs/ 或 data/（已说明豁免与影响）

## 修复/改进自检

- [ ] 回归测试已新增/更新（简述用例）
- 严重性：Sev1 / Sev2 / Sev3 / Sev4
- 根因类型：实现缺陷 / 需求缺陷 / 配置 / 数据 / 并发 / 时区 / 单位 / 其他
- 监控/告警：无需 / 已更新（简述）

## 如何验证

- 运行质量闸脚本：`python scripts/quality_gate.py`（需 Python 3.9+）
- 运行测试：`pytest -q`（可选）

## 影响范围

- 受影响模块：
- 风险与回滚方案：

## 严格模式核对（必选）

- [ ] 已按 docs/严格模式-核对清单.md 全部自检完成（含“仅 YAML 来源”核对项与 sources 快照核对）
- [ ] 已遵循 docs/智能助手行为控制.md，无高风险未授权操作
- [ ] 重要变更已更新 PLAYBOOKS 与相关文档，并保存关键记忆

## E2E 验证与产物（必选）

- [ ] 最小窗口命令已提供（text/by_module）：

## 知识图谱（可选）

- [ ] 本 PR 涉及 PLAYBOOKS/文档更新，已运行 kg_update.py 并确认已提交知识图谱.json
- [ ] 影响面简述（可粘贴 kg_query.py 输出或列出关键节点/关系）

## 【必选】MCP 默认工具确认

- [ ] 已使用 Context 7 进行库/框架文档检索与 API/方案核对（或在下方说明豁免原因）
- [ ] 已使用 Sequential thinking 进行任务分解与反思验证（或在下方说明豁免原因）
- 豁免说明（如未使用上述工具，请简述原因与替代措施；需提供替代验证证据与风险评估）：

## MCP 使用（必选）

- [ ] 已使用 MCP 进行任务分解与验证（Investigate→实施→验证→文档/PLAYBOOKS）

- [ ] 附关键 MCP 验证命令与结果摘要（exit code、关键日志）

- [ ] 若未使用 MCP：说明豁免理由（仅文档/极小变更）

  - 示例：`python -m app.cli.main run-all config/data_mapping.v2.json --window-start ...Z --window-end ...Z --log-run --log-dir logs/runs/pr-verify --log-format text --log-routing by_module --log-level INFO`

- [ ] env.json 核验：包含 args_summary/config_snapshot/sources/ts/run_id/run_dir

- [ ] 附上代表性日志（可粘贴 2–3 行）：

  - logs/modules/sql.log：db.exec.succeeded 或 failed（含 sql_op/target_table/affected_rows/sql_cost_ms）
  - logs/modules/root.log：align.merge.window 或 ingest.copy.batch

## 日志与诊断产物链接（推荐）

- 运行目录：logs/runs/\<日期>/\<时间-pid>/（或 by_module 模式日志路径）
- 关键产物：
  - env.json（args_summary/config_snapshot/sources/ts/run_id/run_dir）
  - app.ndjson/sql.ndjson/perf.ndjson
  - summary.json（含 rows_total/rows_merged/rows_per_sec/duration_ms/backpressure_count/slow_sql_top/diagnostics）
- 建议附：
  - 2–3 行代表性日志（db.exec.succeeded、align.merge.window、ingest.load.progress）
  - slow_sql_top 中 Top-1 的 sql_cost_ms/affected_rows 摘要
