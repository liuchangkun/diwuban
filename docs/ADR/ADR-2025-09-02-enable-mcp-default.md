# ADR: 启用 MCP 工具集作为默认协作流程

日期：2025-09-02
状态：Accepted

## 背景
- 本仓已引入并默认安装一组 MCP 工具：Context 7、Playwright、Sequential thinking、Postgres、Time、Memory、TaskManager。
- 目标是以“检索→规划→验证→审计”闭环降低误操作、提升效率并保证可追溯性。

## 决策
- 将 MCP 工具链确立为默认协作流程：
  1) 任务分解（TaskManager）
  2) 信息获取（Context 7）
  3) 过程管理（Sequential thinking）
  4) 只读验证（launch-process 等最小验证）
  5) 审计与知识沉淀（PLAYBOOKS + Memory）
- 对非 trivial 改动（多文件/跨层/运行命令）必须使用 MCP；纯文档小改可在 PR 模板填写豁免说明。

## 后果
- 质量门与 PR 模板将包含 MCP 勾选区，缺失时报错/警告；CI 可设置严格模式。
- 行为规范、编码规范、导航文档已加入相关链接，便于快速抵达。

## 备选方案
- 自由选择是否使用 MCP：被否决，原因是较难形成一致的安全与审计闭环。

## 关联
- docs/智能助手行为控制.md
- docs/MCP工具使用指南.md
- .github/PULL_REQUEST_TEMPLATE.md
- scripts/quality_gate.py

