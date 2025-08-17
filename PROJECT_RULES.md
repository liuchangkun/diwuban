# 项目规则（总纲）

本文件是工程“唯一行为准则”的总纲。详细内容以 docs/文档地图与导航.md 为入口，所有开发、运维与文档必须与该地图保持一致。

- 本地开发规范：见 README.md 中“本地开发规范（保存即自动 + 全绿门禁）”。

## 1. 基本原则

- 唯一事实源：数据库与 scripts/sql；文档与实现不一致时，以数据库/脚本为准，并立刻修文档追平。
- 文档中文化：统一用中文命名与书写，入口为 docs/文档地图与导航.md。
- 不读目录：venv/.venv 与 data/ 禁止被索引/读取/提交。
- 变更可追溯：所有重要变更用 PLAYBOOKS 记录，并由工具自动汇总“最近变更”。

## 2. 技术选型（现状）

- PostgreSQL 16（不使用 TimescaleDB）
- 调度：APScheduler（不使用 Windows 计划任务）
- 中间件：不使用 Docker/Kafka；可选 Redis 3.0.504（轻量任务/状态缓存）

## 3. 数据与入库边界（事实为准）

- 时区与对齐：所有写入 UTC，整秒对齐（ts_bucket = date_trunc('second', ts_utc)）。
- 主键与合并：PRIMARY KEY(station_id, device_id, metric_id, ts_bucket)，同秒 UPSERT。
- 兜底约束：CHECK(date_trunc('second', ts_bucket) = ts_bucket)。
- 分区：fact_measurements 按周 RANGE 分区；活跃分区维护必要索引。
- 函数边界：safe_upsert_measurement（UTC）、safe_upsert_measurement_local（本地时间 + 站点时区）。
- 详细表/索引/CRUD 优化：参见 docs/文档地图与导航.md 中“表结构与数据库/数据库函数参考/性能优化”等。

## 4. 工程质量与自动化（强制）

- 本地 pre-commit（严格并默认启用）：
  - ruff、black、mypy（仅 app/|src/）、bandit（仅 app/，忽略 B101/B404/B603/B607）、check-yaml、mixed-line-ending、mdformat（严格）、memory-check、memory-index。
  - 目标：提交前必须全绿；mdformat/black 的自动修改应一并提交。
- VSCode 保存即自动：
  - Python：Black + Ruff（保存即格式化/修复/整理 imports）。
  - Markdown：mdformat 规范化。
  - 记忆：保存 PLAYBOOKS 或导航文档时自动运行 memory_index（仅内容变化才写入）。
- CI 门禁：
  - pre-commit 全绿检查 Job：生成报告工件，并在 PR 下自动评论完整报告、Actions Summary 输出摘要。
  - build-test Job 依赖 pre-commit，通过后再执行测试/覆盖率/安全审计。

## 5. PLAYBOOKS（决策/经验/变更/基准）

- 位置：docs/PLAYBOOKS/（决策记录、配置变更记录、改进与优化记录、经验教训、性能基准）。
- 记录格式：统一使用中文；ID 形如 TYPE-YYYYMMDD-SEQ，例如 DEC-20250816-009。
- 工具：
  - memory-check：在 pre-commit 中提示本次改动应记录的类型与覆盖率（仅警告）。
  - memory-index：在 pre-commit 中刷新“最近变更（自动生成）”与 PLAYBOOKS/INDEX.md；仅在内容变化时写入；与 mdformat 兼容。

## 6. 提交流程（DoD）

- 本地保存即自动格式化与索引。
- 撰写/更新必要文档与 PLAYBOOKS 记录。
- pre-commit run --all-files 全绿。
- Push/PR 后，确保 CI 的 pre-commit Job 通过；如失败，请在 PR 页面查看“评论中的完整报告”和“Actions Summary 摘要”并修复。

## 7. 禁止事项与边界

- 禁止提交或读取：venv/.venv、data/、明文凭据。
- 禁止引入与项目无关的服务（Docker/Kafka 等）。
- 需要明确授权的操作：安装新依赖、长时任务、数据库结构变更、部署操作。

## 8. 文档体系（索引）

- 以 docs/文档地图与导航.md 为唯一入口。
- 常见主题（示例）：体系结构、表结构与数据库、数据库函数参考、泵站时间对齐实现、测试指南、性能优化、附录等。

—— 本文件作为“总纲”。细节请以导航文档链接到的子文档为准，并保持与实现一致。
