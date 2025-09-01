# 贡献指南（CONTRIBUTING）

感谢贡献！本指南与 PROJECT_RULES.md（总纲）共同构成贡献者的必读文档，所有流程与工具以当前仓库实际配置为准。

## 1. 开发前准备

- 阅读 PROJECT_RULES.md 与 docs/文档地图与导航.md（中文入口）。
- 安装 VSCode 扩展：ms-python.black-formatter、charliermarsh.ruff、emeraldwalk.runonsave。
- 本地启用 pre-commit：`pre-commit install`。

## 2. 日常开发（保存即自动）

- 保存 .py：Black + Ruff 自动格式化/修复/整理 imports。
- 保存 .md：mdformat 自动规范。
- 修改 PLAYBOOKS 或导航：自动运行 memory_index，仅在内容变化时写入“最近变更”和 INDEX。

## 3. 提交前（必须全绿）

- 运行：`pre-commit run --all-files`
- 必须全部通过：ruff、black、mypy（仅 app/|src/）、bandit（仅 app/）、check-yaml、mixed-line-ending、mdformat、memory-check、memory-index。
- 若 mdformat/black 自动修改，请一并提交。

## 4. Pull Request（PR 门禁）

- 提交 PR 后，CI 会先运行“pre-commit 全绿检查 Job”：
  - PR 会收到机器人评论，包含完整的 pre-commit 报告；
  - Actions 的 Summary 面板会显示结果摘要；
  - 也可下载 pre-commit-report.txt 工件查看全文。
- 只有 pre-commit Job 通过，后续 build-test 才会运行测试/覆盖率/安全审计。

## 5. PLAYBOOKS（记忆三步）

- 记录类型：决策记录、配置变更记录、改进与优化记录、经验教训、性能基准（docs/PLAYBOOKS/）。
- 触发词：记录变更/更新 PLAYBOOKS/保存记忆/按照 PLAYBOOKS 流程完成/记忆和文档都更新了吗？/PLAYBOOKS。
- 工具：memory-check（提示缺失类型，仅警告）、memory-index（刷新索引与“最近变更”，仅在内容变化时写入）。

## 6. 约束与边界

- 禁止读取与提交：venv/.venv、data/、明文凭据。
- 不引入 Docker/Kafka 等非必要中间件。
- 新依赖、长任务、数据库结构变更、部署操作需事前说明并征求确认。

## 7. 常用命令

- 本地全量体检：`pre-commit run --all-files`
- 刷新记忆索引：`python scripts/tools/memory_index.py`
- 运行测试：`pytest -q`（如允许长任务）

## 8. 导入模块贡献指南（强制）

- CSV 列名固定：TagName（变量名称）、DataTime（数据时间）、DataValue（数据值）；严禁自动探测/同义词
- 映射唯一来源：config/data_mapping.json；严禁从文件名/路径推断维度/指标
- 并发与背压：默认 workers=6、按 UTC 周界分窗；实现 shrink_batch/shrink_workers 与回升策略
- 日志验收：runs/YYYYMMDD/\<job_id>/ 多流齐备；字段齐备；SQL 摘要与 explain 开关键符合规范
- 测试要求：并发/背压、日志字段/开关、合并窗口边界、UPSERT 语义均需单测/集成测覆盖
- PR 要求：同步更新相关文档与 PLAYBOOKS；提供回滚方案；“完成一个函数即自查一次”

## 9. 当前程序现状与快速恢复

- 现状（2025-08-18）：
  - CLI 方案B日志开关；中文帮助完善；db-ping --verbose；check-mapping --out/--show-all 聚类
  - 标准 schema 映射：使用 config/data_mapping.v2.json（由转换脚本生成）
  - run-all 进行到 prepare-dim：
    - 已修：dim_stations tz CAST、dim_devices.type 默认 unknown
    - 待修：dim_metric_config RETURNING 列名需与实际表对齐
- 重启后恢复步骤：
  1. 打开 docs/PLAYBOOKS/SESSION_SNAPSHOT_2025-08-18.md
  1. `python -m app.cli.main db-ping --verbose`
  1. `python -m app.cli.main check-mapping config/data_mapping.v2.json --out mapping_report_v2.json --log-run`
  1. 修复 prepare_dim 的 dim_metric_config 返回列后，执行 run-all 并核对 logs/runs/<job>/sql|perf|summary

—— 本指南持续与仓库自动化保持一致。若发现不一致，请以实际 pre-commit/CI 行为为准并提交修正。
