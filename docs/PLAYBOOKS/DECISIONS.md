# DECISIONS（决策记录）

## id: DEC-20250818-010 date: 2025-08-18 topic: ingest | logging scope: docs status: approved

- 决策：采用“方案A”目录规范与导入路径
  - 目录：app/core, app/adapters, app/services, app/cli（子层命名强制）
  - 导入：CSV→staging(UNLOGGED)→集合式合并→UTC周界窗口→背压自适应
- 列名：CSV 固定列（TagName/DataTime/DataValue），不做自动探测
- 窗口：按 ts_bucket 的 UTC ISO 周界（周一 00:00:00），窗口 \[start, end)
- 并发：默认 workers=6；背压阈值（P95>2s 或 失败率>1%）触发缩批/降并发，恢复后回升
- 配置：configs/ingest.yaml、configs/logging.yaml 统一位于 configs/ 根；CLI>ENV>YAML>默认
- 日志：仅摘要 SQL（text=summary, explain=on_error），启用 redaction，多流 runs/YYYYMMDD/\<job_id>/；上下文按文档补全
- 回滚：如需回退，恢复文档旧版本与引用，保留决策条目仅作历史
