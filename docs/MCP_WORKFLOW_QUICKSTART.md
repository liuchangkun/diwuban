# MCP_WORKFLOW 快速上手（团队一页版）

目标：用最少的规则获得最高的效率与质量。

## 必做 5 条
1) 先建任务清单：从 Investigate 开始，保持只有 1 个任务处于 IN_PROGRESS。
2) 信息收集高信号优先：view/grep 限范围；retrieval 用于“找不着北”。
3) 小步编辑：仅用 str_replace_editor/save-file，每块 ≤ 150 行；先看再改。
4) 验证要落地：用户要求“确保/验证”就真的跑命令，给出 exit code + 核心日志。
5) PR 自检：运行 `python scripts/quality_gate.py`，按模板勾选所有项（含 MCP_WORKFLOW）。

## 禁忌 5 条
- 不能广撒网搜索；
- 不能没确认签名就改调用；
- 不能全文件替换或大块重写；
- 不能未授权安装依赖/改数据库/部署；
- 不能访问 venv/.venv/env；

## 工具选择
- view：看文件/目录、定位段落；`search_query_regex` 查单文件符号。
- grep-search：跨文件精准搜，限制范围。
- codebase-retrieval：不知道文件在哪时用。
- str_replace_editor/save-file：唯一编辑方式。
- launch-process：执行命令（wait=true 短命令；wait=false 长进程）。

## PR 清单（最小版）
- [ ] 任务清单使用合规（单一 IN_PROGRESS）
- [ ] 工具调用少而准（理由充分）
- [ ] 编辑小步可回滚（≤150 行）
- [ ] 运行验证并给出摘要
- [ ] 质量闸通过（quality_gate + 必要测试）
- [ ] 文档与代码一致（必要子文档已更新）

