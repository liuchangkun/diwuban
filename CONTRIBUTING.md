# CONTRIBUTING
> 快速上手与文档索引
>
> - MCP 快速上手（1 页）：docs/MCP_WORKFLOW_QUICKSTART.md
> - MCP 全文规范：docs/MCP_WORKFLOW.md（含流程图）
> - 总纲与索引：PROJECT_RULES.md
> - 子文档：
>   - 数据文件规范：docs/DATA_SPEC.md
>   - 表结构与数据库：docs/SCHEMA_AND_DB.md
>   - 时间与网格对齐策略：docs/ALIGNMENT_POLICY.md
>   - 数据质量与校验：docs/QUALITY_VALIDATION.md
>   - 派生量与公式：docs/DERIVATIONS.md
>   - 特性曲线拟合：docs/FITTING_MODELS.md
>   - 泵组优化：docs/OPTIMIZATION.md
>   - 可视化规范：docs/VIZ_SPEC.md
>   - 工程与编码规范：docs/ENGINEERING_STANDARDS.md
>   - 运行手册：docs/RUNBOOK.md
>   - 测试策略：docs/TESTING_STRATEGY.md
>   - 术语表：docs/GLOSSARY.md
>


感谢贡献！为确保质量与一致性，请遵循以下要求。

## 工作流程
1. 阅读 `PROJECT_RULES.md` 并确认适用范围。
2. 创建任务：Investigate → Plan → Implement → Validate → Report。
3. 在 PR 中填写 `.github/PULL_REQUEST_TEMPLATE.md` 的“规则合规清单”。
4. 提交前运行：
   - `python scripts/quality_gate.py`
   - （可选）`pytest -q`

## 规则遵循（强制）
- R1.1：数据来源只能通过 `config/data_mapping.json`，严禁硬编码 `data/` 路径。
- R3：时间对齐遵循“站内优先、最近邻+容差、累计量禁插值”的策略；默认时区 Asia/Shanghai，入库以 UTC。
- R5：必须执行数据质量检查（范围/非递减/离群/交叉校验），不通过不得进入后续阶段。
- R10：所有步骤可重跑且可追溯，必要时增加 `version`。

## 代码规范
- Python 版本 ≥ 3.9。
- 目录结构：后续实现会提供 `src/`、`tests/`、`scripts/` 等标准布局。
- 日志：使用结构化日志（json 或 key=value），记录输入参数、时间范围、版本与统计指标。

## 本地开发建议
- 使用虚拟环境（但仓库与工具不会读取 venv/.venv）。
- 使用 `rules/rules.yml` 管理机读规则参数。

## 联系
- 对 RULES 有疑问或需要豁免，请先在 PR 里说明并标注对应条目（例如 R3.2）。

