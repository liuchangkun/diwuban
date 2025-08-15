# RUNBOOK（运行手册）

## 1. 本地运行（示例）
- 质量闸：`python scripts/quality_gate.py`
- 测试：`pytest -q`
- CLI 流程（占位）：`ingest → align → validate → derive → fit → optimize → viz`

## 2. 失败处置
- 明确阶段、参数与输入范围；读取日志中的 run_id 定位。
- 重跑策略：重复执行失败阶段或从上游阶段重跑（version+1）。

## 3. 版本与回滚
- 参数变化引起 version+1；持久化保留历史版本。
- 回滚：切换至上一个稳定 version；更新文档记录。
