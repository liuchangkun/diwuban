# PR 标题

请简述本次改动的目的与范围。

## 规则合规清单（PROJECT_RULES 索引 + 子文档）
- [ ] DATA_SPEC（docs/DATA_SPEC.md）
- [ ] SCHEMA_AND_DB（docs/SCHEMA_AND_DB.md）
- [ ] ALIGNMENT_POLICY（docs/ALIGNMENT_POLICY.md）
- [ ] QUALITY_VALIDATION（docs/QUALITY_VALIDATION.md）
- [ ] DERIVATIONS（docs/DERIVATIONS.md）
- [ ] FITTING_MODELS（docs/FITTING_MODELS.md）
- [ ] OPTIMIZATION（docs/OPTIMIZATION.md）
- [ ] VIZ_SPEC（docs/VIZ_SPEC.md）
- [ ] ENGINEERING_STANDARDS（docs/ENGINEERING_STANDARDS.md）
- [ ] RUNBOOK（docs/RUNBOOK.md）
- [ ] TESTING_STRATEGY（docs/TESTING_STRATEGY.md）
- [ ] GLOSSARY（docs/GLOSSARY.md）
- [ ] ADR 变更（如 docs/ADR/ADR-0001-docs-structure.md）
- [ ] MCP_WORKFLOW（docs/MCP_WORKFLOW.md）

## 自检项
- [ ] 未访问 venv/.venv 目录
- [ ] 数据文件来源全部由 config/data_mapping.json 驱动
- [ ] 若变更对齐/派生/拟合策略，已增加 version 并更新文档

## 文档/经验库更新
- [ ] 若为修复类 PR：已在 docs/PLAYBOOKS/ERROR_FIX_LOG.md 添加条目（附链接）
- [ ] 若为改进类 PR：已在 docs/PLAYBOOKS/IMPROVEMENTS.md 添加条目（附链接）
- [ ] 如属重大设计变更：已新增/更新 ADR（附链接）

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
