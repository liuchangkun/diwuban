# ERROR_FIX_LOG（错误与修复记录）

目的：沉淀错误根因与修复方法，防止重犯，提升效率。

## 记录模板（复制使用）
---
id: FIX-YYYYMMDD-001
date: YYYY-MM-DD
module: ingest | align | validate | derive | fit | optimize | viz | infra | docs
severity: Sev1 | Sev2 | Sev3 | Sev4
root_cause: impl | requirement | config | data | concurrency | timezone | unit | boundary | other
tests_added: true | false
pr: ''
adr: ''
tags: [ 'encoding', 'csv', 'ingest' ]
---

- 标题：一句话描述问题
- 背景：发生场景与影响
- 复现步骤：最小复现路径
- 根因分析：技术与流程层面
- 修复方案：修改点、验证步骤、回归测试
- 预防措施：新增检查/脚本/文档/工具
- 参考链接：PR/Issue/日志/文档

## 示例
---
id: FIX-20250815-001
date: 2025-08-15
module: ingest
severity: Sev3
root_cause: encoding
tests_added: true
pr: ''
adr: ''
tags: [ 'encoding', 'csv', 'ingest' ]
---

- 标题：UTF-8 解析失败导致文件跳过
- 背景：部分 CSV 为 GBK 编码，入库失败比率升高
- 复现步骤：使用该 CSV 运行 ingest
- 根因分析：仅尝试 UTF-8 未做回退
- 修复方案：加入编码探测与 GBK 回退；增加质量闸校验
- 预防措施：DATA_SPEC 明确编码策略；在单测覆盖该场景
- 参考链接：docs/DATA_SPEC.md, scripts/quality_gate.py

